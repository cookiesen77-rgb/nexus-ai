"""
上下文窗口 - 管理对话上下文
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .token_counter import TokenCounter, TokenUsage, count_tokens


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """对话消息"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = count_tokens(self.content)
    
    def to_dict(self) -> Dict[str, str]:
        """转换为LLM API格式"""
        return {"role": self.role, "content": self.content}


@dataclass
class WindowState:
    """窗口状态"""
    total_tokens: int = 0
    message_count: int = 0
    compressed: bool = False
    compression_count: int = 0
    oldest_message_time: Optional[datetime] = None
    newest_message_time: Optional[datetime] = None


class ContextWindow:
    """
    上下文窗口管理器
    
    管理对话历史，支持自动压缩和Token限制
    """
    
    def __init__(
        self,
        max_tokens: int = 8000,
        reserve_tokens: int = 2000,
        compression_threshold: float = 0.8,
        model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        初始化上下文窗口
        
        Args:
            max_tokens: 最大Token数
            reserve_tokens: 预留给输出的Token数
            compression_threshold: 触发压缩的阈值 (0-1)
            model: 使用的模型
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.compression_threshold = compression_threshold
        self.available_tokens = max_tokens - reserve_tokens
        
        self.counter = TokenCounter(model)
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
        
        self._compressor = None
        self._compression_count = 0
    
    def set_system_message(self, content: str) -> int:
        """
        设置系统消息
        
        Args:
            content: 系统消息内容
            
        Returns:
            int: Token数
        """
        self.system_message = Message(
            role=MessageRole.SYSTEM.value,
            content=content
        )
        return self.system_message.token_count
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> int:
        """
        添加消息
        
        Args:
            role: 消息角色
            content: 消息内容
            metadata: 元数据
            
        Returns:
            int: 当前总Token数
        """
        msg = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        return self.get_total_tokens()
    
    def add_user_message(self, content: str) -> int:
        """添加用户消息"""
        return self.add_message(MessageRole.USER.value, content)
    
    def add_assistant_message(self, content: str) -> int:
        """添加助手消息"""
        return self.add_message(MessageRole.ASSISTANT.value, content)
    
    def add_tool_message(self, content: str, tool_call_id: str = None) -> int:
        """添加工具消息"""
        return self.add_message(
            MessageRole.TOOL.value,
            content,
            metadata={"tool_call_id": tool_call_id}
        )
    
    def get_messages(self) -> List[Dict[str, str]]:
        """
        获取所有消息 (LLM API格式)
        
        Returns:
            List[Dict]: 消息列表
        """
        result = []
        
        if self.system_message:
            result.append(self.system_message.to_dict())
        
        for msg in self.messages:
            result.append(msg.to_dict())
        
        return result
    
    def get_total_tokens(self) -> int:
        """获取当前总Token数"""
        total = 0
        
        if self.system_message:
            total += self.system_message.token_count
        
        for msg in self.messages:
            total += msg.token_count
        
        # 消息格式开销
        total += len(self.messages) * 4 + 2
        
        return total
    
    def get_usage_ratio(self) -> float:
        """获取Token使用率"""
        return self.get_total_tokens() / self.available_tokens
    
    def needs_compression(self) -> bool:
        """检查是否需要压缩"""
        return self.get_usage_ratio() >= self.compression_threshold
    
    async def compress_if_needed(self) -> bool:
        """
        如需要则压缩上下文
        
        Returns:
            bool: 是否执行了压缩
        """
        if not self.needs_compression():
            return False
        
        await self._compress()
        return True
    
    async def _compress(self):
        """执行压缩"""
        if len(self.messages) < 4:
            # 消息太少，直接删除最早的消息
            if self.messages:
                self.messages.pop(0)
            return
        
        # 导入压缩器 (延迟导入避免循环依赖)
        if self._compressor is None:
            from .compressor import ContextCompressor
            self._compressor = ContextCompressor()
        
        # 保留最近的消息
        keep_count = max(2, len(self.messages) // 3)
        old_messages = self.messages[:-keep_count]
        recent_messages = self.messages[-keep_count:]
        
        # 压缩旧消息
        if old_messages:
            summary = await self._compressor.compress(old_messages)
            
            # 用摘要替换旧消息
            summary_msg = Message(
                role=MessageRole.SYSTEM.value,
                content=f"[Previous conversation summary]\n{summary}",
                metadata={"compressed": True, "original_count": len(old_messages)}
            )
            
            self.messages = [summary_msg] + recent_messages
            self._compression_count += 1
    
    def trim_to_fit(self, target_tokens: int = None) -> int:
        """
        裁剪消息以适应Token限制
        
        Args:
            target_tokens: 目标Token数，默认为available_tokens的80%
            
        Returns:
            int: 删除的消息数
        """
        target = target_tokens or int(self.available_tokens * 0.8)
        removed = 0
        
        while self.get_total_tokens() > target and len(self.messages) > 1:
            # 保留最后一条消息
            self.messages.pop(0)
            removed += 1
        
        return removed
    
    def get_state(self) -> WindowState:
        """获取窗口状态"""
        return WindowState(
            total_tokens=self.get_total_tokens(),
            message_count=len(self.messages),
            compressed=self._compression_count > 0,
            compression_count=self._compression_count,
            oldest_message_time=self.messages[0].timestamp if self.messages else None,
            newest_message_time=self.messages[-1].timestamp if self.messages else None
        )
    
    def get_token_usage(self) -> TokenUsage:
        """获取Token使用情况"""
        return TokenUsage(
            input_tokens=self.get_total_tokens(),
            output_tokens=0,
            total_tokens=self.get_total_tokens()
        )
    
    def clear(self):
        """清空消息历史"""
        self.messages = []
        self._compression_count = 0
    
    def __len__(self) -> int:
        return len(self.messages)
    
    def __repr__(self) -> str:
        return f"ContextWindow(messages={len(self.messages)}, tokens={self.get_total_tokens()})"

