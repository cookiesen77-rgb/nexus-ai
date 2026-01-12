"""
图像生成 Provider
使用 Gemini API 通过 ALLAPI 进行图像生成
"""

import os
import base64
import logging
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageProvider(ABC):
    """图像生成 Provider 基类"""
    
    @abstractmethod
    async def generate_image(
        self, 
        prompt: str, 
        reference_images: Optional[List[str]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        生成图像
        
        Args:
            prompt: 图像描述
            reference_images: 参考图像（base64 或 URL）
            
        Returns:
            生成的图像 base64 字符串，失败返回 None
        """
        pass
    
    @abstractmethod
    async def edit_image(
        self,
        original_image: str,
        edit_prompt: str,
        mask_image: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        编辑图像
        
        Args:
            original_image: 原始图像 base64
            edit_prompt: 编辑指令
            mask_image: 可选的遮罩图像 base64
            
        Returns:
            编辑后的图像 base64 字符串
        """
        pass


class GeminiImageProvider(ImageProvider):
    """
    Gemini 图像生成 Provider
    使用 gemini-3-pro-image-preview 模型（支持宽高比控制和4K清晰度）
    
    参考: https://nexusapi.cn
    """
    
    # 升级到 gemini-3-pro-image-preview - 支持 aspectRatio 和更高清晰度
    DEFAULT_API_URL = "https://nexusapi.cn/v1beta/models/gemini-3-pro-image-preview:generateContent"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: str = "gemini-3-pro-image-preview",  # 升级到更高质量模型
        timeout: int = 180,
        output_dir: Optional[str] = None
    ):
        # Security: never ship a default key in code; require env var to be set.
        self.api_key = api_key or os.environ.get("ALLAPI_KEY") or os.environ.get("GEMINI_API_KEY")
        # 注意：现在可由 LSY 配置中心（ppt.image）动态提供 api_key/api_url，
        # 因此这里不强制要求环境变量一定存在（避免启动即崩溃）。
        self.api_url = api_url or self.DEFAULT_API_URL
        self.model = model
        self.timeout = timeout
        self.output_dir = output_dir or "/Users/mac/Desktop/manus/uploads/ppt_images"
        
        # 确保输出目录存在
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    async def generate_image(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        生成 PPT 幻灯片图像
        
        Args:
            prompt: 图像描述
            reference_images: 参考图像列表
            **kwargs: 额外参数
                - aspect_ratio: 宽高比，支持 "16:9", "4:3", "1:1" 等
                - temperature: 温度参数
        """
        
        api_key = self.api_key
        api_url = self.api_url
        timeout = self.timeout

        if not api_key:
            return None
        if not api_url:
            return None

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # 构建内容
        parts = []
        
        # 添加参考图像
        if reference_images:
            for ref_img in reference_images[:3]:  # 最多 3 张参考图
                if ref_img.startswith("data:"):
                    # 已经是 data URL
                    mime_type = ref_img.split(";")[0].split(":")[1]
                    img_data = ref_img.split(",")[1]
                elif ref_img.startswith("http"):
                    # URL，需要下载
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(ref_img)
                            img_data = base64.b64encode(resp.content).decode()
                            mime_type = resp.headers.get("content-type", "image/png")
                    except Exception as e:
                        logger.warning(f"下载参考图像失败: {e}")
                        continue
                else:
                    # 假设是 base64
                    img_data = ref_img
                    mime_type = "image/png"
                
                parts.append({
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": img_data
                    }
                })
        
        # 添加文本提示 - 增强 PPT 专用描述
        enhanced_prompt = self._enhance_ppt_prompt(prompt)
        parts.append({"text": enhanced_prompt})
        
        # 构建生成配置 - 使用官方 imageConfig 参数
        # 参考: https://ai.google.dev/gemini-api/docs/image-generation?hl=zh-cn
        
        # 获取参数
        aspect_ratio = kwargs.get("aspect_ratio", "16:9")
        image_size = kwargs.get("image_size", "1K")  # 支持 "1K", "2K", "4K"
        
        generation_config = {
            "temperature": kwargs.get("temperature", 1.0),
            "topP": kwargs.get("top_p", 0.95),
            "responseModalities": ["TEXT", "IMAGE"],
            # gemini-3-pro-image-preview 专用 imageConfig 参数
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size  # 1K=1376x768, 2K=2752x1536, 4K=5504x3072 (16:9)
            }
        }
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"调用 Gemini Image API, prompt 长度: {len(prompt)}")
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 提取图像
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            return part["inlineData"].get("data")
                
                logger.warning("Gemini Image API 未返回图像")
                return None
                
        except httpx.TimeoutException:
            logger.error("Gemini Image API 调用超时")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini Image API HTTP 错误: {e.response.status_code}, {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Gemini Image API 调用失败: {e}")
            return None
    
    def _enhance_ppt_prompt(self, prompt: str) -> str:
        """
        增强 PPT 图片生成的提示词
        添加 PPT 专业设计要求
        """
        ppt_enhancement = """【PPT幻灯片设计要求】
- 专业演示文稿页面，画面清晰锐利
- 文字必须清晰可读，字体大小适中
- 使用专业配色方案，色彩协调
- 布局美观，视觉层次分明
- 适当使用装饰性图形或图标
- 禁止模糊、失真或低质量元素

"""
        return ppt_enhancement + prompt
    
    async def edit_image(
        self,
        original_image: str,
        edit_prompt: str,
        mask_image: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """编辑图像"""
        
        # 构建带有原图的提示
        parts = []
        
        # 添加原图
        if original_image.startswith("data:"):
            mime_type = original_image.split(";")[0].split(":")[1]
            img_data = original_image.split(",")[1]
        else:
            img_data = original_image
            mime_type = "image/png"
        
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": img_data
            }
        })
        
        # 添加编辑指令
        parts.append({
            "text": f"请根据以下要求修改这张图片：{edit_prompt}"
        })
        
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 1.0),
                "topP": kwargs.get("top_p", 0.95),
                "responseModalities": ["TEXT", "IMAGE"],
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "candidates" in result and len(result["candidates"]) > 0:
                    parts = result["candidates"][0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            return part["inlineData"].get("data")
                
                return None
                
        except Exception as e:
            logger.error(f"Gemini Image Edit API 调用失败: {e}")
            return None
    
    def save_image(self, image_base64: str, filename: str) -> str:
        """保存图像到文件"""
        filepath = Path(self.output_dir) / filename
        
        # 解码并保存
        image_data = base64.b64decode(image_base64)
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return str(filepath)


def get_image_provider(
    provider_type: str = "gemini",
    **kwargs
) -> ImageProvider:
    """获取图像生成 Provider"""
    if provider_type == "gemini":
        return GeminiImageProvider(**kwargs)
    else:
        raise ValueError(f"不支持的 provider 类型: {provider_type}")

