"""
PPT Service Prompts - 专业的 PPT 生成提示词模板
参考 banana-slides 项目的设计理念

重要区分：
- 配图 (Illustration): 独立的插图/图像，放在 PPT 页面的某个区域，不含文字
- 页面图像 (Page Image): 整个 PPT 页面的完整图像（已废弃此方式）
"""

from typing import List, Dict, Optional
import json


# =============================================================================
# 语言配置
# =============================================================================
LANGUAGE_CONFIG = {
    'zh': {
        'name': '中文',
        'instruction': '请使用全中文输出。',
        'ppt_text': 'PPT文字请使用全中文。'
    },
    'en': {
        'name': 'English',
        'instruction': 'Please output all in English.',
        'ppt_text': 'Use English for PPT text.'
    },
    'auto': {
        'name': '自动',
        'instruction': '',
        'ppt_text': ''
    }
}


def get_language_instruction(language: str = 'zh') -> str:
    """获取语言限制指令"""
    config = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG['zh'])
    return config['instruction']


def get_ppt_language_instruction(language: str = 'zh') -> str:
    """获取PPT文字语言限制指令"""
    config = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG['zh'])
    return config['ppt_text']


# =============================================================================
# 大纲生成 Prompt
# =============================================================================
def get_outline_generation_prompt(
    topic: str,
    page_count: int,
    requirements: str = "",
    language: str = 'zh'
) -> str:
    """
    生成 PPT 大纲的 prompt
    
    Args:
        topic: PPT 主题
        page_count: 页数
        requirements: 额外要求
        language: 输出语言
    """
    prompt = f"""\
你是一位专业的 PPT 内容策划专家。请根据以下主题和要求，生成一个包含 {page_count} 页的 PPT 大纲。

用户主题：{topic}
{f'额外要求：{requirements}' if requirements else ''}

请生成结构化的大纲，可以选择以下两种格式：

1. 简单格式（适用于没有明显章节的短 PPT）：
[{{"title": "标题1", "points": ["要点1", "要点2"]}}, {{"title": "标题2", "points": ["要点1", "要点2"]}}]

2. 章节格式（适用于有明确主要章节的长 PPT）：
[
    {{
        "part": "第一部分：引言",
        "pages": [
            {{"title": "欢迎", "points": ["要点1", "要点2"]}},
            {{"title": "概述", "points": ["要点1", "要点2"]}}
        ]
    }}
]

重要规则：
- 第一页应为封面页，只包含标题、副标题和演讲人信息
- 最后一页通常为总结或感谢页
- 每页的要点数量控制在 3-5 个
- 要点内容应简洁精炼
- 选择最适合内容的格式

只输出 JSON 格式的大纲，不要包含其他文字。
{get_language_instruction(language)}
"""
    return prompt


# =============================================================================
# 页面描述生成 Prompt
# =============================================================================
def get_page_description_prompt(
    topic: str,
    outline: List[Dict],
    page_outline: Dict,
    page_index: int,
    previous_context: str = "",
    language: str = 'zh'
) -> str:
    """
    生成单个页面描述的 prompt
    
    Args:
        topic: PPT 主题
        outline: 完整大纲
        page_outline: 当前页面的大纲
        page_index: 页面编号（从1开始）
        previous_context: 之前页面的内容摘要
        language: 输出语言
    """
    outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
    page_outline_json = json.dumps(page_outline, ensure_ascii=False, indent=2)
    
    is_cover_page = page_index == 1
    
    cover_instructions = """
**注意：这是PPT的封面页，内容需要保持极简：**
- 只放标题和副标题
- 可以包含演讲人信息
- 不添加任何详细内容或素材
""" if is_cover_page else ""
    
    prompt = f"""\
我们正在为PPT的每一页生成详细内容描述。

PPT主题：{topic}

完整大纲：
{outline_json}

{f'之前页面内容摘要：{previous_context}' if previous_context else ''}

现在请为第 {page_index} 页生成描述：
{page_outline_json}

{cover_instructions}

【重要提示】生成的"页面文字"部分会直接渲染到PPT页面上，因此请务必注意：
1. 文字内容要简洁精炼，每条要点控制在 **15-25 字以内**
2. 条理清晰，使用列表形式组织内容
3. 避免冗长的句子和复杂的表述
4. 确保内容可读性强，适合在演示时展示
5. 不要包含任何额外的说明性文字或注释

输出格式示例：
页面标题：{page_outline.get('title', '标题')}
{f"副标题：{topic}" if is_cover_page else ""}

页面文字：
- 简洁的要点一（15-25字）
- 简洁的要点二（15-25字）
- 简洁的要点三（15-25字）

请直接输出内容，不需要其他说明。
{get_language_instruction(language)}
"""
    return prompt


