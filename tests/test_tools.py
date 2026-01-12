"""
工具测试

测试各类工具的功能
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.tools.base import BaseTool, ToolResult, ToolStatus
from src.tools.registry import ToolRegistry
from src.tools.calculator import CalculatorTool, calculator
from src.tools.text_processor import TextProcessorTool, text_processor
from src.tools.web_search import WebSearchTool, MockWebSearchTool, create_web_search_tool


class TestToolResult:
    """测试工具结果"""

    def test_success_result(self):
        """测试成功结果"""
        result = ToolResult(
            status=ToolStatus.SUCCESS,
            output="42"
        )
        assert result.is_success is True
        assert result.to_string() == "42"

    def test_error_result(self):
        """测试错误结果"""
        result = ToolResult(
            status=ToolStatus.ERROR,
            output=None,
            error="Something went wrong"
        )
        assert result.is_success is False
        assert "Error" in result.to_string()


class TestToolRegistry:
    """测试工具注册器"""

    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        registry.register(calculator)

        assert "calculator" in registry
        assert len(registry) == 1

    def test_get_tool(self):
        """测试获取工具"""
        registry = ToolRegistry()
        registry.register(calculator)

        tool = registry.get("calculator")
        assert tool is not None
        assert tool.name == "calculator"

    def test_list_tools(self):
        """测试列出工具"""
        registry = ToolRegistry()
        registry.register(calculator)
        registry.register(text_processor)

        names = registry.list_names()
        assert "calculator" in names
        assert "text_processor" in names

    def test_get_schemas(self):
        """测试获取Schema"""
        registry = ToolRegistry()
        registry.register(calculator)

        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "calculator"

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """测试执行工具"""
        registry = ToolRegistry()
        registry.register(calculator)

        result = await registry.execute("calculator", expression="2 + 3")
        assert result.is_success
        assert result.output == 5

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()

        result = await registry.execute("nonexistent", param="value")
        assert not result.is_success
        assert "not found" in result.error


class TestCalculatorTool:
    """测试计算器工具"""

    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """测试基础运算"""
        calc = CalculatorTool()

        # 加法
        result = await calc.execute(expression="2 + 3")
        assert result.is_success
        assert result.output == 5

        # 减法
        result = await calc.execute(expression="10 - 4")
        assert result.output == 6

        # 乘法
        result = await calc.execute(expression="3 * 4")
        assert result.output == 12

        # 除法
        result = await calc.execute(expression="15 / 3")
        assert result.output == 5

    @pytest.mark.asyncio
    async def test_complex_expressions(self):
        """测试复杂表达式"""
        calc = CalculatorTool()

        result = await calc.execute(expression="2 + 3 * 4")
        assert result.output == 14

        result = await calc.execute(expression="(2 + 3) * 4")
        assert result.output == 20

        result = await calc.execute(expression="2 ** 10")
        assert result.output == 1024

    @pytest.mark.asyncio
    async def test_math_functions(self):
        """测试数学函数"""
        calc = CalculatorTool()

        result = await calc.execute(expression="sqrt(16)")
        assert result.output == 4

        result = await calc.execute(expression="abs(-5)")
        assert result.output == 5

        result = await calc.execute(expression="round(3.7)")
        assert result.output == 4

    @pytest.mark.asyncio
    async def test_constants(self):
        """测试常量"""
        calc = CalculatorTool()

        result = await calc.execute(expression="pi")
        assert 3.14 < result.output < 3.15

        result = await calc.execute(expression="e")
        assert 2.71 < result.output < 2.72

    @pytest.mark.asyncio
    async def test_division_by_zero(self):
        """测试除零错误"""
        calc = CalculatorTool()

        result = await calc.execute(expression="1 / 0")
        assert not result.is_success
        assert "Division by zero" in result.error

    @pytest.mark.asyncio
    async def test_invalid_expression(self):
        """测试无效表达式"""
        calc = CalculatorTool()

        result = await calc.execute(expression="2 +")
        assert not result.is_success


class TestTextProcessorTool:
    """测试文本处理工具"""

    @pytest.mark.asyncio
    async def test_count_words(self):
        """测试单词统计"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Hello world test test",
            operation="count_words"
        )
        assert result.is_success
        assert result.output["total_words"] == 4
        assert result.output["unique_words"] == 3

    @pytest.mark.asyncio
    async def test_count_chars(self):
        """测试字符统计"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Hello World",
            operation="count_chars"
        )
        assert result.is_success
        assert result.output["total_chars"] == 11
        assert result.output["spaces"] == 1

    @pytest.mark.asyncio
    async def test_to_upper_lower(self):
        """测试大小写转换"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Hello World",
            operation="to_upper"
        )
        assert result.output == "HELLO WORLD"

        result = await processor.execute(
            text="Hello World",
            operation="to_lower"
        )
        assert result.output == "hello world"

    @pytest.mark.asyncio
    async def test_find_replace(self):
        """测试查找替换"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Hello World World",
            operation="find_replace",
            find="World",
            replace="Universe"
        )
        assert result.is_success
        assert result.output["result"] == "Hello Universe Universe"
        assert result.output["replacements"] == 2

    @pytest.mark.asyncio
    async def test_extract_emails(self):
        """测试提取邮箱"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Contact us at test@example.com or support@test.org",
            operation="extract_emails"
        )
        assert result.is_success
        assert "test@example.com" in result.output
        assert "support@test.org" in result.output

    @pytest.mark.asyncio
    async def test_extract_urls(self):
        """测试提取URL"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Visit https://example.com or http://test.org for more info",
            operation="extract_urls"
        )
        assert result.is_success
        assert "https://example.com" in result.output

    @pytest.mark.asyncio
    async def test_word_frequency(self):
        """测试词频统计"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="the cat sat on the mat the cat",
            operation="word_frequency"
        )
        assert result.is_success
        assert result.output["the"] == 3
        assert result.output["cat"] == 2

    @pytest.mark.asyncio
    async def test_summary_stats(self):
        """测试文本统计摘要"""
        processor = TextProcessorTool()

        result = await processor.execute(
            text="Hello world. This is a test. How are you?",
            operation="summary_stats"
        )
        assert result.is_success
        assert result.output["sentences"] == 3
        assert result.output["words"] == 9


