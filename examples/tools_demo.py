#!/usr/bin/env python3
"""
工具生态演示

展示Phase 4新增的各类工具使用方法
"""

import asyncio
import sys
import tempfile
import os
sys.path.insert(0, '.')

from src.tools import (
    setup_default_tools,
    list_available_tools,
    # 文件工具
    file_reader, file_writer, file_manager,
    json_tool, csv_tool,
    # 数据库
    sqlite_tool, data_store,
    # 系统
    shell, environment,
    # HTTP
    http_client,
    # 编排
    ToolChain
)


async def demo_file_operations():
    """文件操作演示"""
    print("\n" + "=" * 50)
    print("1. 文件操作工具")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入文本文件
        txt_file = os.path.join(tmpdir, "hello.txt")
        result = await file_writer.execute(
            path=txt_file,
            content="Hello, Manus AI Agent!"
        )
        print(f"\n写入文本文件: {result.output}")
        
        # 读取文件
        result = await file_reader.execute(path=txt_file)
        print(f"读取内容: {result.output}")
        
        # 写入JSON
        json_file = os.path.join(tmpdir, "data.json")
        data = {
            "name": "Manus",
            "version": "0.4.0",
            "features": ["multi-agent", "code-execution", "tool-ecosystem"]
        }
        result = await file_writer.execute(path=json_file, content=data)
        print(f"\n写入JSON: {result.output}")
        
        # 读取JSON
        result = await file_reader.execute(path=json_file, parse=True)
        print(f"解析JSON: {result.output}")
        
        # 列出目录
        result = await file_manager.execute(action="list", path=tmpdir)
        print(f"\n目录内容:")
        for f in result.output:
            print(f"  - {f['name']} ({f['type']}, {f['size']} bytes)")


async def demo_json_csv():
    """JSON/CSV处理演示"""
    print("\n" + "=" * 50)
    print("2. JSON/CSV处理")
    print("=" * 50)
    
    # JSON查询
    data = {
        "users": [
            {"name": "Alice", "age": 25, "city": "NYC"},
            {"name": "Bob", "age": 30, "city": "LA"},
            {"name": "Charlie", "age": 35, "city": "NYC"}
        ]
    }
    
    print("\nJSON数据:")
    print(f"  {data}")
    
    result = await json_tool.execute(action="query", data=data, path="users.1.name")
    print(f"\n查询 users.1.name: {result.output}")
    
    # CSV处理
    csv_data = [
        {"name": "Alice", "score": "85"},
        {"name": "Bob", "score": "92"},
        {"name": "Charlie", "score": "78"}
    ]
    
    # 过滤
    result = await csv_tool.execute(
        action="filter",
        data=csv_data,
        condition={"name": "Bob"}
    )
    print(f"\nCSV过滤 (name=Bob): {result.output}")
    
    # 选择列
    result = await csv_tool.execute(
        action="select",
        data=csv_data,
        columns=["name"]
    )
    print(f"CSV选择列 (name): {result.output}")


async def demo_data_store():
    """数据存储演示"""
    print("\n" + "=" * 50)
    print("3. 键值存储")
    print("=" * 50)
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_file = f.name
    
    try:
        # 存储数据
        await data_store.execute(
            action="set",
            key="agent_name",
            value="Manus",
            store_file=store_file
        )
        await data_store.execute(
            action="set",
            key="agent_config",
            value={"model": "claude-sonnet-4.5", "tools": 17},
            store_file=store_file
        )
        
        print("\n已存储键值对")
        
        # 列出所有键
        result = await data_store.execute(action="list", store_file=store_file)
        print(f"所有键: {result.output}")
        
        # 获取值
        result = await data_store.execute(
            action="get",
            key="agent_config",
            store_file=store_file
        )
        print(f"获取 agent_config: {result.output}")
        
    finally:
        os.unlink(store_file)


async def demo_shell():
    """Shell命令演示"""
    print("\n" + "=" * 50)
    print("4. Shell命令执行")
    print("=" * 50)
    
    # 基本命令
    result = await shell.execute(command="echo 'Hello from Shell!'")
    print(f"\necho命令: {result.output}")
    
    result = await shell.execute(command="date")
    print(f"date命令: {result.output}")
    
    result = await shell.execute(command="pwd")
    print(f"pwd命令: {result.output}")
    
    # Python版本
    result = await shell.execute(command="python3 --version")
    print(f"Python版本: {result.output}")
    
    # 安全测试
    print("\n安全检查:")
    result = await shell.execute(command="rm -rf /")
    print(f"  危险命令被阻止: {result.error[:50]}...")


async def demo_environment():
    """环境变量演示"""
    print("\n" + "=" * 50)
    print("5. 环境变量")
    print("=" * 50)
    
    # 检查变量存在
    result = await environment.execute(action="has", name="HOME")
    print(f"\nHOME存在: {result.output}")
    
    # 获取变量
    result = await environment.execute(action="get", name="HOME")
    print(f"HOME值: {result.output}")
    
    # 设置变量
    await environment.execute(action="set", name="MANUS_TEST", value="hello")
    result = await environment.execute(action="get", name="MANUS_TEST")
    print(f"设置并获取 MANUS_TEST: {result.output}")


async def demo_tool_chain():
    """工具链演示"""
    print("\n" + "=" * 50)
    print("6. 工具链编排")
    print("=" * 50)
    
    # 确保工具已注册
    setup_default_tools()
    
    # 创建工具链
    chain = ToolChain("demo_chain")
    
    # 设置初始变量
    chain.set_variable("greeting", "Hello")
    chain.set_variable("name", "Manus")
    
    # 添加步骤
    chain.add_step(
        name="step1",
        tool="text_processor",
        params={
            "text": "$greeting, $name!",
            "operation": "uppercase"
        }
    )
    
    chain.add_step(
        name="step2",
        tool="calculator",
        params={"expression": "2 * 3 + 4"}
    )
    
    # 执行
    result = await chain.execute()
    
    print(f"\n工具链执行结果:")
    print(f"  成功: {result['success']}")
    for step in result['steps']:
        print(f"  - {step['step']}: {step['status']}")
        if step.get('output'):
            print(f"    输出: {step['output']}")


async def demo_list_tools():
    """列出所有可用工具"""
    print("\n" + "=" * 50)
    print("7. 可用工具列表")
    print("=" * 50)
    
    setup_default_tools()
    tools = list_available_tools()
    
    print(f"\n共 {len(tools)} 个工具:")
    for name, info in sorted(tools.items()):
        print(f"\n  📦 {name}")
        print(f"     {info['description'][:60]}...")
        print(f"     参数: {', '.join(info['parameters'][:5])}")


async def main():
    """主函数"""
    print("=" * 50)
    print("Manus AI Agent - 工具生态演示")
    print("=" * 50)
    
    await demo_file_operations()
    await demo_json_csv()
    await demo_data_store()
    await demo_shell()
    await demo_environment()
    await demo_tool_chain()
    await demo_list_tools()
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

