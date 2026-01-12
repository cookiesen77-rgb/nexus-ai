"""PPT API 路由"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.services.ppt_service import get_ppt_service
from src.models.ppt import get_all_templates, get_template_reference_image_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ppt", tags=["ppt"])


# 请求模型
class CreatePresentationRequest(BaseModel):
    topic: str
    page_count: int = 8
    template: str = "modern"
    requirements: str = ""


class UpdateSlideRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    layout: Optional[str] = None
    notes: Optional[str] = None


class RegenerateImageRequest(BaseModel):
    custom_prompt: Optional[str] = None


# 路由
@router.get("/templates")
async def list_templates():
    """获取所有可用模板"""
    templates = get_all_templates()
    return {"templates": templates}


@router.post("/create")
async def create_presentation(request: CreatePresentationRequest):
    """创建演示文稿"""
    try:
        ppt_service = get_ppt_service()
        template_ref = get_template_reference_image_bytes(request.template)
        presentation = await ppt_service.create_presentation(
            topic=request.topic,
            page_count=request.page_count,
            template=request.template,
            requirements=request.requirements,
            template_image=template_ref,
        )
        return {
            "success": True,
            "presentation": presentation.to_dict()
        }
    except Exception as e:
        logger.error(f"创建演示文稿失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{presentation_id}")
async def get_presentation(presentation_id: str):
    """获取演示文稿详情"""
    ppt_service = get_ppt_service()
    presentation = ppt_service.get_presentation(presentation_id)
    
    if not presentation:
        raise HTTPException(status_code=404, detail="演示文稿不存在")
    
    return {
        "success": True,
        "presentation": presentation.to_dict()
    }


@router.put("/{presentation_id}/slides/{slide_index}")
async def update_slide(
    presentation_id: str,
    slide_index: int,
    request: UpdateSlideRequest
):
    """更新幻灯片"""
    ppt_service = get_ppt_service()
    
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.content is not None:
        updates["content"] = request.content
    if request.layout is not None:
        updates["layout"] = request.layout
    if request.notes is not None:
        updates["notes"] = request.notes
    
    if not updates:
        raise HTTPException(status_code=400, detail="没有提供更新内容")
    
    slide = ppt_service.update_slide(presentation_id, slide_index, updates)
    
    if not slide:
        raise HTTPException(status_code=404, detail="幻灯片不存在")
    
    return {
        "success": True,
        "slide": slide.to_dict()
    }


@router.post("/{presentation_id}/slides/{slide_index}/regenerate-image")
async def regenerate_slide_image(
    presentation_id: str,
    slide_index: int,
    request: RegenerateImageRequest
):
    """重新生成幻灯片配图"""
    ppt_service = get_ppt_service()
    
    slide = await ppt_service.regenerate_slide_image(
        presentation_id,
        slide_index,
        request.custom_prompt
    )
    
    if not slide:
        raise HTTPException(status_code=404, detail="幻灯片不存在")
    
    return {
        "success": bool(slide.image_base64),
        "slide": slide.to_dict()
    }


@router.get("/{presentation_id}/export")
async def export_presentation(presentation_id: str):
    """导出为 PPTX 文件"""
    ppt_service = get_ppt_service()
    
    presentation = ppt_service.get_presentation(presentation_id)
    if not presentation:
        raise HTTPException(status_code=404, detail="演示文稿不存在")
    
    output_path = ppt_service.export_pptx(presentation_id)
    
    if not output_path:
        raise HTTPException(status_code=500, detail="导出失败")
    
    return FileResponse(
        path=output_path,
        filename=f"{presentation.title}.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@router.delete("/{presentation_id}")
async def delete_presentation(presentation_id: str):
    """删除演示文稿"""
    ppt_service = get_ppt_service()
    
    success = ppt_service.delete_presentation(presentation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="演示文稿不存在")
    
    return {"success": True, "message": "演示文稿已删除"}

