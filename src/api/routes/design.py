"""
Nexus AI Design Module API Routes
设计模块 API 路由

提供：
- 图像生成 (支持多模型)
- AI 设计对话 (使用 Grok)
- 项目持久化 (使用 Supabase)
- 元素拆分 (SAM + OCR + Inpainting)
- 视频生成 (预留)
"""

import os
import base64
import logging
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from src.services.gemini_image import GeminiImageClient
from src.llm.openai_compat import create_openai_client

logger = logging.getLogger(__name__)

_LOCAL_PROJECTS: Dict[str, Dict[str, Any]] = {}

async def get_design_llm(vision: bool = False):
    """获取设计模块使用的 LLM 客户端（开源版：仅环境变量配置）"""
    api_key = (os.getenv("ALLAPI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    base_url = (os.getenv("ALLAPI_BASE_URL") or "https://nexusapi.cn/v1").strip()
    if not api_key:
        raise RuntimeError("Missing ALLAPI_KEY (set it in your .env).")
    if not base_url:
        raise RuntimeError("Missing ALLAPI_BASE_URL (set it in your .env).")

    model = ((os.getenv("LLM_VISION_MODEL") if vision else os.getenv("LLM_DEFAULT_MODEL")) or "").strip()
    if not model:
        raise RuntimeError("Missing LLM_DEFAULT_MODEL / LLM_VISION_MODEL.")
    return create_openai_client(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    )

router = APIRouter(prefix="/design", tags=["Design"])


# ============================================
# 模型配置
# ============================================

class ImageModelProvider(str, Enum):
    GEMINI = "gemini"
    FLUX = "flux"
    DALLE = "dalle"
    MIDJOURNEY = "midjourney"


# 可用图像模型配置
IMAGE_MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-flash": {
        "name": "Gemini Flash",
        "provider": ImageModelProvider.GEMINI,
        "endpoint": "gemini-2.5-flash-image",
        "icon": "⚡",
        "speed": "fast",
        "quality": "good",
        "available": True,
        "description": "快速生成，适合迭代设计"
    },
    "gemini-pro": {
        "name": "Gemini Pro",
        "provider": ImageModelProvider.GEMINI,
        "endpoint": "gemini-3-pro-image-preview",
        "icon": "🎯",
        "speed": "medium",
        "quality": "excellent",
        "available": True,
        "description": "高质量输出，细节丰富"
    },
    "flux-pro": {
        "name": "Flux Pro",
        "provider": ImageModelProvider.FLUX,
        "endpoint": "flux-pro",
        "icon": "🎨",
        "speed": "medium",
        "quality": "excellent",
        "available": False,  # 待用户提供 API
        "description": "艺术风格生成专家"
    },
    "dall-e-3": {
        "name": "DALL-E 3",
        "provider": ImageModelProvider.DALLE,
        "endpoint": "dall-e-3",
        "icon": "🖼️",
        "speed": "medium",
        "quality": "excellent",
        "available": False,  # 待用户提供 API
        "description": "OpenAI 最新图像模型"
    },
}

# 视频模型配置（预留）
VIDEO_MODELS: Dict[str, Dict[str, Any]] = {
    "veo-3": {
        "name": "Veo 3.1",
        "provider": "google",
        "icon": "🎬",
        "available": False,
        "description": "Google 视频生成"
    },
    "sora-2": {
        "name": "Sora 2",
        "provider": "openai",
        "icon": "🎥",
        "available": False,
        "description": "OpenAI 视频生成"
    },
    "hailuo": {
        "name": "Hailuo 2.3",
        "provider": "minimax",
        "icon": "🌊",
        "available": False,
        "description": "MiniMax 视频生成"
    },
    "kling": {
        "name": "Kling o1",
        "provider": "kuaishou",
        "icon": "🎭",
        "available": False,
        "description": "快手可灵视频生成"
    },
}


# ============================================
# 请求/响应模型
# ============================================

class ImageGenerationRequest(BaseModel):
    """图像生成请求"""
    prompt: str = Field(..., description="图像描述提示词")
    resolution: str = Field("1K", description="分辨率: 1K, 2K, 4K")
    aspect_ratio: str = Field("1:1", description="宽高比: 1:1, 4:3, 16:9, 9:16, 3:4")
    reference_image: Optional[str] = Field(None, description="参考图片 base64")
    model: str = Field("gemini-flash", description="模型ID")


class ImageGenerationResponse(BaseModel):
    """图像生成响应"""
    image_base64: str
    width: int
    height: int
    model_used: str


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    icon: str
    speed: str
    quality: str
    available: bool
    description: str


class ModelsResponse(BaseModel):
    """模型列表响应"""
    image_models: List[ModelInfo]
    video_models: List[ModelInfo]


class DesignChatMessage(BaseModel):
    """对话消息"""
    role: str  # 'user' | 'assistant'
    content: str


class DesignAction(BaseModel):
    """AI 建议的操作"""
    type: str  # 'generate_image' | 'edit_element' | 'suggestion' | 'none'
    data: Optional[Dict[str, Any]] = None


