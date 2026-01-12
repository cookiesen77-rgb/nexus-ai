"""
Phase 4 工具测试
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path


class TestFileTools:
    """文件工具测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.mark.asyncio
    async def test_file_writer_and_reader(self, temp_dir):
        """测试文件读写"""
        from src.tools import file_writer, file_reader
        
        test_file = os.path.join(temp_dir, "test.txt")
        content = "Hello, World!"
        
        # 写入
        result = await file_writer.execute(path=test_file, content=content)
        assert result.is_success
        
        # 读取
        result = await file_reader.execute(path=test_file)
        assert result.is_success
        assert result.output == content
    
    @pytest.mark.asyncio
    async def test_json_file(self, temp_dir):
        """测试JSON文件"""
        from src.tools import file_writer, file_reader
        
        test_file = os.path.join(temp_dir, "test.json")
        data = {"name": "Alice", "age": 30}
        
        # 写入JSON
        result = await file_writer.execute(path=test_file, content=data)
        assert result.is_success
        
        # 读取并解析
        result = await file_reader.execute(path=test_file, parse=True)
        assert result.is_success
        assert result.output == data
    
    @pytest.mark.asyncio
    async def test_file_manager_list(self, temp_dir):
        """测试文件列表"""
        from src.tools import file_manager
        
        # 创建测试文件
        Path(temp_dir, "file1.txt").write_text("test1")
        Path(temp_dir, "file2.txt").write_text("test2")
        
        result = await file_manager.execute(action="list", path=temp_dir)
        assert result.is_success
        assert len(result.output) == 2


class TestJsonTool:
    """JSON工具测试"""
    
    @pytest.mark.asyncio
    async def test_parse(self):
        """测试JSON解析"""
        from src.tools import json_tool
        
        json_str = '{"name": "Bob", "age": 25}'
        result = await json_tool.execute(action="parse", data=json_str)
        
        assert result.is_success
        assert result.output["name"] == "Bob"
    
    @pytest.mark.asyncio
    async def test_query(self):
        """测试JSON查询"""
        from src.tools import json_tool
        
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        result = await json_tool.execute(action="query", data=data, path="users.0.name")
        
        assert result.is_success
        assert result.output == "Alice"
    
    @pytest.mark.asyncio
    async def test_validate(self):
        """测试JSON验证"""
        from src.tools import json_tool
        
        # 有效JSON
        result = await json_tool.execute(action="validate", data='{"valid": true}')
        assert result.output["valid"]
        
        # 无效JSON
        result = await json_tool.execute(action="validate", data='{invalid}')
        assert not result.output["valid"]


class TestCsvTool:
    """CSV工具测试"""
    
    @pytest.mark.asyncio
    async def test_parse(self):
        """测试CSV解析"""
        from src.tools import csv_tool
        
        csv_str = "name,age\nAlice,25\nBob,30"
        result = await csv_tool.execute(action="parse", data=csv_str)
        
        assert result.is_success
        assert len(result.output) == 2
        assert result.output[0]["name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_filter(self):
        """测试CSV过滤"""
        from src.tools import csv_tool
        
        data = [
            {"name": "Alice", "city": "NYC"},
            {"name": "Bob", "city": "LA"},
            {"name": "Charlie", "city": "NYC"}
        ]
        
        result = await csv_tool.execute(
            action="filter", 
            data=data, 
            condition={"city": "NYC"}
        )
        
        assert result.is_success
        assert len(result.output) == 2


class TestDataStore:
    """数据存储测试"""
    
    @pytest.fixture
    def temp_store(self):
        """创建临时存储文件"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, temp_store):
        """测试设置和获取"""
        from src.tools import data_store
        
        # 设置
        result = await data_store.execute(
            action="set", 
            key="test_key", 
            value="test_value",
            store_file=temp_store
        )
        assert result.is_success
        
        # 获取
        result = await data_store.execute(
            action="get", 
            key="test_key",
            store_file=temp_store
        )
        assert result.is_success
        assert result.output == "test_value"
    
    @pytest.mark.asyncio
    async def test_list_keys(self, temp_store):
        """测试列出键"""
        from src.tools import data_store
        
        await data_store.execute(action="set", key="key1", value="v1", store_file=temp_store)
        await data_store.execute(action="set", key="key2", value="v2", store_file=temp_store)
        
        result = await data_store.execute(action="list", store_file=temp_store)
        assert result.is_success
        assert set(result.output) == {"key1", "key2"}


class TestShellExecutor:
    """Shell执行器测试"""
    
    @pytest.mark.asyncio
    async def test_echo(self):
        """测试echo命令"""
        from src.tools import shell
        
        result = await shell.execute(command="echo 'Hello World'")
        assert result.is_success
        assert "Hello World" in result.output
    
    @pytest.mark.asyncio
    async def test_pwd(self):
        """测试pwd命令"""
        from src.tools import shell
        
        result = await shell.execute(command="pwd")
        assert result.is_success
    
    @pytest.mark.asyncio
    async def test_blocked_command(self):
        """测试被阻止的命令"""
        from src.tools import shell
        
        result = await shell.execute(command="rm -rf /")
        assert not result.is_success
        assert "Security check failed" in result.error


class TestEnvironmentTool:
    """环境变量工具测试"""
    
    @pytest.mark.asyncio
    async def test_get_env(self):
        """测试获取环境变量"""
        from src.tools import environment
        
        result = await environment.execute(action="get", name="PATH")
        assert result.is_success
        assert result.output is not None
    
    @pytest.mark.asyncio
    async def test_has_env(self):
        """测试检查环境变量"""
        from src.tools import environment
        
        result = await environment.execute(action="has", name="PATH")
        assert result.is_success
        assert result.output is True
        
        result = await environment.execute(action="has", name="NONEXISTENT_VAR_12345")
        assert result.is_success
        assert result.output is False


class TestHttpClient:
    """HTTP客户端测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires network access")
    async def test_get_request(self):
        """测试GET请求"""
        from src.tools import http_client
        
        result = await http_client.execute(
            url="https://httpbin.org/get",
            method="GET"
        )
        
        assert result.is_success
        assert result.output["status_code"] == 200


class TestToolChain:
    """工具链测试"""
    
    @pytest.mark.asyncio
    async def test_simple_chain(self):
        """测试简单工具链"""
        from src.tools import ToolChain, setup_default_tools
        
        # 确保工具已注册
        setup_default_tools()
        
        chain = ToolChain("test_chain")
        chain.set_variable("expr", "2 + 2")
        
        chain.add_step(
            name="calculate",
            tool="calculator",
            params={"expression": "$expr"}
        )
        
        result = await chain.execute()
        
        assert result["success"]
        assert len(result["steps"]) == 1


class TestRateLimiter:
    """限流器测试"""
    
    @pytest.mark.asyncio
    async def test_acquire(self):
        """测试获取令牌"""
        from src.tools import RateLimiter, RateLimitConfig
        
        config = RateLimitConfig(requests_per_second=10, burst_size=5)
        limiter = RateLimiter(config)
        
        # 应该能快速获取多个令牌
        for _ in range(5):
            assert await limiter.acquire("test")
    
    def test_get_stats(self):
        """测试获取统计"""
        from src.tools import RateLimiter
        
        limiter = RateLimiter()
        stats = limiter.get_stats("test")
        
        assert "available_tokens" in stats
        assert "requests_last_minute" in stats

