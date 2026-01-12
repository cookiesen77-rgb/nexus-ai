"""
任务和计划数据结构

定义任务、计划、步骤等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
import json


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """计划步骤"""
    id: str
    action: str
    expected_output: str
    tool: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def start(self) -> None:
        """标记步骤开始"""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now()

    def complete(self, result: Any) -> None:
        """标记步骤完成"""
        self.status = StepStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """标记步骤失败"""
        self.status = StepStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def skip(self) -> None:
        """跳过步骤"""
        self.status = StepStatus.SKIPPED
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        return self.status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]

    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "action": self.action,
            "tool": self.tool,
            "parameters": self.parameters,
            "expected_output": self.expected_output,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": self.error
        }


@dataclass
class Plan:
    """执行计划"""
    task_id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    estimated_iterations: int = 5
    required_tools: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    # 执行状态
    current_step_index: int = 0

    @property
    def current_step(self) -> Optional[PlanStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        """计划是否执行完成"""
        return all(step.is_complete for step in self.steps)

    @property
    def is_success(self) -> bool:
        """计划是否成功完成"""
        return all(step.is_success for step in self.steps)

    @property
    def progress(self) -> float:
        """执行进度 (0-1)"""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.is_complete)
        return completed / len(self.steps)

    def advance(self) -> bool:
        """
        推进到下一步骤
        
        Returns:
            bool: 是否还有下一步
        """
        self.current_step_index += 1
        return self.current_step_index < len(self.steps)

    def get_completed_steps(self) -> List[PlanStep]:
        """获取已完成的步骤"""
        return [s for s in self.steps if s.is_complete]

    def get_pending_steps(self) -> List[PlanStep]:
        """获取待执行的步骤"""
        return [s for s in self.steps if s.status == StepStatus.PENDING]

    def get_step_by_id(self, step_id: str) -> Optional[PlanStep]:
        """根据ID获取步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def can_execute_step(self, step: PlanStep) -> bool:
        """检查步骤是否可以执行（依赖是否满足）"""
        for dep_id in step.depends_on:
            dep_step = self.get_step_by_id(dep_id)
            if dep_step and not dep_step.is_success:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_iterations": self.estimated_iterations,
            "required_tools": self.required_tools,
            "version": self.version,
            "progress": self.progress
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], task_id: str) -> "Plan":
        """从字典创建Plan"""
        steps = []
        for step_data in data.get("steps", []):
            step = PlanStep(
                id=step_data.get("id", f"step_{len(steps)+1}"),
                action=step_data.get("action", ""),
                tool=step_data.get("tool"),
                parameters=step_data.get("parameters", {}),
                expected_output=step_data.get("expected_output", ""),
                depends_on=step_data.get("depends_on", [])
            )
            steps.append(step)

        return cls(
            task_id=task_id,
            goal=data.get("goal", ""),
            steps=steps,
            estimated_iterations=data.get("estimated_iterations", 5),
            required_tools=data.get("required_tools", [])
        )


@dataclass
class Task:
    """任务"""
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    plan: Optional[Plan] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 执行统计
    total_iterations: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0

    def start(self) -> None:
        """开始任务"""
        self.status = TaskStatus.PLANNING
        self.started_at = datetime.now()

    def set_plan(self, plan: Plan) -> None:
        """设置执行计划"""
        self.plan = plan
        self.status = TaskStatus.EXECUTING

    def complete(self, result: Any) -> None:
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """任务失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "total_iterations": self.total_iterations,
            "total_tool_calls": self.total_tool_calls,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class VerificationResult:
    """验证结果"""
    passed: bool
    confidence: float  # 0-1
    feedback: str
    needs_retry: bool = False
    needs_replan: bool = False
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "feedback": self.feedback,
            "needs_retry": self.needs_retry,
            "needs_replan": self.needs_replan,
            "suggestions": self.suggestions
        }

