import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Users, Cpu, History, Play, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { StatusCard } from '@/components'
import { useDashboardStats, useWebSocket } from '@/hooks'
import { cn } from '@/utils'

export function Home() {
  const { data: stats, isLoading, error, refetch } = useDashboardStats()
  const { isConnected, subscribe } = useWebSocket()

  // Subscribe to WebSocket updates
  useEffect(() => {
    subscribe({
      onRunUpdate: () => refetch(),
      onBuildProgress: () => refetch(),
      onAgentStatus: () => refetch(),
    })
  }, [subscribe, refetch])

  if (error) {
    return (
      <div className="card text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-200 mb-2">Failed to load dashboard</h3>
        <p className="text-sm text-dark-400 mb-4">Unable to fetch statistics from the server</p>
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
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-dark-400 mt-1">Overview of your agent system</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm",
            isConnected ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
          )}>
            <div className={cn(
              "w-2 h-2 rounded-full",
              isConnected ? "bg-green-500" : "bg-red-500"
            )} />
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard
          title="Total Agents"
          value={isLoading ? '-' : stats?.total_agents ?? 0}
          icon={<Users className="w-5 h-5" />}
          status="neutral"
          trend={stats?.active_agents ? {
            value: Math.round((stats.active_agents / stats.total_agents) * 100),
            label: 'active'
          } : undefined}
        />
        <StatusCard
          title="Available Models"
          value={isLoading ? '-' : stats?.total_models ?? 0}
          icon={<Cpu className="w-5 h-5" />}
          status="success"
        />
        <StatusCard
          title="Total Runs"
          value={isLoading ? '-' : stats?.total_runs ?? 0}
          icon={<History className="w-5 h-5" />}
          status="neutral"
        />
        <StatusCard
          title="Running"
          value={isLoading ? '-' : stats?.running_runs ?? 0}
          icon={<Play className="w-5 h-5" />}
          status={stats?.running_runs && stats.running_runs > 0 ? 'warning' : 'neutral'}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/plan"
          className="card-hover group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500/20 to-purple-600/10 flex items-center justify-center group-hover:from-purple-500/30 group-hover:to-purple-600/20 transition-colors">
            <Play className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-purple-400 transition-colors">
              New Plan
            </h3>
            <p className="text-sm text-dark-400">Create a new agent blueprint</p>
          </div>
        </Link>

        <Link
          to="/agents"
          className="card-hover group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500/20 to-blue-600/10 flex items-center justify-center group-hover:from-blue-500/30 group-hover:to-blue-600/20 transition-colors">
            <Users className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors">
              View Agents
            </h3>
            <p className="text-sm text-dark-400">Manage your agents</p>
          </div>
        </Link>

        <Link
          to="/runs"
          className="card-hover group flex items-center gap-4"
        >
          <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-green-500/20 to-green-600/10 flex items-center justify-center group-hover:from-green-500/30 group-hover:to-green-600/20 transition-colors">
            <History className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-green-400 transition-colors">
              Run History
            </h3>
            <p className="text-sm text-dark-400">View past executions</p>
          </div>
        </Link>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
        <div className="space-y-3">
          {isLoading ? (
            <div className="animate-pulse space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-dark-700 rounded-lg" />
                  <div className="flex-1 space-y-1">
                    <div className="h-4 bg-dark-700 rounded w-1/3" />
                    <div className="h-3 bg-dark-700 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-dark-400">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Recent activity will appear here</p>
            </div>
          )}
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            Completed Runs
          </h3>
          <div className="text-3xl font-bold text-white">
            {isLoading ? '-' : stats?.completed_runs ?? 0}
          </div>
          {stats?.total_runs && stats.total_runs > 0 && (
            <div className="mt-2 h-2 bg-dark-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${(stats.completed_runs / stats.total_runs) * 100}%` }}
              />
            </div>
          )}
        </div>

        <div className="card">
          <h3 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            Failed Runs
          </h3>
          <div className="text-3xl font-bold text-white">
            {isLoading ? '-' : stats?.failed_runs ?? 0}
          </div>
          {stats?.total_runs && stats.total_runs > 0 && (
            <div className="mt-2 h-2 bg-dark-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-red-500 rounded-full"
                style={{ width: `${(stats.failed_runs / stats.total_runs) * 100}%` }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Home
