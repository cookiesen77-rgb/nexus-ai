"""服务模块"""

from .gemini_image import GeminiImageClient, get_gemini_client
from .ppt_service import PPTService, get_ppt_service

__all__ = [
    "GeminiImageClient",
    "get_gemini_client",
    "PPTService",
    "get_ppt_service"
]

