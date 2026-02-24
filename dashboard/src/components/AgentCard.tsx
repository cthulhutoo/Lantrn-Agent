import { User, Cpu, Clock, MoreVertical, Play, Pause, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { cn, formatDate, getStatusColor } from '@/utils'
import type { Agent } from '@/types'

interface AgentCardProps {
  agent: Agent
  onAction?: (action: 'start' | 'stop' | 'delete', agent: Agent) => void
  onClick?: (agent: Agent) => void
}

export function AgentCard({ agent, onAction, onClick }: AgentCardProps) {
  const [showMenu, setShowMenu] = useState(false)

  const statusLabel = agent.status.charAt(0).toUpperCase() + agent.status.slice(1)

  return (
    <div 
      className={cn(
        "card-hover cursor-pointer group",
        "border border-dark-700 hover:border-primary-500/50"
      )}
      onClick={() => onClick?.(agent)}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-600/10 flex items-center justify-center">
            <User className="w-5 h-5 text-primary-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-primary-400 transition-colors">
              {agent.name}
            </h3>
            <p className="text-sm text-dark-400">{agent.role}</p>
          </div>
        </div>

        <div className="relative">
          <button 
            className="p-1.5 rounded-lg hover:bg-dark-700 transition-colors opacity-0 group-hover:opacity-100"
            onClick={(e) => {
              e.stopPropagation()
              setShowMenu(!showMenu)
            }}
          >
            <MoreVertical className="w-4 h-4 text-dark-400" />
          </button>

          {showMenu && (
            <div 
              className="absolute right-0 top-full mt-1 w-36 bg-dark-800 border border-dark-700 rounded-lg shadow-lg z-10"
              onClick={(e) => e.stopPropagation()}
            >
              {agent.status === 'idle' && (
                <button
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-dark-200 hover:bg-dark-700 transition-colors"
                  onClick={() => {
                    onAction?.('start', agent)
                    setShowMenu(false)
                  }}
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
              )}
              {agent.status === 'running' && (
                <button
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-dark-200 hover:bg-dark-700 transition-colors"
                  onClick={() => {
                    onAction?.('stop', agent)
                    setShowMenu(false)
                  }}
                >
                  <Pause className="w-4 h-4" />
                  Stop
                </button>
              )}
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-dark-700 transition-colors"
                onClick={() => {
                  onAction?.('delete', agent)
                  setShowMenu(false)
                }}
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1.5">
          <div className={cn("w-2 h-2 rounded-full", getStatusColor(agent.status))} />
          <span className="text-dark-300">{statusLabel}</span>
        </div>

        <div className="flex items-center gap-1.5 text-dark-400">
          <Cpu className="w-4 h-4" />
          <span>{agent.model}</span>
        </div>

        <div className="flex items-center gap-1.5 text-dark-400 ml-auto">
          <Clock className="w-4 h-4" />
          <span>{formatDate(agent.updated_at)}</span>
        </div>
      </div>

      {agent.metadata && Object.keys(agent.metadata).length > 0 && (
        <div className="mt-4 pt-4 border-t border-dark-700">
          <div className="flex flex-wrap gap-2">
            {Object.entries(agent.metadata).slice(0, 3).map(([key, value]) => (
              <span 
                key={key}
                className="px-2 py-0.5 text-xs bg-dark-700 text-dark-300 rounded"
              >
                {key}: {String(value).slice(0, 20)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AgentCard
