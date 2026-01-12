"""
API响应模型
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCallInfo(BaseModel):
    """工具调用信息"""
    id: str
    name: str
    parameters: Dict[str, Any]


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str = Field(..., description="响应内容")
    model: str = Field(..., description="使用的模型")
    tool_calls: Optional[List[ToolCallInfo]] = Field(None, description="工具调用")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token使用")
    thinking_mode: bool = Field(False, description="是否使用思考模式")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(default_factory=datetime.now)
    message: str = Field("", description="状态消息")


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    result: Optional[str] = Field(None, description="任务结果")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="执行步骤")
    total_tokens: int = Field(0, description="总Token消耗")
    execution_time: float = Field(0.0, description="执行时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[Dict[str, Any]] = Field(..., description="可用工具列表")
    count: int = Field(..., description="工具数量")


class ToolResultResponse(BaseModel):
    """工具执行结果"""
    tool_name: str = Field(..., description="工具名称")
    status: str = Field(..., description="执行状态")
    output: Any = Field(None, description="输出结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: float = Field(0.0, description="执行时间(毫秒)")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field("healthy", description="服务状态")
    version: str = Field(..., description="版本号")
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, str] = Field(default_factory=dict, description="组件状态")


class MetricsResponse(BaseModel):
    """指标响应"""
    llm_calls: int = Field(0, description="LLM调用次数")
    tool_calls: int = Field(0, description="工具调用次数")
    tasks_completed: int = Field(0, description="完成任务数")
    avg_latency_ms: float = Field(0.0, description="平均延迟")
    total_tokens: int = Field(0, description="总Token消耗")
    cache_hit_rate: float = Field(0.0, description="缓存命中率")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细信息")
    timestamp: datetime = Field(default_factory=datetime.now)

