"""
Verifier Agent

负责验证执行结果
"""

import json
import re
from typing import Any, Dict, List, Optional

from src.llm import BaseLLM
from src.core.task import Plan, PlanStep, VerificationResult, Task
from src.prompts.verifier import (
    VERIFIER_SYSTEM_PROMPT,
    VERIFIER_VERIFY_TEMPLATE,
    VERIFIER_FINAL_CHECK_TEMPLATE
)
from src.utils import info, error, debug
from .base import BaseAgent, AgentConfig, AgentResult


class VerifierAgent(BaseAgent):
    """
    Verifier Agent - 结果验证专家
    
    负责:
    - 验证执行结果
    - 评估任务完成度
    - 识别问题和偏差
    - 决定下一步行动
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: BaseLLM,
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(config, llm, tools)
        self.name = config.name or "VerifierAgent"
        self.confidence_threshold = config.timeout if hasattr(config, 'threshold') else 0.7

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """
        执行验证任务
        
        Args:
            task: 验证任务描述
            context: 上下文，应包含result和expected
            
        Returns:
            AgentResult: 包含VerificationResult的结果
        """
        if not context:
            return AgentResult(
                success=False,
                output=None,
                error="Context required for verification"
            )
        
        result = context.get("result")
        expected = context.get("expected")
        step = context.get("step")
        
        verification = await self.verify_step(
            step=step,
            actual_result=result,
            task_goal=task
        )
        
        return AgentResult(
            success=True,
            output=verification,
            metadata={
                "passed": verification.passed,
                "confidence": verification.confidence
            }
        )

    async def verify_step(
        self,
        step: PlanStep,
        actual_result: Any,
        task_goal: str = "",
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        验证单个步骤的执行结果
        
        Args:
            step: 执行的步骤
            actual_result: 实际执行结果
            task_goal: 任务目标
            context: 额外上下文
            
        Returns:
            VerificationResult: 验证结果
        """
        info(f"[{self.name}] 验证步骤: {step.id}")
        
        prompt = VERIFIER_VERIFY_TEMPLATE.format(
            task_goal=task_goal,
            step_id=step.id,
            action=step.action,
            expected_output=step.expected_output,
            actual_result=str(actual_result)[:1000],  # 限制长度
            context=json.dumps(context or {}, ensure_ascii=False)
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.llm.complete(
            messages=messages,
            system=VERIFIER_SYSTEM_PROMPT,
            temperature=0.3  # 验证需要更确定性的输出
        )
        
        verification = self._parse_verification_response(response.content)
        
        log_func = info if verification.passed else error
        log_func(f"[{self.name}] 验证结果: {'通过' if verification.passed else '未通过'} (置信度: {verification.confidence:.2f})")
        
        return verification

    async def verify_plan(
        self,
        plan: Plan,
        original_task: str
    ) -> VerificationResult:
        """
        验证整个计划的执行结果
        
        Args:
            plan: 执行的计划
            original_task: 原始任务
            
        Returns:
            VerificationResult: 最终验证结果
        """
        info(f"[{self.name}] 进行最终验证...")
        
        # 收集所有步骤结果
        results_summary = []
        for step in plan.steps:
            status = "✓" if step.is_success else "✗"
            result_str = str(step.result)[:200] if step.result else "无结果"
            results_summary.append(f"[{status}] {step.id}: {step.action}\n    结果: {result_str}")
        
        execution_summary = f"总步骤: {len(plan.steps)}, 成功: {sum(1 for s in plan.steps if s.is_success)}"
        
        prompt = VERIFIER_FINAL_CHECK_TEMPLATE.format(
            original_task=original_task,
            plan_goal=plan.goal,
            execution_summary=execution_summary,
            all_results="\n".join(results_summary)
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.llm.complete(
            messages=messages,
            system=VERIFIER_SYSTEM_PROMPT,
            temperature=0.3
        )
        
        verification = self._parse_verification_response(response.content)
        
        info(f"[{self.name}] 最终验证: {'通过' if verification.passed else '未通过'}")
        
        return verification

    async def quick_verify(
        self,
        expected: str,
        actual: Any
    ) -> VerificationResult:
        """
        快速验证结果
        
        Args:
            expected: 预期结果描述
            actual: 实际结果
            
        Returns:
            VerificationResult: 验证结果
        """
        # 简单的字符串匹配验证
        actual_str = str(actual).lower()
        expected_lower = expected.lower()
        
        # 检查关键词匹配
        keywords = expected_lower.split()
        matches = sum(1 for kw in keywords if kw in actual_str)
        confidence = matches / len(keywords) if keywords else 0.5
        
        passed = confidence >= 0.5
        
        return VerificationResult(
            passed=passed,
            confidence=confidence,
            feedback=f"快速验证: {'匹配' if passed else '不匹配'}",
            needs_retry=not passed and confidence > 0.3,
            needs_replan=not passed and confidence <= 0.3
        )

    async def step(self, state) -> Any:
        """单步执行"""
        pass

    def _parse_verification_response(self, content: str) -> VerificationResult:
        """
        解析验证响应
        
        Args:
            content: LLM响应内容
            
        Returns:
            VerificationResult: 解析后的验证结果
        """
        # 尝试解析JSON
        try:
            # 直接解析
            data = json.loads(content)
            return self._dict_to_verification(data)
        except json.JSONDecodeError:
            pass
        
        # 从Markdown代码块提取
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._dict_to_verification(data)
            except json.JSONDecodeError:
                pass
        
        # 查找JSON对象
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                return self._dict_to_verification(data)
            except json.JSONDecodeError:
                pass
        
        # 解析失败，基于内容推断
        return self._infer_verification(content)

    def _dict_to_verification(self, data: Dict[str, Any]) -> VerificationResult:
        """从字典创建VerificationResult"""
        return VerificationResult(
            passed=data.get("passed", False),
            confidence=data.get("confidence", 0.5),
            feedback=data.get("feedback", ""),
            needs_retry=data.get("needs_retry", False),
            needs_replan=data.get("needs_replan", False),
            suggestions=data.get("suggestions", [])
        )

    def _infer_verification(self, content: str) -> VerificationResult:
        """从内容推断验证结果"""
        content_lower = content.lower()
        
        # 检查正面/负面关键词
        positive_keywords = ["成功", "通过", "正确", "完成", "pass", "success", "correct"]
        negative_keywords = ["失败", "错误", "未通过", "问题", "fail", "error", "wrong"]
        
        positive_count = sum(1 for kw in positive_keywords if kw in content_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in content_lower)
        
        passed = positive_count > negative_count
        confidence = 0.6 if positive_count > 0 or negative_count > 0 else 0.5
        
        return VerificationResult(
            passed=passed,
            confidence=confidence,
            feedback=content[:500],
            needs_retry=not passed,
            needs_replan=False
        )

    def _default_system_prompt(self) -> str:
        return VERIFIER_SYSTEM_PROMPT


def create_verifier_agent(
    llm: BaseLLM,
    name: str = "VerifierAgent",
    temperature: float = 0.3,
    confidence_threshold: float = 0.7
) -> VerifierAgent:
    """
    创建VerifierAgent的便捷函数
    
    Args:
        llm: LLM客户端
        name: Agent名称
        temperature: 温度参数
        confidence_threshold: 置信度阈值
        
    Returns:
        VerifierAgent: Agent实例
    """
    config = AgentConfig(
        name=name,
        temperature=temperature
    )
    
    agent = VerifierAgent(config=config, llm=llm)
    agent.confidence_threshold = confidence_threshold
    
    return agent

