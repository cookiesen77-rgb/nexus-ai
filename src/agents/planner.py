"""
Planner Agent

负责任务分析和计划制定
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.llm import BaseLLM
from src.core.task import Plan, Task, PlanStep
from src.prompts.planner import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_PLAN_TEMPLATE,
    PLANNER_REPLAN_TEMPLATE
)
from src.utils import info, error, debug
from .base import BaseAgent, AgentConfig, AgentResult


class PlannerAgent(BaseAgent):
    """
    Planner Agent - 任务规划专家
    
    负责:
    - 分析任务需求
    - 分解为可执行步骤
    - 识别所需工具
    - 制定执行计划
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(config, llm, tools)
        self.name = config.name or "PlannerAgent"

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        执行规划任务
        
        Args:
            task: 任务描述
            context: 上下文信息
            
        Returns:
            AgentResult: 包含Plan的结果
        """
        info(f"[{self.name}] 开始规划任务: {task[:50]}...")
        
        try:
            plan = await self.create_plan(task, context)
            
            return AgentResult(
                success=True,
                output=plan,
                metadata={
                    "steps_count": len(plan.steps),
                    "required_tools": plan.required_tools,
                    "estimated_iterations": plan.estimated_iterations
                }
            )
        except Exception as e:
            error(f"[{self.name}] 规划失败: {e}")
            return AgentResult(
                success=False,
                output=None,
                error=str(e)
            )

    async def create_plan(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """
        创建执行计划
        
        Args:
            task: 任务描述
            context: 上下文信息
            
        Returns:
            Plan: 执行计划
        """
        # 构建提示词
        tools_desc = self._format_tools_description()
        context_desc = json.dumps(context or {}, ensure_ascii=False)
        
        prompt = PLANNER_PLAN_TEMPLATE.format(
            task=task,
            tools=tools_desc,
            context=context_desc
        )
        
        # 调用LLM
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(
            messages=messages,
            system=PLANNER_SYSTEM_PROMPT,
            temperature=0.5  # 规划需要更确定性的输出
        )
        
        # 解析计划
        plan_data = self._parse_plan_response(response.content)
        
        # 创建Task和Plan对象
        task_obj = Task(description=task, context=context or {})
        plan = Plan.from_dict(plan_data, task_obj.id)
        
        info(f"[{self.name}] 计划创建完成: {len(plan.steps)}个步骤")
        debug(f"[{self.name}] 计划详情: {plan.to_json()}")
        
        return plan

    async def replan(
        self,
        task: str,
        original_plan: Plan,
        feedback: str,
        failure_reason: str
    ) -> Plan:
        """
        重新制定计划
        
        Args:
            task: 原始任务
            original_plan: 原计划
            feedback: 执行反馈
            failure_reason: 失败原因
            
        Returns:
            Plan: 新计划
        """
        info(f"[{self.name}] 重新规划任务...")
        
        tools_desc = self._format_tools_description()
        
        prompt = PLANNER_REPLAN_TEMPLATE.format(
            task=task,
            original_plan=original_plan.to_json(),
            feedback=feedback,
            failure_reason=failure_reason,
            tools=tools_desc
        )
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.complete(
            messages=messages,
            system=PLANNER_SYSTEM_PROMPT,
            temperature=0.5
        )
        
        plan_data = self._parse_plan_response(response.content)
        
        # 创建新计划，继承task_id
        new_plan = Plan.from_dict(plan_data, original_plan.task_id)
        new_plan.version = original_plan.version + 1
        
        # 保留已完成步骤的结果
        self._preserve_completed_results(original_plan, new_plan)
        
        info(f"[{self.name}] 重规划完成: 版本 {new_plan.version}")
        
        return new_plan

    async def step(self, state) -> Any:
        """单步执行（Planner通常一次性输出完整计划）"""
        # Planner主要是一次性规划，不需要step-by-step
        pass

    def _format_tools_description(self) -> str:
        """格式化工具描述"""
        if not self.tools:
            return "无可用工具"
        
        descriptions = []
        for tool in self.tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "无描述")
            params = tool.get("input_schema", {}).get("properties", {})
            
            param_desc = ", ".join(
                f"{k}: {v.get('description', v.get('type', 'any'))}"
                for k, v in params.items()
            )
            
            descriptions.append(f"- {name}: {desc}\n  参数: {param_desc}")
        
        return "\n".join(descriptions)

    def _parse_plan_response(self, content: str) -> Dict[str, Any]:
        """
        解析LLM返回的计划内容
        
        Args:
            content: LLM响应内容
            
        Returns:
            Dict: 解析后的计划数据
        """
        # 尝试直接解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # 尝试从Markdown代码块中提取JSON
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试找到JSON对象
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # 解析失败，创建默认计划
        error(f"[{self.name}] 无法解析计划，创建默认计划")
        return {
            "goal": "完成任务",
            "steps": [
                {
                    "id": "step_1",
                    "action": "执行任务",
                    "expected_output": "任务结果"
                }
            ],
            "estimated_iterations": 3
        }

    def _preserve_completed_results(
        self,
        old_plan: Plan,
        new_plan: Plan
    ) -> None:
        """保留已完成步骤的结果"""
        completed_results = {}
        for step in old_plan.steps:
            if step.is_success and step.result:
                completed_results[step.id] = step.result
        
        # 尝试匹配新计划中相同ID的步骤
        for step in new_plan.steps:
            if step.id in completed_results:
                step.result = completed_results[step.id]
                step.status = step.status  # 保持PENDING让Executor决定是否跳过

    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return PLANNER_SYSTEM_PROMPT


def create_planner_agent(
    llm: BaseLLM,
    tools: List[Dict[str, Any]] = None,
    name: str = "PlannerAgent",
    temperature: float = 0.5,
    max_iterations: int = 3
) -> PlannerAgent:
    """
    创建PlannerAgent的便捷函数
    
    Args:
        llm: LLM客户端
        tools: 可用工具列表
        name: Agent名称
        temperature: 温度参数
        max_iterations: 最大迭代次数
        
    Returns:
        PlannerAgent: Agent实例
    """
    config = AgentConfig(
        name=name,
        temperature=temperature,
        max_iterations=max_iterations
    )
    
    return PlannerAgent(config=config, llm=llm, tools=tools)

