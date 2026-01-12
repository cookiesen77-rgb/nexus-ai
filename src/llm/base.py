"""
LLM 客户端抽象基类

定义所有LLM客户端的通用接口，支持：
- 消息补全
- 工具调用
- 流式响应
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class StopReason(Enum):
    """LLM停止原因"""
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"


@dataclass
class ToolCall:
    """工具调用信息"""
    id: str
    name: str
    parameters: Dict[str, Any]


@dataclass
class Message:
    """消息结构"""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None  # 用于工具结果消息


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    stop_reason: StopReason
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = ""
    raw_response: Optional[Any] = None

    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return len(self.tool_calls) > 0


@dataclass
class LLMConfig:
    """LLM配置"""
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    
    # 模型切换支持
    thinking_model: Optional[str] = None  # 思考模型名称
    thinking_mode: bool = False  # 是否启用思考模式
    
    def get_active_model(self) -> str:
        """获取当前活跃模型"""
        if self.thinking_mode and self.thinking_model:
            return self.thinking_model
        return self.model


class BaseLLM(ABC):
    """LLM客户端抽象基类"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.model = config.model

    @abstractmethod
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
            tools: 可用工具列表（可选）
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大token数（可选，覆盖默认值）

        Returns:
            LLMResponse: LLM响应
        """
        pass

    @abstractmethod
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
            tools: 可用工具列表（可选）

        Yields:
            str: 响应文本片段
        """
        pass

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False
    ) -> Dict[str, Any]:
        """
        格式化工具调用结果为消息格式

        Args:
            tool_call_id: 工具调用ID
            result: 工具执行结果
            is_error: 是否为错误结果

        Returns:
            Dict: 格式化的消息
        """
        content = str(result) if not isinstance(result, str) else result
        if is_error:
            content = f"Error: {content}"

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

    @staticmethod
    def create_message(role: str, content: str) -> Dict[str, Any]:
        """创建标准消息格式"""
        return {"role": role, "content": content}

    @staticmethod
    def create_system_message(content: str) -> Dict[str, Any]:
        """创建系统消息"""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(content: str) -> Dict[str, Any]:
        """创建用户消息"""
        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> Dict[str, Any]:
        """创建助手消息"""
        return {"role": "assistant", "content": content}

