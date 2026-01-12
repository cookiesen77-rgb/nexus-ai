"""
文本生成 Provider
使用 Gemini API 通过 ALLAPI 进行文本生成
"""

import os
import json
import logging
import httpx
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class TextProvider(ABC):
    """文本生成 Provider 基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def generate_json(self, prompt: str, **kwargs) -> Dict:
        """生成 JSON 格式的文本"""
        pass


class GeminiTextProvider(TextProvider):
    """
    Gemini 文本生成 Provider
    使用 gemini-3-pro-preview 模型
    """
    
    DEFAULT_API_URL = "https://nexusapi.cn/v1beta/models/gemini-3-pro-preview:generateContent"
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: str = "gemini-3-pro-preview",
        timeout: int = 120
    ):
        # Security: never ship a default key in code; require env var to be set.
        self.api_key = api_key or os.environ.get("ALLAPI_KEY") or os.environ.get("GEMINI_API_KEY")
        # 注意：现在可由 LSY 配置中心（ppt.text）动态提供 api_key/api_url，
        # 因此这里不强制要求环境变量一定存在（避免启动即崩溃）。
        self.api_url = api_url or self.DEFAULT_API_URL
        self.model = model
        self.timeout = timeout
    
    def _filter_thinking(self, text: str) -> str:
        """过滤掉 Gemini 的思考文本"""
        import re
        
        # 思考标记模式
        thinking_patterns = [
            r'<thinking>.*?</thinking>',
            r'\[thinking\].*?\[/thinking\]',
            r'Let me think.*?\n',
            r'I\'m considering.*?\n',
            r'My thought process.*?\n',
            r'\*\*Formulating.*?\*\*',
            r'\*\*Defining.*?\*\*',
            r'\*\*Structuring.*?\*\*',
            r'\*\*Planning.*?\*\*',
            r'\*\*Analyzing.*?\*\*',
            r'Okay,.*?\n',
            r'Here\'s my.*?\n',
        ]
        
        result = text
        for pattern in thinking_patterns:
            result = re.sub(pattern, '', result, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理多余空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        api_key = self.api_key
        api_url = self.api_url
        timeout = self.timeout

        if not api_key:
            raise ValueError("Missing ALLAPI_KEY.")
        if not api_url:
            raise ValueError("Missing request_url.")

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 60),
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"调用 Gemini Text API, prompt 长度: {len(prompt)}")
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                if "candidates" in result and len(result["candidates"]) > 0:
                    text = result["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return self._filter_thinking(text)
                else:
                    error_msg = result.get("error", {}).get("message", "未知错误")
                    logger.error(f"Gemini Text API 响应异常: {error_msg}")
                    return ""
                    
        except httpx.TimeoutException:
            logger.error("Gemini Text API 调用超时")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini Text API HTTP 错误: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Gemini Text API 调用失败: {e}")
            raise
    
    async def generate_json(self, prompt: str, **kwargs) -> Dict:
        """生成 JSON 格式的文本"""
        import re
        
        # 在 prompt 中添加 JSON 格式要求
        json_prompt = f"""{prompt}

请严格按照 JSON 格式输出，不要包含任何其他文字或 markdown 标记。"""
        
        text = await self.generate(json_prompt, **kwargs)
        
        # 尝试提取 JSON
        try:
            # 清理 markdown 代码块
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r'^```\w*\n?', '', text)
                text = re.sub(r'\n?```$', '', text)
            
            # 查找 JSON 数组或对象
            json_match = re.search(r'[\[\{][\s\S]*[\]\}]', text)
            if json_match:
                return json.loads(json_match.group())
            
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, 原始文本: {text[:200]}")
            return {}


def get_text_provider(
    provider_type: str = "gemini",
    **kwargs
) -> TextProvider:
    """获取文本生成 Provider"""
    if provider_type == "gemini":
        return GeminiTextProvider(**kwargs)
    else:
        raise ValueError(f"不支持的 provider 类型: {provider_type}")

