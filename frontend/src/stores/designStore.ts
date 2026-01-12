/**
 * Nexus AI Design Store
 * 设计模块状态管理 (Zustand)
 */

import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'

// 画布元素类型定义
export type CanvasElementType = 'image' | 'text' | 'shape' | 'path' | 'image-generator' | 'video-generator' | 'video' | 'connector'

export interface CanvasElement {
  id: string
  type: CanvasElementType
  x: number
  y: number
  name?: string
  content?: string
  width?: number
  height?: number
  hidden?: boolean
  locked?: boolean
  color?: string
  shapeType?: 'square' | 'circle' | 'triangle' | 'star' | 'message' | 'arrow-left' | 'arrow-right'
  fontSize?: number
  fontFamily?: string
  points?: { x: number; y: number }[]
  strokeWidth?: number
  referenceImageId?: string
  groupId?: string
  linkedElements?: string[]
  connectorFrom?: string
  connectorTo?: string
  connectorStyle?: 'solid' | 'dashed'
}

// 项目接口
export interface DesignProject {
  id: string
  name: string
  thumbnail?: string
  createdAt: Date
  updatedAt: Date
}

// AI 对话消息
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  action?: {
    type: string
    data?: Record<string, unknown>
  }
  optimizedPrompt?: string
  imageBase64?: string  // 消息附带的图像
}

export interface ChatSession {
  id: string
  title: string
  createdAt: number
  messages: ChatMessage[]
  elementsSnapshot: CanvasElement[]
}

// 检测到的元素
export interface AnalyzedElement {
  id: string
  type: 'text' | 'object' | 'background' | 'person' | 'shape'
  label: string
  bbox: [number, number, number, number]  // [x, y, width, height] 0-1
  confidence: number
  content?: string
  description?: string
}

// Store 状态接口
interface DesignState {
  // 画布状态
  elements: CanvasElement[]
  selectedIds: string[]
  scale: number
  pan: { x: number; y: number }
  activeTool: string
  
  // 项目状态
  currentProjectId: string | null
  projectName: string
  isDirty: boolean
  
  // UI 状态
  isImageGeneratorOpen: boolean
  imageGeneratorElementId: string | null
  isVideoGeneratorOpen: boolean
  videoGeneratorElementId: string | null
  isAiDesignerOpen: boolean
  isGeneratingImage: boolean
  isGeneratingVideo: boolean
  
  // AI 对话状态
  conversationHistory: ChatMessage[]
  isAiThinking: boolean
  chatSessions: ChatSession[]
  
  // 元素分析状态
  analyzedElements: AnalyzedElement[]
  selectedAnalyzedElementId: string | null
  isAnalyzing: boolean
  analyzedImageBase64: string | null
  
  // 操作方法
  setElements: (elements: CanvasElement[]) => void
  addElement: (element: CanvasElement) => void
  updateElement: (id: string, updates: Partial<CanvasElement>) => void
  deleteElement: (id: string) => void
  
  setSelectedIds: (ids: string[]) => void
  setScale: (scale: number) => void
  setPan: (pan: { x: number; y: number }) => void
  setActiveTool: (tool: string) => void
  
  setCurrentProjectId: (id: string | null) => void
  setProjectName: (name: string) => void
  setIsDirty: (isDirty: boolean) => void
  
  openImageGenerator: (elementId?: string) => void
  closeImageGenerator: () => void
  openVideoGenerator: (elementId?: string) => void
  closeVideoGenerator: () => void
  toggleAiDesigner: () => void
  
  setIsGeneratingImage: (isGenerating: boolean) => void
  setIsGeneratingVideo: (isGenerating: boolean) => void
  
  // AI 对话方法
  addMessage: (role: 'user' | 'assistant', content: string, action?: ChatMessage['action'], optimizedPrompt?: string, imageBase64?: string) => void
  clearConversation: () => void
  setIsAiThinking: (value: boolean) => void
  startNewChat: () => void
  loadChatSession: (sessionId: string) => void
  deleteChatSession: (sessionId: string) => void
  
  // 元素分析方法
  setAnalyzedElements: (elements: AnalyzedElement[]) => void
  selectAnalyzedElement: (id: string | null) => void
  setIsAnalyzing: (value: boolean) => void
  setAnalyzedImageBase64: (base64: string | null) => void
  clearAnalysis: () => void
  
  // 工具方法
  addImageElement: (file: File, x?: number, y?: number) => void
  addVideoElement: (file: File, x?: number, y?: number) => void
  addTextElement: (x?: number, y?: number) => void
  addShapeElement: (shapeType: CanvasElement['shapeType'], x?: number, y?: number) => void
  addImageGeneratorElement: (x?: number, y?: number, referenceImageId?: string) => void
  addVideoGeneratorElement: (x?: number, y?: number, referenceImageId?: string) => void
  createFlowConnection: (sourceElement: CanvasElement, options?: { generatorName?: string }) => string | null
  toggleElementHidden: (id: string) => void
  toggleElementLocked: (id: string) => void
  
