"""
Manus AI Agent

通用型自主AI Agent系统，支持多Agent协作

核心组件：
- LLM: Claude 4.5 Sonnet / GPT 5.2 客户端
- Agents: Planner, Executor, Verifier, Orchestrator, CodeAgent
- Tools: Calculator, TextProcessor, WebSearch, CodeExecutor
- Sandbox: 安全的代码执行环境
- Core: 状态管理, Agent循环, 任务管理
"""

__version__ = "0.3.0"
__author__ = "Manus Team"

# LLM客户端
from .llm import create_claude_client, create_openai_client

# Agent
from .agents import (
    create_simple_agent,
    SimpleAgent,
    create_planner_agent,
    PlannerAgent,
    create_executor_agent,
    ExecutorAgent,
    create_verifier_agent,
    VerifierAgent,
    create_orchestrator,
    Orchestrator,
    CodeAgent
)

# 工具
from .tools import setup_default_tools, get_global_registry, CodeExecutorTool

# 沙箱
from .sandbox import create_sandbox, ExecutionRequest, ExecutionResult, quick_execute

# 核心
from .core import AgentLoop, run_agent, Task, Plan

__all__ = [
    # 版本
    "__version__",
    # LLM
    "create_claude_client",
    "create_openai_client",
    # 简单Agent
    "create_simple_agent",
    "SimpleAgent",
    # 多Agent
    "create_planner_agent",
    "PlannerAgent",
    "create_executor_agent",
    "ExecutorAgent",
    "create_verifier_agent",
    "VerifierAgent",
    "create_orchestrator",
    "Orchestrator",
    "CodeAgent",
    # 工具
    "setup_default_tools",
    "get_global_registry",
    "CodeExecutorTool",
    # 沙箱
    "create_sandbox",
    "ExecutionRequest",
    "ExecutionResult",
    "quick_execute",
    # 核心
    "AgentLoop",
    "run_agent",
    "Task",
    "Plan",
]
