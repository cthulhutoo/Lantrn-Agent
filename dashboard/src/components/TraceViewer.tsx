import { useState, useRef, useEffect } from 'react'
import { 
  Brain, 
  Play, 
  Eye, 
  AlertCircle, 
  ChevronDown, 
  ChevronRight,
  Filter,
  User
} from 'lucide-react'
import { cn, truncate } from '@/utils'
import type { Trace } from '@/types'

interface TraceViewerProps {
  traces: Trace[]
  isLoading?: boolean
  className?: string
  autoScroll?: boolean
}

const traceTypeConfig = {
  thought: {
    icon: Brain,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
    label: 'Thought',
  },
  action: {
    icon: Play,
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    label: 'Action',
  },
  observation: {
    icon: Eye,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    label: 'Observation',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
    label: 'Error',
  },
}

export function TraceViewer({ traces, isLoading, className, autoScroll = true }: TraceViewerProps) {
  const [expandedTraces, setExpandedTraces] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<Trace['type'] | 'all'>('all')
  const containerRef = useRef<HTMLDivElement>(null)

  const filteredTraces = filter === 'all' 
    ? traces 
    : traces.filter(t => t.type === filter)

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [traces, autoScroll])

  const toggleTrace = (id: string) => {
    const newExpanded = new Set(expandedTraces)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedTraces(newExpanded)
  }

  if (isLoading) {
    return (
      <div className={cn("card", className)}>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <div className="w-8 h-8 bg-dark-700 rounded-lg" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-dark-700 rounded w-1/3" />
                <div className="h-3 bg-dark-700 rounded w-2/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!traces || traces.length === 0) {
    return (
      <div className={cn("card text-center py-12", className)}>
        <Brain className="w-12 h-12 text-dark-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-300 mb-2">No Traces Available</h3>
        <p className="text-sm text-dark-400">
          Execution traces will appear here when a run is in progress
        </p>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Filter */}
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-4 h-4 text-dark-400" />
        <div className="flex gap-1">
          {(['all', 'thought', 'action', 'observation', 'error'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={cn(
                "px-3 py-1 text-sm rounded-lg transition-colors",
                filter === type 
                  ? "bg-primary-600 text-white" 
                  : "bg-dark-800 text-dark-300 hover:bg-dark-700"
              )}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
        <span className="ml-auto text-sm text-dark-400">
          {filteredTraces.length} trace{filteredTraces.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Traces */}
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto scrollbar-thin space-y-2 max-h-[600px]"
      >
        {filteredTraces.map((trace) => {
          const config = traceTypeConfig[trace.type]
          const Icon = config.icon
          const isExpanded = expandedTraces.has(trace.id)

          return (
            <div
              key={trace.id}
              className={cn(
                "border rounded-lg overflow-hidden transition-all",
                config.borderColor,
                config.bgColor
              )}
            >
              <button
                onClick={() => toggleTrace(trace.id)}
                className="w-full flex items-start gap-3 p-3 hover:bg-dark-800/30 transition-colors"
              >
                <div className={cn("p-1.5 rounded-lg", config.bgColor)}>
                  <Icon className={cn("w-4 h-4", config.color)} />
                </div>
                <div className="flex-1 text-left">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={cn("text-sm font-medium", config.color)}>
                      {config.label}
                    </span>
                    <span className="text-xs text-dark-400">
                      {new Date(trace.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-sm text-dark-200">
                    {truncate(trace.content, 150)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {trace.agent_id && (
                    <span className="flex items-center gap-1 text-xs text-dark-400">
                      <User className="w-3 h-3" />
                      {trace.agent_id.slice(0, 8)}
                    </span>
                  )}
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-dark-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-dark-400" />
                  )}
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 pt-0">
                  <div className="ml-9 p-3 bg-dark-900/50 rounded-lg">
                    <pre className="text-sm text-dark-200 whitespace-pre-wrap font-mono">
                      {trace.content}
                    </pre>
                    {trace.metadata && Object.keys(trace.metadata).length > 0 && (
                      <div className="mt-3 pt-3 border-t border-dark-700">
                        <div className="text-xs text-dark-400 mb-2">Metadata</div>
                        <pre className="text-xs text-dark-300 font-mono">
                          {JSON.stringify(trace.metadata, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default TraceViewer
