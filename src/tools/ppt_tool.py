"""
PPT 制作工具 - 供 LLM 调用
深度集成 Banana Slides 功能
"""

import logging
from typing import Any, Optional, List, Dict

from src.tools.base import BaseTool, ToolResult, ToolStatus
from src.services.banana import AIService, ProjectContext, get_ai_service
from src.services.banana.export_service import ExportService, get_export_service
from src.models.banana.project import PPTProject, save_project, get_project, list_projects

logger = logging.getLogger(__name__)


class PPTTool(BaseTool):
    """PPT 创建和编辑工具 - 深度集成 Banana Slides"""
    
    name = "ppt"
    description = """创建、编辑和导出 PPT 演示文稿。支持三种创建方式和完整编辑功能。

创建方式：
1. from_idea: 一句话生成 PPT（最简单）
2. from_outline: 从大纲文本生成
3. from_description: 从详细描述生成

编辑功能：
- get: 获取项目详情
- refine_outline: 修改大纲
- generate_descriptions: 生成页面描述
- generate_images: 生成页面图片
- edit_image: 编辑单页图片
- export_pptx: 导出 PPTX 文件
- export_pdf: 导出 PDF 文件
- list_projects: 列出所有项目

示例：
- 一句话生成: {"action": "from_idea", "idea": "人工智能发展历程", "page_count": 8}
- 从大纲生成: {"action": "from_outline", "outline": "1. 引言\\n2. 历史\\n3. 现状\\n4. 未来\\n5. 总结"}
- 修改大纲: {"action": "refine_outline", "project_id": "xxx", "requirement": "增加一页关于机器学习的内容"}
- 导出: {"action": "export_pptx", "project_id": "xxx"}
"""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "from_idea", "from_outline", "from_description",
                    "get", "list_projects",
                    "refine_outline", "generate_descriptions", "generate_images",
                    "edit_image", "export_pptx", "export_pdf"
                ],
                "description": "操作类型"
            },
            "idea": {
                "type": "string",
                "description": "一句话想法（from_idea 时必需）"
            },
            "outline": {
                "type": "string",
                "description": "大纲文本（from_outline 时必需）"
            },
            "description": {
                "type": "string",
                "description": "详细描述文本（from_description 时必需）"
            },
            "page_count": {
                "type": "integer",
                "description": "页数，默认 8",
                "default": 8
            },
            "style": {
                "type": "string",
                "description": "风格描述，如：深色科技风、简约商务风"
            },
            "language": {
                "type": "string",
                "enum": ["zh", "en", "ja"],
                "description": "输出语言，默认中文",
                "default": "zh"
            },
            "project_id": {
                "type": "string",
                "description": "项目 ID（编辑操作时必需）"
            },
            "page_id": {
                "type": "string",
                "description": "页面 ID（单页操作时必需）"
            },
            "requirement": {
                "type": "string",
                "description": "修改要求（refine_outline 时必需）"
            },
            "edit_instruction": {
                "type": "string",
                "description": "图片编辑指令（edit_image 时必需）"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.export_service = get_export_service()
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行 PPT 操作"""
        action = kwargs.get("action")
        
        try:
            if action == "from_idea":
                return await self._create_from_idea(kwargs)
            elif action == "from_outline":
                return await self._create_from_outline(kwargs)
            elif action == "from_description":
                return await self._create_from_description(kwargs)
            elif action == "get":
                return self._get_project(kwargs)
            elif action == "list_projects":
                return self._list_projects()
            elif action == "refine_outline":
                return await self._refine_outline(kwargs)
            elif action == "generate_descriptions":
                return await self._generate_descriptions(kwargs)
            elif action == "generate_images":
                return await self._generate_images(kwargs)
            elif action == "edit_image":
                return await self._edit_image(kwargs)
            elif action == "export_pptx":
                return self._export_pptx(kwargs)
            elif action == "export_pdf":
                return self._export_pdf(kwargs)
            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    output="",
                    error=f"未知操作: {action}"
                )
        except Exception as e:
            logger.error(f"PPT 工具执行错误: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=str(e)
            )
    
    # ==================== 创建操作 ====================
    
    async def _create_from_idea(self, kwargs: dict) -> ToolResult:
        """从一句话想法创建 PPT"""
        idea = kwargs.get("idea")
        if not idea:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: idea"
            )
        
        page_count = kwargs.get("page_count", 8)
        style = kwargs.get("style", "")
        language = kwargs.get("language", "zh")
        
        # 创建项目
        project = PPTProject(
            name=idea[:30] + "..." if len(idea) > 30 else idea,
            creation_type="idea",
            idea_prompt=idea,
            template_style=style,
            status="generating"
        )
        save_project(project)
        
        logger.info(f"[PPT Tool] 从想法创建 PPT: {idea[:50]}...")
        
        # 创建上下文
        context = ProjectContext(
            idea_prompt=idea,
            creation_type="idea",
            template_style=style
        )
        
        # 生成大纲
        outline = await self.ai_service.generate_outline(context, language=language)
        
        # 限制页数
        if len(outline) > page_count:
            outline = outline[:page_count]
        
        # 更新项目
        project.outline = outline
        project.pages = []
        for i, item in enumerate(outline):
            page_data = {
                "id": f"page_{i}",
                "order_index": i,
                "outline_content": {"title": item.get("title", ""), "points": item.get("points", [])},
                "part": item.get("part"),
                "status": "draft"
            }
            project.pages.append(page_data)
        
        project.status = "outline_ready"
        save_project(project)
        
        # 生成描述
        logger.info(f"[PPT Tool] 生成页面描述...")
        descriptions = await self.ai_service.generate_all_descriptions(
            project_context=context,
            outline=outline,
            language=language
        )
        
        for i, desc in enumerate(descriptions):
            if i < len(project.pages):
                project.pages[i]["description_content"] = desc.get("description_content", "")
                project.pages[i]["status"] = "description_ready"
        
        project.status = "descriptions_ready"
        save_project(project)
        
        # 生成图片
        logger.info(f"[PPT Tool] 生成页面图片...")
        images = await self.ai_service.generate_all_images(
            pages=project.pages,
            outline=outline,
            extra_requirements=style,
            language=language
        )
        
        for i, image_base64 in enumerate(images):
            if image_base64 and i < len(project.pages):
                project.pages[i]["image_base64"] = image_base64
                project.pages[i]["status"] = "completed"
        
        project.status = "completed"
        save_project(project)
        
        # 构建输出
        slides_summary = []
        for i, page in enumerate(project.pages):
            has_image = "✓" if page.get("image_base64") else "✗"
            title = page.get("outline_content", {}).get("title", "未命名")
            slides_summary.append(f"  {i+1}. {title} [图片: {has_image}]")
        
        output = f"""✅ PPT 创建成功！

项目 ID: {project.id}
主题: {project.name}
页数: {len(project.pages)}
状态: 已完成

大纲:
{chr(10).join(slides_summary)}

后续操作：
- 查看详情: {{"action": "get", "project_id": "{project.id}"}}
- 修改大纲: {{"action": "refine_outline", "project_id": "{project.id}", "requirement": "你的修改要求"}}
- 重新生成图片: {{"action": "generate_images", "project_id": "{project.id}"}}
- 导出 PPTX: {{"action": "export_pptx", "project_id": "{project.id}"}}
- 导出 PDF: {{"action": "export_pdf", "project_id": "{project.id}"}}
"""
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            data=project.to_dict()
        )
    
    async def _create_from_outline(self, kwargs: dict) -> ToolResult:
        """从大纲文本创建 PPT"""
        outline_text = kwargs.get("outline")
        if not outline_text:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: outline"
            )
        
        style = kwargs.get("style", "")
        language = kwargs.get("language", "zh")
        
        # 创建项目
        project = PPTProject(
            name="从大纲创建",
            creation_type="outline",
            outline_text=outline_text,
            template_style=style,
            status="generating"
        )
        save_project(project)
        
        # 创建上下文
        context = ProjectContext(
            outline_text=outline_text,
            creation_type="outline",
            template_style=style
        )
        
        # 解析大纲
        outline = await self.ai_service.generate_outline(context, language=language)
        
        # 更新项目
        project.outline = outline
        project.pages = []
        for i, item in enumerate(outline):
            page_data = {
                "id": f"page_{i}",
                "order_index": i,
                "outline_content": {"title": item.get("title", ""), "points": item.get("points", [])},
                "part": item.get("part"),
                "status": "draft"
            }
            project.pages.append(page_data)
        
        if project.pages:
            first_title = project.pages[0].get("outline_content", {}).get("title", "")
            project.name = first_title if first_title else "从大纲创建"
        
        project.status = "outline_ready"
        save_project(project)
        
        # 生成描述和图片
        context.idea_prompt = project.name
        
        descriptions = await self.ai_service.generate_all_descriptions(
            project_context=context,
            outline=outline,
            language=language
        )
        
        for i, desc in enumerate(descriptions):
            if i < len(project.pages):
                project.pages[i]["description_content"] = desc.get("description_content", "")
        
        images = await self.ai_service.generate_all_images(
            pages=project.pages,
            outline=outline,
            extra_requirements=style,
            language=language
        )
        
        for i, image_base64 in enumerate(images):
            if image_base64 and i < len(project.pages):
                project.pages[i]["image_base64"] = image_base64
                project.pages[i]["status"] = "completed"
        
        project.status = "completed"
        save_project(project)
        
        slides_summary = [f"  {i+1}. {p.get('outline_content', {}).get('title', '')}" for i, p in enumerate(project.pages)]
        
        output = f"""✅ PPT 创建成功！

项目 ID: {project.id}
主题: {project.name}
页数: {len(project.pages)}

大纲:
{chr(10).join(slides_summary)}

导出命令: {{"action": "export_pptx", "project_id": "{project.id}"}}
"""
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            data=project.to_dict()
        )
    
    async def _create_from_description(self, kwargs: dict) -> ToolResult:
        """从详细描述创建 PPT"""
        description = kwargs.get("description")
        if not description:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: description"
            )
        
        style = kwargs.get("style", "")
        language = kwargs.get("language", "zh")
        
        # 创建项目
        project = PPTProject(
            name="从描述创建",
            creation_type="description",
            description_text=description,
            template_style=style,
            status="generating"
        )
        save_project(project)
        
        # 创建上下文
        context = ProjectContext(
            description_text=description,
            creation_type="description",
            template_style=style
        )
        
        # 生成大纲
        outline = await self.ai_service.generate_outline(context, language=language)
        
        # 更新项目
        project.outline = outline
        project.pages = []
        for i, item in enumerate(outline):
            page_data = {
                "id": f"page_{i}",
                "order_index": i,
                "outline_content": {"title": item.get("title", ""), "points": item.get("points", [])},
                "description_content": "",
                "status": "draft"
            }
            project.pages.append(page_data)
        
        if project.pages:
            first_title = project.pages[0].get("outline_content", {}).get("title", "")
            project.name = first_title if first_title else "从描述创建"
        
        # 生成描述和图片
        descriptions = await self.ai_service.generate_all_descriptions(
            project_context=context,
            outline=outline,
            language=language
        )
        
        for i, desc in enumerate(descriptions):
            if i < len(project.pages):
                project.pages[i]["description_content"] = desc.get("description_content", "")
        
        images = await self.ai_service.generate_all_images(
            pages=project.pages,
            outline=outline,
            extra_requirements=style,
            language=language
        )
        
        for i, image_base64 in enumerate(images):
            if image_base64 and i < len(project.pages):
                project.pages[i]["image_base64"] = image_base64
                project.pages[i]["status"] = "completed"
        
        project.status = "completed"
        save_project(project)
        
        slides_summary = [f"  {i+1}. {p.get('outline_content', {}).get('title', '')}" for i, p in enumerate(project.pages)]
        
        output = f"""✅ PPT 创建成功！

项目 ID: {project.id}
主题: {project.name}
页数: {len(project.pages)}

大纲:
{chr(10).join(slides_summary)}

导出命令: {{"action": "export_pptx", "project_id": "{project.id}"}}
"""
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            data=project.to_dict()
        )
    
    # ==================== 查询操作 ====================
    
    def _get_project(self, kwargs: dict) -> ToolResult:
        """获取项目详情"""
        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: project_id"
            )
        
        project = get_project(project_id)
        if not project:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"项目不存在: {project_id}"
            )
        
        slides_info = []
        for i, page in enumerate(project.pages):
            title = page.get("outline_content", {}).get("title", "未命名")
            has_image = "✓" if page.get("image_base64") else "✗"
            desc_preview = (page.get("description_content", "") or "")[:50]
            slides_info.append(f"  {i+1}. {title}\n     图片: {has_image} | 描述: {desc_preview}...")
        
        output = f"""项目详情：

ID: {project.id}
名称: {project.name}
状态: {project.status}
页数: {len(project.pages)}
创建时间: {project.created_at}

幻灯片:
{chr(10).join(slides_info)}
"""
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            data=project.to_dict()
        )
    
    def _list_projects(self) -> ToolResult:
        """列出所有项目"""
        projects = list_projects(limit=20)
        
        if not projects:
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="暂无 PPT 项目",
                data={"projects": []}
            )
        
        lines = ["PPT 项目列表：\n"]
        for p in projects:
            lines.append(f"- {p.name} (ID: {p.id}) [{p.status}] - {len(p.pages)} 页")
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output="\n".join(lines),
            data={"projects": [p.to_dict() for p in projects]}
        )
    
    # ==================== 编辑操作 ====================
    
    async def _refine_outline(self, kwargs: dict) -> ToolResult:
        """修改大纲"""
        project_id = kwargs.get("project_id")
        requirement = kwargs.get("requirement")
        
        if not project_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: project_id"
            )
        if not requirement:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: requirement"
            )
        
        project = get_project(project_id)
        if not project:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"项目不存在: {project_id}"
            )
        
        language = kwargs.get("language", "zh")
        
        # 修改大纲
        new_outline = await self.ai_service.refine_outline(
            current_outline=project.outline,
            user_requirement=requirement,
            original_input=project.idea_prompt or project.name,
            language=language
        )
        
        # 更新项目
        project.outline = new_outline
        project.pages = []
        for i, item in enumerate(new_outline):
            page_data = {
                "id": f"page_{i}",
                "order_index": i,
                "outline_content": {"title": item.get("title", ""), "points": item.get("points", [])},
                "part": item.get("part"),
                "status": "draft"
            }
            project.pages.append(page_data)
        
        project.status = "outline_ready"
        save_project(project)
        
        slides_summary = [f"  {i+1}. {p.get('outline_content', {}).get('title', '')}" for i, p in enumerate(project.pages)]
        
        output = f"""✅ 大纲已更新！

新大纲:
{chr(10).join(slides_summary)}

下一步：
- 生成描述: {{"action": "generate_descriptions", "project_id": "{project.id}"}}
- 继续修改: {{"action": "refine_outline", "project_id": "{project.id}", "requirement": "..."}}
"""
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=output,
            data=project.to_dict()
        )
    
    async def _generate_descriptions(self, kwargs: dict) -> ToolResult:
        """生成页面描述"""
        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: project_id"
            )
        
        project = get_project(project_id)
        if not project:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"项目不存在: {project_id}"
            )
        
        language = kwargs.get("language", "zh")
        
        context = ProjectContext(
            idea_prompt=project.idea_prompt,
            outline_text=project.outline_text,
            description_text=project.description_text,
            creation_type=project.creation_type,
            template_style=project.template_style
        )
        
        descriptions = await self.ai_service.generate_all_descriptions(
            project_context=context,
            outline=project.outline,
            language=language
        )
        
        for i, desc in enumerate(descriptions):
            if i < len(project.pages):
                project.pages[i]["description_content"] = desc.get("description_content", "")
                project.pages[i]["status"] = "description_ready"
        
        project.status = "descriptions_ready"
        save_project(project)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 已生成 {len(descriptions)} 页描述\n\n下一步: {{\"action\": \"generate_images\", \"project_id\": \"{project.id}\"}}",
            data=project.to_dict()
        )
    
    async def _generate_images(self, kwargs: dict) -> ToolResult:
        """生成页面图片"""
        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="缺少必需参数: project_id"
            )
        
        project = get_project(project_id)
        if not project:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"项目不存在: {project_id}"
            )
        
        language = kwargs.get("language", "zh")
        
        images = await self.ai_service.generate_all_images(
            pages=project.pages,
            outline=project.outline,
            extra_requirements=project.template_style,
            language=language
        )
        
        success_count = 0
        for i, image_base64 in enumerate(images):
            if image_base64 and i < len(project.pages):
                project.pages[i]["image_base64"] = image_base64
                project.pages[i]["status"] = "completed"
                success_count += 1
        
        project.status = "completed"
        save_project(project)
        
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"✅ 已生成 {success_count}/{len(project.pages)} 页图片\n\n导出命令: {{\"action\": \"export_pptx\", \"project_id\": \"{project.id}\"}}",
            data=project.to_dict()
        )
    
    async def _edit_image(self, kwargs: dict) -> ToolResult:
        """编辑单页图片"""
        project_id = kwargs.get("project_id")
        page_id = kwargs.get("page_id")
        edit_instruction = kwargs.get("edit_instruction")
        
        if not project_id:
            return ToolResult(status=ToolStatus.ERROR, output="", error="缺少 project_id")
        if not page_id:
            return ToolResult(status=ToolStatus.ERROR, output="", error="缺少 page_id")
        if not edit_instruction:
            return ToolResult(status=ToolStatus.ERROR, output="", error="缺少 edit_instruction")
        
        project = get_project(project_id)
        if not project:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"项目不存在: {project_id}")
        
        page = project.get_page(page_id)
        if not page:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"页面不存在: {page_id}")
        
        if not page.get("image_base64"):
            return ToolResult(status=ToolStatus.ERROR, output="", error="该页面没有图片")
        
        edited_image = await self.ai_service.edit_page_image(
            original_image=page["image_base64"],
            edit_instruction=edit_instruction,
            original_description=page.get("description_content")
        )
        
        if edited_image:
            page["image_base64"] = edited_image
            save_project(project)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"✅ 图片编辑成功",
                data={"page_id": page_id}
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error="图片编辑失败"
            )
    
    # ==================== 导出操作 ====================
    
    def _export_pptx(self, kwargs: dict) -> ToolResult:
        """导出 PPTX"""
        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(status=ToolStatus.ERROR, output="", error="缺少 project_id")
        
        project = get_project(project_id)
        if not project:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"项目不存在: {project_id}")
        
        try:
            filepath = self.export_service.export_pptx(project.pages, project.name)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"✅ PPTX 已导出到: {filepath}",
                data={"path": filepath}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, output="", error=str(e))
    
    def _export_pdf(self, kwargs: dict) -> ToolResult:
        """导出 PDF"""
        project_id = kwargs.get("project_id")
        if not project_id:
            return ToolResult(status=ToolStatus.ERROR, output="", error="缺少 project_id")
        
        project = get_project(project_id)
        if not project:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"项目不存在: {project_id}")
        
        try:
            filepath = self.export_service.export_pdf(project.pages, project.name)
            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"✅ PDF 已导出到: {filepath}",
                data={"path": filepath}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, output="", error=str(e))


# 注意：不要在模块导入时创建实例（会触发依赖初始化，阻塞 API 启动）。
# 需要使用时请由工具注册/调用方显式实例化。
