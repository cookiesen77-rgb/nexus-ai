"""
Gemini LLM 客户端

支持 Gemini 3 Pro Preview 和其他 Gemini 模型
通过 ALLAPI 中转站调用
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, AsyncIterator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseLLM, LLMConfig, LLMResponse, StopReason, ToolCall

logger = logging.getLogger(__name__)


class GeminiLLM(BaseLLM):
    """Gemini LLM 客户端"""

    # Gemini API 配置
    DEFAULT_MODEL = "gemini-3-pro-preview"
    DEFAULT_API_URL = "https://nexusapi.cn/v1beta/models"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("ALLAPI_KEY", "")
        if not self.api_key:
            raise ValueError("Missing ALLAPI_KEY for GeminiLLM.")
        self.base_url = config.base_url or self.DEFAULT_API_URL
        self.timeout = 120  # Gemini 可能需要较长时间

    def _get_api_url(self, model: str = None) -> str:
        """获取 API URL"""
        model_name = model or self.model
        return f"{self.base_url}/{model_name}:generateContent"

    def _convert_messages_to_gemini_format(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将 OpenAI 格式的消息转换为 Gemini 格式

        OpenAI 格式:
        [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]

        Gemini 格式:
        [{"role": "user", "parts": [{"text": "Hello"}]}, {"role": "model", "parts": [{"text": "Hi"}]}]
        """
        gemini_messages = []
        system_instruction = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 处理系统消息 - Gemini 使用 systemInstruction
            if role == "system":
                system_instruction = content
                continue

            # 角色映射
            gemini_role = "model" if role == "assistant" else "user"

            # 处理内容
            parts = []
            if isinstance(content, str):
                parts.append({"text": content})
            elif isinstance(content, list):
                # 处理多模态内容
                for item in content:
                    if isinstance(item, str):
                        parts.append({"text": item})
                    elif isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append({"text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            # 处理图片
                            image_url = item.get("image_url", {})
                            url = image_url.get("url", "")
                            if url.startswith("data:"):
                                # Base64 图片
                                import re
                                match = re.match(r"data:([^;]+);base64,(.+)", url)
                                if match:
                                    mime_type, data = match.groups()
                                    parts.append({
                                        "inlineData": {
                                            "mimeType": mime_type,
                                            "data": data
                                        }
                                    })
                            else:
                                # URL 图片
                                parts.append({
                                    "fileData": {
                                        "mimeType": "image/jpeg",
                                        "fileUri": url
                                    }
                                })

            if parts:
                gemini_messages.append({
                    "role": gemini_role,
                    "parts": parts
                })

        return gemini_messages, system_instruction

    def _convert_tools_to_gemini_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将工具转换为 Gemini 格式

        Gemini 格式:
        {
            "functionDeclarations": [
                {
                    "name": "tool_name",
                    "description": "...",
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            ]
        }
        """
        function_declarations = []
        for tool in tools:
            # 支持多种输入格式
            if "function" in tool:
                # OpenAI 格式
                func = tool["function"]
                function_declarations.append({
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "parameters": func.get("parameters", {})
                })
            else:
                # Claude/自定义格式
                function_declarations.append({
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", tool.get("parameters", {}))
                })

        return [{"functionDeclarations": function_declarations}] if function_declarations else []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成补全响应

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            LLMResponse: LLM响应
        """
        # 转换消息格式
        gemini_messages, system_instruction = self._convert_messages_to_gemini_format(messages)

        # 构建请求体
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature or self.config.temperature,
                "maxOutputTokens": max_tokens or self.config.max_tokens,
            }
        }

        # 添加系统指令
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # 添加工具
        if tools:
            payload["tools"] = self._convert_tools_to_gemini_format(tools)

        # 请求头
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # 发送请求
        url = self._get_api_url()
        logger.info(f"调用 Gemini API: {url}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

        # 解析响应
        return self._parse_response(result)

    async def complete_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成补全响应

        Args:
            messages: 消息列表
            tools: 可用工具列表

        Yields:
            str: 响应文本片段
        """
        # 转换消息格式
        gemini_messages, system_instruction = self._convert_messages_to_gemini_format(messages)

        # 构建请求体
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if tools:
            payload["tools"] = self._convert_tools_to_gemini_format(tools)

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # 流式 API URL
        url = f"{self.base_url}/{self.model}:streamGenerateContent?alt=sse"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "candidates" in chunk:
                                for candidate in chunk["candidates"]:
                                    content = candidate.get("content", {})
                                    for part in content.get("parts", []):
                                        if "text" in part:
                                            yield part["text"]
                        except json.JSONDecodeError:
                            continue

    def complete_sync(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步生成补全响应
        """
        import asyncio
        return asyncio.run(self.complete(messages, tools, temperature, max_tokens, **kwargs))

    def _parse_response(self, result: Dict[str, Any]) -> LLMResponse:
        """解析 Gemini API 响应"""
        content = ""
        tool_calls = []
        stop_reason = StopReason.END_TURN

        # 提取候选响应
        candidates = result.get("candidates", [])
        if candidates:
            candidate = candidates[0]
            content_obj = candidate.get("content", {})
            parts = content_obj.get("parts", [])

            for part in parts:
                # 文本内容
                if "text" in part:
                    content += part["text"]

                # 工具调用
                if "functionCall" in part:
                    func_call = part["functionCall"]
                    tool_calls.append(
                        ToolCall(
                            id=f"call_{len(tool_calls)}",
                            name=func_call.get("name", ""),
                            parameters=func_call.get("args", {})
                        )
                    )

            # 解析停止原因
            finish_reason = candidate.get("finishReason", "STOP")
            finish_reason_map = {
                "STOP": StopReason.END_TURN,
                "MAX_TOKENS": StopReason.MAX_TOKENS,
                "SAFETY": StopReason.END_TURN,
                "RECITATION": StopReason.END_TURN,
                "OTHER": StopReason.END_TURN,
            }
            stop_reason = finish_reason_map.get(finish_reason, StopReason.END_TURN)

            # 如果有工具调用，设置为 TOOL_USE
            if tool_calls:
                stop_reason = StopReason.TOOL_USE

        # 使用统计
        usage = {}
        usage_metadata = result.get("usageMetadata", {})
        if usage_metadata:
            usage = {
                "input_tokens": usage_metadata.get("promptTokenCount", 0),
                "output_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0)
            }

        return LLMResponse(
            content=content,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            usage=usage,
            model=self.model,
            raw_response=result
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """
        格式化工具调用结果为 Gemini 消息格式
        """
        content = str(result) if not isinstance(result, str) else result
        if is_error:
            content = f"Error: {content}"

        return {
            "role": "user",
            "parts": [{
                "functionResponse": {
                    "name": tool_call_id,
                    "response": {
                        "result": content
                    }
                }
            }]
        }


def create_gemini_client(
    model: str = "gemini-3-pro-preview",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192
) -> GeminiLLM:
    """
    创建 Gemini 客户端的便捷函数

    Args:
        model: 模型名称
        api_key: API密钥
        base_url: API基础URL
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        GeminiLLM: Gemini客户端实例
    """
    config = LLMConfig(
        model=model,
        api_key=api_key or GeminiLLM.DEFAULT_API_KEY,
        base_url=base_url or GeminiLLM.DEFAULT_API_URL,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return GeminiLLM(config)

