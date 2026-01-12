"""
Agent 状态管理

管理Agent执行过程中的状态，包括：
- 消息历史
- 工具调用记录
- 执行状态
- 上下文信息
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_TOOL = "waiting_tool"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolExecution:
    """工具执行记录"""
    id: str
    name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def is_success(self) -> bool:
        return self.is_completed and self.error is None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() * 1000
        return None


@dataclass
class AgentState:
    """Agent状态"""
    # 基础信息
    task: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    # 执行状态
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_iteration: int = 0
    max_iterations: int = 10

    # 消息历史
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # 工具执行记录
    tool_executions: List[ToolExecution] = field(default_factory=list)

    # 结果
    final_result: Optional[str] = None
    error: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Token统计
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.messages.append({
            "role": "user",
            "content": content
        })

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息"""
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def add_system_message(self, content: str) -> None:
        """添加系统消息（插入到开头）"""
        self.messages.insert(0, {
            "role": "system",
            "content": content
        })

    def add_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False
    ) -> None:
        """
        添加工具调用结果

        根据不同的LLM格式，此方法可能需要适配
        """
        # Claude格式
        self.messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": str(result),
                    "is_error": is_error
                }
            ]
        })

    def add_raw_message(self, message: Dict[str, Any]) -> None:
        """添加原始格式消息"""
        self.messages.append(message)

    def record_tool_execution(
        self,
        tool_id: str,
        name: str,
        parameters: Dict[str, Any]
    ) -> ToolExecution:
        """记录工具执行开始"""
        execution = ToolExecution(
            id=tool_id,
            name=name,
            parameters=parameters,
            started_at=datetime.now()
        )
        self.tool_executions.append(execution)
        return execution

    def complete_tool_execution(
        self,
        tool_id: str,
        result: Any = None,
        error: str = None
    ) -> None:
        """完成工具执行记录"""
        for execution in self.tool_executions:
            if execution.id == tool_id:
                execution.result = result
                execution.error = error
                execution.completed_at = datetime.now()
                break

    def update_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """更新Token使用统计"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def increment_iteration(self) -> bool:
        """
        增加迭代次数

        Returns:
            bool: 是否还可以继续迭代
        """
        self.current_iteration += 1
        return self.current_iteration < self.max_iterations

    def complete(self, result: str) -> None:
        """标记为完成"""
        self.status = ExecutionStatus.COMPLETED
        self.final_result = result

    def fail(self, error: str) -> None:
        """标记为失败"""
        self.status = ExecutionStatus.FAILED
        self.error = error

    def timeout(self) -> None:
        """标记为超时"""
        self.status = ExecutionStatus.TIMEOUT
        self.error = f"Exceeded max iterations: {self.max_iterations}"

    @property
    def is_complete(self) -> bool:
        """是否已完成"""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT
        ]

    @property
    def is_success(self) -> bool:
        """是否成功完成"""
        return self.status == ExecutionStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "status": self.status.value,
            "current_iteration": self.current_iteration,
            "max_iterations": self.max_iterations,
            "message_count": len(self.messages),
            "tool_execution_count": len(self.tool_executions),
            "final_result": self.final_result,
            "error": self.error,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "created_at": self.created_at.isoformat()
        }


class StateManager:
    """状态管理器"""

    def __init__(self):
        self._states: Dict[str, AgentState] = {}

    def create_state(
        self,
        task: str,
        max_iterations: int = 10,
        metadata: Dict[str, Any] = None
    ) -> AgentState:
        """创建新状态"""
        state = AgentState(
            task=task,
            max_iterations=max_iterations,
            metadata=metadata or {}
        )
        self._states[state.session_id] = state
        return state

    def get_state(self, session_id: str) -> Optional[AgentState]:
        """获取状态"""
        return self._states.get(session_id)

    def delete_state(self, session_id: str) -> bool:
        """删除状态"""
        if session_id in self._states:
            del self._states[session_id]
            return True
        return False

    def list_states(self) -> List[AgentState]:
        """列出所有状态"""
        return list(self._states.values())

    def get_active_states(self) -> List[AgentState]:
        """获取活跃状态"""
        return [
            s for s in self._states.values()
            if not s.is_complete
        ]

