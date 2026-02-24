import { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/utils'

interface StatusCardProps {
  title: string
  value: string | number
  icon: ReactNode
  trend?: {
    value: number
    label: string
  }
  status?: 'success' | 'warning' | 'error' | 'neutral'
  className?: string
}

export function StatusCard({ 
  title, 
  value, 
  icon, 
  trend, 
  status = 'neutral',
  className 
}: StatusCardProps) {
  const statusColors = {
    success: 'from-green-500/20 to-green-600/10 border-green-500/30',
    warning: 'from-yellow-500/20 to-yellow-600/10 border-yellow-500/30',
    error: 'from-red-500/20 to-red-600/10 border-red-500/30',
    neutral: 'from-primary-500/20 to-primary-600/10 border-primary-500/30',
  }

  const iconColors = {
    success: 'text-green-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
    neutral: 'text-primary-400',
  }

  return (
    <div className={cn(
      "relative overflow-hidden rounded-xl border bg-gradient-to-br p-6 transition-all duration-200 hover:shadow-lg",
      statusColors[status],
      className
    )}>
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 opacity-10">
        <div className="absolute transform rotate-12 scale-150">
          {icon}
        </div>
      </div>

      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-medium text-dark-300">{title}</span>
          <div className={cn("p-2 rounded-lg bg-dark-800/50", iconColors[status])}>
            {icon}
          </div>
        </div>

        <div className="flex items-end justify-between">
          <div>
            <h3 className="text-3xl font-bold text-white mb-1">{value}</h3>
            {trend && (
              <div className="flex items-center gap-1 text-sm">
                {trend.value > 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-400" />
                ) : trend.value < 0 ? (
                  <TrendingDown className="w-4 h-4 text-red-400" />
                ) : (
                  <Minus className="w-4 h-4 text-dark-400" />
                )}
                <span className={cn(
                  trend.value > 0 ? "text-green-400" : 
                  trend.value < 0 ? "text-red-400" : 
                  "text-dark-400"
                )}>
                  {trend.value > 0 ? '+' : ''}{trend.value}%
                </span>
                <span className="text-dark-400">{trend.label}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default StatusCard
