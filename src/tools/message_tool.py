"""
消息交互工具

用于Agent与用户之间的结构化通信
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseTool, ToolResult, ToolStatus


class MessageType(str, Enum):
    """消息类型"""
    INFO = "info"           # 信息通知
    ASK = "ask"             # 请求输入
    RESULT = "result"       # 任务结果
    PROGRESS = "progress"   # 进度更新
    WARNING = "warning"     # 警告
    ERROR = "error"         # 错误


class SuggestedAction(str, Enum):
    """建议操作"""
    NONE = "none"
    CONFIRM = "confirm"
    INPUT = "input"
    CHOOSE = "choose"
    TAKEOVER_BROWSER = "takeover_browser"


@dataclass
class Attachment:
    """附件"""
    type: str  # 'file', 'image', 'link'
    name: str
    path: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None


@dataclass
class AgentMessage:
    """Agent消息"""
    id: str
    type: MessageType
    content: str
    attachments: List[Attachment] = field(default_factory=list)
    suggested_action: SuggestedAction = SuggestedAction.NONE
    options: List[str] = field(default_factory=list)  # For CHOOSE action
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MessageQueue:
    """消息队列"""
    
    def __init__(self):
        self._messages: List[AgentMessage] = []
        self._pending_response: Optional[str] = None
        self._response_received = False
    
    def add_message(self, message: AgentMessage):
        """添加消息"""
        self._messages.append(message)
    
    def get_messages(self, limit: int = 50) -> List[AgentMessage]:
        """获取消息"""
        return self._messages[-limit:]
    
    def clear(self):
        """清空消息"""
        self._messages.clear()
    
    def set_response(self, response: str):
        """设置用户响应"""
        self._pending_response = response
        self._response_received = True
    
    def get_response(self) -> Optional[str]:
        """获取用户响应"""
        response = self._pending_response
        self._pending_response = None
        self._response_received = False
        return response
    
    def is_waiting_response(self) -> bool:
        """是否在等待响应"""
        if self._messages:
            last_msg = self._messages[-1]
            return last_msg.suggested_action != SuggestedAction.NONE and not self._response_received
        return False


# 全局消息队列
_message_queue = MessageQueue()


def get_message_queue() -> MessageQueue:
    """获取消息队列"""
    return _message_queue


class MessageTool(BaseTool):
    """
    消息交互工具
    
    用于向用户发送消息、请求输入、展示结果
    """
    
    name = "message"
    description = "Communication tool for sending messages and requesting user input"
    parameters = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["info", "ask", "result", "progress", "warning", "error"],
                "description": "Type of message"
            },
            "content": {
                "type": "string",
                "description": "Message content"
            },
            "attachments": {
                "type": "array",
                "description": "File attachments",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["file", "image", "link"]},
                        "name": {"type": "string"},
                        "path": {"type": "string"},
                        "url": {"type": "string"}
                    }
                }
            },
            "suggested_action": {
                "type": "string",
                "enum": ["none", "confirm", "input", "choose", "takeover_browser"],
                "description": "Suggested action for user"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Options for choose action"
            }
        },
        "required": ["type", "content"]
    }
    
    async def execute(
        self,
        type: str,
        content: str,
        attachments: List[Dict[str, Any]] = None,
        suggested_action: str = "none",
        options: List[str] = None
    ) -> ToolResult:
        """发送消息"""
        import uuid
        
        try:
            message = AgentMessage(
                id=str(uuid.uuid4())[:8],
                type=MessageType(type),
                content=content,
                attachments=[
                    Attachment(
                        type=a.get('type', 'file'),
                        name=a.get('name', ''),
                        path=a.get('path'),
                        url=a.get('url')
                    )
                    for a in (attachments or [])
                ],
                suggested_action=SuggestedAction(suggested_action),
                options=options or []
            )
            
            queue = get_message_queue()
            queue.add_message(message)
            
            # 如果需要用户响应，等待
            if suggested_action != "none":
                # 在实际实现中，这里应该通过WebSocket通知前端
                # 并等待用户响应
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Message sent, waiting for user response",
                    data={
                        'message_id': message.id,
                        'type': type,
                        'waiting_response': True
                    }
                )
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Message sent: {content[:100]}...",
                data={
                    'message_id': message.id,
                    'type': type
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )


# 工具实例
message_tool = MessageTool()

