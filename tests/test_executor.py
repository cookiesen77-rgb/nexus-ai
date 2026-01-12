"""
Executor Agent 测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.executor import ExecutorAgent, create_executor_agent
from src.agents.base import AgentConfig
from src.core.task import Plan, PlanStep, StepStatus
from src.llm.base import LLMResponse, StopReason, ToolCall


class TestExecutorAgent:
    """测试ExecutorAgent"""

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
                expr = params.get("expression", "0")
                return eval(expr)
            elif name == "web_search":
                return {"results": ["result1", "result2"]}
            return f"Executed {name}"
        return executor

    @pytest.fixture
    def sample_tools(self):
        """示例工具"""
        return [
            {"name": "calculator", "description": "数学计算"},
            {"name": "web_search", "description": "网络搜索"}
        ]

    @pytest.fixture
    def sample_plan(self):
        """示例计划"""
        steps = [
            PlanStep(
                id="step_1",
                action="计算",
                tool="calculator",
                parameters={"expression": "2 + 3"},
                expected_output="计算结果"
            ),
            PlanStep(
                id="step_2",
                action="搜索",
                tool="web_search",
                parameters={"query": "test"},
                expected_output="搜索结果",
                depends_on=["step_1"]
            )
        ]
        return Plan(
            task_id="test_task",
            goal="测试目标",
            steps=steps
        )

    @pytest.mark.asyncio
    async def test_execute_step_with_tool(
        self, mock_llm, mock_tool_executor, sample_tools
    ):
        """测试使用工具执行步骤"""
        config = AgentConfig(name="TestExecutor")
        executor = ExecutorAgent(
            config, mock_llm, sample_tools, mock_tool_executor
        )
        
        step = PlanStep(
            id="step_1",
            action="计算",
            tool="calculator",
            parameters={"expression": "2 + 3"},
            expected_output="5"
        )
        
        result = await executor.execute_step(step)
        
        assert result.success
        assert result.output == 5
        assert step.status == StepStatus.COMPLETED
        assert step.result == 5

    @pytest.mark.asyncio
    async def test_execute_step_with_llm(self, mock_llm, sample_tools):
        """测试使用LLM执行步骤"""
        mock_llm.complete.return_value = LLMResponse(
            content="任务已完成",
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestExecutor")
        executor = ExecutorAgent(config, mock_llm, sample_tools)
        
        step = PlanStep(
            id="step_1",
            action="分析数据",
            expected_output="分析结果"
        )
        
        result = await executor.execute_step(step)
        
        assert result.success
        assert result.output == "任务已完成"
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_plan(
        self, mock_llm, mock_tool_executor, sample_tools, sample_plan
    ):
        """测试执行完整计划"""
        config = AgentConfig(name="TestExecutor")
        executor = ExecutorAgent(
            config, mock_llm, sample_tools, mock_tool_executor
        )
        
        result = await executor.execute_plan(sample_plan)
        
        assert result.success
        assert sample_plan.is_complete
        assert sample_plan.progress == 1.0
        assert result.metadata["steps_executed"] == 2

    @pytest.mark.asyncio
    async def test_execute_plan_with_failure(
        self, mock_llm, sample_tools
    ):
        """测试计划执行失败"""
        async def failing_executor(name, params):
            raise Exception("Tool failed")
        
        config = AgentConfig(name="TestExecutor")
        executor = ExecutorAgent(
            config, mock_llm, sample_tools, failing_executor
        )
        
        step = PlanStep(
            id="step_1",
            action="失败步骤",
            tool="calculator",
            parameters={"expression": "1/0"},
            expected_output="结果"
        )
        plan = Plan(task_id="test", goal="测试", steps=[step])
        
        result = await executor.execute_plan(plan)
        
        assert not result.success
        assert step.status == StepStatus.FAILED

    @pytest.mark.asyncio
    async def test_dependency_check(
        self, mock_llm, mock_tool_executor, sample_tools
    ):
        """测试依赖检查"""
        steps = [
            PlanStep(id="s1", action="步骤1", expected_output="输出1"),
            PlanStep(id="s2", action="步骤2", expected_output="输出2", depends_on=["s1"])
        ]
        plan = Plan(task_id="test", goal="测试", steps=steps)
        
        # s1未完成时，s2不能执行
        assert not plan.can_execute_step(steps[1])
        
        # 完成s1后，s2可以执行
        steps[0].complete("result1")
        assert plan.can_execute_step(steps[1])

    @pytest.mark.asyncio
    async def test_handle_tool_calls_from_llm(
        self, mock_llm, mock_tool_executor, sample_tools
    ):
        """测试处理LLM发起的工具调用"""
        # LLM返回工具调用
        mock_llm.complete.return_value = LLMResponse(
            content="",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="calculator",
                    parameters={"expression": "10 * 5"}
                )
            ],
            usage={}
        )
        
        config = AgentConfig(name="TestExecutor")
        executor = ExecutorAgent(
            config, mock_llm, sample_tools, mock_tool_executor
        )
        
        step = PlanStep(
            id="step_1",
            action="计算",
            expected_output="结果"
        )
        
        result = await executor.execute_step(step)
        
        assert result.success
        assert result.output == 50


class TestCreateExecutorAgent:
    """测试便捷创建函数"""

    def test_create_with_defaults(self):
        """测试默认参数创建"""
        mock_llm = MagicMock()
        executor = create_executor_agent(llm=mock_llm)
        
        assert executor.name == "ExecutorAgent"
        assert executor.config.max_iterations == 10

    def test_create_with_tool_executor(self):
        """测试带工具执行器创建"""
        mock_llm = MagicMock()
        
        async def tool_exec(name, params):
            return "result"
        
        executor = create_executor_agent(
            llm=mock_llm,
            tool_executor=tool_exec,
            name="CustomExecutor"
        )
        
        assert executor.name == "CustomExecutor"
        assert executor.tool_executor is not None

