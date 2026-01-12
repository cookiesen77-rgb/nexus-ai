"""
工具模块

提供各类工具实现和注册机制

工具分类:
- 基础工具: Calculator, TextProcessor
- 代码执行: CodeExecutor, DataAnalysis
- 网络工具: WebSearch, WebScraper, HttpClient
- 文件工具: FileReader, FileWriter, FileManager
- 数据工具: JsonTool, CsvTool, SQLite
- 系统工具: Shell, Environment
- 编排工具: ToolChain
- 浏览器: Browser (网页自动化)
- 规划: Plan (任务规划)
- 消息: Message (用户交互)
- 调度: Schedule (定时任务)
- 暴露: Expose (端口暴露)
- 生成: Generate (多媒体生成)
"""

import os

from .base import BaseTool, ToolResult, ToolStatus
from .registry import (
    ToolRegistry,
    get_global_registry,
    register_tool,
    get_tool,
    list_tools,
    execute_tool
)

# 基础工具
from .calculator import CalculatorTool, calculator
from .text_processor import TextProcessorTool, text_processor

# 网络搜索
from .web_search import (
    WebSearchTool,
    MockWebSearchTool,
    create_web_search_tool,
    web_search
)

# 代码执行
from .code_executor import CodeExecutorTool, DataAnalysisTool

# 网页抓取
from .web_scraper import WebScraperTool, ContentExtractorTool, web_scraper, content_extractor

# 文件操作
from .file_tools import (
    FileReaderTool, FileWriterTool, FileManagerTool,
    JsonTool, CsvTool,
    file_reader, file_writer, file_manager, json_tool, csv_tool
)

# HTTP客户端
from .http_client import HttpClientTool, ApiClientTool, http_client

# 数据库
from .database_tool import SQLiteTool, DataStoreTool, sqlite_tool, data_store

# Shell执行
from .shell_executor import ShellExecutorTool, EnvironmentTool, shell, environment

# 工具链
from .tool_chain import ToolChain, ToolChainTool, ToolChainTemplates, tool_chain

# 限流器
from .rate_limiter import RateLimiter, RateLimitConfig, get_rate_limiter

# 新工具 - Manus功能
from .browser_tool import BrowserTool, browser_tool, get_browser_instance
from .plan_tool import PlanTool, plan_tool, get_plan_manager
from .message_tool import MessageTool, message_tool, get_message_queue
from .schedule_tool import ScheduleTool, schedule_tool, get_scheduler
from .expose_tool import ExposeTool, expose_tool, get_port_exposer
from .generate_tool import GenerateTool, generate_tool
from .ppt_tool import PPTTool

# 上下文工程 - Manus 3文件模式
from .context_engineering_tool import (
    ContextEngineeringTool, 
    context_engineering_tool,
    get_context_dir,
    read_task_plan
)

# 注意：不要在模块导入时创建 PPTTool 实例（会触发依赖初始化，阻塞 API 启动）。
# 需要时再惰性初始化。
ppt_tool: PPTTool | None = None


def get_ppt_tool() -> PPTTool:
    global ppt_tool
    if ppt_tool is None:
        ppt_tool = PPTTool()
    return ppt_tool

# 创建代码执行工具实例
code_executor = CodeExecutorTool()
data_analysis = DataAnalysisTool()


