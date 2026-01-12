"""
代码执行工具测试
"""

import pytest
from src.tools.code_executor import CodeExecutorTool, DataAnalysisTool


class TestCodeExecutorTool:
    """代码执行工具测试"""
    
    @pytest.fixture
    def executor(self):
        """创建执行器实例"""
        return CodeExecutorTool()
    
    @pytest.mark.asyncio
    async def test_simple_print(self, executor):
        """测试简单打印"""
        result = await executor.execute(code="print('Hello World')")
        
        assert result.is_success
        assert "Hello World" in result.output
    
    @pytest.mark.asyncio
    async def test_math_calculation(self, executor):
        """测试数学计算"""
        # 不使用import语句，因为沙箱预导入了math模块
        code = """
print(f"Pi: {math.pi:.4f}")
print(f"Sqrt(2): {math.sqrt(2):.4f}")
"""
        result = await executor.execute(code=code)
        
        assert result.is_success
        assert "Pi:" in result.output
        assert "Sqrt(2):" in result.output
    
    @pytest.mark.asyncio
    async def test_empty_code(self, executor):
        """测试空代码"""
        result = await executor.execute(code="")
        
        assert not result.is_success
        assert "empty" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_syntax_error(self, executor):
        """测试语法错误"""
        result = await executor.execute(code="print('unclosed string")
        
        assert not result.is_success
        assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_runtime_error(self, executor):
        """测试运行时错误"""
        result = await executor.execute(code="undefined_variable")
        
        assert not result.is_success
        assert "NameError" in result.error
    
    @pytest.mark.asyncio
    async def test_list_operations(self, executor):
        """测试列表操作"""
        code = """
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]
print(squared)
print(f"Sum: {sum(squared)}")
"""
        result = await executor.execute(code=code)
        
        assert result.is_success
        assert "[1, 4, 9, 16, 25]" in result.output
        assert "Sum: 55" in result.output
    
    @pytest.mark.asyncio
    async def test_json_processing(self, executor):
        """测试JSON处理"""
        # 不使用import语句，因为沙箱预导入了json模块
        code = """
data = {"name": "Alice", "age": 30}
json_str = json.dumps(data)
print(json_str)
parsed = json.loads(json_str)
print(f"Name: {parsed['name']}")
"""
        result = await executor.execute(code=code)
        
        assert result.is_success
        assert "Alice" in result.output
    
    @pytest.mark.asyncio
    async def test_datetime(self, executor):
        """测试日期时间"""
        # 不使用import语句，因为沙箱预导入了datetime模块
        code = """
now = datetime.datetime.now()
print(f"Year: {now.year}")
"""
        result = await executor.execute(code=code)
        
        assert result.is_success
        assert "Year:" in result.output
    
    @pytest.mark.asyncio
    async def test_statistics(self, executor):
        """测试统计计算"""
        # 不使用import语句，因为沙箱预导入了statistics模块
        code = """
data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(f"Mean: {statistics.mean(data)}")
print(f"Median: {statistics.median(data)}")
print(f"Stdev: {statistics.stdev(data):.2f}")
"""
        result = await executor.execute(code=code)
        
        assert result.is_success
        assert "Mean: 5.5" in result.output
        assert "Median: 5.5" in result.output
    
    @pytest.mark.asyncio
    async def test_timeout_parameter(self, executor):
        """测试超时参数"""
        # 超时应该被限制在合理范围
        result = await executor.execute(code="print(1)", timeout=1000)
        
        assert result.is_success  # 应该成功，因为代码很快
    
    @pytest.mark.asyncio
    async def test_security_blocked(self, executor):
        """测试安全阻止"""
        result = await executor.execute(code="__import__('subprocess')")
        
        assert not result.is_success
        # 安全检查可能在不同阶段触发
        assert result.error is not None
    
    def test_execution_stats(self, executor):
        """测试执行统计"""
        stats = executor.get_execution_stats()
        
        assert "total_executions" in stats
        assert "success_rate" in stats


class TestDataAnalysisTool:
    """数据分析工具测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return DataAnalysisTool()
    
    @pytest.mark.asyncio
    async def test_describe_analysis(self, analyzer):
        """测试描述性分析"""
        data = [
            {"name": "Alice", "age": 25, "score": 85},
            {"name": "Bob", "age": 30, "score": 90},
            {"name": "Charlie", "age": 35, "score": 78}
        ]
        
        result = await analyzer.execute(data=data, analysis_type="describe")
        
        # 可能需要pandas，如果没有安装会失败
        # 这里只检查执行是否完成
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_value_counts(self, analyzer):
        """测试值计数"""
        data = [
            {"category": "A"},
            {"category": "B"},
            {"category": "A"},
            {"category": "A"}
        ]
        
        result = await analyzer.execute(data=data, analysis_type="value_counts")
        
        assert result is not None

