"""PPT 数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid
from pathlib import Path


class SlideLayout(str, Enum):
    """幻灯片布局类型"""
    TITLE = "title"  # 标题页
    TITLE_CONTENT = "title_content"  # 标题+正文
    TITLE_IMAGE = "title_image"  # 标题+图片
    TWO_COLUMN = "two_column"  # 左右分栏
    IMAGE_ONLY = "image_only"  # 纯图片
    SECTION = "section"  # 章节页
    CONCLUSION = "conclusion"  # 总结页


class TemplateStyle(str, Enum):
    """模板风格"""
    MODERN = "modern"  # 现代商务
    MINIMAL = "minimal"  # 简约学术
    CREATIVE = "creative"  # 创意营销
    NATURE = "nature"  # 自然环保
    DARK = "dark"  # 深色科技
    # Banana Slides 参考模板（图片模板，用于风格参考）
    BANANA_TEMPLATE_Y = "banana_template_y"  # 复古卷轴
    BANANA_TEMPLATE_VECTOR_ILLUSTRATION = "banana_template_vector_illustration"  # 矢量插画
    BANANA_TEMPLATE_GLASS = "banana_template_glass"  # 拟物玻璃
    BANANA_TEMPLATE_B = "banana_template_b"  # 科技蓝
    BANANA_TEMPLATE_S = "banana_template_s"  # 简约商务
    BANANA_TEMPLATE_ACADEMIC = "banana_template_academic"  # 学术报告


@dataclass
class Slide:
    """单张幻灯片"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order: int = 0
    layout: str = SlideLayout.TITLE_CONTENT.value
    title: str = ""
    content: str = ""
    image_base64: str = ""
    image_prompt: str = ""
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order": self.order,
            "layout": self.layout,
            "title": self.title,
            "content": self.content,
            "imageBase64": self.image_base64,
            "imagePrompt": self.image_prompt,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Slide":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            order=data.get("order", 0),
            layout=data.get("layout", SlideLayout.TITLE_CONTENT.value),
            title=data.get("title", ""),
            content=data.get("content", ""),
            image_base64=data.get("imageBase64", ""),
            image_prompt=data.get("imagePrompt", ""),
            notes=data.get("notes", "")
        )


