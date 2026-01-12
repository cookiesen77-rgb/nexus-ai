"""
Banana Slides 代理路由
将 /api/banana/* 请求代理到 banana-slides 后端
"""
import httpx
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/banana", tags=["banana-ppt"])

# Banana Slides 后端地址
BANANA_BACKEND_URL = "http://127.0.0.1:5001"

# 超时配置
TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=300.0,  # 图片生成可能需要较长时间
    write=60.0,
    pool=10.0
)


async def proxy_request(
    request: Request,
    path: str,
    method: str = "GET",
    body: Optional[bytes] = None
) -> Response:
    """
    代理请求到 Banana Slides 后端
    """
    # 构建目标 URL
    target_url = f"{BANANA_BACKEND_URL}/api/{path}"
    
    # 复制请求头（排除 host）
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # 添加查询参数
    if request.query_params:
        target_url += f"?{request.query_params}"
    
    logger.debug(f"Proxying {method} request to: {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
            )
            
            # 复制响应头
            response_headers = dict(response.headers)
            # 移除可能导致问题的头
            response_headers.pop("content-encoding", None)
            response_headers.pop("transfer-encoding", None)
            response_headers.pop("content-length", None)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except httpx.ConnectError:
        logger.error(f"Cannot connect to Banana Slides backend at {BANANA_BACKEND_URL}")
        raise HTTPException(
            status_code=503,
            detail="Banana Slides 服务不可用，请确保后端已启动"
        )
    except httpx.TimeoutException:
        logger.error(f"Timeout connecting to Banana Slides backend")
        raise HTTPException(
            status_code=504,
            detail="Banana Slides 服务响应超时"
        )
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"代理请求失败: {str(e)}"
        )


# ============ 项目相关 API ============

@router.post("/projects")
async def create_project(request: Request):
    """创建新项目"""
    body = await request.body()
    return await proxy_request(request, "projects", "POST", body)


@router.get("/projects")
async def list_projects(request: Request):
    """获取项目列表"""
    return await proxy_request(request, "projects", "GET")


@router.get("/projects/{project_id}")
async def get_project(request: Request, project_id: str):
    """获取项目详情"""
    return await proxy_request(request, f"projects/{project_id}", "GET")


@router.put("/projects/{project_id}")
async def update_project(request: Request, project_id: str):
    """更新项目"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}", "PUT", body)


@router.delete("/projects/{project_id}")
async def delete_project(request: Request, project_id: str):
    """删除项目"""
    return await proxy_request(request, f"projects/{project_id}", "DELETE")


# ============ 大纲相关 API ============

@router.get("/projects/{project_id}/outline")
async def get_outline(request: Request, project_id: str):
    """获取项目大纲"""
    return await proxy_request(request, f"projects/{project_id}/outline", "GET")


@router.post("/projects/{project_id}/generate/outline")
async def generate_outline(request: Request, project_id: str):
    """生成大纲"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/generate/outline", "POST", body)


@router.put("/projects/{project_id}/outline")
async def update_outline(request: Request, project_id: str):
    """更新大纲"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/outline", "PUT", body)


@router.post("/projects/{project_id}/refine/outline")
async def refine_outline(request: Request, project_id: str):
    """AI 优化大纲"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/refine/outline", "POST", body)


# ============ 页面描述相关 API ============

@router.get("/projects/{project_id}/pages")
async def get_pages(request: Request, project_id: str):
    """获取所有页面"""
    return await proxy_request(request, f"projects/{project_id}/pages", "GET")


@router.get("/projects/{project_id}/pages/{page_id}")
async def get_page(request: Request, project_id: str, page_id: str):
    """获取单个页面"""
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}", "GET")


@router.put("/projects/{project_id}/pages/{page_id}")
async def update_page(request: Request, project_id: str, page_id: str):
    """更新页面"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}", "PUT", body)


@router.post("/projects/{project_id}/generate/descriptions")
async def generate_descriptions(request: Request, project_id: str):
    """生成所有页面描述"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/generate/descriptions", "POST", body)


@router.post("/projects/{project_id}/refine/descriptions")
async def refine_descriptions(request: Request, project_id: str):
    """AI 优化描述"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/refine/descriptions", "POST", body)


@router.post("/projects/{project_id}/generate/from-description")
async def generate_from_description(request: Request, project_id: str):
    """从描述生成大纲和页面"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/generate/from-description", "POST", body)


@router.post("/projects/{project_id}/pages")
async def create_page(request: Request, project_id: str):
    """创建页面"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages", "POST", body)


@router.delete("/projects/{project_id}/pages/{page_id}")
async def delete_page(request: Request, project_id: str, page_id: str):
    """删除页面"""
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}", "DELETE")


@router.put("/projects/{project_id}/pages/{page_id}/outline")
async def update_page_outline(request: Request, project_id: str, page_id: str):
    """更新页面大纲"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/outline", "PUT", body)


@router.put("/projects/{project_id}/pages/{page_id}/description")
async def update_page_description(request: Request, project_id: str, page_id: str):
    """更新页面描述"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/description", "PUT", body)


@router.post("/projects/{project_id}/pages/{page_id}/generate/description")
async def generate_page_description(request: Request, project_id: str, page_id: str):
    """生成单个页面描述"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/generate/description", "POST", body)


# ============ 图片生成相关 API ============

