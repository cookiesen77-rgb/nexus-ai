"""
工具使用演示

展示如何使用各种工具和Agent集成
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client
from src.tools import (
    setup_default_tools,
    calculator,
    text_processor,
    web_search,
    get_global_registry
)
from src.agents import create_simple_agent
from src.utils import setup_logging, info

# 加载环境变量
load_dotenv()


async def demo_calculator():
    """演示计算器工具"""
    print("\n--- 计算器工具演示 ---\n")

    # 基础运算
    result = await calculator.run(expression="2 + 3 * 4")
    print(f"2 + 3 * 4 = {result.output}")

    result = await calculator.run(expression="sqrt(144)")
    print(f"sqrt(144) = {result.output}")

    result = await calculator.run(expression="pi * 2")
    print(f"pi * 2 = {result.output}")

    result = await calculator.run(expression="2 ** 10")
    print(f"2 ** 10 = {result.output}")

    # 错误处理
    result = await calculator.run(expression="1 / 0")
    print(f"1 / 0 = {result.error}")


async def demo_text_processor():
    """演示文本处理工具"""
    print("\n--- 文本处理工具演示 ---\n")

    sample_text = """
    Python is a high-level programming language.
    It was created by Guido van Rossum.
    Contact: python@python.org or info@example.com
    Visit https://python.org for more information.
    """

    # 文本统计
    result = await text_processor.run(text=sample_text, operation="summary_stats")
    print(f"文本统计: {result.output}")

    # 提取邮箱
    result = await text_processor.run(text=sample_text, operation="extract_emails")
    print(f"提取的邮箱: {result.output}")

    # 提取URL
    result = await text_processor.run(text=sample_text, operation="extract_urls")
    print(f"提取的URL: {result.output}")

    # 词频统计
    result = await text_processor.run(text=sample_text, operation="word_frequency")
    print(f"词频统计: {result.output}")


async def demo_web_search():
    """演示网络搜索工具"""
    print("\n--- 网络搜索工具演示 ---\n")

    result = await web_search.run(query="Python programming language", max_results=3)

    if result.is_success:
        print(f"搜索答案: {result.output.get('answer', 'N/A')[:200]}...")
        print(f"\n搜索结果数: {len(result.output['results'])}")
        for i, item in enumerate(result.output["results"], 1):
            print(f"\n{i}. {item['title']}")
            print(f"   URL: {item['url']}")
            print(f"   摘要: {item['content'][:100]}...")
    else:
        print(f"搜索失败: {result.error}")


async def demo_agent_with_tools():
    """演示Agent使用工具"""
    print("\n--- Agent工具调用演示 ---\n")

    # 检查API密钥
    if not os.getenv("CLAUDE_API_KEY"):
        print("⚠️  需要设置 CLAUDE_API_KEY 才能运行此演示")
        return

    # 设置工具
    registry = setup_default_tools()

    # 创建LLM客户端
    llm = create_claude_client()

    # 创建Agent
    agent = create_simple_agent(
        name="工具助手",
        llm=llm,
        tools=registry.get_schemas(),
        tool_executor=registry.create_executor(),
        max_iterations=5
    )

    # 测试任务1：数学计算
    print("任务1: 数学计算")
    result = await agent.execute(
        task="请帮我计算：如果一个圆的半径是5，它的面积是多少？(使用π约等于3.14159)"
    )
    if result.success:
        print(f"✅ 结果: {result.output[:300]}...")
        print(f"   工具调用次数: {result.metadata.get('tool_calls', 0)}")
    else:
        print(f"❌ 失败: {result.error}")

    # 测试任务2：文本分析
    print("\n任务2: 文本分析")
    result = await agent.execute(
        task="请分析这段文本的统计信息：'The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet.'"
    )
    if result.success:
        print(f"✅ 结果: {result.output[:300]}...")
    else:
        print(f"❌ 失败: {result.error}")


async def demo_tool_chaining():
    """演示工具链式调用"""
    print("\n--- 工具链式调用演示 ---\n")

    # 步骤1：获取文本统计
    text = "Hello World! This is a test message. Python is great for data processing."

    stats_result = await text_processor.run(text=text, operation="summary_stats")
    print(f"原始文本统计: {stats_result.output}")

    # 步骤2：计算平均单词长度
    avg_length = stats_result.output["avg_word_length"]
    calc_result = await calculator.run(expression=f"{avg_length} * 2")
    print(f"平均单词长度的两倍: {calc_result.output}")

    # 步骤3：转换文本
    upper_result = await text_processor.run(text=text, operation="to_upper")
    print(f"转换为大写: {upper_result.output}")


async def main():
    """主函数"""
    setup_logging(level="INFO")

    print("=" * 60)
    print("Manus AI Agent - 工具使用演示")
    print("=" * 60)

    # 运行各个演示
    await demo_calculator()
    await demo_text_processor()
    await demo_web_search()
    await demo_tool_chaining()
    await demo_agent_with_tools()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

