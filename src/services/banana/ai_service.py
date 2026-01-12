"""
Nexus PPT AI 服务
处理所有 AI 模型交互，包括大纲生成、页面描述、图片生成
"""

import os
import re
import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .providers.text_provider import GeminiTextProvider, get_text_provider
from .providers.image_provider import GeminiImageProvider, get_image_provider
from .prompts import PPTPrompts

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """项目上下文数据类"""
    idea_prompt: Optional[str] = None
    outline_text: Optional[str] = None
    description_text: Optional[str] = None
    creation_type: str = 'idea'  # 'idea', 'outline', 'description'
    reference_files_content: List[Dict[str, str]] = field(default_factory=list)
    template_style: Optional[str] = None  # 风格描述
    
    def get_original_input(self) -> str:
        """获取原始用户输入"""
        if self.creation_type == 'idea' and self.idea_prompt:
            return self.idea_prompt
        elif self.creation_type == 'outline' and self.outline_text:
            return f"用户提供的大纲：\n{self.outline_text}"
        elif self.creation_type == 'description' and self.description_text:
            return f"用户提供的描述：\n{self.description_text}"
        return self.idea_prompt or ""


class AIService:
    """AI 服务类 - 处理所有 AI 模型交互"""
    
    def __init__(
        self,
        text_provider: Optional[GeminiTextProvider] = None,
        image_provider: Optional[GeminiImageProvider] = None
    ):
        """
        初始化 AI 服务
        
        Args:
            text_provider: 文本生成 Provider（默认使用 Gemini）
            image_provider: 图像生成 Provider（默认使用 Gemini）
        """
        self.text_provider = text_provider or get_text_provider("gemini")
        self.image_provider = image_provider or get_image_provider("gemini")
    
    # ==================== 大纲生成 ====================
    
    async def generate_outline(
        self,
        project_context: ProjectContext,
        language: str = 'zh'
    ) -> List[Dict]:
        """
        生成 PPT 大纲
        
        Args:
            project_context: 项目上下文
            language: 输出语言
            
        Returns:
            大纲列表，每个元素为 {"title": str, "points": List[str]}
        """
        if project_context.creation_type == 'idea':
            # 从想法生成大纲
            prompt = PPTPrompts.outline_generation(
                idea_prompt=project_context.idea_prompt or "",
                reference_files_content=project_context.reference_files_content,
                language=language
            )
        elif project_context.creation_type == 'outline':
            # 解析用户提供的大纲
            prompt = PPTPrompts.outline_parsing(
                outline_text=project_context.outline_text or "",
                reference_files_content=project_context.reference_files_content,
                language=language
            )
        elif project_context.creation_type == 'description':
            # 从描述提取大纲
            prompt = PPTPrompts.description_to_outline(
                description_text=project_context.description_text or "",
                reference_files_content=project_context.reference_files_content,
                language=language
            )
        else:
            raise ValueError(f"不支持的创建类型: {project_context.creation_type}")
        
        logger.info(f"[AIService] 生成大纲, type={project_context.creation_type}")
        
        result = await self.text_provider.generate_json(prompt)
        
        if not result:
            logger.warning("[AIService] 大纲生成返回空结果，使用默认大纲")
            return self._default_outline(project_context.idea_prompt or "演示文稿", 5)
        
        # 展平大纲（如果有 part 结构）
        return self._flatten_outline(result)
    
    def _flatten_outline(self, outline: Any) -> List[Dict]:
        """展平大纲结构（处理 part-based 格式）"""
        if not isinstance(outline, list):
            return []
        
        flattened = []
        for item in outline:
            if "part" in item and "pages" in item:
                # Part-based 格式
                for page in item["pages"]:
                    page["part"] = item["part"]
                    flattened.append(page)
            else:
                # 简单格式
                flattened.append(item)
        
        return flattened
    
    def _default_outline(self, topic: str, page_count: int = 5) -> List[Dict]:
        """生成默认大纲"""
        return [
            {"title": topic, "points": ["副标题"]},
            {"title": "目录", "points": ["第一部分", "第二部分", "第三部分"]},
            {"title": "第一部分", "points": ["要点1", "要点2", "要点3"]},
            {"title": "第二部分", "points": ["要点1", "要点2", "要点3"]},
            {"title": "总结", "points": ["感谢观看"]},
        ][:page_count]
    
    # ==================== 页面描述生成 ====================
    
    async def generate_page_description(
        self,
        project_context: ProjectContext,
        outline: List[Dict],
        page_outline: Dict,
        page_index: int,
        language: str = 'zh'
    ) -> Dict:
        """
        生成单个页面的描述
        
        Args:
            project_context: 项目上下文
            outline: 完整大纲
            page_outline: 当前页面大纲
            page_index: 页面索引（从1开始）
            language: 输出语言
            
        Returns:
            页面描述字典
        """
        part_info = ""
        if "part" in page_outline:
            part_info = f"\n当前章节: {page_outline['part']}"
        
        prompt = PPTPrompts.page_description(
            original_input=project_context.get_original_input(),
            outline=outline,
            page_outline=page_outline,
            page_index=page_index,
            part_info=part_info,
            reference_files_content=project_context.reference_files_content,
            language=language
        )
        
        logger.info(f"[AIService] 生成第 {page_index} 页描述")
        
        result = await self.text_provider.generate(prompt)
        
        return {
            "title": page_outline.get("title", f"第 {page_index} 页"),
            "description_content": result,
            "page_index": page_index
        }
    
    async def generate_all_descriptions(
        self,
        project_context: ProjectContext,
        outline: List[Dict],
        language: str = 'zh',
        max_workers: int = 3,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        并行生成所有页面的描述
        
        Args:
            project_context: 项目上下文
            outline: 完整大纲
            language: 输出语言
            max_workers: 最大并行数
            progress_callback: 进度回调 (current, total)
            
        Returns:
            所有页面描述列表
        """
        total = len(outline)
        results = [None] * total
        completed = 0
        
        async def generate_one(index: int):
            nonlocal completed
            result = await self.generate_page_description(
                project_context=project_context,
                outline=outline,
                page_outline=outline[index],
                page_index=index + 1,
                language=language
            )
            results[index] = result
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
            return result
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_workers)
        
        async def bounded_generate(index: int):
            async with semaphore:
                return await generate_one(index)
        
        await asyncio.gather(*[bounded_generate(i) for i in range(total)])
        
        return results
    
    # ==================== 图片生成 ====================
    
    async def generate_page_image(
        self,
        page_description: str,
        outline_text: str,
        current_section: str,
        page_index: int = 1,
        template_image: Optional[str] = None,
        material_images: Optional[List[str]] = None,
        extra_requirements: Optional[str] = None,
        language: str = 'zh'
    ) -> Optional[str]:
        """
        生成单个页面的图片
        
        Args:
            page_description: 页面描述
            outline_text: 大纲文本
            current_section: 当前章节
            page_index: 页面索引
            template_image: 模板图片 base64
            material_images: 素材图片列表
            extra_requirements: 额外要求（风格描述）
            language: 输出语言
            
        Returns:
            图片 base64 字符串
        """
        has_template = template_image is not None
        has_material = material_images and len(material_images) > 0
        
        prompt = PPTPrompts.image_generation(
            page_desc=page_description,
            outline_text=outline_text,
            current_section=current_section,
            has_material_images=has_material,
            extra_requirements=extra_requirements,
            language=language,
            has_template=has_template,
            page_index=page_index
        )
        
        # 收集参考图片
        reference_images = []
        if template_image:
            reference_images.append(template_image)
        if material_images:
            reference_images.extend(material_images[:3])  # 最多3张素材
        
        logger.info(f"[AIService] 生成第 {page_index} 页图片, 参考图数量: {len(reference_images)}")
        
        result = await self.image_provider.generate_image(
            prompt=prompt,
            reference_images=reference_images if reference_images else None,
            aspect_ratio="16:9",  # PPT 标准宽高比
            image_size="1K"       # 1K 清晰度 (1376x768)
        )
        
        return result
    
    async def generate_all_images(
        self,
        pages: List[Dict],
        outline: List[Dict],
        template_image: Optional[str] = None,
        material_images: Optional[List[str]] = None,
        extra_requirements: Optional[str] = None,
        language: str = 'zh',
        max_workers: int = 2,
        progress_callback: Optional[callable] = None
    ) -> List[Optional[str]]:
        """
        并行生成所有页面的图片
        
        Args:
            pages: 页面列表，每个包含 description_content
            outline: 完整大纲
            template_image: 模板图片
            material_images: 素材图片
            extra_requirements: 额外要求
            language: 输出语言
            max_workers: 最大并行数
            progress_callback: 进度回调
            
        Returns:
            图片列表
        """
        total = len(pages)
        results = [None] * total
        completed = 0
        
        outline_text = json.dumps(outline, ensure_ascii=False)
        
        async def generate_one(index: int):
            nonlocal completed
            page = pages[index]
            page_outline = outline[index] if index < len(outline) else {}
            current_section = page_outline.get("part", f"第 {index + 1} 页")
            
            result = await self.generate_page_image(
                page_description=page.get("description_content", ""),
                outline_text=outline_text,
                current_section=current_section,
                page_index=index + 1,
                template_image=template_image,
                material_images=material_images,
                extra_requirements=extra_requirements,
                language=language
            )
            results[index] = result
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
            return result
        
        semaphore = asyncio.Semaphore(max_workers)
        
        async def bounded_generate(index: int):
            async with semaphore:
                return await generate_one(index)
        
        await asyncio.gather(*[bounded_generate(i) for i in range(total)])
        
        return results
    
    # ==================== 图片编辑 ====================
    
    async def edit_page_image(
        self,
        original_image: str,
        edit_instruction: str,
        original_description: Optional[str] = None
    ) -> Optional[str]:
        """
        编辑页面图片
        
        Args:
            original_image: 原始图片 base64
            edit_instruction: 编辑指令
            original_description: 原始页面描述
            
        Returns:
            编辑后的图片 base64
        """
        prompt = PPTPrompts.image_edit(
            edit_instruction=edit_instruction,
            original_description=original_description
        )
        
        logger.info(f"[AIService] 编辑图片: {edit_instruction[:50]}...")
        
        result = await self.image_provider.edit_image(
            original_image=original_image,
            edit_prompt=prompt
        )
        
        return result
    
    # ==================== 大纲修改 ====================
    
    async def refine_outline(
        self,
        current_outline: List[Dict],
        user_requirement: str,
        original_input: str = "",
        previous_requirements: Optional[List[str]] = None,
        language: str = 'zh'
    ) -> List[Dict]:
        """
        根据用户要求修改大纲
        
        Args:
            current_outline: 当前大纲
            user_requirement: 用户要求
            original_input: 原始输入
            previous_requirements: 之前的修改要求
            language: 输出语言
            
        Returns:
            修改后的大纲
        """
        prompt = PPTPrompts.outline_refinement(
            current_outline=current_outline,
            user_requirement=user_requirement,
            original_input=original_input,
            previous_requirements=previous_requirements,
            language=language
        )
        
        logger.info(f"[AIService] 修改大纲: {user_requirement[:50]}...")
        
        result = await self.text_provider.generate_json(prompt)
        
        if not result:
            logger.warning("[AIService] 大纲修改返回空结果，保持原大纲")
            return current_outline
        
        return self._flatten_outline(result)
    
    # ==================== 工具方法 ====================
    
    @staticmethod
    def extract_image_urls_from_markdown(text: str) -> List[str]:
        """从 Markdown 文本中提取图片 URL"""
        pattern = r'!\[[^\]]*\]\(([^)]+)\)'
        matches = re.findall(pattern, text)
        return matches
    
    @staticmethod
    def remove_image_urls_from_markdown(text: str) -> str:
        """从 Markdown 文本中移除图片 URL"""
        pattern = r'!\[[^\]]*\]\([^)]+\)'
        return re.sub(pattern, '', text).strip()


# 全局实例
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """获取 AI 服务单例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service

