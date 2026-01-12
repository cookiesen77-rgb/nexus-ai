"""
上下文管理模块

提供对话上下文窗口管理、Token计数、上下文压缩等功能
"""

from .token_counter import (
    TokenCounter,
    TokenUsage,
    ModelConfig,
    MODEL_CONFIGS,
    ConversationTokenTracker,
    get_token_counter,
    count_tokens,
    count_message_tokens
)

from .window import (
    ContextWindow,
    Message,
    MessageRole,
    WindowState
)

from .compressor import (
    ContextCompressor,
    IncrementalCompressor,
    CompressionResult,
    compress_text
)


__all__ = [
    # Token计数
    "TokenCounter",
    "TokenUsage",
    "ModelConfig",
    "MODEL_CONFIGS",
    "ConversationTokenTracker",
    "get_token_counter",
    "count_tokens",
    "count_message_tokens",
    
    # 上下文窗口
    "ContextWindow",
    "Message",
    "MessageRole",
    "WindowState",
    
    # 压缩
    "ContextCompressor",
    "IncrementalCompressor",
    "CompressionResult",
    "compress_text",
]