# =============================================================================
# 图片生成 Prompt
# =============================================================================
def get_image_generation_prompt(
    page_desc: str,
    outline_text: str,
    current_section: str,
    page_index: int = 1,
    has_template: bool = True,
    template_style: str = "",
    extra_requirements: str = "",
    language: str = 'zh'
) -> str:
    """
    生成图片生成 prompt（参考 banana-slides 的专业设计）
    
    Args:
        page_desc: 页面描述文本
        outline_text: 大纲文本
        current_section: 当前章节
        page_index: 页面索引
        has_template: 是否有模板图片
        template_style: 模板风格描述
        extra_requirements: 额外要求
        language: 输出语言
    """
    # 根据是否有模板生成不同的设计指南
    if has_template:
        style_guideline = "- 配色和设计语言必须与模板图片严格保持一致"
        template_note = "- 只参考模板的风格设计，禁止出现模板中的原有文字"
    elif template_style:
        style_guideline = f"- 严格按照以下风格描述进行设计：{template_style}"
        template_note = ""
    else:
        style_guideline = "- 使用现代、专业的商务演示风格"
        template_note = ""
    
    # 封面页特殊处理
    cover_instructions = """
**注意：当前页面为PPT的封面页，请你采用专业的封面设计美学技巧：**
- 务必凸显出页面标题，分清主次
- 使用大胆的排版设计
- 确保一下就能抓住观众的注意力
- 背景设计要有视觉冲击力
""" if page_index == 1 else ""
    
    extra_req_text = f"\n\n额外要求（请务必遵循）：\n{extra_requirements}\n" if extra_requirements else ""
    
    prompt = f"""\
你是一位专家级UI UX演示设计师，专注于生成设计良好的PPT页面。

当前PPT页面的页面描述如下：
<page_description>
{page_desc}
</page_description>

<reference_information>
整个PPT的大纲为：
{outline_text}

当前位于章节：{current_section}
</reference_information>

<design_guidelines>
- 要求文字清晰锐利，画面为4K分辨率，16:9比例
{style_guideline}
- 根据内容自动设计最完美的构图，不重不漏地渲染"页面描述"中的文本
- 如非必要，禁止出现 markdown 格式符号（如 # 和 * 等）
{template_note}
- 使用大小恰当的装饰性图形或插画对空缺位置进行填补
- 确保文字与背景有足够的对比度
- 保持页面整洁、专业、美观
</design_guidelines>

{get_ppt_language_instruction(language)}
{cover_instructions}
{extra_req_text}

请生成这张PPT页面的完整图像。
"""
    return prompt


# =============================================================================
# 图片提示词生成 Prompt
# =============================================================================
def get_slide_image_prompt(
    slide_title: str,
    slide_content: str,
    ppt_topic: str,
    template_colors: Dict[str, str] = None,
    language: str = 'zh'
) -> str:
    """
    根据幻灯片标题和内容生成图片提示词
    
    Args:
        slide_title: 幻灯片标题
        slide_content: 幻灯片内容
        ppt_topic: PPT 主题
        template_colors: 模板配色（可选）
        language: 语言
    """
    color_guidance = ""
    if template_colors:
        color_guidance = f"""
配色要求：
- 主色调：{template_colors.get('primary', '#1E40AF')}
- 次要色：{template_colors.get('secondary', '#3B82F6')}
- 强调色：{template_colors.get('accent', '#F97316')}
- 背景色：{template_colors.get('background', '#FFFFFF')}
- 文字色：{template_colors.get('text', '#1F2937')}
"""
    
    prompt = f"""\
你是一个专业的PPT背景图设计师。请根据以下信息，为PPT页面设计一张高质量的背景或装饰图。

PPT主题：{ppt_topic}
页面标题：{slide_title}
页面内容摘要：{slide_content[:200] if len(slide_content) > 200 else slide_content}

{color_guidance}

设计要求：
- 生成适合作为PPT页面背景的图像
- 图像应与页面内容主题相关
- 保持现代、专业的视觉风格
- 4K分辨率，16:9比例
- 不要在图像中包含任何文字
- 确保有足够的空白区域用于放置文字
- 使用抽象几何图形、渐变色块或简约插画风格

请直接返回用于AI图片生成的英文提示词，不需要任何其他说明。
示例输出格式：
"A futuristic city skyline at sunset, cyberpunk style, neon lights, abstract geometric shapes, gradient background, professional presentation style, 4k, high detail, no text"
"""
    return prompt


