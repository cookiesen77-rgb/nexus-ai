/**
 * Nexus PPT Store
 * 基于 banana-slides 的 useProjectStore 适配
 * 管理 PPT 项目状态
 */
import { create } from 'zustand'

// PPT 页面类型
export interface PPTPage {
  id: string
  order_index: number
  title?: string
  part?: string
  status?: string
  outline_content?: {
    title: string
    points: string[]
  }
  description_content?: {
    text: string
    generated_at?: string
  }
  generated_image_path?: string
  updated_at?: string
}

// PPT 项目类型
export interface PPTProject {
  id: string
  title?: string
  idea_prompt?: string
  outline_text?: string
  description_text?: string
  template_style?: string
  status?: string
  pages: PPTPage[]
  created_at?: string
  updated_at?: string
}

// 任务进度类型
export interface TaskProgress {
  total: number
  completed: number
  failed?: number
  current_step?: string
  percent?: number
  messages?: string[]
  download_url?: string
}

// API 基础 URL
const API_BASE = '/api/banana'

// API 请求辅助函数
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: response.statusText } }))
    throw new Error(error.error?.message || error.message || '请求失败')
  }
  
  return response.json()
}

// Store 接口
interface PPTStoreState {
  // 状态
  currentProject: PPTProject | null
  isLoading: boolean
  activeTaskId: string | null
  taskProgress: TaskProgress | null
  error: string | null
  pageGeneratingTasks: Record<string, string>
  pageDescriptionGeneratingTasks: Record<string, boolean>
  
