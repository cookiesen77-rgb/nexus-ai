#!/usr/bin/env python3
"""
ALLAPI 集成演示

展示模型切换功能和双模型使用
"""

import asyncio
import os
import sys
sys.path.insert(0, '.')

# 使用环境变量（不要在仓库中写死密钥）
os.environ["ALLAPI_BASE_URL"] = os.environ.get("ALLAPI_BASE_URL", "https://nexusapi.cn/v1")

from src.llm import (
    create_allapi_client,
    ModelSwitcher,
    ModelConfig,
    get_model_switcher,
    enable_thinking_mode,
    disable_thinking_mode,
    get_current_model
)


async def demo_basic_chat():
    """基本对话演示"""
    print("\n" + "=" * 50)
    print("1. 基本对话 (默认模型)")
    print("=" * 50)
    
    client = create_allapi_client(thinking_mode=False)
    
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍一下Python语言的优点。"}
    ]
    
    response = await client.complete(messages)
    
    print(f"模型: {response.model}")
    print(f"响应: {response.content}")
    print(f"Token: 输入={response.usage.get('input_tokens', 'N/A')}, 输出={response.usage.get('output_tokens', 'N/A')}")


async def demo_thinking_mode():
    """思考模式演示"""
    print("\n" + "=" * 50)
    print("2. 思考模式 (深度推理)")
    print("=" * 50)
    
    client = create_allapi_client(thinking_mode=True)
    
    messages = [
        {"role": "user", "content": "分析一下为什么Python适合AI开发，给出三个核心原因。"}
    ]
    
    response = await client.complete(messages, max_tokens=500)
    
    print(f"模型: {response.model}")
    print(f"响应: {response.content[:500]}...")
    print(f"Token: 输入={response.usage.get('input_tokens', 'N/A')}, 输出={response.usage.get('output_tokens', 'N/A')}")


async def demo_model_switcher():
    """模型切换器演示"""
    print("\n" + "=" * 50)
    print("3. 模型切换器")
    print("=" * 50)
    
    config = ModelConfig(
        default_model="doubao-seed-1-8-251228",
        thinking_model="doubao-seed-1-8-251228-thinking",
        base_url="https://nexusapi.cn/v1",
        api_key=os.environ["ALLAPI_KEY"]
    )
    
    switcher = ModelSwitcher(config)
    
    # 显示初始状态
    print(f"初始状态: {switcher}")
    print(f"当前模型: {switcher.get_current_model()}")
    
    # 启用思考模式
    switcher.enable_thinking()
    print(f"\n启用思考模式后: {switcher}")
    print(f"当前模型: {switcher.get_current_model()}")
    
    # 使用上下文管理器临时切换
    print("\n使用上下文管理器临时切换到默认模式:")
    with switcher.default():
        print(f"  临时模式: {switcher}")
        print(f"  当前模型: {switcher.get_current_model()}")
    
    print(f"\n退出上下文后: {switcher}")
    print(f"当前模型: {switcher.get_current_model()}")
    
    # 获取完整状态
    print(f"\n完整状态: {switcher.get_status()}")


async def demo_tool_calling():
    """工具调用演示"""
    print("\n" + "=" * 50)
    print("4. 工具调用 (默认模型)")
    print("=" * 50)
    
    client = create_allapi_client(thinking_mode=False)
    
    messages = [
        {"role": "user", "content": "请帮我计算 (15 + 25) * 3 的结果"}
    ]
    
    tools = [
        {
            "name": "calculator",
            "description": "进行数学计算",
            "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式"
                    }
                },
                "required": ["expression"]
            }
        }
    ]
    
    response = await client.complete(messages, tools=tools)
    
    print(f"模型: {response.model}")
    
    if response.has_tool_calls:
        print("工具调用:")
        for tc in response.tool_calls:
            print(f"  函数: {tc.name}")
            print(f"  参数: {tc.parameters}")
    else:
        print(f"响应: {response.content}")


async def demo_global_switcher():
    """全局切换器演示"""
    print("\n" + "=" * 50)
    print("5. 全局模型切换")
    print("=" * 50)
    
    print(f"当前全局模型: {get_current_model()}")
    
    enable_thinking_mode()
    print(f"启用思考模式后: {get_current_model()}")
    
    disable_thinking_mode()
    print(f"禁用思考模式后: {get_current_model()}")


async def main():
    """主函数"""
    print("=" * 50)
    print("ALLAPI 集成演示")
    print("=" * 50)
    print(f"Base URL: {os.environ['ALLAPI_BASE_URL']}")
    print(f"默认模型: doubao-seed-1-8-251228")
    print(f"思考模型: doubao-seed-1-8-251228-thinking")
    
    await demo_basic_chat()
    await demo_thinking_mode()
    await demo_model_switcher()
    await demo_tool_calling()
    await demo_global_switcher()
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

