import { useState, useEffect } from 'react'
import { Plus, Search, Filter, Users, AlertCircle } from 'lucide-react'
import { AgentCard } from '@/components'
import { useAgents, useDeleteAgent, useWebSocket } from '@/hooks'
import type { Agent } from '@/types'

export function Agents() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { data: agents, isLoading, error, refetch } = useAgents()
  const deleteAgent = useDeleteAgent()
  const { subscribe } = useWebSocket()

  useEffect(() => {
    subscribe({
      onAgentStatus: () => refetch(),
    })
  }, [subscribe, refetch])

  const handleAction = async (action: 'start' | 'stop' | 'delete', agent: Agent) => {
    if (action === 'delete') {
      if (confirm(`Are you sure you want to delete agent "${agent.name}"?`)) {
        await deleteAgent.mutateAsync(agent.id)
      }
    }
  }

  const filteredAgents = agents?.filter((agent) => {
    const matchesSearch = agent.name.toLowerCase().includes(search.toLowerCase()) ||
                          agent.role.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'all' || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const statusCounts = agents?.reduce((acc, agent) => {
    acc[agent.status] = (acc[agent.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (error) {
    return (
      <div className="card text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-200 mb-2">Failed to load agents</h3>
        <p className="text-sm text-dark-400 mb-4">Unable to fetch agents from the server</p>
        <button onClick={() => refetch()} className="btn-primary">
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agents</h1>
          <p className="text-dark-400 mt-1">Manage your AI agents</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Create Agent
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-2xl font-bold text-white">{agents?.length ?? 0}</div>
          <div className="text-sm text-dark-400">Total</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-blue-400">{statusCounts?.running ?? 0}</div>
          <div className="text-sm text-dark-400">Running</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-gray-400">{statusCounts?.idle ?? 0}</div>
          <div className="text-sm text-dark-400">Idle</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-red-400">{statusCounts?.error ?? 0}</div>
          <div className="text-sm text-dark-400">Error</div>
        </div>
      </div>

      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents..."
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
              <option value="idle">Idle</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-dark-700 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-dark-700 rounded w-1/2" />
                  <div className="h-3 bg-dark-700 rounded w-1/3" />
                </div>
              </div>
              <div className="h-3 bg-dark-700 rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : filteredAgents && filteredAgents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onAction={handleAction}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Users className="w-12 h-12 text-dark-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-dark-300 mb-2">No Agents Found</h3>
          <p className="text-sm text-dark-400 mb-4">
            {search || statusFilter !== 'all' 
              ? 'Try adjusting your search or filter criteria'
              : 'Create your first agent to get started'}
          </p>
          {!search && statusFilter === 'all' && (
            <button className="btn-primary flex items-center gap-2 mx-auto">
              <Plus className="w-4 h-4" />
              Create Agent
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default Agents
