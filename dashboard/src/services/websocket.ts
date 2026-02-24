import type { WSMessage, AgentStatusPayload, RunUpdatePayload, BuildProgressPayload, Trace, LogEntry } from '@/types'

type MessageHandler<T = unknown> = (payload: T) => void

type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

interface WebSocketCallbacks {
  onAgentStatus?: MessageHandler<AgentStatusPayload>
  onRunUpdate?: MessageHandler<RunUpdatePayload>
  onBuildProgress?: MessageHandler<BuildProgressPayload>
  onTrace?: MessageHandler<Trace>
  onLog?: MessageHandler<LogEntry>
  onStatusChange?: (status: WSStatus) => void
}

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private callbacks: WebSocketCallbacks = {}
  private status: WSStatus = 'disconnected'
  private pingInterval: ReturnType<typeof setInterval> | null = null

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//localhost:8000/ws`
  }

  connect(callbacks: WebSocketCallbacks = {}): void {
    this.callbacks = callbacks
    this.setStatus('connecting')
    
    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.setStatus('connected')
        this.reconnectAttempts = 0
        this.startPing()
      }
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.setStatus('disconnected')
        this.stopPing()
        this.attemptReconnect()
      }
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.setStatus('error')
      }
      
      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.setStatus('error')
      this.attemptReconnect()
    }
  }

  private setStatus(status: WSStatus): void {
    this.status = status
    this.callbacks.onStatusChange?.(status)
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`)
      setTimeout(() => this.connect(this.callbacks), delay)
    }
  }

  private handleMessage(message: WSMessage): void {
    switch (message.type) {
      case 'agent_status':
        this.callbacks.onAgentStatus?.(message.payload as AgentStatusPayload)
        break
      case 'run_update':
        this.callbacks.onRunUpdate?.(message.payload as RunUpdatePayload)
        break
      case 'build_progress':
        this.callbacks.onBuildProgress?.(message.payload as BuildProgressPayload)
        break
      case 'trace':
        this.callbacks.onTrace?.(message.payload as Trace)
        break
      case 'log':
        this.callbacks.onLog?.(message.payload as LogEntry)
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }

  send<T>(type: string, payload: T): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  disconnect(): void {
    this.stopPing()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.setStatus('disconnected')
  }

  getStatus(): WSStatus {
    return this.status
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsService = new WebSocketService()
export default wsService
