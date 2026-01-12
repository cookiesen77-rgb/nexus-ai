"""
多Agent协作演示

展示Planner、Executor、Verifier协作完成复杂任务
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.agents.orchestrator import create_orchestrator, OrchestratorConfig
from src.tools import setup_default_tools, get_global_registry
from src.utils import setup_logging, info

load_dotenv()


async def demo_simple_orchestration():
    """简单协调演示"""
    print("\n--- 简单协调演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    orchestrator = create_orchestrator(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        max_iterations=10
    )
    
    task = "计算一个边长为6的正方形的面积和周长"
    print(f"任务: {task}\n")
    
    result = await orchestrator.execute(task)
    
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  最终输出: {result.final_output}")
    print(f"  迭代次数: {result.metadata.get('iterations', 0)}")
    print(f"  重规划次数: {result.metadata.get('replans', 0)}")
    print(f"  完成步骤: {result.metadata.get('steps_completed', 0)}")


async def demo_complex_task():
    """复杂任务演示"""
    print("\n--- 复杂任务演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    orchestrator = create_orchestrator(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        max_iterations=15,
        verify_steps=True
    )
    
    task = """
    请完成以下任务：
    1. 分析文本"Python is a great programming language for AI"的统计信息
    2. 计算文本中单词数量的平方
    3. 搜索Python AI相关信息
    最后给出综合结果
    """
    
    print(f"任务: {task}\n")
    
    result = await orchestrator.execute(task)
    
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  任务状态: {result.task.status.value}")
    
    if result.success:
        print(f"\n最终输出:")
        output = str(result.final_output)
        if len(output) > 500:
            print(f"  {output[:500]}...")
        else:
            print(f"  {output}")
    else:
        print(f"  错误: {result.error}")
    
    print(f"\n统计:")
    print(f"  总迭代: {result.metadata.get('iterations', 0)}")
    print(f"  重规划: {result.metadata.get('replans', 0)}")
    print(f"  计划版本: {result.metadata.get('plan_version', 1)}")


async def demo_with_verification():
    """带验证的演示"""
    print("\n--- 带验证的协调演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    config = OrchestratorConfig(
        max_iterations=10,
        max_replan_attempts=2,
        max_retry_per_step=2,
        verify_each_step=True,
        verify_final_result=True
    )
    
    from src.agents.orchestrator import Orchestrator
    orchestrator = Orchestrator(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        config=config
    )
    
    task = "计算圆周率乘以10的结果，并验证结果是否约等于31.4"
    print(f"任务: {task}\n")
    
    result = await orchestrator.execute(task)
    
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  输出: {result.final_output}")
    
    if result.task.plan:
        print(f"\n计划执行详情:")
        for step in result.task.plan.steps:
            status = "✅" if step.is_success else "❌"
            print(f"  {status} {step.id}: {step.action}")
            if step.result:
                print(f"      结果: {str(step.result)[:100]}")


async def demo_workflow_visualization():
    """工作流可视化演示"""
    print("\n--- 工作流可视化演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    orchestrator = create_orchestrator(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor()
    )
    
    task = "搜索Python最新版本，然后计算版本号数字之和"
    print(f"任务: {task}\n")
    print("工作流程:")
    print("  [用户] → [Orchestrator] → [Planner] → 制定计划")
    print("                         → [Executor] → 执行步骤")
    print("                         → [Verifier] → 验证结果")
    print("                         → [Orchestrator] → 协调决策")
    print()
    
    result = await orchestrator.execute(task)
    
    print(f"\n最终结果:")
    print(f"  状态: {'成功' if result.success else '失败'}")
    print(f"  输出: {result.final_output}")
    
    # 显示工作流统计
    print(f"\n工作流统计:")
    print(f"  ├── Planner: 生成{result.metadata.get('plan_version', 1)}个计划版本")
    print(f"  ├── Executor: 执行{result.metadata.get('steps_completed', 0)}个步骤")
    print(f"  ├── Verifier: 验证{result.metadata.get('iterations', 0)}次")
    print(f"  └── 总迭代: {result.metadata.get('iterations', 0)}次")


async def demo_error_recovery():
    """错误恢复演示"""
    print("\n--- 错误恢复演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    
    config = OrchestratorConfig(
        max_iterations=10,
        max_replan_attempts=3,
        max_retry_per_step=2
    )
    
    from src.agents.orchestrator import Orchestrator
    orchestrator = Orchestrator(
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        config=config
    )
    
    # 一个可能需要重试的任务
    task = "计算sqrt(16)的结果，然后将结果乘以自身"
    print(f"任务: {task}\n")
    
    result = await orchestrator.execute(task)
    
    print(f"执行结果:")
    print(f"  成功: {result.success}")
    print(f"  输出: {result.final_output}")
    print(f"  重规划次数: {result.metadata.get('replans', 0)}")
    
    if result.metadata.get('replans', 0) > 0:
        print("\n  ⚠️  任务经历了重规划，系统自动恢复并完成")


async def main():
    setup_logging(level="INFO")
    
    print("=" * 70)
    print("Manus AI Agent - 多Agent协作演示")
    print("=" * 70)
    print("\n协作架构:")
    print("  Orchestrator (协调器)")
    print("      ├── PlannerAgent (规划)")
    print("      ├── ExecutorAgent (执行)")
    print("      └── VerifierAgent (验证)")
    
    if not os.getenv("CLAUDE_API_KEY"):
        print("\n⚠️  需要设置 CLAUDE_API_KEY")
        return
    
    try:
        await demo_simple_orchestration()
        await demo_complex_task()
        await demo_with_verification()
        await demo_workflow_visualization()
        await demo_error_recovery()
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

