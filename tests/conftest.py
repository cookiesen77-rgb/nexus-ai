"""
Pytest 配置文件

提供测试夹具和通用配置
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def setup_test_env():
    """设置测试环境变量"""
    os.environ.setdefault("CLAUDE_API_KEY", "test-claude-key")
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    yield


@pytest.fixture
def mock_claude_response():
    """创建Mock的Claude响应"""
    response = MagicMock()
    response.content = [MagicMock(type="text", text="Test response")]
    response.stop_reason = "end_turn"
    response.usage.input_tokens = 10
    response.usage.output_tokens = 20
    response.model = "claude-sonnet-4-5-20250514"
    return response


@pytest.fixture
def mock_openai_response():
    """创建Mock的OpenAI响应"""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response"
    response.choices[0].message.tool_calls = None
    response.choices[0].finish_reason = "stop"
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 20
    response.usage.total_tokens = 30
    response.model = "gpt-5.2"
    return response


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "What can you help me with?"}
    ]


@pytest.fixture
def sample_tools():
    """示例工具定义"""
    return [
        {
            "name": "calculator",
            "description": "A simple calculator",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        },
        {
            "name": "web_search",
            "description": "Search the web",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    ]


@pytest.fixture
def async_mock():
    """创建异步Mock"""
    return AsyncMock


# Pytest配置
def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
