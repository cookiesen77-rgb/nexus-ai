"""
Nexus PPT API 路由
提供完整的 PPT 生成、编辑、导出 API
"""

import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ...services.banana import AIService, ProjectContext, get_ai_service
from ...services.banana.task_manager import TaskManager, TaskType, TaskStatus, get_task_manager
from ...services.banana.export_service import ExportService, get_export_service
from ...models.banana.project import PPTProject, save_project, get_project, delete_project, list_projects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ppt", tags=["PPT"])


# ==================== 请求/响应模型 ====================

class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    creation_type: str = Field(default="idea", description="创建类型: idea, outline, description")
    idea_prompt: Optional[str] = Field(default=None, description="一句话想法")
    outline_text: Optional[str] = Field(default=None, description="大纲文本")
    description_text: Optional[str] = Field(default=None, description="描述文本")
    template_style: Optional[str] = Field(default=None, description="模板风格描述")
    name: Optional[str] = Field(default=None, description="项目名称")


class RefineRequest(BaseModel):
    """修改请求"""
    user_requirement: str = Field(..., description="用户要求")
    previous_requirements: Optional[List[str]] = Field(default=None, description="之前的要求")


class EditImageRequest(BaseModel):
    """编辑图片请求"""
    edit_instruction: str = Field(..., description="编辑指令")


class GenerateImagesRequest(BaseModel):
    """批量生成图片请求"""
    page_ids: Optional[List[str]] = Field(default=None, description="要生成的页面ID列表")
    language: str = Field(default="zh", description="输出语言")


class ApiResponse(BaseModel):
    """通用 API 响应"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[Dict] = None


# ==================== 项目管理 API ====================

@router.post("/projects", response_model=ApiResponse)
async def create_project(request: CreateProjectRequest, background_tasks: BackgroundTasks):
    """创建 PPT 项目"""
    try:
        # 确定项目名称
        name = request.name
        if not name:
            if request.idea_prompt:
                name = request.idea_prompt[:30] + "..." if len(request.idea_prompt) > 30 else request.idea_prompt
            else:
                name = "演示文稿"
        
        # 创建项目
        project = PPTProject(
            name=name,
            creation_type=request.creation_type,
            idea_prompt=request.idea_prompt,
            outline_text=request.outline_text,
            description_text=request.description_text,
            template_style=request.template_style,
            status="draft"
        )
        
        save_project(project)
        
        logger.info(f"[PPT API] 创建项目: {project.id}")
        
        return ApiResponse(data={
            "project_id": project.id,
            **project.to_dict()
        })
        
    except Exception as e:
        logger.error(f"[PPT API] 创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=ApiResponse)
async def list_all_projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """获取项目列表"""
    projects = list_projects(limit=limit, offset=offset)
    return ApiResponse(data={
        "projects": [p.to_dict() for p in projects],
        "total": len(projects)
    })


@router.get("/projects/{project_id}", response_model=ApiResponse)
async def get_project_detail(project_id: str):
    """获取项目详情"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return ApiResponse(data=project.to_dict())


@router.delete("/projects/{project_id}", response_model=ApiResponse)
async def delete_project_api(project_id: str):
    """删除项目"""
    if delete_project(project_id):
        return ApiResponse(data={"message": "项目已删除"})
    raise HTTPException(status_code=404, detail="项目不存在")


# ==================== 大纲生成 API ====================

