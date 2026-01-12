"""API 路由模块"""

from .health import router as health_router
from .agents import router as agents_router
from .tools import router as tools_router
from .banana_ppt import router as banana_ppt_router

__all__ = [
    'health_router',
    'agents_router', 
    'tools_router',
    'banana_ppt_router',
]
