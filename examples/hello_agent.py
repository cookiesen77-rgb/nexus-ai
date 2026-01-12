"""
Hello Agent 示例

演示基础的 LLM 对话功能
"""

import asyncio
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.llm import create_claude_client, create_openai_client
from src.utils import setup_logging, info, error

# 加载环境变量
load_dotenv()


async def hello_claude():
    """使用Claude进行简单对话"""
    info("正在连接 Claude 4.5 Sonnet...")

    try:
        client = create_claude_client()

        messages = [
            {"role": "user", "content": "你好！请用一句话介绍你自己。"}
        ]

        response = await client.complete(messages=messages)

        print(f"\n🤖 Claude: {response.content}")
        print(f"\n📊 Token使用: {response.usage}")

        return response

    except Exception as e:
        error(f"Claude 调用失败: {e}")
        raise


async def hello_openai():
    """使用OpenAI兼容API进行简单对话"""
    info("正在连接 GPT 5.2...")

    try:
        client = create_openai_client()

        messages = [
            {"role": "user", "content": "你好！请用一句话介绍你自己。"}
        ]

        response = await client.complete(messages=messages)

        print(f"\n🤖 GPT: {response.content}")
        print(f"\n📊 Token使用: {response.usage}")

        return response

    except Exception as e:
        error(f"OpenAI 调用失败: {e}")
        raise


async def multi_turn_conversation():
    """多轮对话示例"""
    info("开始多轮对话...")

    client = create_claude_client()
    messages = []

    conversations = [
        "你好，我想学习Python编程",
        "请给我推荐一个适合初学者的项目",
        "这个项目大概需要多长时间完成？"
    ]

    for user_input in conversations:
        print(f"\n👤 用户: {user_input}")

        messages.append({"role": "user", "content": user_input})

        response = await client.complete(messages=messages)

        print(f"🤖 Claude: {response.content}")

        # 添加助手回复到消息历史
        messages.append({"role": "assistant", "content": response.content})


async def main():
    """主函数"""
    # 配置日志
    setup_logging(level="INFO")

    print("=" * 50)
    print("Manus AI Agent - Hello World 示例")
    print("=" * 50)

    # 检查API密钥
    claude_key = os.getenv("CLAUDE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not claude_key and not openai_key:
        print("\n⚠️  警告: 未设置API密钥")
        print("请在 .env 文件中设置 CLAUDE_API_KEY 或 OPENAI_API_KEY")
        print("\n示例:")
        print("  CLAUDE_API_KEY=YOUR_CLAUDE_API_KEY")
        print("  CLAUDE_BASE_URL=https://your-proxy.com  # 如果使用中转API")
        return

    # 运行示例
    if claude_key:
        print("\n--- 测试 Claude 4.5 Sonnet ---")
        try:
            await hello_claude()
        except Exception as e:
            print(f"❌ Claude测试失败: {e}")

    if openai_key:
        print("\n--- 测试 GPT 5.2 ---")
        try:
            await hello_openai()
        except Exception as e:
            print(f"❌ OpenAI测试失败: {e}")

    # 多轮对话示例（仅在Claude可用时运行）
    if claude_key:
        print("\n--- 多轮对话示例 ---")
        try:
            await multi_turn_conversation()
        except Exception as e:
            print(f"❌ 多轮对话失败: {e}")

    print("\n" + "=" * 50)
    print("示例运行完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
