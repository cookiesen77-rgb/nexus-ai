#!/usr/bin/env python3
"""
监控系统演示

展示Phase 5新增的监控、缓存和上下文管理功能
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.context import (
    TokenCounter, ContextWindow, ContextCompressor,
    ConversationTokenTracker, count_tokens, Message
)
from src.memory import (
    MemoryStore, MemoryType, remember, recall
)
from src.cache import (
    LRUCache, LLMResponseCache, get_response_cache
)
from src.monitor import (
    MetricsCollector, TokenTracker, AlertManager,
    get_metrics_collector, get_token_tracker, get_alert_manager
)
from src.queue import (
    TaskQueue, TaskPriority, get_task_queue
)


async def demo_token_counting():
    """Token计数演示"""
    print("\n" + "=" * 50)
    print("1. Token计数")
    print("=" * 50)
    
    counter = TokenCounter(model="claude-sonnet-4-5-20250929")
    
    # 计数示例
    texts = [
        "Hello, world!",
        "你好，世界！",
        "This is a longer text for testing token counting functionality.",
    ]
    
    for text in texts:
        tokens = counter.count(text)
        print(f"\n文本: {text[:30]}...")
        print(f"  Token数: {tokens}")
        print(f"  字符数: {len(text)}")
        print(f"  比率: {len(text)/tokens:.1f} chars/token")
    
    # 成本估算
    from src.context.token_counter import TokenUsage
    usage = TokenUsage(input_tokens=1000, output_tokens=500)
    cost = counter.estimate_cost(usage)
    print(f"\n成本估算 (1000 in / 500 out): ${cost:.4f}")


async def demo_context_window():
    """上下文窗口演示"""
    print("\n" + "=" * 50)
    print("2. 上下文窗口管理")
    print("=" * 50)
    
    window = ContextWindow(
        max_tokens=500,
        reserve_tokens=100,
        compression_threshold=0.7
    )
    
    # 设置系统消息
    window.set_system_message("You are a helpful assistant.")
    
    # 添加对话
    conversations = [
        ("user", "What is Python?"),
        ("assistant", "Python is a high-level programming language known for its simplicity."),
        ("user", "How do I install it?"),
        ("assistant", "You can download Python from python.org and follow the installation guide."),
    ]
    
    for role, content in conversations:
        window.add_message(role, content)
        print(f"\n添加: {role}: {content[:40]}...")
        print(f"  当前Token: {window.get_total_tokens()}")
        print(f"  使用率: {window.get_usage_ratio():.1%}")
    
    # 获取状态
    state = window.get_state()
    print(f"\n窗口状态:")
    print(f"  消息数: {state.message_count}")
    print(f"  总Token: {state.total_tokens}")
    print(f"  已压缩: {state.compression_count}次")


async def demo_memory_system():
    """记忆系统演示"""
    print("\n" + "=" * 50)
    print("3. 记忆系统")
    print("=" * 50)
    
    store = MemoryStore(storage_path="data/demo_memory")
    
    # 存储记忆
    memories = [
        ("User prefers Python over JavaScript", ["preference", "programming"]),
        ("User is working on a web scraping project", ["project", "scraping"]),
        ("User asked about Docker deployment", ["question", "docker"]),
    ]
    
    for content, tags in memories:
        memory_id = await store.store(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            tags=tags,
            session_id="demo-session"
        )
        print(f"\n存储记忆: {content[:40]}...")
        print(f"  ID: {memory_id[:8]}...")
        print(f"  标签: {tags}")
    
    # 检索记忆
    print("\n搜索 'Python':")
    from src.memory import MemoryQuery
    results = await store.search(MemoryQuery(
        query="Python programming",
        limit=3
    ))
    
    for r in results:
        print(f"  [{r.score:.2f}] {r.memory.content[:50]}...")
    
    # 统计
    stats = store.get_stats()
    print(f"\n记忆统计: {stats}")


async def demo_cache():
    """缓存演示"""
    print("\n" + "=" * 50)
    print("4. 响应缓存")
    print("=" * 50)
    
    cache = LRUCache(max_size=100, default_ttl=3600)
    
    # 模拟缓存LLM响应
    responses = [
        ("What is AI?", "AI stands for Artificial Intelligence..."),
        ("Hello!", "Hello! How can I help you?"),
        ("What is AI?", None),  # 应该命中缓存
    ]
    
    for query, response in responses:
        key = f"query:{hash(query)}"
        
        hit, cached = cache.get(key)
        if hit:
            print(f"\n缓存命中: {query}")
            print(f"  响应: {cached[:30]}...")
        else:
            print(f"\n缓存未命中: {query}")
            if response:
                cache.set(key, response)
                print(f"  已缓存响应")
    
    # 统计
    stats = cache.get_stats()
    print(f"\n缓存统计:")
    print(f"  命中: {stats.hits}")
    print(f"  未命中: {stats.misses}")
    print(f"  命中率: {stats.hit_rate:.1%}")


async def demo_metrics():
    """指标收集演示"""
    print("\n" + "=" * 50)
    print("5. 性能指标")
    print("=" * 50)
    
    collector = MetricsCollector()
    
    # 模拟LLM调用
    import random
    for i in range(10):
        collector.record_llm_call(
            model="claude-sonnet-4-5-20250929",
            input_tokens=random.randint(50, 200),
            output_tokens=random.randint(20, 100),
            latency_ms=random.randint(100, 500),
            success=random.random() > 0.1
        )
    
    # 模拟工具调用
    for i in range(5):
        collector.record_tool_call(
            tool="calculator",
            latency_ms=random.randint(5, 20),
            success=True
        )
    
    # 获取摘要
    summary = collector.get_summary("1h")
    print(f"\n指标摘要 (1h):")
    print(f"  LLM调用: {summary.llm_calls}")
    print(f"  LLM错误: {summary.llm_errors}")
    print(f"  LLM成功率: {summary.llm_success_rate:.1%}")
    print(f"  平均延迟: {summary.llm_avg_latency_ms:.1f}ms")
    print(f"  工具调用: {summary.tool_calls}")


async def demo_token_tracking():
    """Token跟踪演示"""
    print("\n" + "=" * 50)
    print("6. Token使用跟踪")
    print("=" * 50)
    
    tracker = TokenTracker()
    
    # 模拟使用
    models = ["claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"]
    
    import random
    for _ in range(20):
        model = random.choice(models)
        tracker.track(
            model=model,
            input_tokens=random.randint(100, 500),
            output_tokens=random.randint(50, 200),
            cached=random.random() > 0.7
        )
    
    # 获取使用摘要
    usage = tracker.get_usage("today")
    print(f"\n今日Token使用:")
    print(f"  调用次数: {usage.call_count}")
    print(f"  输入Token: {usage.total_input_tokens:,}")
    print(f"  输出Token: {usage.total_output_tokens:,}")
    print(f"  总Token: {usage.total_tokens:,}")
    print(f"  缓存Token: {usage.cached_tokens:,}")
    print(f"  预估成本: ${usage.estimated_cost_usd:.4f}")
    print(f"  缓存节省: ${usage.cache_savings_usd:.4f}")
    
    # 按模型统计
    print(f"\n按模型统计:")
    for model, tokens in usage.by_model.items():
        print(f"  {model}: {tokens['input']} in / {tokens['output']} out")


async def demo_alerts():
    """告警演示"""
    print("\n" + "=" * 50)
    print("7. 告警系统")
    print("=" * 50)
    
    manager = AlertManager()
    
    # 检查各种指标
    test_metrics = [
        {"error_rate": 0.05, "avg_latency_ms": 200},   # 正常
        {"error_rate": 0.15, "avg_latency_ms": 300},   # 高错误率
        {"error_rate": 0.02, "avg_latency_ms": 6000},  # 高延迟
        {"cost_usd_today": 15},                         # 高成本
    ]
    
    for metrics in test_metrics:
        print(f"\n检查指标: {metrics}")
        alerts = await manager.check_rules(metrics)
        if alerts:
            for alert in alerts:
                print(f"  ⚠️ [{alert.severity.value}] {alert.name}: {alert.message}")
        else:
            print(f"  ✅ 无告警")
    
    # 获取统计
    stats = manager.get_stats()
    print(f"\n告警统计:")
    print(f"  总告警: {stats['total']}")
    print(f"  活跃: {stats['active']}")
    print(f"  按级别: {stats['by_severity']}")


async def demo_task_queue():
    """任务队列演示"""
    print("\n" + "=" * 50)
    print("8. 异步任务队列")
    print("=" * 50)
    
    queue = TaskQueue(max_workers=3)
    await queue.start()
    
    # 定义一些任务
    async def simple_task(name: str, delay: float):
        await asyncio.sleep(delay)
        return f"Task {name} completed"
    
    # 提交任务
    handles = []
    for i in range(5):
        handle = await queue.submit(
            simple_task,
            f"task-{i}",
            0.2,
            priority=TaskPriority.NORMAL
        )
        handles.append(handle)
        print(f"提交任务: {handle.id[:8]}...")
    
    # 等待完成
    for handle in handles:
        result = await queue.get_result(handle, timeout=5)
        print(f"  完成: {result}")
    
    # 统计
    stats = queue.get_stats()
    print(f"\n队列统计:")
    print(f"  已提交: {stats.total_submitted}")
    print(f"  已完成: {stats.completed}")
    print(f"  平均等待: {stats.avg_wait_time_ms:.1f}ms")
    print(f"  平均执行: {stats.avg_execution_time_ms:.1f}ms")
    
    await queue.stop()


async def main():
    """主函数"""
    print("=" * 50)
    print("Manus AI Agent - 高级特性演示 (Phase 5)")
    print("=" * 50)
    
    await demo_token_counting()
    await demo_context_window()
    await demo_memory_system()
    await demo_cache()
    await demo_metrics()
    await demo_token_tracking()
    await demo_alerts()
    await demo_task_queue()
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

