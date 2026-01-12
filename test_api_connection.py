"""
API连接测试脚本
"""

import sys
import os
sys.path.insert(0, '.')

from anthropic import Anthropic
from openai import OpenAI

# API配置
CLAUDE_BASE_URL = "https://new-api.xhm.gd.cn"
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

OPENAI_BASE_URL = "https://new-api.xhm.gd.cn/v1"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def test_claude():
    """测试Claude API连接"""
    print("\n=== 测试 Claude API ===")
    print(f"Base URL: {CLAUDE_BASE_URL}")

    if not CLAUDE_API_KEY:
        raise RuntimeError("Missing CLAUDE_API_KEY. Please export CLAUDE_API_KEY before running this test.")
    
    model = "claude-sonnet-4-5-20250929"
    print(f"   使用模型: {model}")
    
    try:
        client = Anthropic(
            api_key=CLAUDE_API_KEY,
            base_url=CLAUDE_BASE_URL
        )
        
        response = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "请回复'Claude API连接成功'"}
            ]
        )
        
        print(f"✅ Claude API 连接成功!")
        print(f"   模型: {response.model}")
        print(f"   响应: {response.content[0].text}")
        print(f"   Token使用: 输入={response.usage.input_tokens}, 输出={response.usage.output_tokens}")
        return True, model
        
    except Exception as e:
        print(f"❌ Claude API 连接失败: {e}")
        return False, None

def test_fallback():
    """测试备用LLM (Claude Haiku via OpenAI兼容接口)"""
    print("\n=== 测试备用 LLM (OpenAI兼容接口) ===")
    print(f"Base URL: {OPENAI_BASE_URL}")

    if not OPENAI_API_KEY and not CLAUDE_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY/CLAUDE_API_KEY. Please export keys before running this test.")
    
    # 使用Claude Key调用Haiku模型作为备用
    model = "claude-haiku-4-5-20251001"
    print(f"   使用模型: {model}")
    
    try:
        # 优先使用 OPENAI_API_KEY；若未设置则回退到 CLAUDE_API_KEY（取决于你的网关策略）
        client = OpenAI(api_key=OPENAI_API_KEY or CLAUDE_API_KEY, base_url=OPENAI_BASE_URL)
        
        response = client.chat.completions.create(
            model=model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "请回复'备用LLM连接成功'"}
            ]
        )
        
        print(f"✅ 备用LLM 连接成功!")
        print(f"   模型: {response.model}")
        print(f"   响应: {response.choices[0].message.content}")
        if response.usage:
            print(f"   Token使用: 输入={response.usage.prompt_tokens}, 输出={response.usage.completion_tokens}")
        return True, model
        
    except Exception as e:
        print(f"❌ 备用LLM 连接失败: {e}")
        return False, None

def main():
    print("=" * 50)
    print("Manus AI Agent - API连接测试")
    print("=" * 50)
    
    claude_ok, claude_model = test_claude()
    fallback_ok, fallback_model = test_fallback()
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"  主LLM (Claude Sonnet): {'✅ 成功 (' + claude_model + ')' if claude_ok else '❌ 失败'}")
    print(f"  备用LLM (Claude Haiku): {'✅ 成功 (' + fallback_model + ')' if fallback_ok else '❌ 失败'}")
    print("=" * 50)
    
    return claude_ok and fallback_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
