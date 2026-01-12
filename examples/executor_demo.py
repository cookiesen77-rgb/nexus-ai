"""
Executor Agent 演示

展示如何使用ExecutorAgent执行任务
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.agents.executor import create_executor_agent
from src.agents.planner import create_planner_agent
from src.core.task import Plan, PlanStep
from src.tools import setup_default_tools, get_global_registry
from src.utils import setup_logging, info

load_dotenv()


async def demo_execute_single_step():
    """执行单个步骤演示"""
    print("\n--- 执行单个步骤演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    executor = create_executor_agent(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        name="步骤执行器"
    )
    
    # 创建一个计算步骤
    step = PlanStep(
        id="calc_step",
        action="计算圆的面积",
        tool="calculator",
        parameters={"expression": "3.14159 * 5 * 5"},
        expected_output="圆的面积值"
    )
    
    result = await executor.execute_step(step)
    
    if result.success:
        print(f"✅ 步骤执行成功!")
        print(f"   结果: {result.output}")
        print(f"   步骤状态: {step.status.value}")
    else:
        print(f"❌ 执行失败: {result.error}")


async def demo_execute_plan():
    """执行完整计划演示"""
    print("\n--- 执行完整计划演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    executor = create_executor_agent(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor()
    )
    
    # 创建一个多步骤计划
    steps = [
        PlanStep(
            id="step_1",
            action="计算长方形面积",
            tool="calculator",
            parameters={"expression": "8 * 5"},
            expected_output="面积值"
        ),
        PlanStep(
            id="step_2",
            action="计算长方形周长",
            tool="calculator",
            parameters={"expression": "2 * (8 + 5)"},
            expected_output="周长值",
            depends_on=["step_1"]
        ),
        PlanStep(
            id="step_3",
            action="计算面积与周长的比值",
            tool="calculator",
            parameters={"expression": "40 / 26"},
            expected_output="比值",
            depends_on=["step_2"]
        )
    ]
    
    plan = Plan(
        task_id="geometry_task",
        goal="计算长方形的面积、周长和它们的比值",
        steps=steps,
        required_tools=["calculator"]
    )
    
    print(f"计划目标: {plan.goal}")
    print(f"步骤数: {len(plan.steps)}")
    print()
    
    result = await executor.execute_plan(plan)
    
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  进度: {plan.progress * 100:.0f}%")
    print(f"  执行步骤数: {result.metadata['steps_executed']}")
    
    print(f"\n各步骤结果:")
    for step in plan.steps:
        status = "✅" if step.is_success else "❌"
        print(f"  {status} {step.id}: {step.action} -> {step.result}")


async def demo_planner_executor_integration():
    """Planner + Executor 集成演示"""
    print("\n--- Planner + Executor 集成演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    # 创建Planner和Executor
    planner = create_planner_agent(
        llm=llm,
        tools=registry.get_schemas()
    )
    
    executor = create_executor_agent(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor()
    )
    
    # 任务
    task = "分析文本'Hello World, this is a test message.'的统计信息，然后计算单词数量的平方"
    
    print(f"任务: {task}\n")
    
    # 1. Planner规划
    print("1. 规划阶段...")
    plan_result = await planner.execute(task)
    
    if not plan_result.success:
        print(f"❌ 规划失败: {plan_result.error}")
        return
    
    plan = plan_result.output
    print(f"   计划创建成功: {len(plan.steps)}个步骤")
    for step in plan.steps:
        print(f"   - {step.action}")
    
    # 2. Executor执行
    print("\n2. 执行阶段...")
    exec_result = await executor.execute_plan(plan)
    
    if exec_result.success:
        print(f"✅ 执行成功!")
        print(f"   最终结果: {exec_result.output}")
    else:
        print(f"❌ 执行失败: {exec_result.error}")


async def demo_error_handling():
    """错误处理演示"""
    print("\n--- 错误处理演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    executor = create_executor_agent(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor()
    )
    
    # 创建一个会失败的步骤（除零）
    step = PlanStep(
        id="error_step",
        action="除零计算",
        tool="calculator",
        parameters={"expression": "1 / 0"},
        expected_output="结果"
    )
    
    result = await executor.execute_step(step)
    
    print(f"执行结果: {'成功' if result.success else '失败'}")
    print(f"步骤状态: {step.status.value}")
    if step.error:
        print(f"错误信息: {step.error}")


async def main():
    setup_logging(level="INFO")
    
    print("=" * 60)
    print("Manus AI Agent - Executor Agent 演示")
    print("=" * 60)
    
    if not os.getenv("CLAUDE_API_KEY"):
        print("\n⚠️  需要设置 CLAUDE_API_KEY")
        return
    
    try:
        await demo_execute_single_step()
        await demo_execute_plan()
        await demo_planner_executor_integration()
        await demo_error_handling()
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

