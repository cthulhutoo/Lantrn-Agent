import { useState, useEffect } from 'react'
import { Play, RefreshCw, Terminal, Clock } from 'lucide-react'
import { ProgressIndicator, TraceViewer } from '@/components'
import { useBuildProgress, useBuildLogs, useRun, useRunTraces, useWebSocket } from '@/hooks'
import { cn, formatDate } from '@/utils'
import type { LogEntry } from '@/types'

export function Build() {
  const [runId, setRunId] = useState<string>('')
  const [inputRunId, setInputRunId] = useState<string>('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  
  const { data: progress, isLoading: progressLoading, refetch: refetchProgress } = useBuildProgress(runId)
  const { data: logs, isLoading: logsLoading, refetch: refetchLogs } = useBuildLogs(runId)
  const { data: run } = useRun(runId)
  const { data: traces } = useRunTraces(runId)
  const { subscribe } = useWebSocket()

  useEffect(() => {
    subscribe({
      onBuildProgress: (payload) => {
        if (payload.build_id === runId) {
          refetchProgress()
          refetchLogs()
        }
      },
    })
  }, [subscribe, runId, refetchProgress, refetchLogs])

  useEffect(() => {
    if (!autoRefresh || !runId) return
    const interval = setInterval(() => {
      refetchProgress()
      refetchLogs()
    }, 3000)
    return () => clearInterval(interval)
  }, [autoRefresh, runId, refetchProgress, refetchLogs])

  const handleLoadRun = () => {
    if (inputRunId.trim()) {
      setRunId(inputRunId.trim())
    }
  }

  const getLogColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return 'text-red-400'
      case 'warning': return 'text-yellow-400'
      case 'debug': return 'text-dark-400'
      default: return 'text-dark-200'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Build</h1>
          <p className="text-dark-400 mt-1">Monitor build progress and logs</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              "p-2 rounded-lg transition-colors",
              autoRefresh ? "bg-primary-600 text-white" : "bg-dark-700 text-dark-300"
            )}
            title={autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}
          >
            <RefreshCw className={cn("w-5 h-5", autoRefresh && "animate-spin")} />
          </button>
        </div>
      </div>

      <div className="card">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputRunId}
            onChange={(e) => setInputRunId(e.target.value)}
            placeholder="Enter Run ID to monitor..."
            className="input flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleLoadRun()}
          />
          <button
            onClick={handleLoadRun}
            disabled={!inputRunId.trim()}
            className="btn-primary flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            Load
          </button>
        </div>
      </div>

      {!runId ? (
        <div className="card text-center py-12">
          <Terminal className="w-12 h-12 text-dark-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-dark-300 mb-2">No Build Selected</h3>
          <p className="text-sm text-dark-400">
            Enter a Run ID to monitor build progress and logs
          </p>
        </div>
      ) : (
        <>
          {run && (
            <div className="card">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-white">Run: {run.id}</h3>
                  <p className="text-sm text-dark-400 mt-1">{run.request}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn(
                    "px-3 py-1 rounded-full text-sm font-medium",
                    run.status === 'completed' ? "bg-green-500/20 text-green-400" :
                    run.status === 'running' ? "bg-blue-500/20 text-blue-400" :
                    run.status === 'failed' ? "bg-red-500/20 text-red-400" :
                    "bg-gray-500/20 text-gray-400"
                  )}>
                    {run.status.charAt(0).toUpperCase() + run.status.slice(1)}
                  </span>
                  {run.created_at && (
                    <span className="text-sm text-dark-400">
                      {formatDate(run.created_at)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          <ProgressIndicator
            progress={progress?.progress ?? 0}
            status={progress?.status ?? 'initializing'}
            currentStep={progress?.current_step}
            totalSteps={progress?.total_steps}
            currentStepNumber={Math.floor((progress?.progress ?? 0) / (100 / (progress?.total_steps ?? 1)))}
            isLoading={progressLoading}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Terminal className="w-5 h-5 text-primary-400" />
                Build Logs
              </h3>
              <div className="bg-dark-900 rounded-lg p-4 h-[400px] overflow-y-auto scrollbar-thin font-mono text-sm">
                {logsLoading ? (
                  <div className="animate-pulse space-y-2">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="h-4 bg-dark-700 rounded w-full" />
                    ))}
                  </div>
                ) : logs && logs.length > 0 ? (
                  <div className="space-y-1">
                    {logs.map((log) => (
                      <div key={log.id} className="flex gap-2">
                        <span className="text-dark-500 shrink-0">
                          [{new Date(log.timestamp).toLocaleTimeString()}]
                        </span>
                        <span className={cn(
                          "shrink-0 uppercase",
                          getLogColor(log.level)
                        )}>
                          [{log.level}]
                        </span>
                        <span className={getLogColor(log.level)}>
                          {log.message}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center text-dark-400 py-8">
                    No logs available
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary-400" />
                Execution Traces
              </h3>
              <div className="h-[400px]">
                <TraceViewer traces={traces ?? []} autoScroll={autoRefresh} />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default Build
