"""
OpenAI 兼容 LLM 客户端

支持 GPT 系列和任何 OpenAI 兼容的中转API
"""

import os
from typing import Any, Dict, List, Optional, AsyncIterator

from openai import OpenAI, AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseLLM, LLMConfig, LLMResponse, StopReason, ToolCall


class OpenAICompatLLM(BaseLLM):
    """OpenAI 兼容 LLM 客户端"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        # 初始化客户端，支持中转API
        client_kwargs = {"api_key": config.api_key}
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        self.client = OpenAI(**client_kwargs)
        self.async_client = AsyncOpenAI(**client_kwargs)

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
        # 准备请求参数
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        # 转换工具格式为OpenAI格式
        if tools:
            request_params["tools"] = self._convert_tools_to_openai_format(tools)

        # 发送请求
        response = await self.async_client.chat.completions.create(**request_params)

        # 解析响应
        return self._parse_response(response)

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
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": True,
        }

        if tools:
            request_params["tools"] = self._convert_tools_to_openai_format(tools)

        stream = await self.async_client.chat.completions.create(**request_params)

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

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
        request_params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        if tools:
            request_params["tools"] = self._convert_tools_to_openai_format(tools)

        response = self.client.chat.completions.create(**request_params)
        return self._parse_response(response)

    def _convert_tools_to_openai_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将Claude工具格式转换为OpenAI格式

        Claude格式:
        {
            "name": "tool_name",
            "description": "...",
            "input_schema": {...}
        }

        OpenAI格式:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        openai_tools = []
        for tool in tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", tool.get("parameters", {}))
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools

    def _parse_response(self, response) -> LLMResponse:
        """解析OpenAI API响应"""
        choice = response.choices[0]
        message = choice.message

        # 提取内容
        content = message.content or ""

        # 提取工具调用
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                import json
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        parameters=json.loads(tc.function.arguments)
                    )
                )

        # 解析停止原因
        finish_reason = choice.finish_reason
        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "tool_calls": StopReason.TOOL_USE,
            "length": StopReason.MAX_TOKENS,
        }
        stop_reason = stop_reason_map.get(finish_reason, StopReason.END_TURN)

        # 使用统计
        usage = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

        return LLMResponse(
            content=content,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            usage=usage,
            model=response.model,
            raw_response=response
        )

    async def achat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        异步聊天方法 - complete 的简化别名
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLMResponse: LLM响应
        """
        return await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        同步聊天方法 - complete_sync 的简化别名
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            LLMResponse: LLM响应
        """
        return self.complete_sync(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """
        格式化工具调用结果为OpenAI消息格式
        """
        content = str(result) if not isinstance(result, str) else result
        if is_error:
            content = f"Error: {content}"

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content
        }


def create_openai_client(
    model: str = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    thinking_model: Optional[str] = None,
    thinking_mode: bool = False
) -> OpenAICompatLLM:
    """
    创建OpenAI兼容客户端的便捷函数

    Args:
        model: 模型名称 (默认使用doubao)
        api_key: API密钥
        base_url: API基础URL（中转API使用）
        temperature: 温度参数
        max_tokens: 最大token数
        thinking_model: 思考模型名称
        thinking_mode: 是否启用思考模式

    Returns:
        OpenAICompatLLM: OpenAI兼容客户端实例
    """
    # 默认使用ALLAPI配置
    default_model = model or os.getenv("LLM_DEFAULT_MODEL", "doubao-seed-1-8-251228")
    default_thinking = thinking_model or os.getenv("LLM_THINKING_MODEL", "doubao-seed-1-8-251228-thinking")
    
    config = LLMConfig(
        model=default_model,
        api_key=api_key or os.getenv("ALLAPI_KEY", os.getenv("OPENAI_API_KEY", "")),
        base_url=base_url or os.getenv("ALLAPI_BASE_URL", "https://nexusapi.cn/v1"),
        temperature=temperature,
        max_tokens=max_tokens,
        thinking_model=default_thinking,
        thinking_mode=thinking_mode
    )
    return OpenAICompatLLM(config)


def create_allapi_client(
    thinking_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> OpenAICompatLLM:
    """
    创建ALLAPI客户端的便捷函数
    
    Args:
        thinking_mode: 是否启用思考模式
        temperature: 温度参数
        max_tokens: 最大token数
    
    Returns:
        OpenAICompatLLM: ALLAPI客户端实例
    """
    return create_openai_client(
        model=os.getenv("LLM_DEFAULT_MODEL", "grok-4.1"),
        thinking_model=os.getenv("LLM_THINKING_MODEL", "grok-4.1"),
        thinking_mode=thinking_mode,
        temperature=temperature,
        max_tokens=max_tokens
    )