@dataclass
class Presentation:
    """演示文稿"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    topic: str = ""
    template: str = TemplateStyle.MODERN.value
    slides: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "template": self.template,
            "slides": [s.to_dict() if isinstance(s, Slide) else s for s in self.slides],
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Presentation":
        slides = [Slide.from_dict(s) if isinstance(s, dict) else s for s in data.get("slides", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            template=data.get("template", TemplateStyle.MODERN.value),
            slides=slides,
            created_at=data.get("createdAt", datetime.now().isoformat()),
            updated_at=data.get("updatedAt", datetime.now().isoformat())
        )
    
    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()


@dataclass
class PPTTemplate:
    """PPT 模板定义"""
    id: str
    name: str
    name_zh: str
    description: str
    colors: dict = field(default_factory=dict)
    fonts: dict = field(default_factory=dict)
    # 前端预览图（可选）
    preview_image: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "nameZh": self.name_zh,
            "description": self.description,
            "colors": self.colors,
            "fonts": self.fonts,
            "previewImage": self.preview_image,
        }


# 预定义模板
# 注意：避免在 TEMPLATES 初始化过程中引用 TEMPLATES 自己（会导致 NameError）。
MODERN_TEMPLATE = PPTTemplate(
    id="modern",
    name="Modern",
    name_zh="现代商务",
    description="专业的商务风格，适合工作汇报和商业演示",
    colors={
        "primary": "#1E40AF",
        "secondary": "#3B82F6",
        "accent": "#F97316",
        "background": "#FFFFFF",
        "text": "#1F2937",
    },
    fonts={"title": "Arial Black", "body": "Arial"},
)

MINIMAL_TEMPLATE = PPTTemplate(
    id="minimal",
    name="Minimal",
    name_zh="简约学术",
    description="简洁清晰的风格，适合学术报告和教育演示",
    colors={
        "primary": "#111827",
        "secondary": "#6B7280",
        "accent": "#10B981",
        "background": "#FAFAFA",
        "text": "#111827",
    },
    fonts={"title": "Georgia", "body": "Times New Roman"},
)

CREATIVE_TEMPLATE = PPTTemplate(
    id="creative",
    name="Creative",
    name_zh="创意营销",
    description="活泼有创意的风格，适合营销和创意展示",
    colors={
        "primary": "#7C3AED",
        "secondary": "#EC4899",
        "accent": "#FBBF24",
        "background": "#FFFFFF",
        "text": "#1F2937",
    },
    fonts={"title": "Helvetica Neue", "body": "Helvetica"},
)

NATURE_TEMPLATE = PPTTemplate(
    id="nature",
    name="Nature",
    name_zh="自然环保",
    description="自然清新的风格，适合环保和健康主题",
    colors={
        "primary": "#166534",
        "secondary": "#22C55E",
        "accent": "#A3E635",
        "background": "#F0FDF4",
        "text": "#14532D",
    },
    fonts={"title": "Trebuchet MS", "body": "Verdana"},
)

DARK_TEMPLATE = PPTTemplate(
    id="dark",
    name="Dark",
    name_zh="深色科技",
    description="深色科技风格，适合技术演示和产品发布",
    colors={
        "primary": "#06B6D4",
        "secondary": "#8B5CF6",
        "accent": "#F43F5E",
        "background": "#0F172A",
        "text": "#F8FAFC",
    },
    fonts={"title": "Consolas", "body": "Segoe UI"},
)

# ===========================
# Banana Slides 图片模板（参考图）
# ===========================
BANANA_TEMPLATE_Y = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_Y.value,
    name="Banana / Scroll",
    name_zh="复古卷轴",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    # 导出风格仍沿用现代模板的配色/字体，避免破坏现有 PPTX 构建逻辑
    colors=MODERN_TEMPLATE.colors,
    fonts=MODERN_TEMPLATE.fonts,
)

BANANA_TEMPLATE_VECTOR_ILLUSTRATION = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_VECTOR_ILLUSTRATION.value,
    name="Banana / Vector",
    name_zh="矢量插画",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    colors=CREATIVE_TEMPLATE.colors,
    fonts=CREATIVE_TEMPLATE.fonts,
)

BANANA_TEMPLATE_GLASS = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_GLASS.value,
    name="Banana / Glass",
    name_zh="拟物玻璃",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    colors=DARK_TEMPLATE.colors,
    fonts=DARK_TEMPLATE.fonts,
)

BANANA_TEMPLATE_B = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_B.value,
    name="Banana / Tech Blue",
    name_zh="科技蓝",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    colors=MODERN_TEMPLATE.colors,
    fonts=MODERN_TEMPLATE.fonts,
)

BANANA_TEMPLATE_S = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_S.value,
    name="Banana / Simple Biz",
    name_zh="简约商务",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    colors=MINIMAL_TEMPLATE.colors,
    fonts=MINIMAL_TEMPLATE.fonts,
)

BANANA_TEMPLATE_ACADEMIC = PPTTemplate(
    id=TemplateStyle.BANANA_TEMPLATE_ACADEMIC.value,
    name="Banana / Academic",
    name_zh="学术报告",
    description="参考 banana-slides 的模板图（用于风格参考）。",
    colors=MINIMAL_TEMPLATE.colors,
    fonts=MINIMAL_TEMPLATE.fonts,
    preview_image="/ppt-templates/banana/template_academic.jpg",
)

TEMPLATES = {
    TemplateStyle.MODERN.value: MODERN_TEMPLATE,
    TemplateStyle.MINIMAL.value: MINIMAL_TEMPLATE,
    TemplateStyle.CREATIVE.value: CREATIVE_TEMPLATE,
    TemplateStyle.NATURE.value: NATURE_TEMPLATE,
    TemplateStyle.DARK.value: DARK_TEMPLATE,
    TemplateStyle.BANANA_TEMPLATE_Y.value: BANANA_TEMPLATE_Y,
    TemplateStyle.BANANA_TEMPLATE_VECTOR_ILLUSTRATION.value: BANANA_TEMPLATE_VECTOR_ILLUSTRATION,
    TemplateStyle.BANANA_TEMPLATE_GLASS.value: BANANA_TEMPLATE_GLASS,
    TemplateStyle.BANANA_TEMPLATE_B.value: BANANA_TEMPLATE_B,
    TemplateStyle.BANANA_TEMPLATE_S.value: BANANA_TEMPLATE_S,
    TemplateStyle.BANANA_TEMPLATE_ACADEMIC.value: BANANA_TEMPLATE_ACADEMIC,
}


_TEMPLATE_REFERENCE_IMAGE_FILES: dict[str, str] = {
    TemplateStyle.BANANA_TEMPLATE_ACADEMIC.value: "banana/template_academic.jpg",
}


def get_template_reference_image_bytes(template_id: str) -> Optional[bytes]:
    """
    获取模板参考图（用于引导配图风格），若不存在则返回 None。
    """
    rel = _TEMPLATE_REFERENCE_IMAGE_FILES.get(template_id)
    if not rel:
        return None
    base = Path(__file__).resolve().parents[1] / "assets" / "ppt_templates"
    path = base / rel
    try:
        return path.read_bytes()
    except Exception:
        return None


def get_template(style: str) -> PPTTemplate:
    """获取模板配置"""
    return TEMPLATES.get(style, TEMPLATES[TemplateStyle.MODERN.value])


def get_all_templates() -> list[dict]:
    """获取所有模板"""
    return [t.to_dict() for t in TEMPLATES.values()]

