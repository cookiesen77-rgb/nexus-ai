"""
核心模块

提供Agent循环、状态管理、任务和消息等核心功能
"""

from .state import AgentState, StateManager, ExecutionStatus
from .loop import AgentLoop, run_agent
from .task import (
    Task,
    TaskStatus,
    Plan,
    PlanStep,
    StepStatus,
    VerificationResult
)
from .message import (
    AgentMessage,
    MessageType,
    MessagePriority,
    MessageBus,
    create_plan_request,
    create_execute_request,
    create_verify_request
)

__all__ = [
    # 状态管理
    "AgentState",
    "StateManager",
    "ExecutionStatus",
    # 循环
    "AgentLoop",
    "run_agent",
    # 任务
    "Task",
    "TaskStatus",
    "Plan",
    "PlanStep",
    "StepStatus",
    "VerificationResult",
    # 消息
    "AgentMessage",
    "MessageType",
    "MessagePriority",
    "MessageBus",
    "create_plan_request",
    "create_execute_request",
    "create_verify_request",
]
