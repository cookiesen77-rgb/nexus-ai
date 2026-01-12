"""
简单任务示例

演示使用SimpleAgent执行基础任务
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.agents import create_simple_agent, AgentConfig
from src.utils import setup_logging, info

# 加载环境变量
load_dotenv()


async def simple_conversation():
    """简单对话示例"""
    print("\n--- 简单对话示例 ---\n")

    # 创建LLM客户端
    llm = create_claude_client()

    # 创建Agent
    agent = create_simple_agent(
        name="对话助手",
        llm=llm,
        max_iterations=5
    )

    # 执行任务
    result = await agent.execute(
        task="请用简短的话解释什么是人工智能，并举一个日常生活中的例子。"
    )

    if result.success:
        print(f"✅ 任务完成:\n{result.output}")
        print(f"\n📊 统计: {result.metadata}")
    else:
        print(f"❌ 任务失败: {result.error}")


async def math_problem():
    """数学问题示例"""
    print("\n--- 数学问题示例 ---\n")

    llm = create_claude_client()

    agent = create_simple_agent(
        name="数学助手",
        llm=llm,
        system_prompt="""你是一个数学助手，擅长解决各种数学问题。
请一步一步解释你的思路，并给出最终答案。"""
    )

    result = await agent.execute(
        task="如果一个长方形的长是8厘米，宽是5厘米，求它的面积和周长。"
    )

    if result.success:
        print(f"✅ 答案:\n{result.output}")
    else:
        print(f"❌ 失败: {result.error}")


async def code_explanation():
    """代码解释示例"""
    print("\n--- 代码解释示例 ---\n")

    llm = create_claude_client()

    agent = create_simple_agent(
        name="代码助手",
        llm=llm,
        system_prompt="你是一个编程助手，擅长解释代码和编程概念。"
    )

    code = '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
'''

    result = await agent.execute(
        task=f"请解释以下Python代码的功能和工作原理:\n```python{code}```"
    )

    if result.success:
        print(f"✅ 解释:\n{result.output}")
    else:
        print(f"❌ 失败: {result.error}")


async def multi_turn_task():
    """多轮任务示例"""
    print("\n--- 多轮任务示例 ---\n")

    llm = create_claude_client()

    agent = create_simple_agent(
        name="写作助手",
        llm=llm,
        system_prompt="你是一个写作助手，帮助用户改进和优化文章。"
    )

    # 第一轮
    result1 = await agent.execute(
        task="请帮我写一个关于'保护环境'的开头段落，大约50字。"
    )

    if result1.success:
        print(f"第一轮结果:\n{result1.output}\n")

        # 第二轮，带上上下文
        result2 = await agent.execute(
            task="请在这个基础上，添加一个具体的例子。",
            context={
                "history": [
                    {"role": "user", "content": "请帮我写一个关于'保护环境'的开头段落"},
                    {"role": "assistant", "content": result1.output}
                ]
            }
        )

        if result2.success:
            print(f"第二轮结果:\n{result2.output}")


async def main():
    """主函数"""
    setup_logging(level="INFO")

    print("=" * 60)
    print("Manus AI Agent - 简单任务示例")
    print("=" * 60)

    # 检查API密钥
    if not os.getenv("CLAUDE_API_KEY"):
        print("\n⚠️  错误: 未设置 CLAUDE_API_KEY")
        print("请在 .env 文件中设置 API 密钥")
        return

    try:
        # 运行各个示例
        await simple_conversation()
        await math_problem()
        await code_explanation()
        await multi_turn_task()

    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

