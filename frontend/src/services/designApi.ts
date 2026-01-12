/**
 * Nexus AI Design API Service
 * 设计模块 API 调用服务
 */

import { CanvasElement } from '../stores/designStore'

const API_BASE = '/api/v1/design'

// 响应类型
interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
}

// 项目类型
export interface DesignProject {
  id: string
  name: string
  elements: CanvasElement[]
  thumbnail?: string
  created_at: string
  updated_at: string
}

// 模型信息类型
export interface ModelInfo {
  id: string
  name: string
  icon: string
  speed: string
  quality: string
  available: boolean
  description: string
}

// 模型列表响应
export interface ModelsResponse {
  image_models: ModelInfo[]
  video_models: ModelInfo[]
}

// 图像生成参数
export interface ImageGenerationParams {
  prompt: string
  resolution: '1K' | '2K' | '4K'
  aspect_ratio: '1:1' | '4:3' | '16:9' | '9:16' | '3:4'
  reference_image?: string
  model?: string  // 模型选择
}

// 图像生成结果
export interface ImageGenerationResult {
  image_base64: string
  width: number
  height: number
  model_used: string
}

// AI 对话消息
export interface ChatMessageParam {
  role: 'user' | 'assistant'
  content: string
}

// AI 操作
export interface DesignAction {
  type: 'generate_image' | 'edit_element' | 'suggestion' | 'none'
  data?: Record<string, unknown>
}

// AI 设计对话参数
export interface DesignChatParams {
  message: string
  conversation_history?: ChatMessageParam[]
  canvas_state?: string
  model?: string
  enable_web_search?: boolean
}

// AI 设计对话结果
export interface DesignChatResult {
  reply: string
  action?: DesignAction
  optimized_prompt?: string
  suggested_params?: Record<string, string>
}

// 图像分析参数
export interface ImageAnalysisParams {
  image_base64: string
  analysis_type?: 'full' | 'text_only' | 'objects_only'
}

// 检测到的元素
export interface DetectedElement {
  id: string
  type: 'text' | 'object' | 'background' | 'person' | 'shape'
  label: string
  bbox: [number, number, number, number]
  confidence: number
  content?: string
  description?: string
}

// 图像分析结果
export interface ImageAnalysisResult {
  elements: DetectedElement[]
  overall_description: string
  suggested_edits: string[]
}

// 元素重新生成参数
export interface ElementRegenerateParams {
  original_image_base64: string
  element_id: string
  element_bbox: number[]
  modification_prompt: string
  keep_style?: boolean
}

// 元素重新生成结果
export interface ElementRegenerateResult {
  result_base64: string
  width: number
  height: number
}

// 元素拆分参数
export interface ElementSplitParams {
  image_base64: string
  extract_text?: boolean
  extract_subjects?: boolean
  extract_background?: boolean
}

// 文字区域
export interface TextRegion {
  id: string
  text: string
  bbox: number[]
  font_size?: number
  color?: string
  confidence: number
}

// 图层
export interface ImageLayer {
  id: string
  type: string
  mask_base64: string
  content_base64?: string
  bbox?: number[]
  metadata?: Record<string, unknown>
}

// 元素拆分结果
export interface ElementSplitResult {
  layers: ImageLayer[]
  text_regions: TextRegion[]
  original_width: number
  original_height: number
}

// 文字编辑参数
export interface TextEditParams {
  image_base64: string
  text_edits: Array<{
    region_id: string
    new_text: string
    font_size?: number
    color?: string
  }>
}

// 文字编辑结果
export interface TextEditResult {
  result_base64: string
  width: number
  height: number
}

/**
 * 通用 API 请求函数
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return {
        success: false,
        error: errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      }
    }

    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : '网络请求失败'
    }
  }
}

/**
 * 获取可用模型列表
 */
export async function getModels(): Promise<ApiResponse<ModelsResponse>> {
  return apiRequest<ModelsResponse>('/models')
}

/**
 * 生成图像
 */
export async function generateImage(
  params: ImageGenerationParams
): Promise<ApiResponse<ImageGenerationResult>> {
  return apiRequest<ImageGenerationResult>('/generate-image', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * AI 设计对话
 * 
 * 支持结构化响应，包含自动操作和优化后的提示词
 */
export async function designChat(
  params: DesignChatParams
): Promise<ApiResponse<DesignChatResult>> {
  return apiRequest<DesignChatResult>('/chat', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 分析图像元素
 * 
 * 使用 AI 视觉能力识别图像中的可编辑元素
 */
export async function analyzeImage(
  params: ImageAnalysisParams
): Promise<ApiResponse<ImageAnalysisResult>> {
  return apiRequest<ImageAnalysisResult>('/analyze-image', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 重新生成图像中的特定元素
 * 
 * 根据用户描述修改图像中的指定区域
 */
export async function regenerateElement(
  params: ElementRegenerateParams
): Promise<ApiResponse<ElementRegenerateResult>> {
  return apiRequest<ElementRegenerateResult>('/regenerate-element', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 元素拆分
 */
export async function splitElements(
  params: ElementSplitParams
): Promise<ApiResponse<ElementSplitResult>> {
  return apiRequest<ElementSplitResult>('/split-elements', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 编辑图像中的文字
 */
export async function editTextInImage(
  params: TextEditParams
): Promise<ApiResponse<TextEditResult>> {
  return apiRequest<TextEditResult>('/edit-text-in-image', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 保存项目
 */
export async function saveProject(
  project: {
    id?: string
    name: string
    elements: CanvasElement[]
    thumbnail?: string
  }
): Promise<ApiResponse<DesignProject>> {
  return apiRequest<DesignProject>('/projects', {
    method: project.id ? 'PUT' : 'POST',
    body: JSON.stringify(project)
  })
}

/**
 * 获取项目列表
 */
export async function getProjects(): Promise<ApiResponse<DesignProject[]>> {
  return apiRequest<DesignProject[]>('/projects')
}

/**
 * 获取单个项目
 */
export async function getProject(
  projectId: string
): Promise<ApiResponse<DesignProject>> {
  return apiRequest<DesignProject>(`/projects/${projectId}`)
}

/**
 * 删除项目
 */
export async function deleteProject(
  projectId: string
): Promise<ApiResponse<{ deleted: boolean }>> {
  return apiRequest<{ deleted: boolean }>(`/projects/${projectId}`, {
    method: 'DELETE'
  })
}

/**
 * 生成视频 (预留接口)
 */
export async function generateVideo(
  params: {
    prompt: string
    duration?: number
    model?: string
    reference_image?: string
  }
): Promise<ApiResponse<{ video_url: string }>> {
  return apiRequest<{ video_url: string }>('/generate-video', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

/**
 * 导出画布为图片
 */
export async function exportCanvas(
  elements: CanvasElement[],
  format: 'png' | 'jpeg' | 'svg' = 'png'
): Promise<ApiResponse<{ image_base64: string }>> {
  return apiRequest<{ image_base64: string }>('/export', {
    method: 'POST',
    body: JSON.stringify({ elements, format })
  })
}
