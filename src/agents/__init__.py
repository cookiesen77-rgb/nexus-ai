"""
Agent 模块

提供各类Agent实现：
- BaseAgent: Agent基类
- SimpleAgent: 简单Agent
- PlannerAgent: 任务规划Agent
- ExecutorAgent: 任务执行Agent
- VerifierAgent: 结果验证Agent
- Orchestrator: 多Agent协调器
"""

from .base import (
    BaseAgent,
    ConversationalAgent,
    AgentConfig,
    AgentResult
)
from .simple_agent import SimpleAgent, create_simple_agent
from .planner import PlannerAgent, create_planner_agent
from .executor import ExecutorAgent, create_executor_agent
from .verifier import VerifierAgent, create_verifier_agent
from .orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    OrchestratorResult,
    create_orchestrator
)
from .code_agent import CodeAgent

__all__ = [
    # 基类
    "BaseAgent",
    "ConversationalAgent",
    "AgentConfig",
    "AgentResult",
    # 简单Agent
    "SimpleAgent",
    "create_simple_agent",
    # Planner
    "PlannerAgent",
    "create_planner_agent",
    # Executor
    "ExecutorAgent",
    "create_executor_agent",
    # Verifier
    "VerifierAgent",
    "create_verifier_agent",
    # Orchestrator
    "Orchestrator",
    "OrchestratorConfig",
    "OrchestratorResult",
    "create_orchestrator",
    # Code Agent
    "CodeAgent",
]