  // Actions
  setCurrentProject: (project: PPTProject | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
  
  // 项目操作
  createProject: (type: 'idea' | 'outline' | 'description', content: string, templateStyle?: string) => Promise<string>
  loadProject: (projectId: string) => Promise<void>
  listProjects: () => Promise<PPTProject[]>
  deleteProject: (projectId: string) => Promise<void>
  
  // 大纲操作
  generateOutline: () => Promise<void>
  updateOutline: (outline: any[]) => Promise<void>
  refineOutline: (requirement: string) => Promise<void>
  
  // 描述操作
  generateDescriptions: () => Promise<void>
  generatePageDescription: (pageId: string) => Promise<void>
  refineDescriptions: (requirement: string) => Promise<void>
  
  // 图片操作
  generateImages: (pageIds?: string[]) => Promise<void>
  generatePageImage: (pageId: string) => Promise<void>
  editPageImage: (pageId: string, editPrompt: string) => Promise<void>
  
  // 导出操作
  exportPPTX: (pageIds?: string[]) => Promise<string>
  exportPDF: (pageIds?: string[]) => Promise<string>
  exportEditablePPTX: (filename?: string, pageIds?: string[]) => Promise<void>
  
  // 任务轮询
  pollTask: (taskId: string) => Promise<void>
  
  // 健康检查
  checkHealth: () => Promise<boolean>
}

export const usePPTStore = create<PPTStoreState>((set, get) => ({
  // 初始状态
  currentProject: null,
  isLoading: false,
  activeTaskId: null,
  taskProgress: null,
  error: null,
  pageGeneratingTasks: {},
  pageDescriptionGeneratingTasks: {},
  
  // Setters
  setCurrentProject: (project) => set({ currentProject: project }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
  
  // 健康检查
  checkHealth: async () => {
    try {
      const response = await apiRequest<{ status: string }>('/health')
      return response.status === 'ok'
    } catch {
      return false
    }
  },
  
  // 创建项目
  createProject: async (type, content, templateStyle) => {
    set({ isLoading: true, error: null })
    
    try {
      // banana-slides API 需要 creation_type 字段
      // 将 'description' 映射为 'descriptions'（banana-slides 使用复数形式）
      const creationType = type === 'description' ? 'descriptions' : type
      
      const request: Record<string, string> = {
        creation_type: creationType,  // 必需字段
      }
      
      if (type === 'idea') {
        request.idea_prompt = content
      } else if (type === 'outline') {
        request.outline_text = content
      } else if (type === 'description') {
        request.description_text = content
      }
      
      if (templateStyle?.trim()) {
        request.template_style = templateStyle.trim()
      }
      
      const response = await apiRequest<{ data: { project_id: string } }>('/projects', {
        method: 'POST',
        body: JSON.stringify(request),
      })
      
      const projectId = response.data?.project_id
      if (!projectId) {
        throw new Error('项目创建失败：未返回项目ID')
      }
      
      // 加载完整项目信息
      await get().loadProject(projectId)
      
      return projectId
    } catch (error: any) {
      set({ error: error.message || '创建项目失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 加载项目
  loadProject: async (projectId) => {
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: PPTProject }>(`/projects/${projectId}`)
      
      if (response.data) {
        set({ currentProject: response.data })
      }
    } catch (error: any) {
      set({ error: error.message || '加载项目失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 获取项目列表
  listProjects: async () => {
    try {
      const response = await apiRequest<{ data: { projects: PPTProject[] } }>('/projects')
      return response.data?.projects || []
    } catch (error: any) {
      set({ error: error.message || '获取项目列表失败' })
      return []
    }
  },
  
  // 删除项目
  deleteProject: async (projectId) => {
    try {
      await apiRequest(`/projects/${projectId}`, { method: 'DELETE' })
      
      // 如果删除的是当前项目，清空状态
      const { currentProject } = get()
      if (currentProject?.id === projectId) {
        set({ currentProject: null })
      }
    } catch (error: any) {
      set({ error: error.message || '删除项目失败' })
      throw error
    }
  },
  
  // 生成大纲
  generateOutline: async () => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      await apiRequest(`/projects/${currentProject.id}/outline/generate`, {
        method: 'POST',
      })
      
      // 刷新项目
      await get().loadProject(currentProject.id)
    } catch (error: any) {
      set({ error: error.message || '生成大纲失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 更新大纲
  updateOutline: async (outline) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    try {
      await apiRequest(`/projects/${currentProject.id}/outline`, {
        method: 'PUT',
        body: JSON.stringify({ outline }),
      })
      
      await get().loadProject(currentProject.id)
    } catch (error: any) {
      set({ error: error.message || '更新大纲失败' })
      throw error
    }
  },
  
  // AI 优化大纲
  refineOutline: async (requirement) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      await apiRequest(`/projects/${currentProject.id}/outline/refine`, {
        method: 'POST',
        body: JSON.stringify({ requirement }),
      })
      
      await get().loadProject(currentProject.id)
    } catch (error: any) {
      set({ error: error.message || '优化大纲失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 生成所有描述
  generateDescriptions: async () => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: { task_id: string } }>(
        `/projects/${currentProject.id}/descriptions/generate`,
        { method: 'POST' }
      )
      
      const taskId = response.data?.task_id
      if (taskId) {
        set({ activeTaskId: taskId })
        await get().pollTask(taskId)
      } else {
        await get().loadProject(currentProject.id)
      }
    } catch (error: any) {
      set({ error: error.message || '生成描述失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 生成单页描述
  generatePageDescription: async (pageId) => {
    const { currentProject, pageDescriptionGeneratingTasks } = get()
    if (!currentProject || pageDescriptionGeneratingTasks[pageId]) return
    
    set({
      pageDescriptionGeneratingTasks: { ...pageDescriptionGeneratingTasks, [pageId]: true },
    })
    
    try {
      await apiRequest(
        `/projects/${currentProject.id}/pages/${pageId}/description/generate`,
        { method: 'POST' }
      )
      
      await get().loadProject(currentProject.id)
    } catch (error: any) {
      set({ error: error.message || '生成描述失败' })
    } finally {
      const { pageDescriptionGeneratingTasks: tasks } = get()
      const newTasks = { ...tasks }
      delete newTasks[pageId]
      set({ pageDescriptionGeneratingTasks: newTasks })
    }
  },
  
  // AI 优化描述
  refineDescriptions: async (requirement) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      await apiRequest(`/projects/${currentProject.id}/descriptions/refine`, {
        method: 'POST',
        body: JSON.stringify({ requirement }),
      })
      
      await get().loadProject(currentProject.id)
    } catch (error: any) {
      set({ error: error.message || '优化描述失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 生成所有图片
  generateImages: async (pageIds) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: { task_id: string } }>(
        `/projects/${currentProject.id}/images/generate`,
        {
          method: 'POST',
          body: JSON.stringify({ page_ids: pageIds }),
        }
      )
      
      const taskId = response.data?.task_id
      if (taskId) {
        set({ activeTaskId: taskId })
        await get().pollTask(taskId)
      } else {
        await get().loadProject(currentProject.id)
      }
    } catch (error: any) {
      set({ error: error.message || '生成图片失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 生成单页图片
  generatePageImage: async (pageId) => {
    const { currentProject, pageGeneratingTasks } = get()
    if (!currentProject || pageGeneratingTasks[pageId]) return
    
    try {
      const response = await apiRequest<{ data: { task_id: string } }>(
        `/projects/${currentProject.id}/pages/${pageId}/image/generate`,
        { method: 'POST' }
      )
      
      const taskId = response.data?.task_id
      if (taskId) {
        set({
          pageGeneratingTasks: { ...pageGeneratingTasks, [pageId]: taskId },
        })
        
        // 开始轮询
        const poll = async () => {
          try {
            const taskResponse = await apiRequest<{ data: any }>(
              `/tasks/${taskId}`
            )
            const task = taskResponse.data
            
            if (task?.status === 'COMPLETED') {
              const { pageGeneratingTasks: tasks } = get()
              const newTasks = { ...tasks }
              delete newTasks[pageId]
              set({ pageGeneratingTasks: newTasks })
              await get().loadProject(currentProject.id)
            } else if (task?.status === 'FAILED') {
              const { pageGeneratingTasks: tasks } = get()
              const newTasks = { ...tasks }
              delete newTasks[pageId]
              set({
                pageGeneratingTasks: newTasks,
                error: task.error_message || '生成图片失败',
              })
            } else {
              setTimeout(poll, 2000)
            }
          } catch (error) {
            const { pageGeneratingTasks: tasks } = get()
            const newTasks = { ...tasks }
            delete newTasks[pageId]
            set({ pageGeneratingTasks: newTasks })
          }
        }
        
        poll()
      }
    } catch (error: any) {
      set({ error: error.message || '生成图片失败' })
    }
  },
  
  // 编辑图片
  editPageImage: async (pageId, editPrompt) => {
    const { currentProject, pageGeneratingTasks } = get()
    if (!currentProject || pageGeneratingTasks[pageId]) return
    
    try {
      const response = await apiRequest<{ data: { task_id: string } }>(
        `/projects/${currentProject.id}/pages/${pageId}/image/edit`,
        {
          method: 'POST',
          body: JSON.stringify({ edit_instruction: editPrompt }),
        }
      )
      
      const taskId = response.data?.task_id
      if (taskId) {
        set({
          pageGeneratingTasks: { ...pageGeneratingTasks, [pageId]: taskId },
        })
        
        // 开始轮询
        const poll = async () => {
          try {
            const taskResponse = await apiRequest<{ data: any }>(
              `/tasks/${taskId}`
            )
            const task = taskResponse.data
            
            if (task?.status === 'COMPLETED') {
              const { pageGeneratingTasks: tasks } = get()
              const newTasks = { ...tasks }
              delete newTasks[pageId]
              set({ pageGeneratingTasks: newTasks })
              await get().loadProject(currentProject.id)
            } else if (task?.status === 'FAILED') {
              const { pageGeneratingTasks: tasks } = get()
              const newTasks = { ...tasks }
              delete newTasks[pageId]
              set({
                pageGeneratingTasks: newTasks,
                error: task.error_message || '编辑图片失败',
              })
            } else {
              setTimeout(poll, 2000)
            }
          } catch (error) {
            const { pageGeneratingTasks: tasks } = get()
            const newTasks = { ...tasks }
            delete newTasks[pageId]
            set({ pageGeneratingTasks: newTasks })
          }
        }
        
        poll()
      }
    } catch (error: any) {
      set({ error: error.message || '编辑图片失败' })
    }
  },
  
  // 导出 PPTX
  exportPPTX: async (pageIds) => {
    const { currentProject } = get()
    if (!currentProject) throw new Error('没有当前项目')
    
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: { download_url: string } }>(
        `/projects/${currentProject.id}/export/pptx`,
        {
          method: 'POST',
          body: JSON.stringify({ page_ids: pageIds }),
        }
      )
      
      const downloadUrl = response.data?.download_url
      if (!downloadUrl) {
        throw new Error('导出链接获取失败')
      }
      
      // 打开下载链接
      window.open(downloadUrl, '_blank')
      return downloadUrl
    } catch (error: any) {
      set({ error: error.message || '导出失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 导出 PDF
  exportPDF: async (pageIds) => {
    const { currentProject } = get()
    if (!currentProject) throw new Error('没有当前项目')
    
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: { download_url: string } }>(
        `/projects/${currentProject.id}/export/pdf`,
        {
          method: 'POST',
          body: JSON.stringify({ page_ids: pageIds }),
        }
      )
      
      const downloadUrl = response.data?.download_url
      if (!downloadUrl) {
        throw new Error('导出链接获取失败')
      }
      
      window.open(downloadUrl, '_blank')
      return downloadUrl
    } catch (error: any) {
      set({ error: error.message || '导出失败' })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 导出可编辑 PPTX
  exportEditablePPTX: async (filename, pageIds) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    set({ isLoading: true, error: null })
    
    try {
      const response = await apiRequest<{ data: { task_id: string } }>(
        `/projects/${currentProject.id}/export/editable-pptx`,
        {
          method: 'POST',
          body: JSON.stringify({ filename, page_ids: pageIds }),
        }
      )
      
      const taskId = response.data?.task_id
      if (taskId) {
        set({ activeTaskId: taskId })
        await get().pollTask(taskId)
      }
    } catch (error: any) {
      set({ error: error.message || '导出可编辑PPTX失败' })
    } finally {
      set({ isLoading: false })
    }
  },
  
  // 任务轮询
  pollTask: async (taskId) => {
    const { currentProject } = get()
    if (!currentProject) return
    
    const poll = async () => {
      try {
        const response = await apiRequest<{ data: any }>(`/tasks/${taskId}`)
        const task = response.data
        
        if (!task) return
        
        // 更新进度
        if (task.progress) {
          set({ taskProgress: task.progress })
        }
        
        if (task.status === 'COMPLETED') {
          set({
            activeTaskId: null,
            taskProgress: null,
            isLoading: false,
          })
          
          // 如果有下载链接（导出任务）
          const progress = typeof task.progress === 'string' 
            ? JSON.parse(task.progress) 
            : task.progress
          if (progress?.download_url) {
            window.open(progress.download_url, '_blank')
          }
          
          // 刷新项目
          await get().loadProject(currentProject.id)
        } else if (task.status === 'FAILED') {
          set({
            activeTaskId: null,
            taskProgress: null,
            isLoading: false,
            error: task.error_message || task.error || '任务失败',
          })
        } else if (task.status === 'PENDING' || task.status === 'PROCESSING') {
          setTimeout(poll, 2000)
        }
      } catch (error: any) {
        set({
          activeTaskId: null,
          taskProgress: null,
          isLoading: false,
          error: error.message || '任务查询失败',
        })
      }
    }
    
    await poll()
  },
}))

// ============ 兼容旧版 API ============

// 旧版 PPT 数据（兼容旧 UI）
interface LegacyPresentation {
  id: string
  title: string
  template: string
  slides: any[]
  createdAt: string
}

interface LegacyPPTState {
  isWizardOpen: boolean
  currentPresentation: LegacyPresentation | null
  isGenerating: boolean
  generationProgress: number
  generationMessage: string
  templates: string[]
  setIsWizardOpen: (open: boolean) => void
  setCurrentPresentation: (presentation: LegacyPresentation | null) => void
  clearCurrentPresentation: () => void
  setGenerationProgress: (progress: number, message: string) => void
  setTemplates: (templates: string[]) => void
}

// 旧版 PPT Store（兼容旧 UI）
import { create as createLegacy } from 'zustand'

export const useLegacyPPTStore = createLegacy<LegacyPPTState>((set) => ({
  isWizardOpen: false,
  currentPresentation: null,
  isGenerating: false,
  generationProgress: 0,
  generationMessage: '',
  templates: [],
  
  setIsWizardOpen: (open) => set({ isWizardOpen: open }),
  setCurrentPresentation: (presentation) => set({ 
    currentPresentation: presentation,
    isGenerating: false,
    generationProgress: 100,
    generationMessage: '生成完成',
  }),
  clearCurrentPresentation: () => set({ 
    currentPresentation: null,
    generationProgress: 0,
    generationMessage: '',
  }),
  setGenerationProgress: (progress, message) => set({ 
    generationProgress: progress, 
    generationMessage: message,
    isGenerating: progress < 100,
  }),
  setTemplates: (templates) => set({ templates }),
}))

/**
 * 处理来自 WebSocket 的 PPT 消息（兼容旧版）
 */
export const handlePPTMessage = (data: any) => {
  const store = useLegacyPPTStore.getState()
  
  switch (data.type) {
    case 'ppt_progress':
      store.setGenerationProgress(data.progress || 0, data.message || '处理中...')
      break
      
    case 'ppt_complete':
      if (data.presentation) {
        store.setCurrentPresentation(data.presentation)
      }
      break
      
    case 'ppt_error':
      console.error('[PPT] Error:', data.error)
      store.setGenerationProgress(0, '')
      break
      
    case 'ppt_templates':
      if (data.templates) {
        store.setTemplates(data.templates)
      }
      break
      
    case 'ppt_slide_updated':
    case 'ppt_exported':
      // 这些消息可以忽略或记录
      console.log('[PPT] Message:', data.type, data)
      break
      
    default:
      console.warn('[PPT] Unknown message type:', data.type)
  }
}

// 为了兼容旧的导入，重新导出 usePPTStore
// MainContent.tsx 使用的是旧版 API
export { useLegacyPPTStore as usePPTStoreLegacy }
