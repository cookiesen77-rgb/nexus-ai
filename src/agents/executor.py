"""
Executor Agent

负责执行计划中的具体步骤
"""

from typing import Any, Callable, Dict, List, Optional

from src.llm import BaseLLM, StopReason
from src.core.task import Plan, PlanStep, StepStatus
from src.core.state import AgentState, ExecutionStatus
from src.prompts.executor import (
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_STEP_TEMPLATE,
    EXECUTOR_CONTINUE_TEMPLATE
)
from src.utils import info, error, debug
from .base import BaseAgent, AgentConfig, AgentResult


class ExecutorAgent(BaseAgent):
    """
    Executor Agent - 任务执行专家
    
    负责:
    - 执行计划中的步骤
    - 调用工具完成操作
    - 记录执行结果
    - 处理执行异常
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_executor: Optional[Callable] = None
    ):
        super().__init__(config, llm, tools)
        self.name = config.name or "ExecutorAgent"
        self.tool_executor = tool_executor

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        执行任务（用于独立执行）
        
        Args:
            task: 任务描述
            context: 上下文，应包含plan
            
        Returns:
            AgentResult: 执行结果
        """
        if context and "plan" in context:
            plan = context["plan"]
            return await self.execute_plan(plan)
        
        # 无计划时作为简单Agent执行
        return await self._execute_simple(task, context)

    async def execute_plan(self, plan: Plan) -> AgentResult:
        """
        执行完整计划
        
        Args:
            plan: 执行计划
            
        Returns:
            AgentResult: 执行结果
        """
        info(f"[{self.name}] 开始执行计划: {plan.goal}")
        
        results = []
        
        while not plan.is_complete:
            step = plan.current_step
            if step is None:
                break
            
            # 检查依赖
            if not plan.can_execute_step(step):
                error(f"[{self.name}] 步骤 {step.id} 依赖未满足")
                step.fail("Dependencies not satisfied")
                break
            
            # 执行步骤
            step_result = await self.execute_step(step, plan)
            results.append(step_result)
            
            if not step_result.success:
                error(f"[{self.name}] 步骤 {step.id} 执行失败")
                break
            
            # 推进计划
            if not plan.advance():
                break
        
        # 返回结果
        success = plan.is_success
        final_result = results[-1].output if results else None
        
        return AgentResult(
            success=success,
            output=final_result,
            error=None if success else "Plan execution failed",
            metadata={
                "steps_executed": len(results),
                "plan_progress": plan.progress,
                "all_results": [r.output for r in results if r.success]
            }
        )

    async def execute_step(
        self,
        step: PlanStep,
        plan: Optional[Plan] = None
    ) -> AgentResult:
        """
        执行单个步骤
        
        Args:
            step: 要执行的步骤
            plan: 所属计划（用于获取上下文）
            
        Returns:
            AgentResult: 步骤执行结果
        """
        info(f"[{self.name}] 执行步骤: {step.id} - {step.action}")
        step.start()
        
        try:
            if step.tool and self.tool_executor:
                # 使用工具执行
                result = await self._execute_with_tool(step)
            else:
                # LLM直接执行
                result = await self._execute_with_llm(step, plan)
            
            if result.success:
                step.complete(result.output)
                info(f"[{self.name}] 步骤 {step.id} 完成")
            else:
                step.fail(result.error or "Unknown error")
                error(f"[{self.name}] 步骤 {step.id} 失败: {result.error}")
            
            return result
            
        except Exception as e:
            step.fail(str(e))
            error(f"[{self.name}] 步骤 {step.id} 异常: {e}")
            return AgentResult(
                success=False,
                output=None,
                error=str(e)
            )

    async def _execute_with_tool(self, step: PlanStep) -> AgentResult:
        """使用工具执行步骤"""
        debug(f"[{self.name}] 调用工具: {step.tool}")
        
        try:
            result = await self.tool_executor(step.tool, step.parameters)
            return AgentResult(
                success=True,
                output=result,
                metadata={"tool": step.tool, "parameters": step.parameters}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output=None,
                error=f"Tool execution failed: {e}"
            )

    async def _execute_with_llm(
        self,
        step: PlanStep,
        plan: Optional[Plan] = None
    ) -> AgentResult:
        """使用LLM执行步骤"""
        # 构建历史记录
        history = self._build_history(plan) if plan else "无历史记录"
        tools_desc = self._format_tools_description()
        
        prompt = EXECUTOR_STEP_TEMPLATE.format(
            step_id=step.id,
            action=step.action,
            tool=step.tool or "无",
            parameters=step.parameters or {},
            expected_output=step.expected_output,
            history=history,
            tools=tools_desc
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        # 调用LLM
        response = await self.llm.complete(
            messages=messages,
            tools=self.tools if self.tools else None,
            system=EXECUTOR_SYSTEM_PROMPT
        )
        
        # 处理工具调用
        if response.stop_reason == StopReason.TOOL_USE and response.tool_calls:
            return await self._handle_tool_calls(response.tool_calls)
        
        # 直接返回结果
        return AgentResult(
            success=True,
            output=response.content,
            metadata={"usage": response.usage}
        )

    async def _handle_tool_calls(self, tool_calls) -> AgentResult:
        """处理LLM发起的工具调用"""
        results = []
        
        for tc in tool_calls:
            debug(f"[{self.name}] LLM调用工具: {tc.name}")
            
            if self.tool_executor:
                try:
                    result = await self.tool_executor(tc.name, tc.parameters)
                    results.append(result)
                except Exception as e:
                    return AgentResult(
                        success=False,
                        output=None,
                        error=f"Tool {tc.name} failed: {e}"
                    )
            else:
                results.append(f"Tool {tc.name} not available")
        
        # 合并结果
        combined = results[0] if len(results) == 1 else results
        return AgentResult(
            success=True,
            output=combined,
            metadata={"tool_calls": len(tool_calls)}
        )

    async def _execute_simple(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """简单执行模式（无计划）"""
        messages = [{"role": "user", "content": task}]
        
        response = await self.llm.complete(
            messages=messages,
            tools=self.tools,
            system=EXECUTOR_SYSTEM_PROMPT
        )
        
        if response.stop_reason == StopReason.TOOL_USE and response.tool_calls:
            return await self._handle_tool_calls(response.tool_calls)
        
        return AgentResult(
            success=True,
            output=response.content
        )

    async def step(self, state: AgentState) -> AgentState:
        """执行单步（用于Agent循环）"""
        # 从状态中获取当前步骤信息
        current_step_data = state.metadata.get("current_step")
        if current_step_data:
            step = PlanStep(**current_step_data)
            result = await self.execute_step(step)
            state.metadata["step_result"] = result.output
            state.metadata["step_success"] = result.success
        
        return state

    def _build_history(self, plan: Plan) -> str:
        """构建执行历史"""
        completed = plan.get_completed_steps()
        if not completed:
            return "无历史记录"
        
        history = []
        for step in completed:
            status = "✓" if step.is_success else "✗"
            result_str = str(step.result)[:100] if step.result else "无结果"
            history.append(f"[{status}] {step.id}: {step.action} -> {result_str}")
        
        return "\n".join(history)

    def _format_tools_description(self) -> str:
        """格式化工具描述"""
        if not self.tools:
            return "无可用工具"
        
        descriptions = []
        for tool in self.tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            descriptions.append(f"- {name}: {desc}")
        
        return "\n".join(descriptions)

    def _default_system_prompt(self) -> str:
        return EXECUTOR_SYSTEM_PROMPT


def create_executor_agent(
    llm: BaseLLM,
    tools: List[Dict[str, Any]] = None,
    tool_executor: Callable = None,
    name: str = "ExecutorAgent",
    temperature: float = 0.7,
    max_iterations: int = 10
) -> ExecutorAgent:
    """
    创建ExecutorAgent的便捷函数
    
    Args:
        llm: LLM客户端
        tools: 可用工具列表
        tool_executor: 工具执行函数
        name: Agent名称
        temperature: 温度参数
        max_iterations: 最大迭代次数
        
    Returns:
        ExecutorAgent: Agent实例
    """
    config = AgentConfig(
        name=name,
        temperature=temperature,
        max_iterations=max_iterations
    )
    
    return ExecutorAgent(
        config=config,
        llm=llm,
        tools=tools,
        tool_executor=tool_executor
    )