# =============================================================================
# 配图生成 Prompt（重要：这是配图，不是整个 PPT 页面！）
# =============================================================================
def get_illustration_prompt(
    topic: str,
    slide_title: str,
    slide_content: str,
    illustration_theme: str = "",
    style: str = "professional",
    language: str = "zh"
) -> str:
    """
    生成 PPT 配图的提示词
    
    重要：这是生成配图/插图，不是生成整个 PPT 页面！
    
    Args:
        topic: PPT 主题
        slide_title: 幻灯片标题
        slide_content: 幻灯片内容
        illustration_theme: 配图主题描述
        style: 风格 (professional, creative, minimal, tech, nature)
        language: 语言
    """
    # 根据风格选择描述
    style_descriptions = {
        "professional": "clean, corporate, professional business style, subtle gradients",
        "creative": "vibrant colors, dynamic shapes, artistic, modern design",
        "minimal": "minimalist, simple shapes, clean lines, whitespace",
        "tech": "futuristic, digital, circuit patterns, neon accents, dark background",
        "nature": "organic shapes, natural colors, leaves, eco-friendly aesthetic"
    }
    
    style_desc = style_descriptions.get(style, style_descriptions["professional"])
    
    # 使用配图主题或从内容推断
    theme = illustration_theme or topic
    
    prompt = f"""Create an illustration for a presentation slide.

Topic: {topic}
Slide Title: {slide_title}
Illustration Theme: {theme}
Content Context: {slide_content[:200] if slide_content else 'General'}

CRITICAL REQUIREMENTS:
1. This is an ILLUSTRATION/IMAGE ONLY, NOT a complete PPT slide
2. DO NOT include ANY text, words, letters, or numbers in the image
3. NO titles, NO captions, NO labels
4. The image should visually represent the theme: {theme}

Style Requirements:
- {style_desc}
- High quality, suitable for professional presentations
- Clean composition with clear focal point
- Aspect ratio: 16:9 or 4:3
- Resolution: High quality (suitable for 4K display)
- The illustration should complement the slide content, not replace it

The image will be placed alongside text content on the slide, so it should:
- Be visually appealing but not overwhelming
- Work well as a supporting visual element
- Have appropriate contrast and colors

Generate a beautiful, professional illustration that enhances the presentation without any text."""

    return prompt


def get_illustration_prompt_cn(
    topic: str,
    slide_title: str,
    slide_content: str,
    illustration_theme: str = "",
    style: str = "professional"
) -> str:
    """
    生成 PPT 配图的中文提示词（备用）
    """
    theme = illustration_theme or topic
    
    prompt = f"""为演示文稿页面创建一张配图。

主题：{topic}
页面标题：{slide_title}
配图主题：{theme}
内容上下文：{slide_content[:150] if slide_content else '通用'}

关键要求：
1. 这只是一张配图/插图，不是完整的 PPT 页面
2. 图片中不要包含任何文字、字母或数字
3. 不要有标题、说明文字或标签
4. 图片应当视觉化地表达主题：{theme}

风格要求：
- 专业、简洁、现代的商务风格
- 高质量，适合专业演示使用
- 清晰的构图和焦点
- 宽高比：16:9 或 4:3
- 高分辨率

这张配图将与文字内容并排放置在幻灯片上，因此：
- 视觉效果吸引但不喧宾夺主
- 作为文字内容的视觉辅助
- 颜色和对比度适当

生成一张精美的专业配图，不包含任何文字。"""

    return prompt


# =============================================================================
# 大纲优化 Prompt
# =============================================================================
def get_outline_refinement_prompt(
    current_outline: List[Dict],
    user_requirement: str,
    original_topic: str,
    language: str = 'zh'
) -> str:
    """
    根据用户要求修改已有大纲的 prompt
    """
    outline_json = json.dumps(current_outline, ensure_ascii=False, indent=2) if current_outline else "(当前没有内容)"
    
    prompt = f"""\
你是一位专业的PPT内容策划专家。请根据用户的要求修改和调整现有的PPT大纲。

原始主题：{original_topic}

当前的PPT大纲结构：
{outline_json}

**用户现在提出新的要求：{user_requirement}**

请根据用户的要求修改和调整大纲。你可以：
- 添加、删除或重新排列页面
- 修改页面标题和要点
- 调整页面的组织结构
- 添加或删除章节（part）
- 合并或拆分页面

输出格式同之前（简单格式或章节格式），只输出JSON，不要包含其他文字。
{get_language_instruction(language)}
"""
    return prompt

