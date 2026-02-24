import { useState, useEffect } from 'react'
import { History, Search, Filter, Play, XCircle, CheckCircle, Clock, AlertCircle, ChevronRight, Eye } from 'lucide-react'
import { TraceViewer } from '@/components'
import { useRuns, useRunTraces, useCancelRun, useWebSocket } from '@/hooks'
import { cn, formatDate, formatDuration, truncate } from '@/utils'
import type { Run } from '@/types'

const statusConfig = {
  pending: { icon: Clock, color: 'text-gray-400', bgColor: 'bg-gray-500/20', label: 'Pending' },
  running: { icon: Play, color: 'text-blue-400', bgColor: 'bg-blue-500/20', label: 'Running' },
  completed: { icon: CheckCircle, color: 'text-green-400', bgColor: 'bg-green-500/20', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-400', bgColor: 'bg-red-500/20', label: 'Failed' },
  cancelled: { icon: XCircle, color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', label: 'Cancelled' },
}

export function Runs() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedRun, setSelectedRun] = useState<Run | null>(null)
  
  const { data: runsData, isLoading, error, refetch } = useRuns(page)
  const { data: traces } = useRunTraces(selectedRun?.id ?? '')
  const cancelRun = useCancelRun()
  const { subscribe } = useWebSocket()

  // Subscribe to WebSocket updates
  useEffect(() => {
    subscribe({
      onRunUpdate: () => refetch(),
    })
  }, [subscribe, refetch])

  const handleCancelRun = async (runId: string) => {
    if (confirm('Are you sure you want to cancel this run?')) {
      await cancelRun.mutateAsync(runId)
    }
  }

  const filteredRuns = runsData?.items.filter((run) => {
    const matchesSearch = run.request.toLowerCase().includes(search.toLowerCase()) ||
                          run.id.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || run.status === statusFilter
    return matchesSearch && matchesStatus
  })

  if (error) {
    return (
      <div className="card text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-200 mb-2">Failed to load runs</h3>
        <p className="text-sm text-dark-400 mb-4">Unable to fetch runs from the server</p>
        <button onClick={() => refetch()} className="btn-primary">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
    {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Runs</h1>
          <p className="text-dark-400 mt-1">View and manage execution history</p>
        </div>
        <div className="text-sm text-dark-400">
          {runsData && `${runsData.total} total runs`}
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search runs..."
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-dark-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input w-auto"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Runs List */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="card animate-pulse">
                  <div className="flex items-center justify-between mb-3">
                    <div className="h-4 bg-dark-700 rounded w-1/4" />
                    <div className="h-6 bg-dark-700 rounded w-20" />
                  </div>
                  <div className="h-3 bg-dark-700 rounded w-3/4" />
                </div>
              ))}
            </div>
          ) : filteredRuns && filteredRuns.length > 0 ? (
            <div className="space-y-3">
              {filteredRuns.map((run) => {
                const config = statusConfig[run.status]
                const StatusIcon = config.icon
                const isSelected = selectedRun?.id === run.id

                return (
                  <div
                    key={run.id}
                    className={cn(
                      "card cursor-pointer transition-all",
                      isSelected ? "border-primary-500 bg-primary-500/5" : "hover:border-dark-600"
                    )}
                    onClick={() => setSelectedRun(run)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "p-2 rounded-lg",
                          config.bgColor
                        )}>
                          <StatusIcon className={cn("w-4 h-4", config.color)} />
                        </div>
                        <div>
                          <h3 className="font-medium text-white">{truncate(run.id, 12)}</h3>
                          <p className="text-xs text-dark-400">{formatDate(run.created_at)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={cn(
                          "px-2 py-1 text-xs font-medium rounded-full",
                          config.bgColor,
                          config.color
                        )}>
                          {config.label}
                        </span>
                        {run.status === 'running' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleCancelRun(run.id)
                            }}
                            className="p-1 rounded hover:bg-dark-700 transition-colors"
                            title="Cancel run"
                          >
                            <XCircle className="w-4 h-4 text-red-400" />
                          </button>
                        )}
                      </div>
                    </div>

                    <p className="text-sm text-dark-300 mb-3">
                      {truncate(run.request, 100)}
                    </p>

                    <div className="flex items-center justify-between text-xs text-dark-400">
                      <div className="flex items-center gap-4">
                        {run.agents && run.agents.length > 0 && (
                          <span>{run.agents.length} agents</span>
                        )}
                        {run.duration && (
                          <span>{formatDuration(run.duration)}</span>
                        )}
                      </div>
                      <ChevronRight className={cn(
                        "w-4 h-4 transition-transform",
                        isSelected && "rotate-90"
                      )} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="card text-center py-12">
              <History className="w-12 h-12 text-dark-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-dark-300 mb-2">No Runs Found</h3>
              <p className="text-sm text-dark-400">
                {search || statusFilter !== 'all' 
                  ? 'Try adjusting your search or filter criteria'
                  : 'Run history will appear here'}
              </p>
            </div>
          )}

          {/* Pagination */}
          {runsData && runsData.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-dark-400">
                Page {page} of {runsData.total_pages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(runsData.total_pages, p + 1))}
                disabled={page === runsData.total_pages}
                className="btn-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>

        {/* Run Details */}
        <div className="lg:col-span-1">
          {selectedRun ? (
            <div className="card sticky top-24">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">Run Details</h3>
                <button
                  onClick={() => setSelectedRun(null)}
                  className="p-1 rounded hover:bg-dark-700 transition-colors"
                >
                  <XCircle className="w-4 h-4 text-dark-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-dark-400">ID</label>
                  <p className="text-sm text-white font-mono">{selectedRun.id}</p>
                </div>

                <div>
                  <label className="text-xs text-dark-400">Request</label>
                  <p className="text-sm text-dark-200">{selectedRun.request}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-dark-400">Status</label>
                    <p className={"text-sm font-medium " + statusConfig[selectedRun.status].color}>
                      {statusConfig[selectedRun.status].label}
                    </p>
                  </div>
                  <div>
                    <label className="text-xs text-dark-400">Duration</label>
                    <p className="text-sm text-white">
                      {selectedRun.duration ? formatDuration(selectedRun.duration) : '-'}
                    </p>
                  </div>
                </div>

                {selectedRun.result && (
                  <div>
                    <label className="text-xs text-dark-400">Result</label>
                    <p className="text-sm text-dark-200">{selectedRun.result}</p>
                  </div>
                )}

                {selectedRun.error && (
                  <div>
                    <label className="text-xs text-dark-400">Error</label>
                    <p className="text-sm text-red-400">{selectedRun.error}</p>
                  </div>
                )}

                {/* Traces */}
                <div className="pt-4 border-t border-dark-700">
                  <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                    <Eye className="w-4 h-4 text-primary-400" />
                    Traces
                  </h4>
                  <div className="max-h-[400px]">
                    <TraceViewer traces={traces ?? []} />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card text-center py-12">
              <Eye className="w-12 h-12 text-dark-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-dark-300 mb-2">No Run Selected</h3>
              <p className="text-sm text-dark-400">
                Select a run to view details
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Runs
