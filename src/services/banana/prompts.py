"""
Nexus PPT 服务 - AI 提示词模板
基于 banana-slides 项目适配
"""

import json
import logging
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .ai_service import ProjectContext

logger = logging.getLogger(__name__)


# 语言配置映射
LANGUAGE_CONFIG = {
    'zh': {
        'name': '中文',
        'instruction': '请使用全中文输出。',
        'ppt_text': 'PPT文字请使用全中文。'
    },
    'ja': {
        'name': '日本語',
        'instruction': 'すべて日本語で出力してください。',
        'ppt_text': 'PPTのテキストは全て日本語で出力してください。'
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


def get_language_instruction(language: str = None) -> str:
    """获取语言限制指令"""
    lang = language or 'zh'
    config = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG['zh'])
    return config['instruction']


def get_ppt_language_instruction(language: str = None) -> str:
    """获取 PPT 文字语言限制指令"""
    lang = language or 'zh'
    config = LANGUAGE_CONFIG.get(lang, LANGUAGE_CONFIG['zh'])
    return config['ppt_text']


def _format_reference_files_xml(reference_files_content: Optional[List[Dict[str, str]]]) -> str:
    """将参考文件格式化为 XML 结构"""
    if not reference_files_content:
        return ""
    
    xml_parts = ["<uploaded_files>"]
    for file_info in reference_files_content:
        filename = file_info.get('filename', 'unknown')
        content = file_info.get('content', '')
        xml_parts.append(f'  <file name="{filename}">')
        xml_parts.append('    <content>')
        xml_parts.append(content)
        xml_parts.append('    </content>')
        xml_parts.append('  </file>')
    xml_parts.append('</uploaded_files>')
    xml_parts.append('')
    
    return '\n'.join(xml_parts)


class PPTPrompts:
    """PPT 生成提示词管理类"""
    
    @staticmethod
    def outline_generation(
        idea_prompt: str,
        reference_files_content: Optional[List[Dict]] = None,
        language: str = 'zh'
    ) -> str:
        """生成 PPT 大纲的提示词"""
        files_xml = _format_reference_files_xml(reference_files_content)
        
        prompt = f"""\
You are a helpful assistant that generates an outline for a ppt.

You can organize the content in two ways:

1. Simple format (for short PPTs without major sections):
[{{"title": "title1", "points": ["point1", "point2"]}}, {{"title": "title2", "points": ["point1", "point2"]}}]

2. Part-based format (for longer PPTs with major sections):
[
    {{
    "part": "Part 1: Introduction",
    "pages": [
        {{"title": "Welcome", "points": ["point1", "point2"]}},
        {{"title": "Overview", "points": ["point1", "point2"]}}
    ]
    }}
]

Choose the format that best fits the content.
Unless otherwise specified, the first page should be kept simplest, containing only the title, subtitle, and presenter information.

The user's request: {idea_prompt}. Now generate the outline, don't include any other text.
{get_language_instruction(language)}
"""
        return files_xml + prompt
    
    @staticmethod
    def outline_parsing(
        outline_text: str,
        reference_files_content: Optional[List[Dict]] = None,
        language: str = 'zh'
    ) -> str:
        """解析用户提供的大纲文本"""
        files_xml = _format_reference_files_xml(reference_files_content)
        
        prompt = f"""\
You are a helpful assistant that parses a user-provided PPT outline text into a structured format.

The user has provided the following outline text:

{outline_text}

Your task is to analyze this text and convert it into a structured JSON format WITHOUT modifying any of the original text content.

Output format:
[{{"title": "title1", "points": ["point1", "point2"]}}, {{"title": "title2", "points": ["point1", "point2"]}}]

Or for longer PPTs with sections:
[{{"part": "Part 1", "pages": [{{"title": "title", "points": ["point1"]}}]}}]

Important: DO NOT modify, rewrite, or change any text from the original outline.
Return only the JSON, don't include any other text.
{get_language_instruction(language)}
"""
        return files_xml + prompt
    
    @staticmethod
    def page_description(
        original_input: str,
        outline: List[Dict],
        page_outline: Dict,
        page_index: int,
        part_info: str = "",
        reference_files_content: Optional[List[Dict]] = None,
        language: str = 'zh'
    ) -> str:
        """生成单个页面描述"""
        files_xml = _format_reference_files_xml(reference_files_content)
        
        first_page_note = ""
        if page_index == 1:
            first_page_note = "**除非特殊要求，第一页的内容需要保持极简，只放标题副标题以及演讲人等，不添加任何素材。**"
        
        prompt = f"""\
我们正在为PPT的每一页生成内容描述。
用户的原始需求是：
{original_input}

我们已经有了完整的大纲：
{json.dumps(outline, ensure_ascii=False)}
{part_info}

现在请为第 {page_index} 页生成描述：
{json.dumps(page_outline, ensure_ascii=False)}
{first_page_note}

【重要提示】生成的"页面文字"部分会直接渲染到PPT页面上，因此请务必注意：
1. 文字内容要简洁精炼，每条要点控制在15-25字以内
2. 条理清晰，使用列表形式组织内容
3. 避免冗长的句子和复杂的表述
4. 确保内容可读性强，适合在演示时展示

输出格式示例：
页面标题：[标题]
{"副标题：[副标题]" if page_index == 1 else ""}

页面文字：
- [要点1]
- [要点2]
- [要点3]

其他页面素材（如果有markdown图片链接、公式、表格等）

{get_language_instruction(language)}
"""
        return files_xml + prompt
    
    @staticmethod
    def image_generation(
        page_desc: str,
        outline_text: str,
        current_section: str,
        has_material_images: bool = False,
        extra_requirements: str = None,
        language: str = 'zh',
        has_template: bool = True,
        page_index: int = 1
    ) -> str:
        """生成图片生成提示词"""
        
        material_note = ""
        if has_material_images:
            material_note = "\n\n提示：用户提供了额外的素材图片，请从这些素材图片中选择合适的元素整合到生成的PPT页面中。"
        
        extra_req_text = ""
        if extra_requirements and extra_requirements.strip():
            extra_req_text = f"\n\n额外要求（请务必遵循）：\n{extra_requirements}\n"
        
        template_guideline = "- 配色和设计语言和模板图片严格相似。" if has_template else "- 严格按照风格描述进行设计。"
        
        cover_note = ""
        if page_index == 1:
            cover_note = "\n\n**注意：当前页面为PPT的封面页，请采用专业的封面设计美学技巧，务必凸显出页面标题，分清主次，确保一下就能抓住观众的注意力。**"
        
        prompt = f"""\
你是一位专家级UI UX演示设计师，专注于生成设计良好的PPT页面。

当前PPT页面的页面描述如下:
<page_description>
{page_desc}
</page_description>

<reference_information>
整个PPT的大纲为：
{outline_text}

当前位于章节：{current_section}
</reference_information>

<design_guidelines>
- 要求文字清晰锐利, 画面为4K分辨率，16:9比例。
{template_guideline}
- 根据内容自动设计最完美的构图，不重不漏地渲染"页面描述"中的文本。
- 如非必要，禁止出现 markdown 格式符号（如 # 和 * 等）。
- 使用大小恰当的装饰性图形或插画对空缺位置进行填补。
</design_guidelines>
{get_ppt_language_instruction(language)}{material_note}{extra_req_text}{cover_note}
"""
        return prompt
    
    @staticmethod
    def image_edit(edit_instruction: str, original_description: str = None) -> str:
        """生成图片编辑提示词"""
        if original_description:
            if "其他页面素材" in original_description:
                original_description = original_description.split("其他页面素材")[0].strip()
            
            prompt = f"""\
该PPT页面的原始页面描述为：
{original_description}

现在，根据以下指令修改这张PPT页面：{edit_instruction}

要求维持原有的文字内容和设计风格，只按照指令进行修改。
"""
        else:
            prompt = f"根据以下指令修改这张PPT页面：{edit_instruction}\n保持原有的内容结构和设计风格，只按照指令进行修改。"
        
        return prompt
    
    @staticmethod
    def outline_refinement(
        current_outline: List[Dict],
        user_requirement: str,
        original_input: str = "",
        previous_requirements: Optional[List[str]] = None,
        language: str = 'zh'
    ) -> str:
        """修改大纲的提示词"""
        outline_text = json.dumps(current_outline, ensure_ascii=False, indent=2) if current_outline else "(当前没有内容)"
        
        prev_text = ""
        if previous_requirements:
            prev_list = "\n".join([f"- {req}" for req in previous_requirements])
            prev_text = f"\n\n之前的修改要求：\n{prev_list}\n"
        
        prompt = f"""\
You are a helpful assistant that modifies PPT outlines based on user requirements.

原始输入：{original_input}

当前的 PPT 大纲：
{outline_text}
{prev_text}
**用户现在提出新的要求：{user_requirement}**

请根据用户的要求修改大纲，可以添加、删除、重新排列页面。

输出格式：
[{{"title": "title1", "points": ["point1", "point2"]}}, ...]

或章节格式：
[{{"part": "Part 1", "pages": [{{"title": "title", "points": ["point1"]}}]}}]

只输出 JSON，不要包含其他文字。
{get_language_instruction(language)}
"""
        return prompt
    
    @staticmethod
    def description_to_outline(
        description_text: str,
        reference_files_content: Optional[List[Dict]] = None,
        language: str = 'zh'
    ) -> str:
        """从描述文本提取大纲"""
        files_xml = _format_reference_files_xml(reference_files_content)
        
        prompt = f"""\
You are a helpful assistant that analyzes a user-provided PPT description text and extracts the outline structure.

The user has provided the following description text:

{description_text}

Your task is to extract the outline structure (titles and key points) for each page.

Output format:
[{{"title": "title1", "points": ["point1", "point2"]}}, ...]

Return only the JSON, don't include any other text.
{get_language_instruction(language)}
"""
        return files_xml + prompt
    
    @staticmethod
    def description_split(
        description_text: str,
        outline: List[Dict],
        language: str = 'zh'
    ) -> str:
        """切分描述文本为每页描述"""
        outline_json = json.dumps(outline, ensure_ascii=False, indent=2)
        
        prompt = f"""\
You are a helpful assistant that splits a complete PPT description text into individual page descriptions.

Complete description text:
{description_text}

Outline structure:
{outline_json}

Split the description into individual page descriptions based on the outline.

Return a JSON array where each element is a page description string:
[
    "页面标题：xxx\\n页面文字：\\n- 要点1\\n- 要点2",
    ...
]

Return only the JSON array, don't include any other text.
{get_language_instruction(language)}
"""
        return prompt