@router.post("/projects/{project_id}/generate/outline", response_model=ApiResponse)
async def generate_outline(project_id: str, language: str = Query(default="zh")):
    """生成大纲"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    try:
        project.status = "generating"
        save_project(project)
        
        ai_service = get_ai_service()
        context = ProjectContext(
            idea_prompt=project.idea_prompt,
            outline_text=project.outline_text,
            description_text=project.description_text,
            creation_type=project.creation_type,
            template_style=project.template_style
        )
        
        outline = await ai_service.generate_outline(context, language=language)
        
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
        
        project.status = "draft"
        save_project(project)
        
        logger.info(f"[PPT API] 大纲生成完成: {project_id}, {len(outline)} 页")
        
        return ApiResponse(data={
            "outline": outline,
            "pages": project.pages
        })
        
    except Exception as e:
        project.status = "failed"
        save_project(project)
        logger.error(f"[PPT API] 大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/refine/outline", response_model=ApiResponse)
async def refine_outline(project_id: str, request: RefineRequest, language: str = Query(default="zh")):
    """修改大纲"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    try:
        ai_service = get_ai_service()
        
        new_outline = await ai_service.refine_outline(
            current_outline=project.outline,
            user_requirement=request.user_requirement,
            original_input=project.idea_prompt or "",
            previous_requirements=request.previous_requirements,
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
        
        save_project(project)
        
        return ApiResponse(data={
            "pages": project.pages,
            "message": "大纲已更新"
        })
        
    except Exception as e:
        logger.error(f"[PPT API] 大纲修改失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 描述生成 API ====================

@router.post("/projects/{project_id}/generate/descriptions", response_model=ApiResponse)
async def generate_descriptions(
    project_id: str, 
    background_tasks: BackgroundTasks,
    language: str = Query(default="zh")
):
    """批量生成页面描述（异步）"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not project.outline:
        raise HTTPException(status_code=400, detail="请先生成大纲")
    
    # 创建任务
    task_manager = get_task_manager()
    task = await task_manager.create_task(TaskType.GENERATE_DESCRIPTIONS)
    
    # 在后台执行
    async def run_generation():
        try:
            await task_manager.update_task(task.id, status=TaskStatus.PROCESSING)
            
            ai_service = get_ai_service()
            context = ProjectContext(
                idea_prompt=project.idea_prompt,
                outline_text=project.outline_text,
                description_text=project.description_text,
                creation_type=project.creation_type,
                template_style=project.template_style
            )
            
            def progress_callback(current, total):
                asyncio.create_task(task_manager.update_task(
                    task.id,
                    progress={"completed": current, "total": total}
                ))
            
            descriptions = await ai_service.generate_all_descriptions(
                project_context=context,
                outline=project.outline,
                language=language,
                progress_callback=progress_callback
            )
            
            # 更新页面描述
            for i, desc in enumerate(descriptions):
                if i < len(project.pages):
                    project.pages[i]["description_content"] = desc.get("description_content", "")
                    project.pages[i]["status"] = "description_ready"
            
            save_project(project)
            
            await task_manager.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result={"pages_count": len(descriptions)}
            )
            
        except Exception as e:
            await task_manager.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
    
    background_tasks.add_task(asyncio.create_task, run_generation())
    
    return ApiResponse(data={"task_id": task.id, "status": "PENDING"})


@router.post("/projects/{project_id}/pages/{page_id}/generate/description", response_model=ApiResponse)
async def generate_page_description(
    project_id: str,
    page_id: str,
    language: str = Query(default="zh"),
    force_regenerate: bool = Query(default=False)
):
    """生成单页描述"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    page = project.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    
    try:
        ai_service = get_ai_service()
        context = ProjectContext(
            idea_prompt=project.idea_prompt,
            outline_text=project.outline_text,
            description_text=project.description_text,
            creation_type=project.creation_type,
            template_style=project.template_style
        )
        
        page_index = page.get("order_index", 0) + 1
        page_outline = page.get("outline_content", {})
        
        result = await ai_service.generate_page_description(
            project_context=context,
            outline=project.outline,
            page_outline=page_outline,
            page_index=page_index,
            language=language
        )
        
        # 更新页面
        page["description_content"] = result.get("description_content", "")
        page["status"] = "description_ready"
        save_project(project)
        
        return ApiResponse(data=page)
        
    except Exception as e:
        logger.error(f"[PPT API] 页面描述生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 图片生成 API ====================

@router.post("/projects/{project_id}/generate/images", response_model=ApiResponse)
async def generate_images(
    project_id: str,
    request: GenerateImagesRequest,
    background_tasks: BackgroundTasks
):
    """批量生成图片（异步）"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 确定要生成的页面
    if request.page_ids:
        pages = [p for p in project.pages if p.get("id") in request.page_ids]
    else:
        pages = project.pages
    
    if not pages:
        raise HTTPException(status_code=400, detail="没有可生成的页面")
    
    # 创建任务
    task_manager = get_task_manager()
    task = await task_manager.create_task(TaskType.GENERATE_IMAGES)
    
    async def run_generation():
        try:
            await task_manager.update_task(task.id, status=TaskStatus.PROCESSING)
            
            ai_service = get_ai_service()
            
            def progress_callback(current, total):
                asyncio.create_task(task_manager.update_task(
                    task.id,
                    progress={"completed": current, "total": total}
                ))
            
            images = await ai_service.generate_all_images(
                pages=pages,
                outline=project.outline,
                extra_requirements=project.template_style,
                language=request.language,
                progress_callback=progress_callback
            )
            
            # 更新页面图片
            for i, image_base64 in enumerate(images):
                if image_base64 and i < len(pages):
                    page_id = pages[i].get("id")
                    for p in project.pages:
                        if p.get("id") == page_id:
                            p["image_base64"] = image_base64
                            p["status"] = "completed"
                            break
            
            save_project(project)
            
            await task_manager.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result={"images_count": len([i for i in images if i])}
            )
            
        except Exception as e:
            await task_manager.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
    
    background_tasks.add_task(asyncio.create_task, run_generation())
    
    return ApiResponse(data={"task_id": task.id, "status": "PENDING"})


@router.post("/projects/{project_id}/pages/{page_id}/generate/image", response_model=ApiResponse)
async def generate_page_image(
    project_id: str,
    page_id: str,
    background_tasks: BackgroundTasks,
    language: str = Query(default="zh"),
    force_regenerate: bool = Query(default=False)
):
    """生成单页图片"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    page = project.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    
    # 创建任务
    task_manager = get_task_manager()
    task = await task_manager.create_task(TaskType.GENERATE_IMAGES)
    
    async def run_generation():
        try:
            await task_manager.update_task(task.id, status=TaskStatus.PROCESSING)
            
            ai_service = get_ai_service()
            
            page_index = page.get("order_index", 0) + 1
            page_outline = page.get("outline_content", {})
            current_section = page.get("part", f"第 {page_index} 页")
            
            import json
            outline_text = json.dumps(project.outline, ensure_ascii=False)
            
            image = await ai_service.generate_page_image(
                page_description=page.get("description_content", ""),
                outline_text=outline_text,
                current_section=current_section,
                page_index=page_index,
                extra_requirements=project.template_style,
                language=language
            )
            
            if image:
                page["image_base64"] = image
                page["status"] = "completed"
                save_project(project)
            
            await task_manager.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result={"success": image is not None}
            )
            
        except Exception as e:
            await task_manager.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
    
    background_tasks.add_task(asyncio.create_task, run_generation())
    
    return ApiResponse(data={"task_id": task.id, "status": "PENDING"})


@router.post("/projects/{project_id}/pages/{page_id}/edit/image", response_model=ApiResponse)
async def edit_page_image(
    project_id: str,
    page_id: str,
    request: EditImageRequest,
    background_tasks: BackgroundTasks
):
    """编辑页面图片"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    page = project.get_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="页面不存在")
    
    if not page.get("image_base64"):
        raise HTTPException(status_code=400, detail="页面没有图片可编辑")
    
    # 创建任务
    task_manager = get_task_manager()
    task = await task_manager.create_task(TaskType.EDIT_IMAGE)
    
    async def run_edit():
        try:
            await task_manager.update_task(task.id, status=TaskStatus.PROCESSING)
            
            ai_service = get_ai_service()
            
            edited_image = await ai_service.edit_page_image(
                original_image=page["image_base64"],
                edit_instruction=request.edit_instruction,
                original_description=page.get("description_content")
            )
            
            if edited_image:
                page["image_base64"] = edited_image
                save_project(project)
            
            await task_manager.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result={"success": edited_image is not None}
            )
            
        except Exception as e:
            await task_manager.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )
    
    background_tasks.add_task(asyncio.create_task, run_edit())
    
    return ApiResponse(data={"task_id": task.id, "status": "PENDING"})


# ==================== 任务查询 API ====================

@router.get("/projects/{project_id}/tasks/{task_id}", response_model=ApiResponse)
async def get_task_status(project_id: str, task_id: str):
    """查询任务状态"""
    task_manager = get_task_manager()
    task = await task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return ApiResponse(data=task.to_dict())


# ==================== 导出 API ====================

@router.get("/projects/{project_id}/export/pptx")
async def export_pptx(
    project_id: str,
    page_ids: Optional[str] = Query(default=None, description="逗号分隔的页面ID")
):
    """导出 PPTX"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 确定要导出的页面
    if page_ids:
        selected_ids = page_ids.split(",")
        pages = [p for p in project.pages if p.get("id") in selected_ids]
    else:
        pages = project.pages
    
    if not pages:
        raise HTTPException(status_code=400, detail="没有可导出的页面")
    
    try:
        export_service = get_export_service()
        filepath = export_service.export_pptx(pages, project_name=project.name)
        
        return ApiResponse(data={
            "download_url": f"/api/ppt/download/{os.path.basename(filepath)}"
        })
        
    except Exception as e:
        logger.error(f"[PPT API] 导出 PPTX 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/export/pdf")
async def export_pdf(
    project_id: str,
    page_ids: Optional[str] = Query(default=None, description="逗号分隔的页面ID")
):
    """导出 PDF"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if page_ids:
        selected_ids = page_ids.split(",")
        pages = [p for p in project.pages if p.get("id") in selected_ids]
    else:
        pages = project.pages
    
    if not pages:
        raise HTTPException(status_code=400, detail="没有可导出的页面")
    
    try:
        export_service = get_export_service()
        filepath = export_service.export_pdf(pages, project_name=project.name)
        
        return ApiResponse(data={
            "download_url": f"/api/ppt/download/{os.path.basename(filepath)}"
        })
        
    except Exception as e:
        logger.error(f"[PPT API] 导出 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_file(filename: str):
    """下载文件"""
    export_service = get_export_service()
    filepath = os.path.join(export_service.output_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )


# ==================== 页面管理 API ====================

@router.put("/projects/{project_id}/pages/{page_id}", response_model=ApiResponse)
async def update_page(project_id: str, page_id: str, data: Dict[str, Any]):
    """更新页面"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    updated_page = project.update_page(page_id, data)
    if not updated_page:
        raise HTTPException(status_code=404, detail="页面不存在")
    
    save_project(project)
    return ApiResponse(data=updated_page)


@router.delete("/projects/{project_id}/pages/{page_id}", response_model=ApiResponse)
async def delete_page(project_id: str, page_id: str):
    """删除页面"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if project.delete_page(page_id):
        save_project(project)
        return ApiResponse(data={"message": "页面已删除"})
    
    raise HTTPException(status_code=404, detail="页面不存在")


@router.post("/projects/{project_id}/pages", response_model=ApiResponse)
async def add_page(project_id: str, data: Dict[str, Any]):
    """添加页面"""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    page = project.add_page(data)
    save_project(project)
    
    return ApiResponse(data=page)

