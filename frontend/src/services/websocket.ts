import type { ConnectionStatus } from '@/types'

export interface WSMessage {
  type: string
  data: unknown
}

type MessageHandler = (message: WSMessage) => void
type StatusHandler = (status: ConnectionStatus) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private messageHandlers: MessageHandler[] = []
  private statusHandlers: StatusHandler[] = []
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  private url: string

  constructor() {
    this.url = `ws://${window.location.hostname}:8000/ws`
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    this.notifyStatus('connecting')
    this.ws = new WebSocket(this.url)

    this.ws.onopen = () => {
      this.notifyStatus('connected')
      this.notifyMessage({ type: 'status', data: 'connected' })
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.notifyMessage({ type: data.type || 'chat', data })
      } catch {
        console.error('Failed to parse WebSocket message')
      }
    }

    this.ws.onclose = () => {
      this.notifyStatus('disconnected')
      this.notifyMessage({ type: 'status', data: 'disconnected' })
      this.scheduleReconnect()
    }

    this.ws.onerror = () => {
      this.notifyStatus('disconnected')
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) return
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null
      this.connect()
    }, 3000)
  }

  send(data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.push(handler)
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler)
    }
  }

  onStatus(handler: StatusHandler) {
    this.statusHandlers.push(handler)
    return () => {
      this.statusHandlers = this.statusHandlers.filter(h => h !== handler)
    }
  }

  private notifyMessage(message: WSMessage) {
    this.messageHandlers.forEach(h => h(message))
  }

  private notifyStatus(status: ConnectionStatus) {
    this.statusHandlers.forEach(h => h(status))
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }
    this.ws?.close()
  }
}

export const wsService = new WebSocketService()