@router.post("/projects/{project_id}/generate/images")
async def generate_images(request: Request, project_id: str):
    """生成所有页面图片"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/generate/images", "POST", body)


@router.post("/projects/{project_id}/pages/{page_id}/generate/image")
async def generate_page_image(request: Request, project_id: str, page_id: str):
    """生成单个页面图片"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/generate/image", "POST", body)


@router.post("/projects/{project_id}/pages/{page_id}/edit/image")
async def edit_page_image(request: Request, project_id: str, page_id: str):
    """编辑页面图片"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/edit/image", "POST", body)


@router.get("/projects/{project_id}/pages/{page_id}/image-versions")
async def get_image_versions(request: Request, project_id: str, page_id: str):
    """获取图片版本历史"""
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/image-versions", "GET")


@router.post("/projects/{project_id}/pages/{page_id}/image-versions/{version_id}/set-current")
async def restore_image_version(request: Request, project_id: str, page_id: str, version_id: str):
    """恢复到指定版本"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/pages/{page_id}/image-versions/{version_id}/set-current", "POST", body)


# ============ 任务相关 API ============

@router.get("/tasks/{task_id}")
async def get_task(request: Request, task_id: str):
    """获取任务状态"""
    return await proxy_request(request, f"tasks/{task_id}", "GET")


# ============ 导出相关 API ============

@router.post("/projects/{project_id}/export/pptx")
async def export_pptx(request: Request, project_id: str):
    """导出 PPTX"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/export/pptx", "POST", body)


@router.post("/projects/{project_id}/export/editable-pptx")
async def export_editable_pptx(request: Request, project_id: str):
    """导出可编辑 PPTX"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/export/editable-pptx", "POST", body)


@router.post("/projects/{project_id}/export/pdf")
async def export_pdf(request: Request, project_id: str):
    """导出 PDF"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/export/pdf", "POST", body)


# ============ 模板相关 API ============

@router.get("/templates")
async def list_templates(request: Request):
    """获取预设模板列表"""
    return await proxy_request(request, "templates", "GET")


@router.get("/user-templates")
async def list_user_templates(request: Request):
    """获取用户模板列表"""
    return await proxy_request(request, "user-templates", "GET")


@router.post("/user-templates")
async def upload_user_template(request: Request):
    """上传用户模板"""
    body = await request.body()
    return await proxy_request(request, "user-templates", "POST", body)


@router.delete("/user-templates/{template_id}")
async def delete_user_template(request: Request, template_id: str):
    """删除用户模板"""
    return await proxy_request(request, f"user-templates/{template_id}", "DELETE")


@router.post("/projects/{project_id}/template")
async def upload_project_template(request: Request, project_id: str):
    """上传项目模板"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/template", "POST", body)


# ============ 素材相关 API ============

@router.get("/materials")
async def list_materials(request: Request):
    """获取素材列表"""
    return await proxy_request(request, "materials", "GET")


@router.post("/materials")
async def upload_material(request: Request):
    """上传素材"""
    body = await request.body()
    return await proxy_request(request, "materials", "POST", body)


@router.post("/materials/generate")
async def generate_material(request: Request):
    """AI 生成素材"""
    body = await request.body()
    return await proxy_request(request, "materials/generate", "POST", body)


@router.get("/projects/{project_id}/materials")
async def list_project_materials(request: Request, project_id: str):
    """获取项目素材"""
    return await proxy_request(request, f"projects/{project_id}/materials", "GET")


@router.post("/projects/{project_id}/materials")
async def upload_project_material(request: Request, project_id: str):
    """上传项目素材"""
    body = await request.body()
    return await proxy_request(request, f"projects/{project_id}/materials", "POST", body)


# ============ 参考文件相关 API ============

@router.get("/reference-files")
async def list_reference_files(request: Request):
    """获取参考文件列表"""
    return await proxy_request(request, "reference-files", "GET")


@router.post("/reference-files")
async def upload_reference_file(request: Request):
    """上传参考文件"""
    body = await request.body()
    return await proxy_request(request, "reference-files", "POST", body)


@router.get("/reference-files/{file_id}")
async def get_reference_file(request: Request, file_id: str):
    """获取参考文件详情"""
    return await proxy_request(request, f"reference-files/{file_id}", "GET")


@router.post("/reference-files/{file_id}/parse")
async def parse_reference_file(request: Request, file_id: str):
    """解析参考文件"""
    body = await request.body()
    return await proxy_request(request, f"reference-files/{file_id}/parse", "POST", body)


# ============ 设置相关 API ============

@router.get("/settings")
async def get_settings(request: Request):
    """获取设置"""
    return await proxy_request(request, "settings", "GET")


@router.put("/settings")
async def update_settings(request: Request):
    """更新设置"""
    body = await request.body()
    return await proxy_request(request, "settings", "PUT", body)


# ============ 文件访问 API ============

@router.get("/files/{path:path}")
async def get_file(request: Request, path: str):
    """获取文件（图片、导出文件等）"""
    return await proxy_request(request, f"files/{path}", "GET")


# ============ 健康检查 ============

@router.get("/health")
async def health_check():
    """检查 Banana Slides 后端状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BANANA_BACKEND_URL}/health")
            if response.status_code == 200:
                return {
                    "status": "ok",
                    "backend": "connected",
                    "message": "Banana Slides 服务运行正常"
                }
    except Exception as e:
        logger.warning(f"Banana Slides health check failed: {e}")
    
    return {
        "status": "error",
        "backend": "disconnected",
        "message": "Banana Slides 服务不可用"
    }
