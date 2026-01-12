import { useEffect, useRef, useCallback } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { useAppStore } from '@/stores/appStore'
import { useTaskStore } from '@/stores/taskStore'
import { handlePPTMessage } from '@/stores/pptStore'
import { v4 as uuidv4 } from 'uuid'
import type { Message, FileAttachment } from '@/types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws'

// Singleton WebSocket to prevent multiple connections
let globalWs: WebSocket | null = null
let connectionId = 0

export const useWebSocket = () => {
  const { 
    addMessageToConversation, 
    updateMessageInConversation, 
    setStreamingContent, 
    currentConversationId,
    getCurrentMessages,
  } = useChatStore()
  const { setConnectionStatus, setAgentIsThinking } = useAppStore()
  const { updateTask, activeTaskId } = useTaskStore()

  const ws = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const messageQueue = useRef<string[]>([])
  const isConnected = useRef(false)
  const instanceId = useRef(++connectionId)

  const connect = useCallback(() => {
    // Use global WebSocket if exists and is open/connecting
    if (globalWs && (globalWs.readyState === WebSocket.OPEN || globalWs.readyState === WebSocket.CONNECTING)) {
      ws.current = globalWs
      if (globalWs.readyState === WebSocket.OPEN) {
        isConnected.current = true
        setConnectionStatus('connected')
      }
      return
    }

    setConnectionStatus('connecting')
    console.log(`[WebSocket #${instanceId.current}] Attempting to connect...`)
    globalWs = new WebSocket(WS_URL)
    ws.current = globalWs

    ws.current.onopen = () => {
      console.log('[WebSocket] Connected')
      setConnectionStatus('connected')
      isConnected.current = true
      // Store global reference for PPT store and other modules
      ;(window as any).__nexus_ws = ws.current
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
      // Send any queued messages
      while (messageQueue.current.length > 0) {
        const message = messageQueue.current.shift()
        if (message) {
          ws.current?.send(message)
        }
      }
    }

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      console.log('[WebSocket] Received:', data)

      // 获取当前对话 ID
      const conversationId = useChatStore.getState().currentConversationId

      switch (data.type) {
        case 'chat':
          const chatMessage: Message = {
            id: data.id || uuidv4(),
            role: data.role === 'assistant' ? 'agent' : data.role,
            content: data.content,
            timestamp: new Date().toISOString(),
            toolCalls: data.toolCalls,
            status: data.status,
            streaming: data.streaming,
          }
          if (data.streaming) {
            setStreamingContent(data.content)
          } else {
            // 添加到当前对话
            if (conversationId) {
              addMessageToConversation(conversationId, chatMessage)
            }
            setStreamingContent('')
            setAgentIsThinking(false)
          }
          break

        case 'status':
          console.log('Agent Status:', data.content)
          if (data.content === 'thinking') {
            setAgentIsThinking(true)
          } else {
            setAgentIsThinking(false)
          }
          break

        case 'task_update':
          updateTask(data.task.id, data.task)
          break

        case 'system':
          console.log('System message:', data)
          // 不再自动添加"已连接"消息，避免污染每个对话
          break

        case 'error':
          console.error('[WebSocket Error]:', data.content)
          if (conversationId) {
            addMessageToConversation(conversationId, {
              id: uuidv4(),
              role: 'system',
              content: `错误: ${data.content}`,
              timestamp: new Date().toISOString(),
              status: 'error',
            })
          }
          setAgentIsThinking(false)
          break

        // PPT 相关消息
        case 'ppt_progress':
        case 'ppt_complete':
        case 'ppt_error':
        case 'ppt_templates':
        case 'ppt_slide_updated':
        case 'ppt_exported':
          handlePPTMessage(data)
          break

        default:
          console.warn('[WebSocket] Unknown message type:', data.type)
      }
    }

    ws.current.onclose = (event) => {
      isConnected.current = false
      setStreamingContent('')
      console.log('[WebSocket] Disconnected:', event.code, event.reason)
      setConnectionStatus('disconnected')
      setAgentIsThinking(false)
      if (!reconnectTimer.current) {
        reconnectTimer.current = setTimeout(() => {
          console.log('[WebSocket] Reconnecting...')
          connect()
        }, 3000)
      }
    }

    ws.current.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
      ws.current?.close()
    }
  }, [addMessageToConversation, setStreamingContent, setConnectionStatus, updateTask, setAgentIsThinking])

  useEffect(() => {
    connect()

    return () => {
      // Only cleanup reconnect timer, don't close global WebSocket
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
    }
  }, [connect])

  const sendMessage = useCallback((message: Omit<Message, 'id' | 'timestamp' | 'status'> & { 
    has_image?: boolean
    attachments?: FileAttachment[]
    file_data?: Array<{ name: string; type: string; mimeType: string; data?: string }>
  }) => {
    // 获取当前对话 ID
    const conversationId = useChatStore.getState().currentConversationId

    if (!conversationId) {
      console.error('[WebSocket] No active conversation, cannot send message')
      return
    }

    const messageWithId: Message = {
      id: uuidv4(),
      role: message.role,
      content: message.content,
      timestamp: new Date().toISOString(),
      status: 'pending',
      attachments: message.attachments,
    }

    // 添加到当前对话
    addMessageToConversation(conversationId, messageWithId)
    setAgentIsThinking(true)

    // 构建发送给后端的 payload
    const payload = JSON.stringify({
      type: 'chat',
      content: message.content,
      conversation_id: conversationId,
      has_image: message.has_image || false,
      file_data: message.file_data || [],
    })

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(payload)
      updateMessageInConversation(conversationId, messageWithId.id, { status: 'sent' })
    } else {
      messageQueue.current.push(payload)
      console.warn('[WebSocket] Not connected, message queued.')
      updateMessageInConversation(conversationId, messageWithId.id, { 
        status: 'error', 
        content: 'Failed to send: Not connected. Message queued.' 
      })
    }
  }, [addMessageToConversation, updateMessageInConversation, setAgentIsThinking])

  return { sendMessage, isConnected: isConnected.current }
}
