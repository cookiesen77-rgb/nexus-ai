"""
任务规划工具

类似Manus的plan工具，用于任务分解和管理
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base import BaseTool, ToolResult, ToolStatus


class PhaseStatus(str, Enum):
    """阶段状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """计划步骤"""
    id: str
    description: str
    status: PhaseStatus = PhaseStatus.PENDING
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PlanPhase:
    """计划阶段"""
    id: str
    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    steps: List[PlanStep] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING


@dataclass
class Plan:
    """任务计划"""
    id: str
    goal: str
    phases: List[PlanPhase] = field(default_factory=list)
    current_phase: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'goal': self.goal,
            'phases': [
                {
                    'id': p.id,
                    'name': p.name,
                    'description': p.description,
                    'capabilities': p.capabilities,
                    'status': p.status.value,
                    'steps': [
                        {
                            'id': s.id,
                            'description': s.description,
                            'status': s.status.value,
                            'output': s.output
                        }
                        for s in p.steps
                    ]
                }
                for p in self.phases
            ],
            'current_phase': self.current_phase,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class PlanManager:
    """计划管理器"""
    
    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._current_plan: Optional[str] = None
    
    def create_plan(self, goal: str, phases: List[Dict[str, Any]]) -> Plan:
        """创建新计划"""
        import uuid
        
        plan_id = str(uuid.uuid4())[:8]
        
        plan_phases = []
        for i, phase_data in enumerate(phases):
            phase = PlanPhase(
                id=f"phase-{i+1}",
                name=phase_data.get('name', f'Phase {i+1}'),
                description=phase_data.get('description', ''),
                capabilities=phase_data.get('capabilities', []),
                steps=[
                    PlanStep(
                        id=f"step-{i+1}-{j+1}",
                        description=step
                    )
                    for j, step in enumerate(phase_data.get('steps', []))
                ]
            )
            plan_phases.append(phase)
        
        plan = Plan(
            id=plan_id,
            goal=goal,
            phases=plan_phases
        )
        
        self._plans[plan_id] = plan
        self._current_plan = plan_id
        
        return plan
    
    def get_plan(self, plan_id: Optional[str] = None) -> Optional[Plan]:
        """获取计划"""
        if plan_id:
            return self._plans.get(plan_id)
        if self._current_plan:
            return self._plans.get(self._current_plan)
        return None
    
    def update_phase_status(
        self,
        plan_id: str,
        phase_id: str,
        status: PhaseStatus
    ) -> bool:
        """更新阶段状态"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        for phase in plan.phases:
            if phase.id == phase_id:
                phase.status = status
                plan.updated_at = datetime.now()
                return True
        
        return False
    
    def update_step_status(
        self,
        plan_id: str,
        phase_id: str,
        step_id: str,
        status: PhaseStatus,
        output: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """更新步骤状态"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        for phase in plan.phases:
            if phase.id == phase_id:
                for step in phase.steps:
                    if step.id == step_id:
                        step.status = status
                        step.output = output
                        step.error = error
                        plan.updated_at = datetime.now()
                        return True
        
        return False
    
    def advance_phase(self, plan_id: str) -> bool:
        """推进到下一阶段"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        
        if plan.current_phase < len(plan.phases) - 1:
            plan.phases[plan.current_phase].status = PhaseStatus.COMPLETED
            plan.current_phase += 1
            plan.phases[plan.current_phase].status = PhaseStatus.RUNNING
            plan.updated_at = datetime.now()
            return True
        
        return False
    
    def list_plans(self) -> List[Plan]:
        """列出所有计划"""
        return list(self._plans.values())
    
    def delete_plan(self, plan_id: str) -> bool:
        """删除计划"""
        if plan_id in self._plans:
            del self._plans[plan_id]
            if self._current_plan == plan_id:
                self._current_plan = None
            return True
        return False


# 全局管理器
_plan_manager = PlanManager()


def get_plan_manager() -> PlanManager:
    """获取计划管理器"""
    return _plan_manager


class PlanTool(BaseTool):
    """
    任务规划工具
    
    用于创建、管理和执行复杂任务计划
    """
    
    name = "plan"
    description = "Task planning tool for breaking down complex tasks into phases and steps"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "get", "update", "advance", "list", "delete"],
                "description": "Action to perform"
            },
            "goal": {
                "type": "string",
                "description": "Goal for creating a plan"
            },
            "phases": {
                "type": "array",
                "description": "Phases for the plan",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "capabilities": {"type": "array", "items": {"type": "string"}},
                        "steps": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "plan_id": {
                "type": "string",
                "description": "Plan ID for get/update/delete actions"
            },
            "phase_id": {
                "type": "string",
                "description": "Phase ID for update action"
            },
            "step_id": {
                "type": "string",
                "description": "Step ID for update action"
            },
            "status": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed", "skipped"],
                "description": "Status for update action"
            }
        },
        "required": ["action"]
    }
    
    async def execute(
        self,
        action: str,
        goal: str = "",
        phases: List[Dict[str, Any]] = None,
        plan_id: str = "",
        phase_id: str = "",
        step_id: str = "",
        status: str = ""
    ) -> ToolResult:
        """执行规划操作"""
        manager = get_plan_manager()
        
        try:
            if action == "create":
                if not goal or not phases:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Goal and phases are required for create action"
                    )
                plan = manager.create_plan(goal, phases)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Created plan '{plan.id}' with {len(plan.phases)} phases",
                    data=plan.to_dict()
                )
            
            elif action == "get":
                plan = manager.get_plan(plan_id or None)
                if not plan:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Plan not found"
                    )
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Plan '{plan.id}': {plan.goal}",
                    data=plan.to_dict()
                )
            
            elif action == "update":
                if not plan_id or not status:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Plan ID and status are required"
                    )
                
                phase_status = PhaseStatus(status)
                
                if step_id and phase_id:
                    success = manager.update_step_status(plan_id, phase_id, step_id, phase_status)
                elif phase_id:
                    success = manager.update_phase_status(plan_id, phase_id, phase_status)
                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Phase ID is required for update"
                    )
                
                if success:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Updated status to {status}"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Update failed"
                )
            
            elif action == "advance":
                if not plan_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Plan ID is required"
                    )
                success = manager.advance_phase(plan_id)
                if success:
                    plan = manager.get_plan(plan_id)
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Advanced to phase {plan.current_phase + 1}",
                        data=plan.to_dict()
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Cannot advance - already at last phase or plan not found"
                )
            
            elif action == "list":
                plans = manager.list_plans()
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=f"Found {len(plans)} plans",
                    data=[p.to_dict() for p in plans]
                )
            
            elif action == "delete":
                if not plan_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        output="",
                        error="Plan ID is required"
                    )
                success = manager.delete_plan(plan_id)
                if success:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        output=f"Deleted plan {plan_id}"
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error="Plan not found"
                )
            
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )


# 工具实例
plan_tool = PlanTool()

