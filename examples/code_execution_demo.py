#!/usr/bin/env python3
"""
代码执行演示

展示如何使用沙箱安全执行Python代码
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.sandbox import (
    create_sandbox,
    ExecutionRequest,
    ResultFormatter,
    quick_execute
)
from src.tools import CodeExecutorTool


async def demo_basic_execution():
    """基础执行演示"""
    print("\n" + "=" * 50)
    print("1. 基础代码执行")
    print("=" * 50)
    
    sandbox = create_sandbox("local")
    
    async with sandbox:
        # 简单打印
        request = ExecutionRequest(
            code="print('Hello from sandbox!')",
            timeout=30
        )
        result = await sandbox.execute(request)
        
        print(ResultFormatter.to_text(result, verbose=True))


async def demo_math_operations():
    """数学运算演示"""
    print("\n" + "=" * 50)
    print("2. 数学运算")
    print("=" * 50)
    
    code = """
import math
import statistics

# 基础运算
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print("=== 基础统计 ===")
print(f"Sum: {sum(numbers)}")
print(f"Mean: {statistics.mean(numbers)}")
print(f"Median: {statistics.median(numbers)}")
print(f"Stdev: {statistics.stdev(numbers):.4f}")

print("\\n=== 数学函数 ===")
print(f"Pi: {math.pi:.6f}")
print(f"E: {math.e:.6f}")
print(f"Sqrt(2): {math.sqrt(2):.6f}")
print(f"10!: {math.factorial(10)}")
"""
    
    sandbox = create_sandbox("local")
    
    async with sandbox:
        result = await sandbox.execute(ExecutionRequest(code=code))
        print(result.output)


async def demo_data_processing():
    """数据处理演示"""
    print("\n" + "=" * 50)
    print("3. 数据处理")
    print("=" * 50)
    
    code = """
import json
from collections import Counter

# 模拟数据
data = [
    {"name": "Alice", "age": 25, "city": "New York"},
    {"name": "Bob", "age": 30, "city": "Los Angeles"},
    {"name": "Charlie", "age": 25, "city": "New York"},
    {"name": "Diana", "age": 35, "city": "Chicago"},
    {"name": "Eve", "age": 30, "city": "New York"}
]

print("=== 数据概览 ===")
print(f"Total records: {len(data)}")

# 年龄统计
ages = [d["age"] for d in data]
print(f"\\n=== 年龄分布 ===")
print(f"Age range: {min(ages)} - {max(ages)}")
print(f"Average age: {sum(ages) / len(ages):.1f}")

# 城市统计
cities = Counter(d["city"] for d in data)
print(f"\\n=== 城市分布 ===")
for city, count in cities.most_common():
    print(f"  {city}: {count}")

# JSON输出
print(f"\\n=== JSON输出 ===")
print(json.dumps(data[0], indent=2))
"""
    
    sandbox = create_sandbox("local")
    
    async with sandbox:
        result = await sandbox.execute(ExecutionRequest(code=code))
        print(result.output)


async def demo_error_handling():
    """错误处理演示"""
    print("\n" + "=" * 50)
    print("4. 错误处理")
    print("=" * 50)
    
    sandbox = create_sandbox("local")
    
    async with sandbox:
        # 语法错误
        print("\n--- 语法错误 ---")
        result = await sandbox.execute(ExecutionRequest(code="print('hello'"))
        print(f"Status: {result.status.value}")
        print(f"Error: {result.error[:100]}...")
        
        # 运行时错误
        print("\n--- 运行时错误 ---")
        result = await sandbox.execute(ExecutionRequest(code="x = 1 / 0"))
        print(f"Status: {result.status.value}")
        print(f"Error: {result.error[:100]}...")
        
        # 安全违规
        print("\n--- 安全违规 ---")
        result = await sandbox.execute(ExecutionRequest(code="import subprocess"))
        print(f"Status: {result.status.value}")
        print(f"Error: {result.error[:100]}...")


async def demo_tool_execution():
    """工具执行演示"""
    print("\n" + "=" * 50)
    print("5. 使用CodeExecutorTool")
    print("=" * 50)
    
    executor = CodeExecutorTool()
    
    code = """
# 斐波那契数列
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

print("Fibonacci sequence:")
for i in range(15):
    print(f"F({i}) = {fibonacci(i)}")
"""
    
    result = await executor.execute(code=code)
    
    print(f"Success: {result.is_success}")
    if result.is_success:
        print(f"Output:\n{result.output}")
    else:
        print(f"Error: {result.error}")


async def demo_quick_execute():
    """快速执行演示"""
    print("\n" + "=" * 50)
    print("6. 快速执行 (quick_execute)")
    print("=" * 50)
    
    # random模块已在沙箱中预导入，无需import
    output = await quick_execute("""
numbers = [random.randint(1, 100) for _ in range(10)]
print(f"Random numbers: {numbers}")
print(f"Max: {max(numbers)}, Min: {min(numbers)}")
""")
    
    print(output)


async def main():
    """主函数"""
    print("=" * 50)
    print("Manus AI Agent - 代码执行演示")
    print("=" * 50)
    
    await demo_basic_execution()
    await demo_math_operations()
    await demo_data_processing()
    await demo_error_handling()
    await demo_tool_execution()
    await demo_quick_execute()
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