class TestWebSearchTool:
    """测试网络搜索工具"""

    @pytest.mark.asyncio
    async def test_mock_search(self):
        """测试模拟搜索"""
        search = MockWebSearchTool()

        result = await search.execute(query="Python programming")
        assert result.is_success
        assert "results" in result.output
        assert len(result.output["results"]) > 0

    @pytest.mark.asyncio
    async def test_create_tool_without_key(self):
        """测试无API密钥时创建工具"""
        with patch.dict("os.environ", {}, clear=True):
            tool = create_web_search_tool()
            assert isinstance(tool, MockWebSearchTool)

    @pytest.mark.asyncio
    async def test_search_without_api_key(self):
        """测试无API密钥搜索"""
        search = WebSearchTool(api_key=None)

        result = await search.execute(query="test")
        assert not result.is_success
        assert "API key" in result.error


class TestToolSchemas:
    """测试工具Schema"""

    def test_calculator_schema(self):
        """测试计算器Schema"""
        schema = calculator.to_schema()

        assert schema["name"] == "calculator"
        assert "description" in schema
        assert "input_schema" in schema
        assert "expression" in schema["input_schema"]["properties"]

    def test_text_processor_schema(self):
        """测试文本处理器Schema"""
        schema = text_processor.to_schema()

        assert schema["name"] == "text_processor"
        assert "text" in schema["input_schema"]["properties"]
        assert "operation" in schema["input_schema"]["properties"]

    def test_openai_schema_format(self):
        """测试OpenAI格式Schema"""
        schema = calculator.to_openai_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "calculator"

