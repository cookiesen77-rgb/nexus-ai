"""
Planner Agent 演示

展示如何使用PlannerAgent进行任务规划
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.agents.planner import create_planner_agent
from src.tools import setup_default_tools, get_global_registry
from src.utils import setup_logging, info

# 加载环境变量
load_dotenv()


async def demo_simple_planning():
    """简单任务规划演示"""
    print("\n--- 简单任务规划演示 ---\n")
    
    # 设置工具
    registry = setup_default_tools()
    
    # 创建LLM和Planner
    llm = create_claude_client()
    planner = create_planner_agent(
        llm=llm,
        tools=registry.get_schemas(),
        name="任务规划师"
    )
    
    # 执行规划
    task = "计算一个半径为7厘米的圆的面积和周长"
    result = await planner.execute(task)
    
    if result.success:
        plan = result.output
        print(f"✅ 规划成功!")
        print(f"\n目标: {plan.goal}")
        print(f"预计迭代: {plan.estimated_iterations}")
        print(f"所需工具: {plan.required_tools}")
        print(f"\n执行步骤:")
        for i, step in enumerate(plan.steps, 1):
            print(f"  {i}. [{step.id}] {step.action}")
            if step.tool:
                print(f"     工具: {step.tool}")
                print(f"     参数: {step.parameters}")
            print(f"     预期输出: {step.expected_output}")
    else:
        print(f"❌ 规划失败: {result.error}")


async def demo_complex_planning():
    """复杂任务规划演示"""
    print("\n--- 复杂任务规划演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    planner = create_planner_agent(
        llm=llm,
        tools=registry.get_schemas()
    )
    
    task = """
    帮我完成以下任务：
    1. 搜索最新的Python 3.12新特性
    2. 统计搜索结果中的关键词频率
    3. 计算结果数量的平方根
    最后给出一个总结报告
    """
    
    result = await planner.execute(task)
    
    if result.success:
        plan = result.output
        print(f"✅ 复杂任务规划成功!")
        print(f"\n目标: {plan.goal}")
        print(f"步骤数: {len(plan.steps)}")
        print(f"\n完整计划:")
        print(plan.to_json())
    else:
        print(f"❌ 规划失败: {result.error}")


async def demo_planning_with_context():
    """带上下文的规划演示"""
    print("\n--- 带上下文的规划演示 ---\n")
    
    registry = setup_default_tools()
    llm = create_claude_client()
    planner = create_planner_agent(
        llm=llm,
        tools=registry.get_schemas()
    )
    
    task = "根据之前的计算结果，生成一份数据报告"
    context = {
        "previous_results": {
            "calculation_1": 42,
            "calculation_2": 3.14159,
            "text_analysis": {"words": 100, "sentences": 5}
        },
        "user_preference": "简洁格式"
    }
    
    result = await planner.execute(task, context=context)
    
    if result.success:
        plan = result.output
        print(f"✅ 上下文规划成功!")
        print(f"目标: {plan.goal}")
        print(f"步骤: {[s.action for s in plan.steps]}")
    else:
        print(f"❌ 失败: {result.error}")


async def demo_plan_structure():
    """计划结构演示"""
    print("\n--- 计划结构演示 ---\n")
    
    from src.core.task import Plan, PlanStep, StepStatus
    
    # 手动创建计划结构
    steps = [
        PlanStep(
            id="step_1",
            action="获取数据",
            tool="web_search",
            parameters={"query": "Python tutorials"},
            expected_output="搜索结果列表"
        ),
        PlanStep(
            id="step_2",
            action="处理数据",
            tool="text_processor",
            parameters={"text": "", "operation": "summary_stats"},
            expected_output="文本统计",
            depends_on=["step_1"]
        ),
        PlanStep(
            id="step_3",
            action="计算汇总",
            tool="calculator",
            parameters={"expression": ""},
            expected_output="最终数值",
            depends_on=["step_2"]
        )
    ]
    
    plan = Plan(
        task_id="demo_task",
        goal="获取并分析Python教程数据",
        steps=steps,
        estimated_iterations=5,
        required_tools=["web_search", "text_processor", "calculator"]
    )
    
    print(f"计划目标: {plan.goal}")
    print(f"总步骤数: {len(plan.steps)}")
    print(f"当前进度: {plan.progress * 100:.1f}%")
    
    # 模拟执行
    print("\n模拟执行过程:")
    
    for step in plan.steps:
        if plan.can_execute_step(step):
            print(f"  执行: {step.action}")
            step.start()
            step.complete(f"{step.action}的结果")
            print(f"    ✅ 完成")
        else:
            print(f"  跳过: {step.action} (依赖未满足)")
    
    print(f"\n最终进度: {plan.progress * 100:.1f}%")
    print(f"计划完成: {plan.is_complete}")
    print(f"计划成功: {plan.is_success}")


async def main():
    """主函数"""
    setup_logging(level="INFO")
    
    print("=" * 60)
    print("Manus AI Agent - Planner Agent 演示")
    print("=" * 60)
    
    # 检查API密钥
    if not os.getenv("CLAUDE_API_KEY"):
        print("\n⚠️  需要设置 CLAUDE_API_KEY")
        print("将只运行不需要API的演示...\n")
        await demo_plan_structure()
        return
    
    try:
        await demo_simple_planning()
        await demo_complex_planning()
        await demo_planning_with_context()
        await demo_plan_structure()
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