def setup_default_tools() -> ToolRegistry:
    """
    设置默认工具集
    
    根据 config/tools.json 配置注册启用的工具到全局注册器
    
    Returns:
        ToolRegistry: 配置好的工具注册器
    """
    registry = get_global_registry()
    
    # 加载配置管理器
    try:
        from src.admin import get_config_manager
        config_manager = get_config_manager()
    except Exception as e:
        print(f"[Tools] 加载配置管理器失败，使用默认配置: {e}")
        config_manager = None
    
    def is_enabled(tool_name: str) -> bool:
        """检查工具是否启用"""
        # 某些工具依赖外部密钥；未配置时不要阻塞 API 启动
        if tool_name == "ppt":
            if not (os.getenv("ALLAPI_KEY") or os.getenv("GEMINI_API_KEY")):
                return False
        if config_manager is None:
            return True  # 配置管理器不可用时默认启用
        return config_manager.is_tool_enabled(tool_name)
    
    # 工具名称到实例的映射
    tool_map = {
        # 基础工具
        "calculator": calculator,
        "text_processor": text_processor,
        # 网络工具
        "web_search": web_search,
        "web_scraper": web_scraper,
        "content_extractor": content_extractor,
        "http_client": http_client,
        # 代码执行
        "code_executor": code_executor,
        "data_analysis": data_analysis,
        # 文件工具
        "file_reader": file_reader,
        "file_writer": file_writer,
        "file_manager": file_manager,
        "json_tool": json_tool,
        "csv_tool": csv_tool,
        # 数据库
        "sqlite": sqlite_tool,
        "data_store": data_store,
        # 系统工具
        "shell": shell,
        "environment": environment,
        # 编排
        "tool_chain": tool_chain,
        # Manus 工具
        "browser": browser_tool,
        "plan": plan_tool,
        "message": message_tool,
        "schedule": schedule_tool,
        "expose": expose_tool,
        "generate": generate_tool,
        # PPT 工具（惰性初始化）
        "ppt": get_ppt_tool,
        # 上下文工程
        "context_engineering": context_engineering_tool,
    }
    
    # 根据配置注册工具
    enabled_count = 0
    disabled_count = 0
    for tool_name, tool_instance in tool_map.items():
        if is_enabled(tool_name):
            # 支持惰性初始化：tool_instance 可以是 BaseTool 实例，也可以是返回实例的 callable
            instance = tool_instance
            if not isinstance(tool_instance, BaseTool) and callable(tool_instance):
                instance = tool_instance()
            registry.register(instance)
            enabled_count += 1
        else:
            disabled_count += 1
            print(f"[Tools] 工具已禁用: {tool_name}")
    
    print(f"[Tools] 已注册 {enabled_count} 个工具，{disabled_count} 个已禁用")
    
    return registry


def list_available_tools() -> dict:
    """
    列出所有可用工具及其描述
    
    Returns:
        dict: 工具名称到描述的映射
    """
    registry = setup_default_tools()
    tools = {}
    for name in registry.list_names():
        tool = registry.get(name)
        tools[name] = {
            "description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
            "parameters": list(tool.parameters.get("properties", {}).keys())
        }
    return tools


__all__ = [
    # 基类
    "BaseTool",
    "ToolResult",
    "ToolStatus",
    
    # 注册器
    "ToolRegistry",
    "get_global_registry",
    "register_tool",
    "get_tool",
    "list_tools",
    "execute_tool",
    
    # 基础工具
    "CalculatorTool",
    "calculator",
    "TextProcessorTool",
    "text_processor",
    
    # 网络搜索
    "WebSearchTool",
    "MockWebSearchTool",
    "create_web_search_tool",
    "web_search",
    
    # 网页抓取
    "WebScraperTool",
    "ContentExtractorTool",
    "web_scraper",
    "content_extractor",
    
    # 代码执行
    "CodeExecutorTool",
    "DataAnalysisTool",
    "code_executor",
    "data_analysis",
    
    # 文件操作
    "FileReaderTool",
    "FileWriterTool", 
    "FileManagerTool",
    "JsonTool",
    "CsvTool",
    "file_reader",
    "file_writer",
    "file_manager",
    "json_tool",
    "csv_tool",
    
    # HTTP客户端
    "HttpClientTool",
    "ApiClientTool",
    "http_client",
    
    # 数据库
    "SQLiteTool",
    "DataStoreTool",
    "sqlite_tool",
    "data_store",
    
    # Shell
    "ShellExecutorTool",
    "EnvironmentTool",
    "shell",
    "environment",
    
    # 工具链
    "ToolChain",
    "ToolChainTool",
    "ToolChainTemplates",
    "tool_chain",
    
    # 限流
    "RateLimiter",
    "RateLimitConfig",
    "get_rate_limiter",
    
    # 浏览器
    "BrowserTool",
    "browser_tool",
    "get_browser_instance",
    
    # 规划
    "PlanTool",
    "plan_tool",
    "get_plan_manager",
    
    # 消息
    "MessageTool",
    "message_tool",
    "get_message_queue",
    
    # 调度
    "ScheduleTool",
    "schedule_tool",
    "get_scheduler",
    
    # 端口暴露
    "ExposeTool",
    "expose_tool",
    "get_port_exposer",
    
    # 内容生成
    "GenerateTool",
    "generate_tool",
    
    # PPT
    "PPTTool",
    "ppt_tool",
    
    # 上下文工程
    "ContextEngineeringTool",
    "context_engineering_tool",
    "get_context_dir",
    "read_task_plan",
    
    # 设置
    "setup_default_tools",
    "list_available_tools",
]
