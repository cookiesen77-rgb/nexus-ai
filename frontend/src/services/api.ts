import type { Task, FileNode, ApiResponse } from '@/types'

const API_BASE = '/api/v1'

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }))
      return { success: false, error: error.message || error.detail }
    }

    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: String(error) }
  }
}

export const api = {
  // Chat
  async chat(messages: Array<{ role: string; content: string }>, thinkingMode = false) {
    return request<{ content: string; tool_calls?: unknown[] }>('/agents/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages,
        thinking_mode: thinkingMode,
      }),
    })
  },

  // Tasks
  async createTask(task: string, thinkingMode = false) {
    return request<{ task_id: string }>('/agents/tasks', {
      method: 'POST',
      body: JSON.stringify({
        task,
        thinking_mode: thinkingMode,
      }),
    })
  },

  async getTask(taskId: string) {
    return request<Task>(`/agents/tasks/${taskId}`)
  },

  async cancelTask(taskId: string) {
    return request<void>(`/agents/tasks/${taskId}/cancel`, {
      method: 'POST',
    })
  },

  // Files
  async listFiles(path = '/') {
    return request<FileNode>(`/files?path=${encodeURIComponent(path)}`)
  },

  async readFile(path: string) {
    return request<{ content: string; language: string }>(`/files/read?path=${encodeURIComponent(path)}`)
  },

  async writeFile(path: string, content: string) {
    return request<void>('/files/write', {
      method: 'POST',
      body: JSON.stringify({ path, content }),
    })
  },

  async deleteFile(path: string) {
    return request<void>('/files/delete', {
      method: 'DELETE',
      body: JSON.stringify({ path }),
    })
  },

  // Tools
  async listTools() {
    return request<Record<string, { description: string; parameters: string[] }>>('/tools')
  },

  async executeTool(name: string, parameters: Record<string, unknown>) {
    return request<{ success: boolean; output: string }>('/tools/execute', {
      method: 'POST',
      body: JSON.stringify({ name, parameters }),
    })
  },

  // Browser
  async browserNavigate(url: string) {
    return request<{ screenshot: string; title: string }>('/browser/navigate', {
      method: 'POST',
      body: JSON.stringify({ url }),
    })
  },

  async browserScreenshot() {
    return request<{ screenshot: string }>('/browser/screenshot')
  },

  async browserClick(selector: string) {
    return request<void>('/browser/click', {
      method: 'POST',
      body: JSON.stringify({ selector }),
    })
  },

  async browserType(selector: string, text: string) {
    return request<void>('/browser/type', {
      method: 'POST',
      body: JSON.stringify({ selector, text }),
    })
  },

  // Health
  async health() {
    return request<{ status: string }>('/health')
  },

  // Metrics
  async metrics() {
    return request<Record<string, unknown>>('/metrics')
  },
}

