"""
Agent 测试

测试Agent基类和SimpleAgent实现
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base import BaseAgent, AgentConfig, AgentResult, ConversationalAgent
from src.agents.simple_agent import SimpleAgent, create_simple_agent
from src.core.state import AgentState, ExecutionStatus
from src.llm.base import LLMResponse, StopReason, ToolCall


class TestAgentConfig:
    """测试Agent配置"""

    def test_config_creation(self):
        """测试配置创建"""
        config = AgentConfig(
            name="TestAgent",
            model="claude-sonnet-4-5-20250514",
            temperature=0.5,
            max_iterations=5
        )

        assert config.name == "TestAgent"
        assert config.model == "claude-sonnet-4-5-20250514"
        assert config.temperature == 0.5
        assert config.max_iterations == 5

    def test_config_defaults(self):
        """测试配置默认值"""
        config = AgentConfig(name="TestAgent")

        assert config.temperature == 0.7
        assert config.max_iterations == 10
        assert config.timeout == 300


class TestAgentResult:
    """测试Agent结果"""

    def test_success_result(self):
        """测试成功结果"""
        result = AgentResult(
            success=True,
            output="Task completed",
            metadata={"iterations": 3}
        )

        assert result.success is True
        assert result.output == "Task completed"
        assert result.error is None

    def test_failure_result(self):
        """测试失败结果"""
        result = AgentResult(
            success=False,
            output=None,
            error="Task failed"
        )

        assert result.success is False
        assert result.error == "Task failed"


class TestAgentState:
    """测试Agent状态"""

    def test_state_creation(self):
        """测试状态创建"""
        state = AgentState(task="Test task", max_iterations=5)

        assert state.task == "Test task"
        assert state.max_iterations == 5
        assert state.status == ExecutionStatus.PENDING
        assert state.current_iteration == 0

    def test_add_messages(self):
        """测试添加消息"""
        state = AgentState(task="Test")

        state.add_user_message("Hello")
        state.add_assistant_message("Hi there")

        assert len(state.messages) == 2
        assert state.messages[0]["role"] == "user"
        assert state.messages[1]["role"] == "assistant"

    def test_iteration_limit(self):
        """测试迭代限制"""
        state = AgentState(task="Test", max_iterations=3)

        assert state.increment_iteration() is True  # 1
        assert state.increment_iteration() is True  # 2
        assert state.increment_iteration() is False  # 3 >= max

    def test_complete_state(self):
        """测试完成状态"""
        state = AgentState(task="Test")
        state.complete("Done!")

        assert state.is_complete is True
        assert state.is_success is True
        assert state.final_result == "Done!"

    def test_fail_state(self):
        """测试失败状态"""
        state = AgentState(task="Test")
        state.fail("Error occurred")

        assert state.is_complete is True
        assert state.is_success is False
        assert state.error == "Error occurred"


class TestSimpleAgent:
    """测试SimpleAgent"""

    @pytest.fixture
    def mock_llm(self):
        """创建Mock LLM"""
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.fixture
    def agent_config(self):
        """创建Agent配置"""
        return AgentConfig(
            name="TestAgent",
            max_iterations=5,
            temperature=0.7
        )

    @pytest.mark.asyncio
    async def test_simple_execution(self, mock_llm, agent_config):
        """测试简单执行"""
        # 设置Mock响应
        mock_llm.complete.return_value = LLMResponse(
            content="Task completed successfully",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        agent = SimpleAgent(agent_config, mock_llm)
        result = await agent.execute("Test task")

        assert result.success is True
        assert result.output == "Task completed successfully"
        mock_llm.complete.assert_called()

    @pytest.mark.asyncio
    async def test_execution_with_tools(self, mock_llm, agent_config):
        """测试带工具的执行"""
        # 第一次调用：返回工具调用
        tool_response = LLMResponse(
            content="",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="calculator",
                    parameters={"expression": "1 + 1"}
                )
            ],
            usage={"input_tokens": 10, "output_tokens": 15}
        )

        # 第二次调用：返回最终结果
        final_response = LLMResponse(
            content="The result is 2",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 20, "output_tokens": 10}
        )

        mock_llm.complete.side_effect = [tool_response, final_response]

        # 工具执行函数
        async def tool_executor(name, params):
            if name == "calculator":
                return "2"
            return "Unknown tool"

        tools = [{
            "name": "calculator",
            "description": "A calculator",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                }
            }
        }]

        agent = SimpleAgent(
            agent_config,
            mock_llm,
            tools=tools,
            tool_executor=tool_executor
        )

        result = await agent.execute("Calculate 1 + 1")

        assert result.success is True
        assert result.output == "The result is 2"
        assert mock_llm.complete.call_count == 2

    @pytest.mark.asyncio
    async def test_max_iterations(self, mock_llm, agent_config):
        """测试最大迭代限制"""
        agent_config.max_iterations = 2

        # 始终返回需要继续的响应
        mock_llm.complete.return_value = LLMResponse(
            content="Still working...",
            stop_reason=StopReason.MAX_TOKENS,
            usage={"input_tokens": 10, "output_tokens": 10}
        )

        agent = SimpleAgent(agent_config, mock_llm)
        result = await agent.execute("Long task")

        assert result.success is False
        assert result.state.status == ExecutionStatus.TIMEOUT


class TestCreateSimpleAgent:
    """测试便捷创建函数"""

    def test_create_with_defaults(self):
        """测试默认参数创建"""
        mock_llm = MagicMock()
        agent = create_simple_agent(llm=mock_llm)

        assert agent.name == "SimpleAgent"
        assert agent.config.max_iterations == 10
        assert agent.config.temperature == 0.7

    def test_create_with_custom_params(self):
        """测试自定义参数创建"""
        mock_llm = MagicMock()
        agent = create_simple_agent(
            name="CustomAgent",
            llm=mock_llm,
            max_iterations=5,
            temperature=0.5
        )

        assert agent.name == "CustomAgent"
        assert agent.config.max_iterations == 5
        assert agent.config.temperature == 0.5

