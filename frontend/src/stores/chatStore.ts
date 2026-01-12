import { create } from 'zustand'
import type { Message, ToolCall } from '@/types'

const STORAGE_KEY = 'nexus_conversations'

interface ChatState {
  // 按 conversation_id 存储消息
  conversations: Record<string, Message[]>
  currentConversationId: string | null
  streamingContent: string

  // 获取当前对话消息
  getCurrentMessages: () => Message[]

  // 设置当前对话 ID
  setCurrentConversationId: (id: string | null) => void

  // 添加消息到指定对话
  addMessageToConversation: (conversationId: string, message: Message) => void

  // 更新消息
  updateMessageInConversation: (conversationId: string, messageId: string, updates: Partial<Message>) => void

  // 添加工具调用
  addToolCall: (conversationId: string, messageId: string, toolCall: ToolCall) => void

  // 更新工具调用
  updateToolCall: (conversationId: string, messageId: string, toolCallId: string, updates: Partial<ToolCall>) => void

  // 清空指定对话
  clearConversation: (conversationId: string) => void

  // 删除对话
  deleteConversation: (conversationId: string) => void

  // 流式内容
  setStreamingContent: (content: string) => void

  // 持久化
  loadFromStorage: () => void
  saveToStorage: () => void

  // 兼容旧 API（逐步废弃）
  messages: Message[]
  addMessage: (message: Message) => void
  updateMessage: (id: string, updates: Partial<Message>) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: {},
  currentConversationId: null,
  streamingContent: '',
  messages: [], // 兼容旧 API，指向当前对话

  // 获取当前对话消息
  getCurrentMessages: () => {
    const { conversations, currentConversationId } = get()
    if (!currentConversationId) return []
    return conversations[currentConversationId] || []
  },

  // 设置当前对话 ID
  setCurrentConversationId: (id) => {
    set({ currentConversationId: id })
    // 同步更新 messages（兼容旧 API）
    const conversations = get().conversations
    set({ messages: id ? (conversations[id] || []) : [] })
  },

  // 添加消息到指定对话
  addMessageToConversation: (conversationId, message) => {
    set((state) => {
      const existing = state.conversations[conversationId] || []
      const updated = {
        ...state.conversations,
        [conversationId]: [...existing, message],
      }
      // 同步 messages
      const newMessages = state.currentConversationId === conversationId
        ? updated[conversationId]
        : state.messages
      return { conversations: updated, messages: newMessages }
    })
    // 自动保存
    get().saveToStorage()
  },

  // 更新消息
  updateMessageInConversation: (conversationId, messageId, updates) => {
    set((state) => {
      const existing = state.conversations[conversationId] || []
      const updated = {
        ...state.conversations,
        [conversationId]: existing.map((msg) =>
          msg.id === messageId ? { ...msg, ...updates } : msg
        ),
      }
      const newMessages = state.currentConversationId === conversationId
        ? updated[conversationId]
        : state.messages
      return { conversations: updated, messages: newMessages }
    })
    get().saveToStorage()
  },

  // 添加工具调用
  addToolCall: (conversationId, messageId, toolCall) => {
    set((state) => {
      const existing = state.conversations[conversationId] || []
      const updated = {
        ...state.conversations,
        [conversationId]: existing.map((msg) =>
          msg.id === messageId
            ? { ...msg, toolCalls: [...(msg.toolCalls || []), toolCall] }
            : msg
        ),
      }
      const newMessages = state.currentConversationId === conversationId
        ? updated[conversationId]
        : state.messages
      return { conversations: updated, messages: newMessages }
    })
    get().saveToStorage()
  },

  // 更新工具调用
  updateToolCall: (conversationId, messageId, toolCallId, updates) => {
    set((state) => {
      const existing = state.conversations[conversationId] || []
      const updated = {
        ...state.conversations,
        [conversationId]: existing.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                toolCalls: (msg.toolCalls || []).map((tc) =>
                  tc.id === toolCallId ? { ...tc, ...updates } : tc
                ),
              }
            : msg
        ),
      }
      const newMessages = state.currentConversationId === conversationId
        ? updated[conversationId]
        : state.messages
      return { conversations: updated, messages: newMessages }
    })
    get().saveToStorage()
  },

  // 清空指定对话
  clearConversation: (conversationId) => {
    set((state) => {
      const updated = { ...state.conversations, [conversationId]: [] }
      const newMessages = state.currentConversationId === conversationId ? [] : state.messages
      return { conversations: updated, messages: newMessages }
    })
    get().saveToStorage()
  },

  // 删除对话
  deleteConversation: (conversationId) => {
    set((state) => {
      const { [conversationId]: _, ...rest } = state.conversations
      return { conversations: rest }
    })
    get().saveToStorage()
  },

  // 流式内容
  setStreamingContent: (content) => set({ streamingContent: content }),

  // 从 localStorage 加载
  loadFromStorage: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const conversations = JSON.parse(stored)
        set({ conversations })
        console.log('[ChatStore] Loaded conversations from storage:', Object.keys(conversations).length)
      }
    } catch (e) {
      console.error('[ChatStore] Failed to load from storage:', e)
    }
  },

  // 保存到 localStorage
  saveToStorage: () => {
    try {
      const { conversations } = get()
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
    } catch (e) {
      console.error('[ChatStore] Failed to save to storage:', e)
    }
  },

  // ============ 兼容旧 API ============
  addMessage: (message) => {
    const { currentConversationId, addMessageToConversation } = get()
    if (currentConversationId) {
      addMessageToConversation(currentConversationId, message)
    } else {
      // 如果没有 conversation，直接添加到 messages（兼容模式）
      set((state) => ({ messages: [...state.messages, message] }))
    }
  },

  updateMessage: (id, updates) => {
    const { currentConversationId, updateMessageInConversation } = get()
    if (currentConversationId) {
      updateMessageInConversation(currentConversationId, id, updates)
    } else {
      set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === id ? { ...msg, ...updates } : msg
        ),
      }))
    }
  },

  clearMessages: () => {
    const { currentConversationId, clearConversation } = get()
    if (currentConversationId) {
      clearConversation(currentConversationId)
    } else {
      set({ messages: [], streamingContent: '' })
    }
  },
}))
