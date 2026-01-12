"""
Agent间消息协议

定义Agent之间通信的消息格式
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MessageType(Enum):
    """消息类型"""
    # 请求类型
    REQUEST = "request"
    PLAN_REQUEST = "plan_request"
    EXECUTE_REQUEST = "execute_request"
    VERIFY_REQUEST = "verify_request"
    
    # 响应类型
    RESPONSE = "response"
    PLAN_RESPONSE = "plan_response"
    EXECUTE_RESPONSE = "execute_response"
    VERIFY_RESPONSE = "verify_response"
    
    # 反馈类型
    FEEDBACK = "feedback"
    ERROR = "error"
    
    # 控制类型
    ABORT = "abort"
    RETRY = "retry"
    REPLAN = "replan"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentMessage:
    """Agent间消息"""
    id: str = field(default_factory=lambda: str(uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    message_type: MessageType = MessageType.REQUEST
    content: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # 关联的请求ID
    metadata: Dict[str, Any] = field(default_factory=dict)

    def create_response(
        self,
        content: Dict[str, Any],
        message_type: Optional[MessageType] = None
    ) -> "AgentMessage":
        """
        创建响应消息
        
        Args:
            content: 响应内容
            message_type: 消息类型
            
        Returns:
            AgentMessage: 响应消息
        """
        return AgentMessage(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=message_type or MessageType.RESPONSE,
            content=content,
            correlation_id=self.id,
            priority=self.priority
        )

    def create_error(self, error: str) -> "AgentMessage":
        """创建错误消息"""
        return AgentMessage(
            from_agent=self.to_agent,
            to_agent=self.from_agent,
            message_type=MessageType.ERROR,
            content={"error": error},
            correlation_id=self.id,
            priority=MessagePriority.HIGH
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }


class MessageBus:
    """消息总线"""

    def __init__(self):
        self._messages: List[AgentMessage] = []
        self._handlers: Dict[str, List[callable]] = {}

    def send(self, message: AgentMessage) -> None:
        """
        发送消息
        
        Args:
            message: 要发送的消息
        """
        self._messages.append(message)
        
        # 通知订阅者
        if message.to_agent in self._handlers:
            for handler in self._handlers[message.to_agent]:
                handler(message)

    def subscribe(self, agent_name: str, handler: callable) -> None:
        """
        订阅消息
        
        Args:
            agent_name: Agent名称
            handler: 消息处理函数
        """
        if agent_name not in self._handlers:
            self._handlers[agent_name] = []
        self._handlers[agent_name].append(handler)

    def unsubscribe(self, agent_name: str, handler: callable) -> None:
        """取消订阅"""
        if agent_name in self._handlers:
            self._handlers[agent_name].remove(handler)

    def get_messages(
        self,
        to_agent: Optional[str] = None,
        message_type: Optional[MessageType] = None
    ) -> List[AgentMessage]:
        """
        获取消息
        
        Args:
            to_agent: 目标Agent
            message_type: 消息类型
            
        Returns:
            List[AgentMessage]: 匹配的消息列表
        """
        messages = self._messages
        
        if to_agent:
            messages = [m for m in messages if m.to_agent == to_agent]
        
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        return messages

    def get_pending_messages(self, agent_name: str) -> List[AgentMessage]:
        """获取待处理消息"""
        return [
            m for m in self._messages
            if m.to_agent == agent_name and not m.metadata.get("processed")
        ]

    def mark_processed(self, message_id: str) -> None:
        """标记消息已处理"""
        for m in self._messages:
            if m.id == message_id:
                m.metadata["processed"] = True
                break

    def clear(self) -> None:
        """清空消息"""
        self._messages.clear()


# 便捷函数
def create_plan_request(
    from_agent: str,
    task: str,
    context: Dict[str, Any] = None
) -> AgentMessage:
    """创建规划请求"""
    return AgentMessage(
        from_agent=from_agent,
        to_agent="planner",
        message_type=MessageType.PLAN_REQUEST,
        content={
            "task": task,
            "context": context or {}
        }
    )


def create_execute_request(
    from_agent: str,
    plan: Dict[str, Any],
    step_id: Optional[str] = None
) -> AgentMessage:
    """创建执行请求"""
    return AgentMessage(
        from_agent=from_agent,
        to_agent="executor",
        message_type=MessageType.EXECUTE_REQUEST,
        content={
            "plan": plan,
            "step_id": step_id
        }
    )


def create_verify_request(
    from_agent: str,
    result: Any,
    expected: str,
    step_id: str
) -> AgentMessage:
    """创建验证请求"""
    return AgentMessage(
        from_agent=from_agent,
        to_agent="verifier",
        message_type=MessageType.VERIFY_REQUEST,
        content={
            "result": result,
            "expected": expected,
            "step_id": step_id
        }
    )

