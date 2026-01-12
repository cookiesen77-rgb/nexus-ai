"""
Orchestrator 测试
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorResult,
    create_orchestrator
)
from src.core.task import Task, Plan, PlanStep, TaskStatus
from src.llm.base import LLMResponse, StopReason


class TestOrchestratorConfig:
    """测试协调器配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = OrchestratorConfig()
        
        assert config.max_iterations == 15
        assert config.max_replan_attempts == 3
        assert config.verify_each_step is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = OrchestratorConfig(
            max_iterations=10,
            max_replan_attempts=2,
            verify_each_step=False
        )
        
        assert config.max_iterations == 10
        assert config.max_replan_attempts == 2
        assert config.verify_each_step is False


class TestOrchestrator:
    """测试Orchestrator"""

    @pytest.fixture
    def mock_llm(self):
        """创建Mock LLM"""
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.fixture
    def mock_tool_executor(self):
        """创建Mock工具执行器"""
        async def executor(name: str, params: dict):
            if name == "calculator":
                return eval(params.get("expression", "0"))
            return f"Executed {name}"
        return executor

    @pytest.fixture
    def sample_tools(self):
        """示例工具"""
        return [
            {"name": "calculator", "description": "计算"},
            {"name": "web_search", "description": "搜索"}
        ]

    @pytest.mark.asyncio
    async def test_simple_task_execution(
        self, mock_llm, mock_tool_executor, sample_tools
    ):
        """测试简单任务执行"""
        # 设置规划响应
        plan_json = json.dumps({
            "goal": "计算",
            "steps": [{
                "id": "step_1",
                "action": "计算2+2",
                "tool": "calculator",
                "parameters": {"expression": "2+2"},
                "expected_output": "4"
            }],
            "estimated_iterations": 1
        })
        
        # 设置验证响应
        verify_json = json.dumps({
            "passed": True,
            "confidence": 0.95,
            "feedback": "正确",
            "needs_retry": False,
            "needs_replan": False
        })
        
        # 配置LLM响应序列
        mock_llm.complete.side_effect = [
            # Planner响应
            LLMResponse(content=plan_json, stop_reason=StopReason.END_TURN, usage={}),
            # Executor响应（不需要，因为有tool_executor）
            # Verifier响应
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={}),
            # 最终验证
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={})
        ]
        
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=sample_tools,
            tool_executor=mock_tool_executor
        )
        
        result = await orchestrator.execute("计算2+2")
        
        assert result.success
        assert result.task.status == TaskStatus.COMPLETED
        assert result.final_output == 4

    @pytest.mark.asyncio
    async def test_multi_step_execution(
        self, mock_llm, mock_tool_executor, sample_tools
    ):
        """测试多步骤执行"""
        plan_json = json.dumps({
            "goal": "多步计算",
            "steps": [
                {
                    "id": "step_1",
                    "action": "计算第一步",
                    "tool": "calculator",
                    "parameters": {"expression": "3*3"},
                    "expected_output": "9"
                },
                {
                    "id": "step_2",
                    "action": "计算第二步",
                    "tool": "calculator",
                    "parameters": {"expression": "9+1"},
                    "expected_output": "10",
                    "depends_on": ["step_1"]
                }
            ]
        })
        
        verify_json = json.dumps({
            "passed": True,
            "confidence": 0.9,
            "feedback": "OK",
            "needs_retry": False,
            "needs_replan": False
        })
        
        mock_llm.complete.side_effect = [
            LLMResponse(content=plan_json, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={})
        ]
        
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=sample_tools,
            tool_executor=mock_tool_executor
        )
        
        result = await orchestrator.execute("多步计算")
        
        assert result.success
        assert result.metadata["steps_completed"] == 2

    @pytest.mark.asyncio
    async def test_max_iterations_limit(self, mock_llm, sample_tools):
        """测试最大迭代限制"""
        # 创建会无限循环的计划
        plan_json = json.dumps({
            "goal": "无限任务",
            "steps": [{"id": "s1", "action": "步骤1", "expected_output": "输出"}]
        })
        
        # 验证始终需要重试
        verify_json = json.dumps({
            "passed": False,
            "confidence": 0.3,
            "feedback": "需要重试",
            "needs_retry": True,
            "needs_replan": False
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=verify_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        # 第一次返回计划
        mock_llm.complete.side_effect = [
            LLMResponse(content=plan_json, stop_reason=StopReason.END_TURN, usage={}),
        ] + [
            LLMResponse(content=verify_json, stop_reason=StopReason.END_TURN, usage={})
        ] * 20
        
        config = OrchestratorConfig(max_iterations=5, max_retry_per_step=2)
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=sample_tools,
            config=config
        )
        
        result = await orchestrator.execute("测试任务")
        
        # 由于重试限制，不会无限执行
        assert result.metadata["iterations"] <= 5

    @pytest.mark.asyncio
    async def test_planning_failure(self, mock_llm, sample_tools):
        """测试规划失败"""
        # 返回无效JSON导致规划失败
        mock_llm.complete.return_value = LLMResponse(
            content="invalid json",
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        orchestrator = Orchestrator(llm=mock_llm, tools=sample_tools)
        
        # 即使JSON无效，Planner也会创建默认计划
        result = await orchestrator.execute("测试任务")
        # 结果取决于默认计划的执行


class TestOrchestratorResult:
    """测试协调器结果"""

    def test_result_creation(self):
        """测试结果创建"""
        task = Task(description="测试")
        result = OrchestratorResult(
            success=True,
            task=task,
            final_output="完成",
            metadata={"iterations": 3}
        )
        
        assert result.success
        assert result.final_output == "完成"

    def test_result_to_dict(self):
        """测试结果序列化"""
        task = Task(description="测试")
        task.status = TaskStatus.COMPLETED
        
        result = OrchestratorResult(
            success=True,
            task=task,
            final_output="结果",
            metadata={"iterations": 5}
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["task_status"] == "completed"


class TestCreateOrchestrator:
    """测试便捷创建函数"""

    def test_create_with_defaults(self):
        """测试默认参数创建"""
        mock_llm = MagicMock()
        orch = create_orchestrator(llm=mock_llm)
        
        assert orch.config.max_iterations == 15
        assert orch.config.verify_each_step is True

    def test_create_with_custom_params(self):
        """测试自定义参数"""
        mock_llm = MagicMock()
        tools = [{"name": "test"}]
        
        orch = create_orchestrator(
            llm=mock_llm,
            tools=tools,
            max_iterations=10,
            verify_steps=False
        )
        
        assert orch.config.max_iterations == 10
        assert orch.config.verify_each_step is False
        assert len(orch.tools) == 1

