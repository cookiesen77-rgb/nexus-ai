"""
AI Providers for Banana Slides
支持 Gemini 文本和图像生成
"""

from .text_provider import TextProvider, GeminiTextProvider
from .image_provider import ImageProvider, GeminiImageProvider

__all__ = [
    'TextProvider',
    'GeminiTextProvider',
    'ImageProvider', 
    'GeminiImageProvider',
]

