"""
集成测试

测试多Agent协作流程
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.orchestrator import Orchestrator, OrchestratorConfig
from src.agents.planner import PlannerAgent
from src.agents.executor import ExecutorAgent
from src.agents.verifier import VerifierAgent
from src.core.task import Task, Plan, PlanStep, TaskStatus
from src.llm.base import LLMResponse, StopReason


class TestPlannerExecutorIntegration:
    """测试Planner和Executor集成"""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.fixture
    def tool_executor(self):
        async def executor(name, params):
            if name == "calculator":
                return eval(params.get("expression", "0"))
            elif name == "text_processor":
                return {"words": 10, "chars": 50}
            return "OK"
        return executor

    @pytest.mark.asyncio
    async def test_planner_creates_executable_plan(self, mock_llm, tool_executor):
        """测试Planner创建的计划可以被Executor执行"""
        # Planner返回计划
        plan_json = json.dumps({
            "goal": "计算圆面积",
            "steps": [{
                "id": "calc",
                "action": "计算",
                "tool": "calculator",
                "parameters": {"expression": "3.14 * 5 * 5"},
                "expected_output": "面积"
            }]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=plan_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        # 创建Planner
        from src.agents.base import AgentConfig
        planner = PlannerAgent(
            AgentConfig(name="Planner"),
            mock_llm,
            tools=[{"name": "calculator", "description": "计算"}]
        )
        
        # 创建计划
        plan = await planner.create_plan("计算半径5的圆面积")
        
        # 创建Executor执行
        executor = ExecutorAgent(
            AgentConfig(name="Executor"),
            mock_llm,
            tools=[{"name": "calculator", "description": "计算"}],
            tool_executor=tool_executor
        )
        
        # 执行计划
        result = await executor.execute_plan(plan)
        
        assert result.success
        assert abs(result.output - 78.5) < 0.1


class TestFullWorkflow:
    """测试完整工作流"""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.fixture
    def tools(self):
        return [
            {"name": "calculator", "description": "数学计算", "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}}}},
            {"name": "text_processor", "description": "文本处理", "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "operation": {"type": "string"}}}}
        ]

    @pytest.fixture
    def tool_executor(self):
        async def executor(name, params):
            if name == "calculator":
                try:
                    return eval(params.get("expression", "0"))
                except:
                    return "Error"
            elif name == "text_processor":
                text = params.get("text", "")
                return {"words": len(text.split()), "chars": len(text)}
            return "Unknown tool"
        return executor

    @pytest.mark.asyncio
    async def test_plan_execute_verify_cycle(
        self, mock_llm, tools, tool_executor
    ):
        """测试 规划->执行->验证 循环"""
        # 规划响应
        plan_json = json.dumps({
            "goal": "分析文本",
            "steps": [
                {
                    "id": "step_1",
                    "action": "分析文本统计",
                    "tool": "text_processor",
                    "parameters": {"text": "Hello World Test", "operation": "count"},
                    "expected_output": "统计结果"
                },
                {
                    "id": "step_2",
                    "action": "计算单词数平方",
                    "tool": "calculator",
                    "parameters": {"expression": "3 * 3"},
                    "expected_output": "9",
                    "depends_on": ["step_1"]
                }
            ]
        })
        
        # 验证响应
        verify_pass = json.dumps({
            "passed": True,
            "confidence": 0.9,
            "feedback": "验证通过",
            "needs_retry": False,
            "needs_replan": False
        })
        
        mock_llm.complete.side_effect = [
            LLMResponse(content=plan_json, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_pass, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_pass, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_pass, stop_reason=StopReason.END_TURN, usage={})
        ]
        
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=tools,
            tool_executor=tool_executor
        )
        
        result = await orchestrator.execute("分析文本'Hello World Test'并计算单词数的平方")
        
        assert result.success
        assert result.final_output == 9
        assert result.metadata["steps_completed"] == 2

    @pytest.mark.asyncio
    async def test_replan_on_verification_failure(
        self, mock_llm, tools, tool_executor
    ):
        """测试验证失败时重规划"""
        # 初始计划
        initial_plan = json.dumps({
            "goal": "测试",
            "steps": [{
                "id": "s1",
                "action": "错误的计算",
                "tool": "calculator",
                "parameters": {"expression": "1+1"},
                "expected_output": "100"  # 预期错误
            }]
        })
        
        # 验证失败，需要重规划
        verify_replan = json.dumps({
            "passed": False,
            "confidence": 0.2,
            "feedback": "结果不符合预期",
            "needs_retry": False,
            "needs_replan": True
        })
        
        # 新计划
        new_plan = json.dumps({
            "goal": "修正后的测试",
            "steps": [{
                "id": "s1",
                "action": "正确的计算",
                "tool": "calculator",
                "parameters": {"expression": "50+50"},
                "expected_output": "100"
            }]
        })
        
        # 验证通过
        verify_pass = json.dumps({
            "passed": True,
            "confidence": 0.95,
            "feedback": "正确",
            "needs_retry": False,
            "needs_replan": False
        })
        
        mock_llm.complete.side_effect = [
            LLMResponse(content=initial_plan, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_replan, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=new_plan, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_pass, stop_reason=StopReason.END_TURN, usage={}),
            LLMResponse(content=verify_pass, stop_reason=StopReason.END_TURN, usage={})
        ]
        
        config = OrchestratorConfig(max_replan_attempts=3)
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=tools,
            tool_executor=tool_executor,
            config=config
        )
        
        result = await orchestrator.execute("计算得到100")
        
        assert result.success
        assert result.metadata["replans"] >= 1


class TestErrorHandling:
    """测试错误处理"""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_tool_execution_error(self, mock_llm):
        """测试工具执行错误"""
        plan_json = json.dumps({
            "goal": "测试",
            "steps": [{
                "id": "s1",
                "action": "调用工具",
                "tool": "failing_tool",
                "parameters": {},
                "expected_output": "结果"
            }]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=plan_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        async def failing_executor(name, params):
            raise Exception("Tool failed!")
        
        orchestrator = Orchestrator(
            llm=mock_llm,
            tools=[{"name": "failing_tool", "description": "会失败的工具"}],
            tool_executor=failing_executor
        )
        
        result = await orchestrator.execute("测试失败")
        
        # Orchestrator会尝试重试和重规划，最终会完成但步骤会失败
        # 检查是否有重规划尝试
        assert result.metadata.get("replans", 0) > 0 or result.task.plan.steps[0].error is not None

