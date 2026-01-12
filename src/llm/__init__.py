"""
LLM 模块

提供统一的LLM客户端接口，支持：
- Doubao (豆包) - ALLAPI中转
- 默认模型和思考模型切换
- 工具调用
"""

from .base import (
    BaseLLM,
    LLMConfig,
    LLMResponse,
    StopReason,
    ToolCall,
    Message
)
from .claude import ClaudeLLM, create_claude_client
from .openai_compat import OpenAICompatLLM, create_openai_client, create_allapi_client
from .gemini import GeminiLLM, create_gemini_client
from .model_switcher import (
    ModelSwitcher,
    ModelConfig,
    get_model_switcher,
    set_model_switcher,
    enable_thinking_mode,
    disable_thinking_mode,
    get_current_model
)

__all__ = [
    # 基类
    "BaseLLM",
    "LLMConfig",
    "LLMResponse",
    "StopReason",
    "ToolCall",
    "Message",
    
    # Claude (保留兼容)
    "ClaudeLLM",
    "create_claude_client",
    
    # OpenAI兼容 / ALLAPI
    "OpenAICompatLLM",
    "create_openai_client",
    "create_allapi_client",
    
    # Gemini
    "GeminiLLM",
    "create_gemini_client",
    
    # 模型切换器
    "ModelSwitcher",
    "ModelConfig",
    "get_model_switcher",
    "set_model_switcher",
    "enable_thinking_mode",
    "disable_thinking_mode",
    "get_current_model",
]
