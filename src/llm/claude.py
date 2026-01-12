"""
Claude LLM 客户端

支持 Claude 4.5 Sonnet 和中转API
"""

import os
from typing import Any, Dict, List, Optional, AsyncIterator

from anthropic import Anthropic, AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseLLM, LLMConfig, LLMResponse, StopReason, ToolCall


class ClaudeLLM(BaseLLM):
    """Claude LLM 客户端"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        # 初始化客户端，支持中转API
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = Anthropic(**client_kwargs)
        self.async_client = AsyncAnthropic(**client_kwargs)

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
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成补全响应

        Args:
            messages: 消息列表
            tools: 可用工具列表
            temperature: 温度参数
            max_tokens: 最大token数
            system: 系统提示词

        Returns:
            LLMResponse: LLM响应
        """
        # 准备请求参数
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        # 添加系统提示词
        if system:
            request_params["system"] = system

        # 添加工具
        if tools:
            request_params["tools"] = tools

        # 发送请求
        response = await self.async_client.messages.create(**request_params)

        # 解析响应
        return self._parse_response(response)

    async def complete_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        流式生成补全响应

        Args:
            messages: 消息列表
            tools: 可用工具列表
            system: 系统提示词

        Yields:
            str: 响应文本片段
        """
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        if system:
            request_params["system"] = system

        if tools:
            request_params["tools"] = tools

        async with self.async_client.messages.stream(**request_params) as stream:
            async for text in stream.text_stream:
                yield text

    def complete_sync(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步生成补全响应（用于测试或简单场景）
        """
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        if system:
            request_params["system"] = system

        if tools:
            request_params["tools"] = tools

        response = self.client.messages.create(**request_params)
        return self._parse_response(response)

    def _parse_response(self, response) -> LLMResponse:
        """解析Claude API响应"""
        # 提取文本内容
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        parameters=block.input
                    )
                )

        # 解析停止原因
        stop_reason_map = {
            "end_turn": StopReason.END_TURN,
            "tool_use": StopReason.TOOL_USE,
            "max_tokens": StopReason.MAX_TOKENS,
            "stop_sequence": StopReason.STOP_SEQUENCE,
        }
        stop_reason = stop_reason_map.get(response.stop_reason, StopReason.END_TURN)

        # 使用统计
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }

        return LLMResponse(
            content=content,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            raw_response=response
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """
        格式化工具调用结果为Claude消息格式

        Claude使用特定的tool_result格式
        """
        content = str(result) if not isinstance(result, str) else result

        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": content,
                    "is_error": is_error
                }
            ]
        }


def create_claude_client(
    model: str = "claude-sonnet-4-5-20250514",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> ClaudeLLM:
    """
    创建Claude客户端的便捷函数

    Args:
        model: 模型名称
        api_key: API密钥，默认从环境变量读取
        base_url: API基础URL（中转API使用）
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        ClaudeLLM: Claude客户端实例
    """
    config = LLMConfig(
        model=model,
        api_key=api_key or os.getenv("CLAUDE_API_KEY", ""),
        base_url=base_url or os.getenv("CLAUDE_BASE_URL"),
        temperature=temperature,
        max_tokens=max_tokens
    )
    return ClaudeLLM(config)

