"""
Orchestrator - 多Agent协调器

协调Planner、Executor、Verifier完成复杂任务
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.llm import BaseLLM
from src.core.task import Task, Plan, TaskStatus, VerificationResult
from src.core.message import MessageBus, AgentMessage, MessageType
from src.utils import info, error, warning, debug
from .base import AgentConfig, AgentResult
from .planner import PlannerAgent, create_planner_agent
from .executor import ExecutorAgent, create_executor_agent
from .verifier import VerifierAgent, create_verifier_agent


@dataclass
class OrchestratorConfig:
    """协调器配置"""
    max_iterations: int = 15
    max_replan_attempts: int = 3
    max_retry_per_step: int = 2
    verify_each_step: bool = True
    verify_final_result: bool = True
    timeout: int = 600  # 秒


@dataclass
class OrchestratorResult:
    """协调器执行结果"""
    success: bool
    task: Task
    final_output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "task_id": self.task.id,
            "task_status": self.task.status.value,
            "final_output": str(self.final_output)[:500] if self.final_output else None,
            "error": self.error,
            "metadata": self.metadata
        }


class Orchestrator:
    """
    多Agent协调器
    
    协调Planner、Executor、Verifier完成任务：
    1. Planner分析任务，制定计划
    2. Executor按计划执行步骤
    3. Verifier验证每步结果
    4. 根据验证结果决定继续、重试或重规划
    """

    def __init__(
        self,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None,
        config: Optional[OrchestratorConfig] = None
    ):
        """
        初始化协调器
        
        Args:
            llm: LLM客户端
            tools: 可用工具列表
            tool_executor: 工具执行函数
            config: 协调器配置
        """
        self.llm = llm
        self.tools = tools or []
        self.tool_executor = tool_executor
        self.config = config or OrchestratorConfig()
        
        # 创建子Agent
        self.planner = create_planner_agent(llm=llm, tools=tools)
        self.executor = create_executor_agent(
            llm=llm,
            tools=tools,
            tool_executor=tool_executor
        )
        self.verifier = create_verifier_agent(llm=llm)
        
        # 消息总线
        self.message_bus = MessageBus()
        
        # 统计
        self._iteration_count = 0
        self._replan_count = 0

    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestratorResult:
        """
        执行任务
        
        Args:
            task_description: 任务描述
            context: 上下文信息
            
        Returns:
            OrchestratorResult: 执行结果
        """
        info(f"[Orchestrator] 开始执行任务: {task_description[:50]}...")
        
        # 创建任务
        task = Task(description=task_description, context=context or {})
        task.start()
        
        self._iteration_count = 0
        self._replan_count = 0
        
        try:
            # 1. 规划阶段
            plan = await self._planning_phase(task)
            if plan is None:
                return self._create_failure_result(task, "Planning failed")
            
            task.set_plan(plan)
            
            # 2. 执行阶段
            final_result = await self._execution_phase(task, plan)
            
            # 3. 最终验证
            if self.config.verify_final_result:
                verification = await self.verifier.verify_plan(plan, task_description)
                if not verification.passed:
                    warning(f"[Orchestrator] 最终验证未通过: {verification.feedback}")
            
            # 完成任务
            task.complete(final_result)
            task.total_iterations = self._iteration_count
            
            info(f"[Orchestrator] 任务完成! 迭代次数: {self._iteration_count}")
            
            return OrchestratorResult(
                success=True,
                task=task,
                final_output=final_result,
                metadata={
                    "iterations": self._iteration_count,
                    "replans": self._replan_count,
                    "steps_completed": len(plan.get_completed_steps()),
                    "plan_version": plan.version
                }
            )
            
        except Exception as e:
            error(f"[Orchestrator] 执行失败: {e}")
            task.fail(str(e))
            return self._create_failure_result(task, str(e))

    async def _planning_phase(self, task: Task) -> Optional[Plan]:
        """规划阶段"""
        info("[Orchestrator] 进入规划阶段...")
        
        result = await self.planner.execute(
            task=task.description,
            context=task.context
        )
        
        if not result.success:
            error(f"[Orchestrator] 规划失败: {result.error}")
            return None
        
        plan = result.output
        info(f"[Orchestrator] 规划完成: {len(plan.steps)}个步骤")
        
        return plan

    async def _execution_phase(
        self,
        task: Task,
        plan: Plan
    ) -> Any:
        """执行阶段"""
        info("[Orchestrator] 进入执行阶段...")
        
        while not plan.is_complete:
            self._iteration_count += 1
            
            # 检查迭代限制
            if self._iteration_count > self.config.max_iterations:
                warning("[Orchestrator] 达到最大迭代次数")
                break
            
            step = plan.current_step
            if step is None:
                break
            
            # 检查依赖
            if not plan.can_execute_step(step):
                error(f"[Orchestrator] 步骤 {step.id} 依赖未满足")
                break
            
            debug(f"[Orchestrator] 执行步骤: {step.id}")
            
            # 执行步骤
            retry_count = 0
            step_success = False
            
            while retry_count < self.config.max_retry_per_step:
                exec_result = await self.executor.execute_step(step, plan)
                
                if exec_result.success:
                    # 验证结果
                    if self.config.verify_each_step:
                        verification = await self.verifier.verify_step(
                            step=step,
                            actual_result=exec_result.output,
                            task_goal=task.description
                        )
                        
                        if verification.passed:
                            step_success = True
                            break
                        elif verification.needs_retry:
                            retry_count += 1
                            warning(f"[Orchestrator] 步骤验证未通过，重试 {retry_count}")
                            step.status = step.status.PENDING  # 重置状态
                            continue
                        elif verification.needs_replan:
                            # 需要重规划
                            new_plan = await self._replan(
                                task, plan, verification.feedback
                            )
                            if new_plan:
                                plan = new_plan
                                task.plan = plan
                                break
                            else:
                                break
                    else:
                        step_success = True
                        break
                else:
                    retry_count += 1
                    warning(f"[Orchestrator] 步骤执行失败，重试 {retry_count}")
            
            if not step_success and step.status != step.status.COMPLETED:
                # 步骤失败，尝试重规划
                if self._replan_count < self.config.max_replan_attempts:
                    new_plan = await self._replan(
                        task, plan, f"Step {step.id} failed after retries"
                    )
                    if new_plan:
                        plan = new_plan
                        task.plan = plan
                        continue
                break
            
            # 推进计划
            if not plan.advance():
                break
        
        # 返回最后一个成功步骤的结果
        completed_steps = plan.get_completed_steps()
        if completed_steps:
            return completed_steps[-1].result
        return None

    async def _replan(
        self,
        task: Task,
        current_plan: Plan,
        failure_reason: str
    ) -> Optional[Plan]:
        """重规划"""
        self._replan_count += 1
        
        if self._replan_count > self.config.max_replan_attempts:
            warning("[Orchestrator] 达到最大重规划次数")
            return None
        
        info(f"[Orchestrator] 重规划 (第{self._replan_count}次)")
        
        try:
            new_plan = await self.planner.replan(
                task=task.description,
                original_plan=current_plan,
                feedback=self._build_execution_feedback(current_plan),
                failure_reason=failure_reason
            )
            return new_plan
        except Exception as e:
            error(f"[Orchestrator] 重规划失败: {e}")
            return None

    def _build_execution_feedback(self, plan: Plan) -> str:
        """构建执行反馈"""
        feedback = []
        for step in plan.steps:
            if step.is_complete:
                status = "成功" if step.is_success else "失败"
                result = str(step.result)[:100] if step.result else "无结果"
                error_msg = f", 错误: {step.error}" if step.error else ""
                feedback.append(f"[{status}] {step.id}: {step.action} -> {result}{error_msg}")
        return "\n".join(feedback) if feedback else "无执行记录"

    def _create_failure_result(
        self,
        task: Task,
        error_msg: str
    ) -> OrchestratorResult:
        """创建失败结果"""
        return OrchestratorResult(
            success=False,
            task=task,
            final_output=None,
            error=error_msg,
            metadata={
                "iterations": self._iteration_count,
                "replans": self._replan_count
            }
        )


def create_orchestrator(
    llm: BaseLLM,
    tools: List[Dict[str, Any]] = None,
    tool_executor: Callable = None,
    max_iterations: int = 15,
    verify_steps: bool = True
) -> Orchestrator:
    """
    创建Orchestrator的便捷函数
    
    Args:
        llm: LLM客户端
        tools: 工具列表
        tool_executor: 工具执行函数
        max_iterations: 最大迭代次数
        verify_steps: 是否验证每个步骤
        
    Returns:
        Orchestrator: 协调器实例
    """
    config = OrchestratorConfig(
        max_iterations=max_iterations,
        verify_each_step=verify_steps
    )
    
    return Orchestrator(
        llm=llm,
        tools=tools,
        tool_executor=tool_executor,
        config=config
    )

