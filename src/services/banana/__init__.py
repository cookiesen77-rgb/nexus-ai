"""
Banana Slides 核心服务模块
深度集成到 Nexus，提供完整的 AI PPT 生成功能
"""

from .ai_service import AIService, ProjectContext, get_ai_service
from .prompts import PPTPrompts
from .export_service import ExportService, get_export_service
from .task_manager import TaskManager, get_task_manager

__all__ = [
    'AIService',
    'ProjectContext',
    'get_ai_service',
    'PPTPrompts',
    'ExportService',
    'get_export_service',
    'TaskManager',
    'get_task_manager',
]

