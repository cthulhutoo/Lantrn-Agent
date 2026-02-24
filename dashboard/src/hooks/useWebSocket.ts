import { useEffect, useState, useCallback, useRef } from 'react'
import wsService from '@/services/websocket'
import type { WSStatus, AgentStatusPayload, RunUpdatePayload, BuildProgressPayload, Trace, LogEntry } from '@/types'

interface UseWebSocketReturn {
  status: WSStatus
  isConnected: boolean
  subscribe: (callbacks: {
    onAgentStatus?: (payload: AgentStatusPayload) => void
    onRunUpdate?: (payload: RunUpdatePayload) => void
    onBuildProgress?: (payload: BuildProgressPayload) => void
    onTrace?: (payload: Trace) => void
    onLog?: (payload: LogEntry) => void
  }) => void
  send: <T>(type: string, payload: T) => void
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<WSStatus>('disconnected')
  const callbacksRef = useRef<{
    onAgentStatus?: (payload: AgentStatusPayload) => void
    onRunUpdate?: (payload: RunUpdatePayload) => void
    onBuildProgress?: (payload: BuildProgressPayload) => void
    onTrace?: (payload: Trace) => void
    onLog?: (payload: LogEntry) => void
  }>({})

  useEffect(() => {
    wsService.connect({
      onStatusChange: setStatus,
      onAgentStatus: (payload) => callbacksRef.current.onAgentStatus?.(payload),
      onRunUpdate: (payload) => callbacksRef.current.onRunUpdate?.(payload),
      onBuildProgress: (payload) => callbacksRef.current.onBuildProgress?.(payload),
      onTrace: (payload) => callbacksRef.current.onTrace?.(payload),
      onLog: (payload) => callbacksRef.current.onLog?.(payload),
    })

    return () => {
      wsService.disconnect()
    }
  }, [])

  const subscribe = useCallback((callbacks: typeof callbacksRef.current) => {
    callbacksRef.current = callbacks
  }, [])

  const send = useCallback(<T,>(type: string, payload: T) => {
    wsService.send(type, payload)
  }, [])

  return {
    status,
    isConnected: status === 'connected',
    subscribe,
    send,
  }
}
