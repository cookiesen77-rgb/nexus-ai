"""
Planner Agent 测试
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.planner import PlannerAgent, create_planner_agent
from src.agents.base import AgentConfig
from src.core.task import Plan, PlanStep, Task, TaskStatus, StepStatus
from src.llm.base import LLMResponse, StopReason


class TestPlanStep:
    """测试计划步骤"""

    def test_step_creation(self):
        """测试步骤创建"""
        step = PlanStep(
            id="step_1",
            action="搜索信息",
            tool="web_search",
            parameters={"query": "Python"},
            expected_output="搜索结果"
        )
        
        assert step.id == "step_1"
        assert step.tool == "web_search"
        assert step.status == StepStatus.PENDING
        assert not step.is_complete

    def test_step_lifecycle(self):
        """测试步骤生命周期"""
        step = PlanStep(
            id="step_1",
            action="计算",
            expected_output="结果"
        )
        
        # 开始
        step.start()
        assert step.status == StepStatus.RUNNING
        assert step.started_at is not None
        
        # 完成
        step.complete("42")
        assert step.status == StepStatus.COMPLETED
        assert step.result == "42"
        assert step.is_complete
        assert step.is_success

    def test_step_failure(self):
        """测试步骤失败"""
        step = PlanStep(id="step_1", action="test", expected_output="test")
        
        step.start()
        step.fail("Error occurred")
        
        assert step.status == StepStatus.FAILED
        assert step.error == "Error occurred"
        assert step.is_complete
        assert not step.is_success


class TestPlan:
    """测试执行计划"""

    @pytest.fixture
    def sample_plan(self):
        """创建示例计划"""
        steps = [
            PlanStep(id="step_1", action="搜索", expected_output="搜索结果"),
            PlanStep(id="step_2", action="分析", expected_output="分析结果", depends_on=["step_1"]),
            PlanStep(id="step_3", action="总结", expected_output="最终结果", depends_on=["step_2"])
        ]
        return Plan(
            task_id="task_1",
            goal="完成任务",
            steps=steps,
            estimated_iterations=3
        )

    def test_plan_creation(self, sample_plan):
        """测试计划创建"""
        assert sample_plan.goal == "完成任务"
        assert len(sample_plan.steps) == 3
        assert sample_plan.current_step_index == 0

    def test_plan_progress(self, sample_plan):
        """测试计划进度"""
        assert sample_plan.progress == 0.0
        
        sample_plan.steps[0].complete("result1")
        assert sample_plan.progress == pytest.approx(1/3)
        
        sample_plan.steps[1].complete("result2")
        assert sample_plan.progress == pytest.approx(2/3)

    def test_plan_advance(self, sample_plan):
        """测试计划推进"""
        assert sample_plan.current_step.id == "step_1"
        
        has_next = sample_plan.advance()
        assert has_next
        assert sample_plan.current_step.id == "step_2"
        
        sample_plan.advance()
        has_next = sample_plan.advance()
        assert not has_next

    def test_plan_dependencies(self, sample_plan):
        """测试依赖检查"""
        # step_1无依赖，可执行
        assert sample_plan.can_execute_step(sample_plan.steps[0])
        
        # step_2依赖step_1，不可执行
        assert not sample_plan.can_execute_step(sample_plan.steps[1])
        
        # 完成step_1后，step_2可执行
        sample_plan.steps[0].complete("result")
        assert sample_plan.can_execute_step(sample_plan.steps[1])

    def test_plan_from_dict(self):
        """测试从字典创建计划"""
        data = {
            "goal": "测试目标",
            "steps": [
                {"id": "s1", "action": "动作1", "expected_output": "输出1"},
                {"id": "s2", "action": "动作2", "tool": "calculator", "expected_output": "输出2"}
            ],
            "estimated_iterations": 5,
            "required_tools": ["calculator"]
        }
        
        plan = Plan.from_dict(data, "task_123")
        
        assert plan.task_id == "task_123"
        assert plan.goal == "测试目标"
        assert len(plan.steps) == 2
        assert plan.steps[1].tool == "calculator"

    def test_plan_to_dict(self, sample_plan):
        """测试计划序列化"""
        data = sample_plan.to_dict()
        
        assert data["goal"] == "完成任务"
        assert len(data["steps"]) == 3
        assert "progress" in data


class TestTask:
    """测试任务"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(description="测试任务")
        
        assert task.description == "测试任务"
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_task_lifecycle(self):
        """测试任务生命周期"""
        task = Task(description="测试")
        
        task.start()
        assert task.status == TaskStatus.PLANNING
        
        plan = Plan(task_id=task.id, goal="目标", steps=[])
        task.set_plan(plan)
        assert task.status == TaskStatus.EXECUTING
        
        task.complete("结果")
        assert task.status == TaskStatus.COMPLETED
        assert task.is_complete
        assert task.is_success


