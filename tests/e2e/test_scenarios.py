"""
端到端测试场景

测试完整的Agent工作流程
"""

import pytest
import asyncio
import os
import sys
sys.path.insert(0, '.')


class TestInformationRetrieval:
    """信息检索场景测试"""
    
    @pytest.mark.asyncio
    async def test_simple_calculation(self):
        """测试简单计算"""
        from src.llm import create_allapi_client
        from src.tools import calculator
        
        # 使用LLM进行计算任务
        client = create_allapi_client()
        
        messages = [
            {"role": "user", "content": "Calculate 25 * 4 + 10"}
        ]
        
        response = await client.complete(messages)
        
        # 验证响应包含正确答案
        assert response.content is not None
        assert "110" in response.content or response.has_tool_calls
    
    @pytest.mark.asyncio
    async def test_tool_calling(self):
        """测试工具调用"""
        from src.llm import create_allapi_client
        
        client = create_allapi_client()
        
        messages = [
            {"role": "user", "content": "Please calculate: (100 + 50) / 3"}
        ]
        
        tools = [
            {
                "name": "calculator",
                "description": "Perform mathematical calculations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression"}
                    },
                    "required": ["expression"]
                }
            }
        ]
        
        response = await client.complete(messages, tools=tools)
        
        # 应该调用工具或直接给出答案
        assert response.content or response.has_tool_calls


class TestCodeExecution:
    """代码执行场景测试"""
    
    @pytest.mark.asyncio
    async def test_python_execution(self):
        """测试Python代码执行"""
        from src.tools import code_executor
        
        code = """
result = sum(range(1, 11))
print(f"Sum of 1 to 10: {result}")
"""
        
        result = await code_executor.execute(code=code)
        
        assert result.status.value == "success"
        assert "55" in str(result.output)
    
    @pytest.mark.asyncio
    async def test_data_analysis(self):
        """测试数据分析"""
        from src.tools.code_executor import DataAnalysisTool
        
        tool = DataAnalysisTool()
        
        code = """
import pandas as pd

data = {'name': ['Alice', 'Bob', 'Charlie'], 'age': [25, 30, 35]}
df = pd.DataFrame(data)
print(df.describe())
"""
        
        result = await tool.execute(code=code)
        
        assert result.status.value == "success"


class TestMultiStepTask:
    """多步任务场景测试"""
    
    @pytest.mark.asyncio
    async def test_plan_and_execute(self):
        """测试规划和执行"""
        from src.agents import PlannerAgent, ExecutorAgent
        from src.llm import create_allapi_client
        from src.tools import get_global_registry, setup_default_tools
        
        # 设置工具
        setup_default_tools()
        registry = get_global_registry()
        
        # 创建Agents
        llm = create_allapi_client()
        planner = PlannerAgent(llm)
        
        # 测试规划
        task = "Calculate the sum of squares from 1 to 5"
        plan = await planner.create_plan(task)
        
        assert plan is not None
        assert len(plan.steps) > 0
    
    @pytest.mark.asyncio
    async def test_context_management(self):
        """测试上下文管理"""
        from src.context import ContextWindow, TokenCounter
        
        window = ContextWindow(max_tokens=1000)
        
        # 添加消息
        window.set_system_message("You are a helpful assistant.")
        window.add_user_message("Hello")
        window.add_assistant_message("Hi there!")
        window.add_user_message("How are you?")
        
        # 获取消息
        messages = window.get_messages()
        
        assert len(messages) == 4
        assert window.get_total_tokens() > 0
        assert window.get_usage_ratio() < 1.0


class TestToolChain:
    """工具链场景测试"""
    
    @pytest.mark.asyncio
    async def test_sequential_tools(self):
        """测试顺序工具调用"""
        from src.tools import calculator, text_processor
        
        # 先计算
        calc_result = await calculator.execute(expression="10 * 5")
        assert calc_result.status.value == "success"
        
        # 再处理文本
        text_result = await text_processor.execute(
            text=f"The result is {calc_result.output}",
            operation="upper"
        )
        assert text_result.status.value == "success"
        assert "50" in str(text_result.output)


class TestMemorySystem:
    """记忆系统场景测试"""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """测试存储和检索"""
        from src.memory import MemoryStore, MemoryQuery
        
        store = MemoryStore(storage_path="data/test_memory")
        
        # 存储
        memory_id = await store.store(
            content="Python is a programming language",
            tags=["programming", "python"]
        )
        
        assert memory_id is not None
        
        # 检索
        results = await store.search(MemoryQuery(
            query="programming language",
            limit=5
        ))
        
        assert len(results) > 0


class TestMonitoring:
    """监控场景测试"""
    
    def test_metrics_collection(self):
        """测试指标收集"""
        from src.monitor import MetricsCollector
        
        collector = MetricsCollector()
        
        # 记录LLM调用
        collector.record_llm_call(
            model="doubao-seed-1-8-251228",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200,
            success=True
        )
        
        # 获取摘要
        summary = collector.get_summary("1h")
        
        assert summary.llm_calls >= 1
    
    def test_token_tracking(self):
        """测试Token跟踪"""
        from src.monitor import TokenTracker
        
        tracker = TokenTracker()
        
        tracker.track(
            model="doubao-seed-1-8-251228",
            input_tokens=100,
            output_tokens=50
        )
        
        usage = tracker.get_usage("today")
        
        assert usage.total_tokens == 150


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

