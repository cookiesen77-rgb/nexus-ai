"""
提示词模块

包含各个Agent的系统提示词和模板
"""

from .planner import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_PLAN_TEMPLATE,
    PLANNER_REPLAN_TEMPLATE
)
from .executor import (
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_STEP_TEMPLATE
)
from .verifier import (
    VERIFIER_SYSTEM_PROMPT,
    VERIFIER_VERIFY_TEMPLATE
)
from .code import (
    CODE_GENERATION_SYSTEM,
    CODE_FIX_SYSTEM,
    DATA_ANALYSIS_SYSTEM,
    get_code_generation_prompt,
    get_code_fix_prompt,
    get_data_analysis_prompt
)

__all__ = [
    # Planner
    "PLANNER_SYSTEM_PROMPT",
    "PLANNER_PLAN_TEMPLATE",
    "PLANNER_REPLAN_TEMPLATE",
    # Executor
    "EXECUTOR_SYSTEM_PROMPT",
    "EXECUTOR_STEP_TEMPLATE",
    # Verifier
    "VERIFIER_SYSTEM_PROMPT",
    "VERIFIER_VERIFY_TEMPLATE",
    # Code
    "CODE_GENERATION_SYSTEM",
    "CODE_FIX_SYSTEM",
    "DATA_ANALYSIS_SYSTEM",
    "get_code_generation_prompt",
    "get_code_fix_prompt",
    "get_data_analysis_prompt",
]