class TestPlannerAgent:
    """测试PlannerAgent"""

    @pytest.fixture
    def mock_llm(self):
        """创建Mock LLM"""
        llm = MagicMock()
        llm.complete = AsyncMock()
        return llm

    @pytest.fixture
    def sample_tools(self):
        """示例工具"""
        return [
            {
                "name": "calculator",
                "description": "数学计算",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "表达式"}
                    }
                }
            },
            {
                "name": "web_search",
                "description": "网络搜索",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索词"}
                    }
                }
            }
        ]

    @pytest.mark.asyncio
    async def test_create_plan(self, mock_llm, sample_tools):
        """测试创建计划"""
        # 设置Mock响应
        plan_json = json.dumps({
            "goal": "计算圆的面积",
            "steps": [
                {
                    "id": "step_1",
                    "action": "计算面积",
                    "tool": "calculator",
                    "parameters": {"expression": "3.14159 * 5 * 5"},
                    "expected_output": "面积值"
                }
            ],
            "estimated_iterations": 2,
            "required_tools": ["calculator"]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=plan_json,
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 100, "output_tokens": 50}
        )
        
        config = AgentConfig(name="TestPlanner")
        planner = PlannerAgent(config, mock_llm, sample_tools)
        
        plan = await planner.create_plan("计算半径为5的圆的面积")
        
        assert plan.goal == "计算圆的面积"
        assert len(plan.steps) == 1
        assert plan.steps[0].tool == "calculator"
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_plan(self, mock_llm, sample_tools):
        """测试execute返回Plan"""
        plan_json = json.dumps({
            "goal": "搜索信息",
            "steps": [{"id": "s1", "action": "搜索", "expected_output": "结果"}]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=plan_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestPlanner")
        planner = PlannerAgent(config, mock_llm, sample_tools)
        
        result = await planner.execute("搜索Python信息")
        
        assert result.success
        assert isinstance(result.output, Plan)
        assert result.metadata["steps_count"] == 1

    @pytest.mark.asyncio
    async def test_replan(self, mock_llm, sample_tools):
        """测试重规划"""
        # 原计划
        original_plan = Plan(
            task_id="task_1",
            goal="原目标",
            steps=[
                PlanStep(id="s1", action="步骤1", expected_output="输出1")
            ],
            version=1
        )
        original_plan.steps[0].complete("result1")
        
        # 新计划响应
        new_plan_json = json.dumps({
            "goal": "调整后的目标",
            "steps": [
                {"id": "s1", "action": "步骤1", "expected_output": "输出1"},
                {"id": "s2", "action": "新步骤", "expected_output": "输出2"}
            ]
        })
        
        mock_llm.complete.return_value = LLMResponse(
            content=new_plan_json,
            stop_reason=StopReason.END_TURN,
            usage={}
        )
        
        config = AgentConfig(name="TestPlanner")
        planner = PlannerAgent(config, mock_llm, sample_tools)
        
        new_plan = await planner.replan(
            task="原任务",
            original_plan=original_plan,
            feedback="步骤2失败",
            failure_reason="工具调用错误"
        )
        
        assert new_plan.version == 2
        assert len(new_plan.steps) == 2

    def test_parse_json_in_markdown(self, mock_llm):
        """测试从Markdown中解析JSON"""
        config = AgentConfig(name="TestPlanner")
        planner = PlannerAgent(config, mock_llm)
        
        content = '''
        这是计划：
        ```json
        {"goal": "测试", "steps": [{"id": "s1", "action": "test", "expected_output": "result"}]}
        ```
        '''
        
        result = planner._parse_plan_response(content)
        
        assert result["goal"] == "测试"
        assert len(result["steps"]) == 1


class TestCreatePlannerAgent:
    """测试便捷创建函数"""

    def test_create_with_defaults(self):
        """测试默认参数创建"""
        mock_llm = MagicMock()
        planner = create_planner_agent(llm=mock_llm)
        
        assert planner.name == "PlannerAgent"
        assert planner.config.temperature == 0.5

    def test_create_with_custom_params(self):
        """测试自定义参数"""
        mock_llm = MagicMock()
        tools = [{"name": "test", "description": "test"}]
        
        planner = create_planner_agent(
            llm=mock_llm,
            tools=tools,
            name="CustomPlanner",
            temperature=0.3
        )
        
        assert planner.name == "CustomPlanner"
        assert len(planner.tools) == 1

