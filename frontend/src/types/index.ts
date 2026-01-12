export type Theme = 'light' | 'dark'

export type MessageRole = 'user' | 'agent' | 'system' | 'assistant'

export type ToolCallStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ToolCall {
  id: string
  name: string
  parameters: Record<string, unknown>
  status: ToolCallStatus
  output?: string
}

export interface FileAttachment {
  id: string
  name: string
  type: 'image' | 'document' | 'other'
  mimeType: string
  size: number
  previewUrl?: string  // 用于图片预览的 base64 或 URL
}

export interface Message {
  id: string
  role: MessageRole
  content: string
  timestamp: string
  toolCalls?: ToolCall[]
  status?: 'pending' | 'sent' | 'error'
  streaming?: boolean
  attachments?: FileAttachment[]  // 附件列表
}

export interface TaskPhase {
  id: string
  title: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  steps?: string[]
}

export interface Task {
  id: string
  title: string
  description?: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused'
  progress: number
  phases?: TaskPhase[]
  createdAt: string
  updatedAt: string
}

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  content?: string
  language?: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export type ViewType = 'chat' | 'task' | 'file' | 'browser' | 'terminal' | 'ppt'

export interface BrowserState {
  url: string
  isLoading: boolean
  htmlContent: string
  screenshot: string | null
}

export interface TerminalSession {
  id: string
  output: string
  input: string
  isRunning: boolean
}

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'
