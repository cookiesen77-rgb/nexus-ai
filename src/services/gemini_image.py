"""
Gemini 图片生成客户端
支持参考图片（ref_images）功能，用于风格参考

重要区分：
- generate_illustration: 生成配图（独立图像，不含文字，用于 PPT 页面的插图区域）
- generate_slide_background: 生成背景图（已废弃，改用配图模式）
"""

import asyncio
import base64
import logging
import os
from io import BytesIO
from typing import Optional, List, Union
from PIL import Image
import httpx

logger = logging.getLogger(__name__)


class GeminiImageClient:
    """
    Gemini 图片生成 API 客户端
    
    支持：
    - 纯文本 prompt 生成图片
    - 带参考图片（ref_images）的风格化生成
    - 多种宽高比
    """
    
    API_URL = "https://nexusapi.cn/v1beta/models/gemini-2.5-flash-image:generateContent"
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        # 注意：现在可由 LSY 配置中心（ppt.image / design.image）动态提供 api_key/api_url，
        # 因此这里不强制要求环境变量一定存在（避免启动即崩溃）。
        self.api_key = api_key or os.getenv("ALLAPI_KEY", "")
        self.api_url = api_url or self.API_URL
        self.timeout = 180  # 增加超时时间，复杂生成可能需要更长
    
    def _image_to_base64(self, image: Union[Image.Image, str, bytes]) -> tuple:
        """
        将图片转换为 base64 格式
        
        Args:
            image: PIL Image、文件路径或字节数据
            
        Returns:
            (base64_data, mime_type) 元组
        """
        if isinstance(image, str):
            # 文件路径
            with open(image, "rb") as f:
                image_bytes = f.read()
            # 检测格式
            if image.lower().endswith('.png'):
                mime_type = "image/png"
            elif image.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"
            return base64.b64encode(image_bytes).decode(), mime_type
        
        elif isinstance(image, bytes):
            # 字节数据
            return base64.b64encode(image).decode(), "image/png"
        
        elif isinstance(image, Image.Image):
            # PIL Image
            buffer = BytesIO()
            # 转换为 RGB 模式（如果是 RGBA）
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            image.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode(), "image/png"
        
        else:
            raise ValueError(f"不支持的图片类型: {type(image)}")
    
    async def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[Union[Image.Image, str, bytes]]] = None,
        aspect_ratio: str = "16:9"
    ) -> dict:
        """
        生成图片（支持参考图片）
        
        Args:
            prompt: 图片描述提示词
            ref_images: 参考图片列表（用于风格参考）
            aspect_ratio: 宽高比，如 "16:9", "1:1", "4:3"
            
        Returns:
            {
                "success": bool,
                "text": str,  # AI 返回的文本
                "image_base64": str,  # base64 编码的图片
                "mime_type": str,  # 图片 MIME 类型
                "error": str  # 错误信息（如果有）
            }
        """
        api_key = self.api_key
        api_url = self.api_url
        timeout = self.timeout

        if not api_key:
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": "Missing ALLAPI_KEY.",
            }
        if not api_url:
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": "Missing request_url.",
            }

        headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
        
        # 构建 parts 列表
        parts = []
        
        # 添加参考图片（如果有）
        if ref_images:
            for i, ref_img in enumerate(ref_images):
                try:
                    img_base64, mime_type = self._image_to_base64(ref_img)
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": img_base64
                        }
                    })
                    logger.debug(f"添加参考图片 {i+1}, mime: {mime_type}")
                except Exception as e:
                    logger.warning(f"处理参考图片 {i+1} 失败: {e}")
        
        # 添加文本 prompt
        parts.append({"text": prompt})
        
        payload = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"调用 Gemini API, prompt 长度: {len(prompt)}, 参考图片数: {len(ref_images) if ref_images else 0}")
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return self._parse_response(result)
                
        except httpx.TimeoutException:
            logger.error("Gemini API 调用超时")
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": "API 调用超时，请重试"
            }
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except:
                pass
            logger.error(f"Gemini API HTTP 错误: {e.response.status_code}, {error_detail}")
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": f"API 错误: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"Gemini API 调用失败: {e}")
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": str(e)
            }
    
    def _parse_response(self, result: dict) -> dict:
        """解析 Gemini API 响应"""
        text_response = ""
        image_base64 = ""
        mime_type = ""
        
        try:
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                for part in parts:
                    if "text" in part:
                        text_response = part["text"]
                    elif "inlineData" in part:
                        inline_data = part["inlineData"]
                        mime_type = inline_data.get("mimeType", "image/png")
                        image_base64 = inline_data.get("data", "")
                
                if image_base64:
                    return {
                        "success": True,
                        "text": text_response,
                        "image_base64": image_base64,
                        "mime_type": mime_type,
                        "error": ""
                    }
                else:
                    return {
                        "success": False,
                        "text": text_response,
                        "image_base64": "",
                        "mime_type": "",
                        "error": "响应中没有图片数据"
                    }
            else:
                # 检查是否有错误信息
                error_msg = "响应格式异常"
                if "error" in result:
                    error_msg = result["error"].get("message", error_msg)
                return {
                    "success": False,
                    "text": "",
                    "image_base64": "",
                    "mime_type": "",
                    "error": error_msg
                }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "image_base64": "",
                "mime_type": "",
                "error": f"解析响应失败: {e}"
            }
    
    async def generate_slide_background(
        self,
        topic: str,
        slide_title: str,
        slide_content: str,
        template_style: str = "modern",
        template_image: Optional[Union[Image.Image, str, bytes]] = None,
        aspect_ratio: str = "16:9"
    ) -> dict:
        """
        为幻灯片生成背景图片
        
        Args:
            topic: PPT 主题
            slide_title: 幻灯片标题
            slide_content: 幻灯片内容
            template_style: 模板风格
            template_image: 模板参考图片（可选）
            aspect_ratio: 宽高比
            
        Returns:
            生成结果字典
        """
        # 根据模板风格构建提示词
        style_prompts = {
            "modern": "professional business style, blue gradient, clean geometric patterns, corporate aesthetic",
            "minimal": "minimalist academic style, white background, subtle gray accents, clean and simple",
            "creative": "creative vibrant style, purple and pink gradients, dynamic shapes, energetic",
            "nature": "natural organic style, green tones, leaves or natural elements, eco-friendly",
            "dark": "dark tech style, deep blue or black background, neon accents, futuristic"
        }
        
        style_desc = style_prompts.get(template_style, style_prompts["modern"])
        
        # 如果有模板图片，使用参考生成模式
        if template_image:
            prompt = f"""Based on the style and design language of the reference image, create a presentation slide.

Topic: {topic}
Slide Title: {slide_title}
Content Theme: {slide_content[:300] if slide_content else 'General'}

Requirements:
- Follow the color scheme and design style of the reference image
- Render the title "{slide_title}" prominently
- Include the key points from the content
- {aspect_ratio} aspect ratio, 4K resolution
- Professional presentation design
- Text should be clear and readable
- Do NOT copy text from the reference image"""
            
            ref_images = [template_image]
        else:
            # 无模板图片，使用纯文本生成
            prompt = f"""Create a professional presentation slide background image.

Topic: {topic}
Slide Title: {slide_title}
Content Theme: {slide_content[:200] if slide_content else 'General'}

Style Requirements:
- {style_desc}
- Clean, professional look suitable for presentations
- NO TEXT in the image (text will be overlaid separately)
- High contrast suitable for projection
- {aspect_ratio} aspect ratio
- Leave space in the center for text overlay
- Subtle and not distracting from the content

The image should be a background that complements the topic without being too busy or distracting."""
            
            ref_images = None
        
        return await self.generate_image(prompt, ref_images, aspect_ratio)
    
    async def edit_image(
        self,
        edit_instruction: str,
        current_image: Union[Image.Image, str, bytes],
        additional_refs: Optional[List[Union[Image.Image, str, bytes]]] = None
    ) -> dict:
        """
        编辑现有图片
        
        Args:
            edit_instruction: 编辑指令
            current_image: 当前图片
            additional_refs: 额外的参考图片
            
        Returns:
            生成结果字典
        """
        ref_images = [current_image]
        if additional_refs:
            ref_images.extend(additional_refs)
        
        prompt = f"""Edit this presentation slide image based on the following instruction:

{edit_instruction}

Requirements:
- Maintain the original design style and color scheme
- Keep the overall layout similar
- Only make the changes specified in the instruction
- Ensure text remains readable
- 16:9 aspect ratio"""
        
        return await self.generate_image(prompt, ref_images, "16:9")
    
    async def generate_illustration(
        self,
        topic: str,
        slide_title: str,
        slide_content: str,
        illustration_theme: str = "",
        style: str = "professional",
        aspect_ratio: str = "16:9"
    ) -> dict:
        """
        为 PPT 页面生成配图（重要：这是配图，不是整个 PPT 页面！）
        
        配图是独立的插图/图像，将放置在 PPT 页面的某个区域，
        与文字内容并排显示。配图不应包含任何文字。
        
        Args:
            topic: PPT 主题
            slide_title: 幻灯片标题
            slide_content: 幻灯片内容
            illustration_theme: 配图主题描述（如"人工智能"、"数据增长"）
            style: 风格 (professional, creative, minimal, tech, nature)
            aspect_ratio: 宽高比，默认 16:9
            
        Returns:
            生成结果字典
        """
        from src.services.ppt_prompts import get_illustration_prompt
        
        prompt = get_illustration_prompt(
            topic=topic,
            slide_title=slide_title,
            slide_content=slide_content,
            illustration_theme=illustration_theme,
            style=style
        )
        
        logger.info(f"生成配图: 主题={topic}, 标题={slide_title}, 配图主题={illustration_theme}")
        
        return await self.generate_image(
            prompt=prompt,
            ref_images=None,  # 配图不使用参考图
            aspect_ratio=aspect_ratio
        )
    
    async def generate_illustration_batch(
        self,
        slides_info: List[dict],
        topic: str,
        style: str = "professional",
        aspect_ratio: str = "16:9",
        progress_callback: Optional[callable] = None
    ) -> List[dict]:
        """
        批量生成多张配图
        
        Args:
            slides_info: 幻灯片信息列表，每项包含:
                - title: 标题
                - content: 内容
                - needs_illustration: 是否需要配图
                - illustration_theme: 配图主题
            topic: PPT 主题
            style: 风格
            aspect_ratio: 宽高比
            progress_callback: 进度回调 (current, total, message)
            
        Returns:
            生成结果列表
        """
        results = []
        total = len(slides_info)
        
        for i, slide_info in enumerate(slides_info):
            # 检查是否需要配图
            if not slide_info.get("needs_illustration", True):
                results.append({
                    "success": True,
                    "image_base64": "",
                    "skipped": True,
                    "reason": "该页面不需要配图"
                })
                continue
            
            if progress_callback:
                await progress_callback(
                    i, total,
                    f"正在为第 {i+1}/{total} 页生成配图..."
                )
            
            result = await self.generate_illustration(
                topic=topic,
                slide_title=slide_info.get("title", ""),
                slide_content=slide_info.get("content", ""),
                illustration_theme=slide_info.get("illustration_theme", ""),
                style=style,
                aspect_ratio=aspect_ratio
            )
            
            results.append(result)
            
            # 短暂延迟，避免 API 限流
            await asyncio.sleep(0.5)
        
        if progress_callback:
            await progress_callback(total, total, "配图生成完成")
        
        return results


# 全局实例
_gemini_client: Optional[GeminiImageClient] = None


def get_gemini_client() -> GeminiImageClient:
    """获取 Gemini 客户端单例"""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiImageClient()
    return _gemini_client