  // 项目方法
  resetCanvas: () => void
  loadProject: (project: { elements: CanvasElement[]; name: string; id: string }) => void
}

const DEFAULT_CENTER_X = 400
const DEFAULT_CENTER_Y = 300

export const useDesignStore = create<DesignState>((set) => ({
  // 初始状态
  elements: [],
  selectedIds: [],
  scale: 1,
  pan: { x: 0, y: 0 },
  activeTool: 'select',
  
  currentProjectId: null,
  projectName: '未命名项目',
  isDirty: false,
  
  isImageGeneratorOpen: false,
  imageGeneratorElementId: null,
  isVideoGeneratorOpen: false,
  videoGeneratorElementId: null,
  isAiDesignerOpen: false,
  isGeneratingImage: false,
  isGeneratingVideo: false,
  
  // AI 对话状态
  conversationHistory: [],
  isAiThinking: false,
  chatSessions: [],
  
  // 元素分析状态
  analyzedElements: [],
  selectedAnalyzedElementId: null,
  isAnalyzing: false,
  analyzedImageBase64: null,
  
  // 画布操作
  setElements: (elements) => set({ elements, isDirty: true }),
  
  addElement: (element) => set((state) => ({
    elements: [...state.elements, element],
    isDirty: true
  })),
  
  updateElement: (id, updates) => set((state) => ({
    elements: state.elements.map((el) =>
      el.id === id ? { ...el, ...updates } : el
    ),
    isDirty: true
  })),
  
  deleteElement: (id) => set((state) => ({
    elements: state.elements.filter((el) => el.id !== id),
    selectedIds: state.selectedIds.filter((selectedId) => selectedId !== id),
    isDirty: true
  })),
  
  setSelectedIds: (ids) => set({ selectedIds: ids }),
  setScale: (scale) => set({ scale: Math.max(0.1, Math.min(3, scale)) }),
  setPan: (pan) => set({ pan }),
  setActiveTool: (tool) => set({ activeTool: tool }),
  
  setCurrentProjectId: (id) => set({ currentProjectId: id }),
  setProjectName: (name) => set({ projectName: name, isDirty: true }),
  setIsDirty: (isDirty) => set({ isDirty }),
  
  // UI 控制
  openImageGenerator: (elementId) => set({
    isImageGeneratorOpen: true,
    imageGeneratorElementId: elementId || null
  }),
  closeImageGenerator: () => set({
    isImageGeneratorOpen: false,
    imageGeneratorElementId: null
  }),
  
  openVideoGenerator: (elementId) => set({
    isVideoGeneratorOpen: true,
    videoGeneratorElementId: elementId || null
  }),
  closeVideoGenerator: () => set({
    isVideoGeneratorOpen: false,
    videoGeneratorElementId: null
  }),
  
  toggleAiDesigner: () => set((state) => ({
    isAiDesignerOpen: !state.isAiDesignerOpen
  })),
  
  setIsGeneratingImage: (isGenerating) => set({ isGeneratingImage: isGenerating }),
  setIsGeneratingVideo: (isGenerating) => set({ isGeneratingVideo: isGenerating }),
  
  // AI 对话方法
  addMessage: (role, content, action, optimizedPrompt, imageBase64) => set((state) => ({
    conversationHistory: [
      ...state.conversationHistory,
      {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        role,
        content,
        timestamp: Date.now(),
        action,
        optimizedPrompt,
        imageBase64
      }
    ]
  })),
  
  clearConversation: () => set({
    conversationHistory: []
  }),
  
  setIsAiThinking: (value) => set({ isAiThinking: value }),

  startNewChat: () => set((state) => {
    const hasAnything = state.conversationHistory.length > 0 || state.elements.length > 0
    const titleSource = state.conversationHistory.find(m => m.role === 'user')?.content || '新对话'
    const title = titleSource.length > 18 ? `${titleSource.slice(0, 18)}…` : titleSource

    const newSessions = hasAnything
      ? [
          {
            id: `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            title,
            createdAt: Date.now(),
            messages: state.conversationHistory,
            elementsSnapshot: state.elements
          },
          ...state.chatSessions
        ]
      : state.chatSessions

    return {
      chatSessions: newSessions,
      // 清空画布 + 新对话
      elements: [],
      selectedIds: [],
      scale: 1,
      pan: { x: 0, y: 0 },
      activeTool: 'select',
      isDirty: false,
      conversationHistory: [],
      isAiThinking: false,
      analyzedElements: [],
      selectedAnalyzedElementId: null,
      isAnalyzing: false,
      analyzedImageBase64: null,
      isImageGeneratorOpen: false,
      imageGeneratorElementId: null,
      isVideoGeneratorOpen: false,
      videoGeneratorElementId: null
    }
  }),

  loadChatSession: (sessionId) => set((state) => {
    const session = state.chatSessions.find(s => s.id === sessionId)
    if (!session) return {}
    return {
      elements: session.elementsSnapshot,
      selectedIds: [],
      scale: 1,
      pan: { x: 0, y: 0 },
      activeTool: 'select',
      projectName: state.projectName,
      conversationHistory: session.messages,
      isAiThinking: false,
      analyzedElements: [],
      selectedAnalyzedElementId: null,
      isAnalyzing: false,
      analyzedImageBase64: null
    }
  }),

  deleteChatSession: (sessionId) => set((state) => ({
    chatSessions: state.chatSessions.filter(s => s.id !== sessionId)
  })),
  
  // 元素分析方法
  setAnalyzedElements: (elements) => set({ analyzedElements: elements }),
  
  selectAnalyzedElement: (id) => set({ selectedAnalyzedElementId: id }),
  
  setIsAnalyzing: (value) => set({ isAnalyzing: value }),
  
  setAnalyzedImageBase64: (base64) => set({ analyzedImageBase64: base64 }),
  
  clearAnalysis: () => set({
    analyzedElements: [],
    selectedAnalyzedElementId: null,
    analyzedImageBase64: null
  }),
  
  // 工具方法：添加图片元素
  addImageElement: (file, x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        const maxSize = 400
        let width = img.width
        let height = img.height
        
        if (width > maxSize || height > maxSize) {
          if (width > height) {
            height = (height / width) * maxSize
            width = maxSize
          } else {
            width = (width / height) * maxSize
            height = maxSize
          }
        }
        
        const element: CanvasElement = {
          id: uuidv4(),
          type: 'image',
          x: x - width / 2,
          y: y - height / 2,
          width,
          height,
          name: file.name || 'Image',
          content: e.target?.result as string
        }
        
        set((state) => ({
          elements: [...state.elements, element],
          selectedIds: [element.id],
          activeTool: 'select',
          isDirty: true
        }))
      }
      img.src = e.target?.result as string
    }
    reader.readAsDataURL(file)
  },
  
  // 工具方法：添加视频元素
  addVideoElement: (file, x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const video = document.createElement('video')
      video.onloadedmetadata = () => {
        const maxSize = 400
        let width = video.videoWidth
        let height = video.videoHeight
        
        if (width > maxSize || height > maxSize) {
          if (width > height) {
            height = (height / width) * maxSize
            width = maxSize
          } else {
            width = (width / height) * maxSize
            height = maxSize
          }
        }
        
        const element: CanvasElement = {
          id: uuidv4(),
          type: 'video',
          x: x - width / 2,
          y: y - height / 2,
          width,
          height,
          name: file.name || 'Video',
          content: e.target?.result as string
        }
        
        set((state) => ({
          elements: [...state.elements, element],
          selectedIds: [element.id],
          activeTool: 'select',
          isDirty: true
        }))
      }
      video.src = e.target?.result as string
    }
    reader.readAsDataURL(file)
  },
  
  // 工具方法：添加文字元素
  addTextElement: (x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y) => {
    // 使用 CSS 变量兼容的颜色，会在渲染时通过 var(--foreground) 处理
    const element: CanvasElement = {
      id: uuidv4(),
      type: 'text',
      x: x - 50,
      y: y - 15,
      width: 200,
      height: 40,
      name: 'Text',
      content: '双击编辑文字',
      fontSize: 24,
      fontFamily: 'Inter',
      color: '' // 空字符串表示使用默认的 var(--foreground)
    }
    
    set((state) => ({
      elements: [...state.elements, element],
      selectedIds: [element.id],
      activeTool: 'select',
      isDirty: true
    }))
  },
  
  // 工具方法：添加形状元素
  addShapeElement: (shapeType, x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y) => {
    const element: CanvasElement = {
      id: uuidv4(),
      type: 'shape',
      x: x - 50,
      y: y - 50,
      width: 100,
      height: 100,
      name: 'Shape',
      shapeType: shapeType || 'square',
      color: '#9CA3AF'
    }
    
    set((state) => ({
      elements: [...state.elements, element],
      selectedIds: [element.id],
      activeTool: 'select',
      isDirty: true
    }))
  },
  
  // 工具方法：添加图像生成器占位元素
  addImageGeneratorElement: (x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y, referenceImageId) => {
    const element: CanvasElement = {
      id: uuidv4(),
      type: 'image-generator',
      x: x - 150,
      y: y - 150,
      width: 300,
      height: 300,
      name: 'Image Generator',
      referenceImageId
    }
    
    set((state) => ({
      elements: [...state.elements, element],
      selectedIds: [element.id],
      isImageGeneratorOpen: true,
      imageGeneratorElementId: element.id,
      isDirty: true
    }))
  },

  // 工具方法：添加视频生成器占位元素
  addVideoGeneratorElement: (x = DEFAULT_CENTER_X, y = DEFAULT_CENTER_Y, referenceImageId) => {
    const element: CanvasElement = {
      id: uuidv4(),
      type: 'video-generator',
      x: x - 150,
      y: y - 150,
      width: 300,
      height: 300,
      name: 'Video Generator',
      referenceImageId
    }

    set((state) => ({
      elements: [...state.elements, element],
      selectedIds: [element.id],
      isVideoGeneratorOpen: true,
      videoGeneratorElementId: element.id,
      isDirty: true
    }))
  },
  
  // 工具方法：创建流程连接（从源图像创建新的生成器）
  // 规则：同一 group 串起来（若源元素已有 groupId，则复用；否则以源元素为起点创建新 group）
  createFlowConnection: (sourceElement: CanvasElement, options) => {
    if (sourceElement.type !== 'image' || !sourceElement.content) return null

    const spacing = 120
    const groupId = sourceElement.groupId || uuidv4()
    const connectorId = uuidv4()
    const generatorId = uuidv4()

    const sourceWidth = sourceElement.width || 300
    const sourceHeight = sourceElement.height || 300

    set((state) => {
      // 计算当前 group 的最右侧边界，避免新生成器与既有节点重叠
      const groupNonConnector = state.elements.filter(
        (el) => el.groupId === groupId && el.type !== 'connector' && !el.hidden
      )
      const rightEdge = groupNonConnector.reduce((max, el) => {
        const w = el.width || 0
        return Math.max(max, el.x + w)
      }, sourceElement.x + sourceWidth)

      const generatorX = rightEdge + spacing
      const generatorY = sourceElement.y

      // 创建连接线
      const connectorElement: CanvasElement = {
        id: connectorId,
        type: 'connector',
        x: 0,
        y: 0,
        connectorFrom: sourceElement.id,
        connectorTo: generatorId,
        connectorStyle: 'dashed',
        color: '#6B7280',
        strokeWidth: 2,
        groupId
      }

      // 创建新的图像生成器
      const generatorElement: CanvasElement = {
        id: generatorId,
        type: 'image-generator',
        x: generatorX,
        y: generatorY,
        width: sourceWidth,
        height: sourceHeight,
        name: options?.generatorName || 'Image Generator',
        referenceImageId: sourceElement.id,
        groupId,
        linkedElements: [sourceElement.id, connectorId]
      }

      // 更新源元素的关联信息：不覆盖已有 groupId
      const updatedElements = state.elements.map(el => {
        if (el.id !== sourceElement.id) return el
        const nextGroupId = el.groupId || groupId
        const merged = new Set([...(el.linkedElements || []), connectorId, generatorId])
        return {
          ...el,
          groupId: nextGroupId,
          linkedElements: Array.from(merged)
        }
      })

      return {
        elements: [...updatedElements, connectorElement, generatorElement],
        selectedIds: [generatorId],
        isImageGeneratorOpen: true,
        imageGeneratorElementId: generatorId,
        activeTool: 'select',
        isDirty: true
      }
    })

    return generatorId
  },

  toggleElementHidden: (id) => set((state) => ({
    elements: state.elements.map((el) => el.id === id ? { ...el, hidden: !el.hidden } : el),
    isDirty: true
  })),

  toggleElementLocked: (id) => set((state) => ({
    elements: state.elements.map((el) => el.id === id ? { ...el, locked: !el.locked } : el),
    isDirty: true
  })),
  
  // 项目方法
  resetCanvas: () => set({
    elements: [],
    selectedIds: [],
    scale: 1,
    pan: { x: 0, y: 0 },
    activeTool: 'select',
    currentProjectId: null,
    projectName: '未命名项目',
    isDirty: false,
    isImageGeneratorOpen: false,
    imageGeneratorElementId: null,
    isVideoGeneratorOpen: false,
    videoGeneratorElementId: null,
    // 重置 AI 对话
    conversationHistory: [],
    isAiThinking: false,
    // 重置元素分析
    analyzedElements: [],
    selectedAnalyzedElementId: null,
    isAnalyzing: false,
    analyzedImageBase64: null
  }),
  
  loadProject: (project) => set({
    elements: project.elements,
    projectName: project.name,
    currentProjectId: project.id,
    selectedIds: [],
    isDirty: false
  })
}))
