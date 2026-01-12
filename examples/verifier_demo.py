"""
Verifier Agent 演示

展示如何使用VerifierAgent验证结果
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.agents.verifier import create_verifier_agent
from src.core.task import Plan, PlanStep, VerificationResult
from src.utils import setup_logging

load_dotenv()


async def demo_step_verification():
    """步骤验证演示"""
    print("\n--- 步骤验证演示 ---\n")
    
    llm = create_claude_client()
    verifier = create_verifier_agent(llm=llm)
    
    # 创建测试步骤
    step = PlanStep(
        id="calc_step",
        action="计算圆的面积",
        expected_output="圆的面积值，约78.5"
    )
    
    # 正确结果验证
    print("验证正确结果:")
    result = await verifier.verify_step(
        step=step,
        actual_result="78.53981633974483",
        task_goal="计算半径为5的圆的面积"
    )
    
    print(f"  通过: {result.passed}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  反馈: {result.feedback[:100]}...")
    
    # 错误结果验证
    print("\n验证错误结果:")
    result = await verifier.verify_step(
        step=step,
        actual_result="50",
        task_goal="计算半径为5的圆的面积"
    )
    
    print(f"  通过: {result.passed}")
    print(f"  需要重试: {result.needs_retry}")
    print(f"  需要重规划: {result.needs_replan}")
    if result.suggestions:
        print(f"  建议: {result.suggestions}")


async def demo_plan_verification():
    """计划验证演示"""
    print("\n--- 计划验证演示 ---\n")
    
    llm = create_claude_client()
    verifier = create_verifier_agent(llm=llm)
    
    # 创建已执行的计划
    steps = [
        PlanStep(
            id="step_1",
            action="获取数据",
            expected_output="数据列表"
        ),
        PlanStep(
            id="step_2",
            action="处理数据",
            expected_output="处理后的数据"
        ),
        PlanStep(
            id="step_3",
            action="生成报告",
            expected_output="最终报告"
        )
    ]
    
    # 模拟执行结果
    steps[0].complete("[1, 2, 3, 4, 5]")
    steps[1].complete("处理完成: 平均值=3, 总和=15")
    steps[2].complete("数据报告: 5个数据点, 平均值3, 总和15")
    
    plan = Plan(
        task_id="data_task",
        goal="分析数据并生成报告",
        steps=steps
    )
    
    # 验证整个计划
    result = await verifier.verify_plan(
        plan=plan,
        original_task="对数据[1,2,3,4,5]进行分析并生成报告"
    )
    
    print(f"最终验证结果:")
    print(f"  通过: {result.passed}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  反馈: {result.feedback[:200]}...")


async def demo_quick_verification():
    """快速验证演示"""
    print("\n--- 快速验证演示 ---\n")
    
    llm = create_claude_client()
    verifier = create_verifier_agent(llm=llm)
    
    test_cases = [
        ("数值计算结果", "计算结果: 42"),
        ("搜索结果列表", "找到3个相关结果: Python, Java, JavaScript"),
        ("错误处理", "成功执行"),
        ("详细报告", "简短回答"),
    ]
    
    for expected, actual in test_cases:
        result = await verifier.quick_verify(expected, actual)
        status = "✅" if result.passed else "❌"
        print(f"{status} 预期: '{expected}' -> 实际: '{actual}'")
        print(f"   置信度: {result.confidence:.2f}")


async def demo_verification_workflow():
    """完整验证工作流演示"""
    print("\n--- 完整验证工作流演示 ---\n")
    
    llm = create_claude_client()
    verifier = create_verifier_agent(llm=llm, confidence_threshold=0.7)
    
    # 模拟一个执行流程
    task = "搜索Python最新版本并计算版本号的数字和"
    
    steps = [
        {
            "step": PlanStep(
                id="search",
                action="搜索Python版本",
                expected_output="Python版本号"
            ),
            "result": "Python 3.12"
        },
        {
            "step": PlanStep(
                id="calc",
                action="计算版本号数字和",
                expected_output="数字和"
            ),
            "result": "3 + 1 + 2 = 6"
        }
    ]
    
    print(f"任务: {task}\n")
    
    all_passed = True
    for item in steps:
        step = item["step"]
        result = item["result"]
        
        print(f"验证步骤: {step.action}")
        verification = await verifier.verify_step(
            step=step,
            actual_result=result,
            task_goal=task
        )
        
        if verification.passed:
            print(f"  ✅ 通过 (置信度: {verification.confidence:.2f})")
            step.complete(result)
        else:
            print(f"  ❌ 未通过")
            print(f"  反馈: {verification.feedback[:100]}...")
            if verification.needs_retry:
                print("  建议: 重试此步骤")
            if verification.needs_replan:
                print("  建议: 重新规划")
            all_passed = False
            break
    
    print(f"\n工作流结果: {'全部通过' if all_passed else '存在失败'}")


async def main():
    setup_logging(level="INFO")
    
    print("=" * 60)
    print("Manus AI Agent - Verifier Agent 演示")
    print("=" * 60)
    
    if not os.getenv("CLAUDE_API_KEY"):
        print("\n⚠️  需要设置 CLAUDE_API_KEY")
        return
    
    try:
        await demo_step_verification()
        await demo_plan_verification()
        await demo_quick_verification()
        await demo_verification_workflow()
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

