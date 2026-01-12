"""
Verifier Agent 测试
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.verifier import VerifierAgent, create_verifier_agent
from src.agents.base import AgentConfig
from src.core.task import Plan, PlanStep, VerificationResult
from src.llm.base import LLMResponse, StopReason


class TestVerificationResult:
    """测试验证结果"""

    def test_creation(self):
        """测试创建"""
        result = VerificationResult(
            passed=True,
            confidence=0.95,
            feedback="验证通过",
            needs_retry=False,
            needs_replan=False
        )
        
        assert result.passed
        assert result.confidence == 0.95
        assert not result.needs_retry

    def test_to_dict(self):
        """测试序列化"""
        result = VerificationResult(
            passed=False,
            confidence=0.3,
            feedback="需要重试",
            needs_retry=True,
            suggestions=["检查参数", "更换方法"]
        )
        
        data = result.to_dict()
        
        assert data["passed"] is False
        assert data["needs_retry"] is True
        assert len(data["suggestions"]) == 2


class TestVerifierAgent:
    """测试VerifierAgent"""

    @pytest.fixture
    def mock_llm(self):
        """创建Mock LLM"""
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_verify_step_passed(self, mock_llm):
        """测试步骤验证通过"""
        verification_json = json.dumps({
            "passed": True,
            "confidence": 0.9,
            "feedback": "结果正确",
            "needs_retry": False,
            "needs_replan": False,
            "suggestions": []
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=verification_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        step = PlanStep(
            id="step_1",
            action="计算",
            expected_output="42"
        )
        
        result = await verifier.verify_step(
            step=step,
            actual_result="42",
            task_goal="计算答案"
        )
        
        assert result.passed
        assert result.confidence == 0.9
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_step_failed(self, mock_llm):
        """测试步骤验证失败"""
        verification_json = json.dumps({
            "passed": False,
            "confidence": 0.8,
            "feedback": "结果不正确",
            "needs_retry": True,
            "needs_replan": False,
            "suggestions": ["检查计算公式"]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=verification_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        step = PlanStep(
            id="step_1",
            action="计算",
            expected_output="42"
        )
        
        result = await verifier.verify_step(
            step=step,
            actual_result="40",
            task_goal="计算答案"
        )
        
        assert not result.passed
        assert result.needs_retry
        assert len(result.suggestions) == 1

    @pytest.mark.asyncio
    async def test_verify_plan(self, mock_llm):
        """测试计划验证"""
        verification_json = json.dumps({
            "passed": True,
            "confidence": 0.85,
            "feedback": "任务完成",
            "needs_retry": False,
            "needs_replan": False
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=verification_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        # 创建已完成的计划
        steps = [
            PlanStep(id="s1", action="步骤1", expected_output="输出1"),
            PlanStep(id="s2", action="步骤2", expected_output="输出2")
        ]
        steps[0].complete("result1")
        steps[1].complete("result2")
        
        plan = Plan(task_id="test", goal="测试目标", steps=steps)
        
        result = await verifier.verify_plan(plan, "原始任务")
        
        assert result.passed
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_quick_verify(self, mock_llm):
        """测试快速验证"""
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        # 匹配情况
        result = await verifier.quick_verify(
            expected="计算结果",
            actual="计算结果是42"
        )
        assert result.passed
        
        # 不匹配情况
        result = await verifier.quick_verify(
            expected="搜索结果列表",
            actual="错误信息"
        )
        assert not result.passed

    def test_parse_json_response(self, mock_llm):
        """测试JSON响应解析"""
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        # 纯JSON
        content = '{"passed": true, "confidence": 0.9, "feedback": "OK"}'
        result = verifier._parse_verification_response(content)
        assert result.passed
        
        # Markdown中的JSON
        content = '''
        验证结果：
        ```json
        {"passed": false, "confidence": 0.5, "feedback": "需要改进", "needs_retry": true}
        ```
        '''
        result = verifier._parse_verification_response(content)
        assert not result.passed
        assert result.needs_retry

    def test_infer_verification(self, mock_llm):
        """测试从文本推断验证结果"""
        config = AgentConfig(name="TestVerifier")
        verifier = VerifierAgent(config, mock_llm)
        
        # 正面内容
        result = verifier._infer_verification("验证通过，结果正确，任务成功完成")
        assert result.passed
        
        # 负面内容
        result = verifier._infer_verification("验证失败，存在错误，结果不正确")
        assert not result.passed


class TestCreateVerifierAgent:
    """测试便捷创建函数"""

    def test_create_with_defaults(self):
        """测试默认参数创建"""
        mock_llm = MagicMock()
        verifier = create_verifier_agent(llm=mock_llm)
        
        assert verifier.name == "VerifierAgent"
        assert verifier.config.temperature == 0.3

    def test_create_with_custom_threshold(self):
        """测试自定义阈值"""
        mock_llm = MagicMock()
        verifier = create_verifier_agent(
            llm=mock_llm,
            confidence_threshold=0.8
        )
        
        assert verifier.confidence_threshold == 0.8

