"""
API请求模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage] = Field(..., description="消息历史")
    model: Optional[str] = Field(None, description="模型名称")
    thinking_mode: bool = Field(False, description="是否启用思考模式")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大Token数")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="可用工具")
    stream: bool = Field(False, description="是否流式响应")


class TaskRequest(BaseModel):
    """任务请求"""
    task: str = Field(..., description="任务描述")
    thinking_mode: bool = Field(False, description="是否启用思考模式")
    max_iterations: int = Field(10, ge=1, le=50, description="最大迭代次数")
    timeout: int = Field(300, ge=10, le=3600, description="超时时间(秒)")
    tools: Optional[List[str]] = Field(None, description="允许使用的工具")


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class CodeExecutionRequest(BaseModel):
    """代码执行请求"""
    code: str = Field(..., description="Python代码")
    timeout: int = Field(30, ge=1, le=300, description="超时时间(秒)")
    sandbox: str = Field("local", description="沙箱类型: local, docker")