class DesignChatRequest(BaseModel):
    """AI 设计对话请求"""
    message: str = Field(..., description="用户消息")
    conversation_history: Optional[List[DesignChatMessage]] = Field(None, description="对话历史")
    canvas_state: Optional[str] = Field(None, description="当前画布状态描述")
    model: Optional[str] = Field(None, description="可选：指定本次对话使用的 LLM 模型")
    enable_web_search: bool = Field(False, description="是否启用联网搜索（为 LLM 提供搜索上下文）")


class DesignChatResponse(BaseModel):
    """AI 设计对话响应"""
    reply: str
    action: Optional[DesignAction] = None
    optimized_prompt: Optional[str] = None
    suggested_params: Optional[Dict[str, str]] = None


class CanvasElement(BaseModel):
    """画布元素"""
    id: str
    type: str
    x: float
    y: float
    content: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    shapeType: Optional[str] = None
    fontSize: Optional[int] = None
    fontFamily: Optional[str] = None
    points: Optional[List[dict]] = None
    strokeWidth: Optional[int] = None
    referenceImageId: Optional[str] = None
    groupId: Optional[str] = None
    linkedElements: Optional[List[str]] = None
    connectorFrom: Optional[str] = None
    connectorTo: Optional[str] = None
    connectorStyle: Optional[str] = None


class ProjectSaveRequest(BaseModel):
    """项目保存请求"""
    id: Optional[str] = None
    name: str = Field(..., description="项目名称")
    elements: List[CanvasElement] = Field(default_factory=list)
    thumbnail: Optional[str] = None


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    elements: List[CanvasElement]
    thumbnail: Optional[str] = None
    created_at: str
    updated_at: str


# 元素拆分相关模型
class TextRegion(BaseModel):
    """文字区域"""
    id: str
    text: str
    bbox: List[float]  # [x, y, width, height]
    font_size: Optional[int] = None
    color: Optional[str] = None
    confidence: float


class ImageLayer(BaseModel):
    """图像图层"""
    id: str
    type: str  # 'text', 'subject', 'background', 'object'
    mask_base64: str  # 蒙版
    content_base64: Optional[str] = None  # 提取的内容
    bbox: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class ElementSplitRequest(BaseModel):
    """元素拆分请求"""
    image_base64: str = Field(..., description="待拆分图像 base64")
    extract_text: bool = Field(True, description="是否提取文字")
    extract_subjects: bool = Field(True, description="是否提取主体")
    extract_background: bool = Field(True, description="是否提取背景")


class ElementSplitResponse(BaseModel):
    """元素拆分响应"""
    layers: List[ImageLayer]
    text_regions: List[TextRegion]
    original_width: int
    original_height: int


class TextEditRequest(BaseModel):
    """文字编辑请求"""
    image_base64: str = Field(..., description="原始图像")
    text_edits: List[Dict[str, Any]] = Field(..., description="文字编辑操作")
    # text_edits 格式: [{"region_id": "...", "new_text": "...", "font_size": 24, "color": "#fff"}]


class TextEditResponse(BaseModel):
    """文字编辑响应"""
    result_base64: str
    width: int
    height: int


# ============================================
# 图像分析相关模型
# ============================================

class DetectedElement(BaseModel):
    """检测到的图像元素"""
    id: str
    type: str  # 'text' | 'object' | 'background' | 'person' | 'shape'
    label: str  # 用户友好的标签
    bbox: List[float]  # [x, y, width, height] 相对坐标 0-1
    confidence: float
    content: Optional[str] = None  # 文字内容（仅 text 类型）
    description: Optional[str] = None  # 元素描述


class ImageAnalysisRequest(BaseModel):
    """图像分析请求"""
    image_base64: str = Field(..., description="待分析图像 base64")
    analysis_type: str = Field("full", description="分析类型: full, text_only, objects_only")


class ImageAnalysisResponse(BaseModel):
    """图像分析响应"""
    elements: List[DetectedElement]
    overall_description: str
    suggested_edits: List[str]


class ElementRegenerateRequest(BaseModel):
    """元素重新生成请求"""
    original_image_base64: str = Field(..., description="原始图像")
    element_id: str = Field(..., description="要修改的元素 ID")
    element_bbox: List[float] = Field(..., description="元素边界框 [x, y, w, h]")
    modification_prompt: str = Field(..., description="修改描述")
    keep_style: bool = Field(True, description="是否保持原风格")


class ElementRegenerateResponse(BaseModel):
    """元素重新生成响应"""
    result_base64: str
    width: int
    height: int


# ============================================
# 辅助函数
# ============================================

def get_dimensions_from_aspect_ratio(aspect_ratio: str, resolution: str) -> tuple:
    """根据宽高比和分辨率计算尺寸"""
    base_sizes = {
        "1K": 1024,
        "2K": 2048,
        "4K": 4096
    }
    
    base = base_sizes.get(resolution, 1024)
    
    ratios = {
        "1:1": (1, 1),
        "4:3": (4, 3),
        "3:4": (3, 4),
        "16:9": (16, 9),
        "9:16": (9, 16)
    }
    
    ratio = ratios.get(aspect_ratio, (1, 1))
    
    if ratio[0] >= ratio[1]:
        width = base
        height = int(base * ratio[1] / ratio[0])
    else:
        height = base
        width = int(base * ratio[0] / ratio[1])
    
    return width, height


