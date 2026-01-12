"""
LLM 客户端测试

测试 Claude 和 OpenAI 兼容客户端
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.base import LLMConfig, LLMResponse, StopReason, ToolCall
from src.llm.claude import ClaudeLLM, create_claude_client
from src.llm.openai_compat import OpenAICompatLLM, create_openai_client


class TestLLMConfig:
    """测试LLM配置"""

    def test_config_creation(self):
        """测试配置创建"""
        config = LLMConfig(
            model="claude-sonnet-4-5-20250514",
            api_key="test-key",
            base_url="https://api.example.com",
            temperature=0.5,
            max_tokens=2048
        )

        assert config.model == "claude-sonnet-4-5-20250514"
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.example.com"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048

    def test_config_defaults(self):
        """测试配置默认值"""
        config = LLMConfig(
            model="test-model",
            api_key="test-key"
        )

        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.base_url is None


class TestLLMResponse:
    """测试LLM响应"""

    def test_response_without_tools(self):
        """测试无工具调用的响应"""
        response = LLMResponse(
            content="Hello, world!",
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 10, "output_tokens": 5}
        )

        assert response.content == "Hello, world!"
        assert response.stop_reason == StopReason.END_TURN
        assert response.has_tool_calls is False

    def test_response_with_tools(self):
        """测试包含工具调用的响应"""
        tool_call = ToolCall(
            id="call_123",
            name="calculator",
            parameters={"expression": "1 + 1"}
        )

        response = LLMResponse(
            content="",
            stop_reason=StopReason.TOOL_USE,
            tool_calls=[tool_call]
        )

        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "calculator"


class TestClaudeLLM:
    """测试Claude LLM客户端"""

    @pytest.fixture
    def mock_config(self):
        """创建测试配置"""
        return LLMConfig(
            model="claude-sonnet-4-5-20250514",
            api_key="test-api-key",
            base_url="https://api.test.com"
        )

    def test_client_initialization(self, mock_config):
        """测试客户端初始化"""
        with patch("src.llm.claude.Anthropic") as mock_anthropic:
            with patch("src.llm.claude.AsyncAnthropic") as mock_async_anthropic:
                client = ClaudeLLM(mock_config)

                assert client.model == "claude-sonnet-4-5-20250514"
                mock_anthropic.assert_called_once_with(
                    api_key="test-api-key",
                    base_url="https://api.test.com"
                )

    def test_format_tool_result(self, mock_config):
        """测试工具结果格式化"""
        with patch("src.llm.claude.Anthropic"):
            with patch("src.llm.claude.AsyncAnthropic"):
                client = ClaudeLLM(mock_config)

                result = client.format_tool_result(
                    tool_call_id="call_123",
                    result="42",
                    is_error=False
                )

                assert result["role"] == "user"
                assert result["content"][0]["type"] == "tool_result"
                assert result["content"][0]["tool_use_id"] == "call_123"
                assert result["content"][0]["content"] == "42"

    def test_format_tool_result_error(self, mock_config):
        """测试错误工具结果格式化"""
        with patch("src.llm.claude.Anthropic"):
            with patch("src.llm.claude.AsyncAnthropic"):
                client = ClaudeLLM(mock_config)

                result = client.format_tool_result(
                    tool_call_id="call_123",
                    result="Division by zero",
                    is_error=True
                )

                assert result["content"][0]["is_error"] is True


class TestOpenAICompatLLM:
    """测试OpenAI兼容LLM客户端"""

    @pytest.fixture
    def mock_config(self):
        """创建测试配置"""
        return LLMConfig(
            model="gpt-5.2",
            api_key="test-api-key",
            base_url="https://api.test.com/v1"
        )

    def test_client_initialization(self, mock_config):
        """测试客户端初始化"""
        with patch("src.llm.openai_compat.OpenAI") as mock_openai:
            with patch("src.llm.openai_compat.AsyncOpenAI") as mock_async_openai:
                client = OpenAICompatLLM(mock_config)

                assert client.model == "gpt-5.2"
                mock_openai.assert_called_once_with(
                    api_key="test-api-key",
                    base_url="https://api.test.com/v1"
                )

    def test_convert_tools_to_openai_format(self, mock_config):
        """测试工具格式转换"""
        with patch("src.llm.openai_compat.OpenAI"):
            with patch("src.llm.openai_compat.AsyncOpenAI"):
                client = OpenAICompatLLM(mock_config)

                claude_tools = [
                    {
                        "name": "calculator",
                        "description": "A calculator",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "expression": {"type": "string"}
                            }
                        }
                    }
                ]

                openai_tools = client._convert_tools_to_openai_format(claude_tools)

                assert len(openai_tools) == 1
                assert openai_tools[0]["type"] == "function"
                assert openai_tools[0]["function"]["name"] == "calculator"

    def test_format_tool_result(self, mock_config):
        """测试工具结果格式化"""
        with patch("src.llm.openai_compat.OpenAI"):
            with patch("src.llm.openai_compat.AsyncOpenAI"):
                client = OpenAICompatLLM(mock_config)

                result = client.format_tool_result(
                    tool_call_id="call_123",
                    result="42",
                    is_error=False
                )

                assert result["role"] == "tool"
                assert result["tool_call_id"] == "call_123"
                assert result["content"] == "42"


class TestConvenienceFunctions:
    """测试便捷创建函数"""

    def test_create_claude_client(self):
        """测试Claude客户端创建"""
        with patch("src.llm.claude.Anthropic"):
            with patch("src.llm.claude.AsyncAnthropic"):
                with patch.dict("os.environ", {"CLAUDE_API_KEY": "env-key"}):
                    client = create_claude_client()
                    assert client.model == "claude-sonnet-4-5-20250514"

    def test_create_openai_client(self):
        """测试OpenAI客户端创建"""
        with patch("src.llm.openai_compat.OpenAI"):
            with patch("src.llm.openai_compat.AsyncOpenAI"):
                with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}):
                    # 使用显式模型名测试
                    client = create_openai_client(model="gpt-5.2")
                    assert client.model == "gpt-5.2"


@pytest.mark.asyncio
class TestAsyncOperations:
    """测试异步操作"""

    async def test_claude_complete(self):
        """测试Claude异步补全"""
        config = LLMConfig(
            model="claude-sonnet-4-5-20250514",
            api_key="test-key"
        )

        with patch("src.llm.claude.Anthropic"):
            with patch("src.llm.claude.AsyncAnthropic") as mock_async:
                # 创建mock响应
                mock_response = MagicMock()
                mock_response.content = [MagicMock(type="text", text="Hello!")]
                mock_response.stop_reason = "end_turn"
                mock_response.usage.input_tokens = 10
                mock_response.usage.output_tokens = 5
                mock_response.model = "claude-sonnet-4-5-20250514"

                mock_async.return_value.messages.create = AsyncMock(
                    return_value=mock_response
                )

                client = ClaudeLLM(config)
                response = await client.complete(
                    messages=[{"role": "user", "content": "Hi"}]
                )

                assert response.content == "Hello!"
                assert response.stop_reason == StopReason.END_TURN

