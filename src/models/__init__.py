"""数据模型模块"""

from .ppt import (
    Presentation,
    Slide,
    SlideLayout,
    TemplateStyle,
    PPTTemplate,
    TEMPLATES,
    get_template,
    get_all_templates
)

__all__ = [
    "Presentation",
    "Slide",
    "SlideLayout",
    "TemplateStyle",
    "PPTTemplate",
    "TEMPLATES",
    "get_template",
    "get_all_templates"
]