# ============================================
# API 端点 - 模型管理
# ============================================

@router.get("/models", response_model=ModelsResponse)
async def get_available_models():
    """
    获取可用模型列表
    """
    image_models = [
        ModelInfo(
            id=model_id,
            name=model["name"],
            icon=model["icon"],
            speed=model["speed"],
            quality=model["quality"],
            available=model["available"],
            description=model["description"]
        )
        for model_id, model in IMAGE_MODELS.items()
    ]
    
    video_models = [
        ModelInfo(
            id=model_id,
            name=model["name"],
            icon=model["icon"],
            speed="medium",
            quality="excellent",
            available=model["available"],
            description=model["description"]
        )
        for model_id, model in VIDEO_MODELS.items()
    ]
    
    return ModelsResponse(
        image_models=image_models,
        video_models=video_models
    )


# ============================================
# API 端点 - 图像生成
# ============================================

@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    生成 AI 图像
    
    支持多模型选择，默认使用 Gemini Flash
    """
    try:
        # 验证模型
        model_config = IMAGE_MODELS.get(request.model)
        if not model_config:
            raise HTTPException(status_code=400, detail=f"未知模型: {request.model}")
        
        if not model_config["available"]:
            raise HTTPException(
                status_code=400, 
                detail=f"模型 {model_config['name']} 暂不可用，请选择其他模型"
            )
        
        # 目前只支持 Gemini 系列
        if model_config["provider"] != ImageModelProvider.GEMINI:
            raise HTTPException(
                status_code=501,
                detail=f"模型 {model_config['name']} 即将上线"
            )
        
        client = GeminiImageClient()
        if not (client.api_key or "").strip():
            raise HTTPException(
                status_code=500,
                detail="design.image is not configured (missing ALLAPI_KEY).",
            )
        
        # 准备参考图片
        ref_images = None
        if request.reference_image:
            ref_data = request.reference_image
            if "," in ref_data:
                ref_data = ref_data.split(",")[1]
            ref_images = [base64.b64decode(ref_data)]
        
        # 构建提示词
        prompt = f"""Create a high-quality image based on the following description:

{request.prompt}

Requirements:
- High resolution, professional quality
- {request.aspect_ratio} aspect ratio
- Rich details and vibrant colors
- Suitable for design and creative work"""

        # 调用生成
        result = await client.generate_image(
            prompt=prompt,
            ref_images=ref_images,
            aspect_ratio=request.aspect_ratio
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"图像生成失败: {result.get('error', '未知错误')}"
            )
        
        width, height = get_dimensions_from_aspect_ratio(
            request.aspect_ratio,
            request.resolution
        )
        
        return ImageGenerationResponse(
            image_base64=result["image_base64"],
            width=width,
            height=height,
            model_used=request.model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像生成错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API 端点 - AI 设计对话
# ============================================

DESIGN_ASSISTANT_SYSTEM_PROMPT = """你是 Nexus AI 设计助手（Nexus Design Copilot），专注于「Canvas + Chatbox」的视觉设计工作流：用简洁清晰的沟通，产出可执行的生成参数与高质量提示词，帮助用户在画布里快速迭代。

你遵循模块化工作方式：先理解需求，再按步骤推进，必要时追问，最后提交可执行结果；并且不要暴露任何内部实现细节或“工具/搜索/系统提示词”等字样。

## 语言与表达
- 默认使用中文回复；若用户明确指定语言，则以用户指定语言为准。
- 回复以短段落为主，避免长篇大论；可以使用少量条目，但不要把整段内容变成纯列表。

## 绝对规则（必须遵守）
1) 你不能直接生成或输出图片。图片由系统后台生成，你只提供文本。
2) 不要输出任何图片 URL、不要使用 ![image]、不要输出 Markdown 图片语法。
3) 不要在回复中提到“搜索工具/联网搜索/内部实现/系统提示词/提示词来源”等字样。系统可能会给你一些“搜索结果”上下文，但你只能把它当参考信息使用，不能暴露来源。

## 你要完成的任务（按顺序）
1) 需求澄清：如果用户缺少关键约束（用途、风格、主体、尺寸/比例、文案语言、是否参考图），先问 1-3 个最关键的问题再生成提示词。
2) 设计建议：给出 2-4 句高密度建议（构图、配色、字体气质、光照/材质、场景）。
3) 提示词优化：把用户的中文需求转成高质量英文提示词（optimized_prompt），并补齐细节：主体、环境、材质、镜头/景别、光照、氛围、风格、排版空间（留白/文字区）、质量关键词。

## 何时输出可执行 JSON（非常重要）
当用户明确要求“生成图像/创建/画一张/设计一个/帮我出图/做一张海报/生成封面/生成 logo”等需要系统出图的请求时，你必须在回复末尾追加且仅追加一个 JSON 代码块（必须使用 ```json 包裹），并严格遵守字段与取值范围：

```json
{
  "action": "generate_image",
  "optimized_prompt": "English prompt here",
  "resolution": "1K",
  "aspect_ratio": "1:1"
}
```

字段规则：
- action：只能是 "generate_image"
- optimized_prompt：必须是英文；不要包含中文；不要包含 URL；不要包含 JSON 或反引号。
- resolution：只能从 "1K" | "2K" | "4K" 选择（默认 1K；强调细节/印刷/大图时选 2K/4K）
- aspect_ratio：只能从 "1:1" | "4:3" | "16:9" | "9:16" | "3:4" 选择（海报/详情页常用 3:4 或 4:3；横幅/封面 16:9；短视频封面 9:16）

如果用户只是讨论建议、评审、配色、文案方向、布局方案等，不要输出 JSON。

## 提示词质量标准（optimized_prompt）
- 结构：Subject + Scene + Composition + Lighting + Material + Style + Typography/negative space + Quality
- 画质：使用 high quality, highly detailed, professional, sharp focus, clean edges（不要强行写 8K）
- 风格：根据用户语气选择 photography / product shot / 3D render / illustration / flat design 等，避免风格冲突。
- 排版：需要文字的海报/封面，要写清 “space for headline and subheading / clean layout / balanced negative space”，但不要把具体中文文案塞进 prompt，除非用户明确给出英文文案。
- 参考图：如果用户提到“基于参考图/保持构图/同风格”，在 optimized_prompt 中加入 “use the reference image as composition/style reference, preserve layout” 等约束。

## 示例
用户：我想要一个咖啡店的宣传海报
助手：建议用温暖大地色+克制的现代排版；主体突出杯子与拉花，背景用木纹与咖啡豆点缀，留出标题区，光线用柔和晨光制造氛围。

```json
{
  "action": "generate_image",
  "optimized_prompt": "A professional coffee shop promotional poster, warm earthy brown and cream color palette, steaming latte art in an elegant ceramic cup on a rustic wooden table, scattered coffee beans, soft natural morning window light, centered composition with balanced negative space for headline and subheading, modern minimalist typography layout, commercial photography style, high quality, highly detailed, sharp focus",
  "resolution": "1K",
  "aspect_ratio": "3:4"
}
```"""


@router.post("/chat", response_model=DesignChatResponse)
async def design_chat(request: DesignChatRequest):
    """
    AI 设计对话
    
    使用 Grok (grok-4.1) 提供智能设计建议和自动图像生成
    
    工作流程：
    1. 接收用户消息和对话历史
    2. LLM 理解需求并优化提示词
    3. 返回结构化响应，包含可执行的操作
    """
    try:
        import json
        import re
        
        # 支持前端通过 @ 切换模型：若 request.model 提供，则覆盖默认模型
        if request.model:
            api_key = (os.getenv("ALLAPI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
            base_url = (os.getenv("ALLAPI_BASE_URL") or "https://nexusapi.cn/v1").strip()
            if not api_key or not base_url:
                raise RuntimeError("design.chat is not configured (missing ALLAPI_KEY/ALLAPI_BASE_URL).")
            llm = create_openai_client(
                model=str(request.model),
                base_url=base_url,
                api_key=api_key,
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            )
        else:
            llm = await get_design_llm(vision=False)
        
        messages = [
            {"role": "system", "content": DESIGN_ASSISTANT_SYSTEM_PROMPT}
        ]

        # 🌐 联网搜索：将搜索结果作为上下文提供给 LLM（不直接展示给用户）
        if request.enable_web_search and request.message:
            try:
                from src.tools.web_search import create_web_search_tool

                web_search_tool = create_web_search_tool()
                search_result = await web_search_tool.execute(query=request.message, max_results=5)
                if search_result.is_success and isinstance(search_result.output, dict):
                    answer = search_result.output.get("answer", "")
                    results = search_result.output.get("results", []) or []

                    def _clip(text: str, n: int = 220) -> str:
                        text = (text or "").strip()
                        return text if len(text) <= n else text[:n] + "…"

                    lines = []
                    if answer:
                        lines.append(f"摘要：{_clip(answer, 300)}")
                    for i, item in enumerate(results[:5], start=1):
                        title = item.get("title", "") if isinstance(item, dict) else ""
                        url = item.get("url", "") if isinstance(item, dict) else ""
                        content = item.get("content", "") if isinstance(item, dict) else ""
                        lines.append(f"{i}. {title}\n   {url}\n   {_clip(content)}")

                    messages.append({
                        "role": "system",
                        "content": "以下为联网搜索结果（仅供参考，优先使用更可信的信息源；不要在回复中暴露“搜索工具/内部实现”等字样）：\n\n"
                                   + "\n".join(lines)
                    })
                else:
                    # 搜索失败不阻断对话
                    logger.warning(f"联网搜索失败: {search_result.error}")
            except Exception as se:
                logger.warning(f"联网搜索异常: {se}")
        
        # 添加画布状态上下文
        if request.canvas_state:
            messages.append({
                "role": "system",
                "content": f"当前画布状态：{request.canvas_state}"
            })
        
        # 添加对话历史
        if request.conversation_history:
            for msg in request.conversation_history[-10:]:  # 限制历史长度
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # 添加当前消息
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # 调用 LLM
        response = await llm.achat(messages)
        full_reply = response.content if hasattr(response, 'content') else str(response)
        
        # 解析响应，提取 JSON 块
        action = None
        optimized_prompt = None
        suggested_params = None
        reply = full_reply
        
        # 尝试提取 JSON 块
        json_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
        json_match = re.search(json_pattern, full_reply)
        
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                
                if json_data.get("action") == "generate_image":
                    action = DesignAction(
                        type="generate_image",
                        data={
                            "resolution": json_data.get("resolution", "1K"),
                            "aspect_ratio": json_data.get("aspect_ratio", "1:1")
                        }
                    )
                    optimized_prompt = json_data.get("optimized_prompt")
                    suggested_params = {
                        "resolution": json_data.get("resolution", "1K"),
                        "aspect_ratio": json_data.get("aspect_ratio", "1:1")
                    }
                    
                # 从回复中移除 JSON 块，保留用户可读的部分
                reply = re.sub(json_pattern, '', full_reply).strip()
                
            except json.JSONDecodeError:
                logger.warning("无法解析 AI 响应中的 JSON 块")
        
        return DesignChatResponse(
            reply=reply,
            action=action,
            optimized_prompt=optimized_prompt,
            suggested_params=suggested_params
        )
        
    except Exception as e:
        logger.error(f"设计对话错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API 端点 - 元素拆分
# ============================================

@router.post("/split-elements", response_model=ElementSplitResponse)
async def split_elements(request: ElementSplitRequest):
    """
    拆分图像元素
    
    使用 AI 分割模型（SAM）将图像拆分为多个独立图层：
    - 文字层
    - 主体层
    - 背景层
    - 其他对象
    
    技术原理：
    1. 使用 SAM (Segment Anything Model) 进行语义分割
    2. 使用 OCR 识别和定位文字
    3. 分离各图层并生成蒙版
    """
    try:
        import json
        import re
        from io import BytesIO
        from PIL import Image, ImageDraw

        # 解析图像（base64，无 data: 前缀）
        image_data = request.image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]

        image_bytes = base64.b64decode(image_data)
        with Image.open(BytesIO(image_bytes)) as im0:
            im = im0.convert("RGBA")
        width, height = im.size

        def _clamp(v: float, a: float, b: float) -> float:
            return max(a, min(b, v))

        def _bbox_to_pixels(bbox01: List[float]) -> tuple[int, int, int, int]:
            x, y, w, h = (bbox01 + [0, 0, 0, 0])[:4]
            x = _clamp(float(x), 0.0, 1.0)
            y = _clamp(float(y), 0.0, 1.0)
            w = _clamp(float(w), 0.0, 1.0)
            h = _clamp(float(h), 0.0, 1.0)
            left = int(round(width * x))
            top = int(round(height * y))
            right = int(round(width * (x + w)))
            bottom = int(round(height * (y + h)))
            right = max(left + 1, min(width, right))
            bottom = max(top + 1, min(height, bottom))
            left = max(0, min(width - 1, left))
            top = max(0, min(height - 1, top))
            return left, top, right, bottom

        def _png_base64(img: Image.Image) -> str:
            buf = BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")

        def _mask_from_bbox(bbox01: List[float]) -> str:
            mask = Image.new("L", (width, height), 0)
            d = ImageDraw.Draw(mask)
            l, t, r, b = _bbox_to_pixels(bbox01)
            d.rectangle([l, t, r, b], fill=255)
            return _png_base64(mask)

        def _crop_content(bbox01: List[float]) -> str:
            l, t, r, b = _bbox_to_pixels(bbox01)
            crop = im.crop((l, t, r, b))
            return _png_base64(crop)

        # 用视觉模型做“元素级拆分”（bbox 级 mask），不依赖 SAM/OCR
        llm = await get_design_llm(vision=True)

        analysis_prompt = """请识别图像中的可编辑元素，重点返回 text 元素（含 content）以及主体对象/背景（bbox 0-1）。
只返回 JSON：
{
  "elements": [
    {"id":"...", "type":"text|object|background|person|shape", "label":"...", "bbox":[x,y,w,h], "confidence":0-1, "content":"(text only)", "description":"..."}
  ]
}"""

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                {"type": "text", "text": analysis_prompt},
            ],
        }]

        response = await llm.achat(messages)
        result_text = response.content if hasattr(response, "content") else str(response)

        json_match = re.search(r"```json\\s*([\\s\\S]*?)\\s*```", result_text)
        if json_match:
            result_text = json_match.group(1)

        try:
            analysis_data = json.loads(result_text)
        except json.JSONDecodeError:
            analysis_data = {"elements": []}

        detected = analysis_data.get("elements", []) or []

        # 生成 text_regions（用于“可编辑 text layer”）
        text_regions: List[TextRegion] = []
        if request.extract_text:
            for el in detected:
                if not isinstance(el, dict):
                    continue
                if el.get("type") != "text":
                    continue
                bbox = el.get("bbox") or [0, 0, 1, 1]
                content = el.get("content") or el.get("label") or ""
                est_font = int(max(12, min(180, round(height * float((bbox + [0, 0, 0, 0])[3]) * 0.9))))
                text_regions.append(TextRegion(
                    id=str(el.get("id") or f"text-{len(text_regions)+1:03d}"),
                    text=str(content),
                    bbox=[float(x) for x in (bbox + [0, 0, 0, 0])[:4]],
                    font_size=est_font,
                    color=None,
                    confidence=float(el.get("confidence") or 0.7),
                ))

        # 生成 layers（mask_base64/content_base64/bbox 均为相对坐标）
        layers: List[ImageLayer] = []

        if request.extract_background:
            bg_mask = Image.new("L", (width, height), 255)
            layers.append(ImageLayer(
                id="background-001",
                type="background",
                mask_base64=_png_base64(bg_mask),
                content_base64=None,
                bbox=[0.0, 0.0, 1.0, 1.0],
                metadata={"description": "背景图层（bbox 级近似）"},
            ))

        for el in detected:
            if not isinstance(el, dict):
                continue
            t = el.get("type") or "object"
            bbox = el.get("bbox") or [0, 0, 1, 1]
            bbox01 = [float(x) for x in (bbox + [0, 0, 0, 0])[:4]]

            if t == "background":
                continue

            if t == "text" and not request.extract_text:
                continue

            if t != "text" and not request.extract_subjects:
                continue

            layer_type = "text" if t == "text" else ("subject" if t == "person" else "object")
            layer_id = str(el.get("id") or f"{layer_type}-{len(layers)+1:03d}")

            layers.append(ImageLayer(
                id=layer_id,
                type=layer_type,
                mask_base64=_mask_from_bbox(bbox01),
                content_base64=_crop_content(bbox01),
                bbox=bbox01,
                metadata={
                    "label": el.get("label"),
                    "confidence": el.get("confidence"),
                    "description": el.get("description"),
                },
            ))

        return ElementSplitResponse(layers=layers, text_regions=text_regions, original_width=width, original_height=height)
        
    except Exception as e:
        logger.error(f"元素拆分错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    分析图像元素
    
    使用 LLM 视觉能力分析图像，识别：
    - 文字元素及内容
    - 主体对象
    - 背景元素
    - 人物
    - 形状和图形
    
    返回每个元素的位置、类型和描述
    """
    try:
        import json
        import re
        
        # 图像分析需要使用视觉模型
        llm = await get_design_llm(vision=True)
        
        # 准备图像数据
        image_data = request.image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        analysis_prompt = """请仔细分析这张图像，识别出所有可编辑的元素。

对于每个元素，请提供：
1. 类型 (text/object/background/person/shape)
2. 标签 (简短的中文描述，如"标题文字"、"咖啡杯"、"木纹背景")
3. 边界框 (相对坐标，范围 0-1，格式 [x, y, width, height])
4. 置信度 (0-1)
5. 内容 (仅文字类型需要，识别出的文字)
6. 描述 (详细的中文描述)

请以 JSON 格式返回，示例：
```json
{
  "overall_description": "这是一张咖啡店宣传海报，包含标题文字、咖啡杯图像和木纹背景",
  "elements": [
    {
      "id": "text-001",
      "type": "text",
      "label": "标题文字",
      "bbox": [0.2, 0.1, 0.6, 0.15],
      "confidence": 0.95,
      "content": "COFFEE HOUSE",
      "description": "大标题文字，白色，粗体"
    },
    {
      "id": "object-001",
      "type": "object",
      "label": "咖啡杯",
      "bbox": [0.3, 0.3, 0.4, 0.5],
      "confidence": 0.92,
      "content": null,
      "description": "一杯拿铁咖啡，带有拉花艺术"
    }
  ],
  "suggested_edits": [
    "可以修改标题文字内容或颜色",
    "可以调整咖啡杯的位置或大小",
    "可以替换背景图案"
  ]
}
```

请只返回 JSON，不要添加其他内容。"""

        # 构建带图像的消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": analysis_prompt
                    }
                ]
            }
        ]
        
        # 调用支持视觉的 LLM
        response = await llm.achat(messages)
        result_text = response.content if hasattr(response, 'content') else str(response)
        
        # 解析 JSON 响应
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        json_match = re.search(json_pattern, result_text)
        
        if json_match:
            result_text = json_match.group(1)
        
        # 尝试直接解析
        try:
            analysis_data = json.loads(result_text)
        except json.JSONDecodeError:
            # 如果解析失败，返回模拟数据
            logger.warning("无法解析图像分析结果，返回默认数据")
            analysis_data = {
                "overall_description": "图像分析完成",
                "elements": [
                    {
                        "id": "background-001",
                        "type": "background",
                        "label": "背景",
                        "bbox": [0, 0, 1, 1],
                        "confidence": 0.9,
                        "content": None,
                        "description": "图像背景"
                    }
                ],
                "suggested_edits": ["可以尝试修改图像内容"]
            }
        
        # 构建响应
        elements = []
        for i, el in enumerate(analysis_data.get("elements", [])):
            elements.append(DetectedElement(
                id=el.get("id", f"element-{i:03d}"),
                type=el.get("type", "object"),
                label=el.get("label", "未知元素"),
                bbox=el.get("bbox", [0, 0, 1, 1]),
                confidence=el.get("confidence", 0.8),
                content=el.get("content"),
                description=el.get("description")
            ))
        
        return ImageAnalysisResponse(
            elements=elements,
            overall_description=analysis_data.get("overall_description", ""),
            suggested_edits=analysis_data.get("suggested_edits", [])
        )
        
    except Exception as e:
        logger.error(f"图像分析错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate-element", response_model=ElementRegenerateResponse)
async def regenerate_element(request: ElementRegenerateRequest):
    """
    重新生成图像中的特定元素
    
    工作流程：
    1. 根据边界框定位元素
    2. 使用 inpainting 或区域重绘
    3. 根据用户描述生成新内容
    4. 合成到原图
    """
    try:
        # 解析图像
        image_data = request.original_image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        client = GeminiImageClient()
        if not (client.api_key or "").strip():
            raise HTTPException(
                status_code=500,
                detail="design.image is not configured (missing ALLAPI_KEY).",
            )
        
        # 构建重新生成提示词
        regenerate_prompt = f"""Edit this image by modifying the element in the specified region.
        
Region (relative coordinates): x={request.element_bbox[0]:.2f}, y={request.element_bbox[1]:.2f}, width={request.element_bbox[2]:.2f}, height={request.element_bbox[3]:.2f}

Modification requested: {request.modification_prompt}

{"Maintain the original artistic style and color palette." if request.keep_style else "Feel free to change the style as needed."}

Create a seamless edit that blends naturally with the rest of the image."""

        # 选择最接近的宽高比，避免固定 1:1 导致输出变形
        aspect_ratio = "1:1"
        try:
            from PIL import Image
            from io import BytesIO

            with Image.open(BytesIO(base64.b64decode(image_data))) as im:
                w0, h0 = im.size
            r = (w0 / h0) if h0 else 1.0
            candidates = {
                "1:1": 1.0,
                "4:3": 4 / 3,
                "3:4": 3 / 4,
                "16:9": 16 / 9,
                "9:16": 9 / 16,
            }
            aspect_ratio = min(candidates.keys(), key=lambda k: abs(candidates[k] - r))
        except Exception:
            pass

        # 调用图像编辑（当前为 bbox 引导的参考图编辑；后续可替换为真正 inpainting）
        result = await client.generate_image(
            prompt=regenerate_prompt,
            ref_images=[base64.b64decode(image_data)],
            aspect_ratio=aspect_ratio
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"元素重新生成失败: {result.get('error', '未知错误')}"
            )
        
        width = 1024
        height = 1024
        try:
            from PIL import Image
            from io import BytesIO

            img_bytes = base64.b64decode(result["image_base64"])
            with Image.open(BytesIO(img_bytes)) as im:
                width, height = im.size
        except Exception:
            # 解码失败不阻断（保持兼容）
            pass

        return ElementRegenerateResponse(result_base64=result["image_base64"], width=width, height=height)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"元素重新生成错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit-text-in-image", response_model=TextEditResponse)
async def edit_text_in_image(request: TextEditRequest):
    """
    编辑图像中的文字
    
    工作流：
    1. OCR 识别原始文字位置和属性
    2. 使用 Inpainting 移除原始文字
    3. 在相同位置渲染新文字
    4. 合成最终图像
    
    这是 Lovart "编辑文字" 功能的核心实现
    """
    try:
        import json
        import re
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont

        # 解析图像
        image_data = request.image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        with Image.open(BytesIO(img_bytes)) as im0:
            im = im0.convert("RGBA")
        width, height = im.size

        # 先用视觉模型识别 text 元素（用 region_id 映射 bbox）
        llm = await get_design_llm(vision=True)
        analysis_prompt = """识别图像中的所有文字元素，返回 JSON：
{
  "elements":[
    {"id":"text-001","type":"text","bbox":[x,y,w,h],"content":"...","confidence":0-1}
  ]
}
只返回 JSON，不要其它内容。"""

        messages = [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                {"type": "text", "text": analysis_prompt},
            ],
        }]
        resp = await llm.achat(messages)
        result_text = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r"```json\\s*([\\s\\S]*?)\\s*```", result_text)
        if m:
            result_text = m.group(1)
        try:
            data = json.loads(result_text)
        except json.JSONDecodeError:
            data = {"elements": []}

        bbox_by_id: Dict[str, List[float]] = {}
        for el in data.get("elements", []) or []:
            if not isinstance(el, dict):
                continue
            if el.get("type") != "text":
                continue
            _id = str(el.get("id") or "")
            bbox = el.get("bbox") or None
            if _id and isinstance(bbox, list) and len(bbox) >= 4:
                bbox_by_id[_id] = [float(x) for x in bbox[:4]]

        def clamp(v: float, a: float, b: float) -> float:
            return max(a, min(b, v))

        def bbox_to_pixels(bbox01: List[float]) -> tuple[int, int, int, int]:
            x, y, w, h = (bbox01 + [0, 0, 0, 0])[:4]
            x = clamp(float(x), 0.0, 1.0)
            y = clamp(float(y), 0.0, 1.0)
            w = clamp(float(w), 0.0, 1.0)
            h = clamp(float(h), 0.0, 1.0)
            left = int(round(width * x))
            top = int(round(height * y))
            right = int(round(width * (x + w)))
            bottom = int(round(height * (y + h)))
            right = max(left + 1, min(width, right))
            bottom = max(top + 1, min(height, bottom))
            left = max(0, min(width - 1, left))
            top = max(0, min(height - 1, top))
            return left, top, right, bottom

        def parse_hex(color: str) -> tuple[int, int, int, int]:
            c = (color or "").strip()
            if c.startswith("#"):
                c = c[1:]
            if len(c) == 3:
                c = "".join([ch * 2 for ch in c])
            if len(c) != 6:
                return (255, 255, 255, 255)
            r = int(c[0:2], 16)
            g = int(c[2:4], 16)
            b = int(c[4:6], 16)
            return (r, g, b, 255)

        def estimate_fill(bbox_px: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
            l, t, r, b = bbox_px
            # 采样 bbox 外沿一圈（尽量贴近背景）
            pad = 2
            l2 = max(0, l - pad)
            t2 = max(0, t - pad)
            r2 = min(width - 1, r + pad)
            b2 = min(height - 1, b + pad)
            samples = []
            pix = im.load()
            for x in range(l2, r2):
                samples.append(pix[x, t2])
                samples.append(pix[x, b2])
            for y in range(t2, b2):
                samples.append(pix[l2, y])
                samples.append(pix[r2, y])
            if not samples:
                return (255, 255, 255, 255)
            sr = sum(p[0] for p in samples)
            sg = sum(p[1] for p in samples)
            sb = sum(p[2] for p in samples)
            n = len(samples)
            return (int(sr / n), int(sg / n), int(sb / n), 255)

        draw = ImageDraw.Draw(im)

        for edit in request.text_edits or []:
            if not isinstance(edit, dict):
                continue
            region_id = str(edit.get("region_id") or "")
            new_text = str(edit.get("new_text") or "")
            if not region_id or not new_text:
                continue

            bbox01 = edit.get("bbox") if isinstance(edit.get("bbox"), list) else bbox_by_id.get(region_id)
            if not bbox01 or not isinstance(bbox01, list) or len(bbox01) < 4:
                continue

            bbox01 = [float(x) for x in bbox01[:4]]
            l, t, r, b = bbox_to_pixels(bbox01)
            fill = estimate_fill((l, t, r, b))
            draw.rectangle([l, t, r, b], fill=fill)

            size = int(edit.get("font_size") or max(12, round((b - t) * 0.8)))
            size = max(10, min(200, size))
            color = parse_hex(str(edit.get("color") or "#ffffff"))
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size=size)
            except Exception:
                font = ImageFont.load_default()

            # 简单左上对齐 + padding
            pad = max(2, int(size * 0.15))
            draw.text((l + pad, t + pad), new_text, fill=color, font=font)

        # 输出 base64 PNG
        out = BytesIO()
        im.save(out, format="PNG")
        result_base64 = base64.b64encode(out.getvalue()).decode("utf-8")
        return TextEditResponse(result_base64=result_base64, width=width, height=height)
        
    except Exception as e:
        logger.error(f"文字编辑错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API 端点 - 项目管理
# ============================================

@router.post("/projects", response_model=ProjectResponse)
async def save_project(request: ProjectSaveRequest):
    """
    保存设计项目
    
    开源版：仅本地内存存储（不依赖 Supabase/云端）
    """
    try:
        now = datetime.now().isoformat()
        project_id = request.id or f"local_{uuid.uuid4().hex}"
        existing = _LOCAL_PROJECTS.get(project_id) or {}
        created_at = str(existing.get("created_at") or now)

        data: Dict[str, Any] = {
            "id": project_id,
            "name": request.name,
            "elements": request.elements,
            "thumbnail": request.thumbnail,
            "created_at": created_at,
            "updated_at": now,
        }
        _LOCAL_PROJECTS[project_id] = data
        return ProjectResponse(**data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存项目错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=List[ProjectResponse])
async def get_projects():
    """
    获取项目列表
    """
    try:
        items = sorted(
            _LOCAL_PROJECTS.values(),
            key=lambda p: str(p.get("updated_at") or ""),
            reverse=True,
        )
        return [ProjectResponse(**p) for p in items]
        
    except Exception as e:
        logger.error(f"获取项目列表错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """
    获取单个项目
    """
    try:
        data = _LOCAL_PROJECTS.get(project_id)
        if not data:
            raise HTTPException(status_code=404, detail="项目不存在")
        return ProjectResponse(**data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """
    删除项目
    """
    try:
        if project_id in _LOCAL_PROJECTS:
            _LOCAL_PROJECTS.pop(project_id, None)
        return {"deleted": True}
        
    except Exception as e:
        logger.error(f"删除项目错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# API 端点 - 视频生成（预留）
# ============================================

@router.post("/generate-video")
async def generate_video(
    prompt: str,
    duration: int = 5,
    model: str = "veo-3",
    reference_image: Optional[str] = None
):
    """
    生成 AI 视频（预留接口）
    
    支持的模型：Veo 3.1, Sora 2, Hailuo 2.3, Kling o1
    等待用户提供视频生成 API
    """
    model_config = VIDEO_MODELS.get(model)
    if model_config and model_config["available"]:
        # 未来实现
        pass
    
    raise HTTPException(
        status_code=501,
        detail="视频生成功能即将上线，请稍后再试"
    )


@router.post("/export")
async def export_canvas(
    elements: List[CanvasElement],
    format: str = "png"
):
    """
    导出画布为图片（预留接口）
    """
    raise HTTPException(
        status_code=501,
        detail="导出功能正在开发中"
    )
