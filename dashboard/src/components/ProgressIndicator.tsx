import { cn } from '@/utils'

interface ProgressIndicatorProps {
  progress: number
  status: 'initializing' | 'planning' | 'building' | 'testing' | 'completed' | 'failed'
  currentStep?: string
  totalSteps?: number
  currentStepNumber?: number
  className?: string
  isLoading?: boolean
}

const statusConfig = {
  initializing: {
    label: 'Initializing',
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
  },
  planning: {
    label: 'Planning',
    color: 'bg-purple-500',
    textColor: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
  },
  building: {
    label: 'Building',
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
  },
  testing: {
    label: 'Testing',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
  },
  completed: {
    label: 'Completed',
    color: 'bg-green-500',
    textColor: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
  },
  failed: {
    label: 'Failed',
    color: 'bg-red-500',
    textColor: 'text-red-400',
    bgColor: 'bg-red-500/20',
    borderColor: 'border-red-500/30',
  },
}

export function ProgressIndicator({
  progress,
  status,
  currentStep,
  totalSteps,
  currentStepNumber,
  className,
  isLoading,
}: ProgressIndicatorProps) {
  const config = statusConfig[status]
  const isComplete = status === 'completed'
  const isFailed = status === 'failed'
  const isActive = !isComplete && !isFailed

  if (isLoading) {
    return (
      <div className={cn("card", className)}>
        <div className="animate-pulse space-y-4">
          <div className="flex items-center justify-between">
            <div className="h-4 bg-dark-700 rounded w-24" />
            <div className="h-6 bg-dark-700 rounded w-16" />
          </div>
          <div className="h-3 bg-dark-700 rounded-full" />
          <div className="h-3 bg-dark-700 rounded w-1/2" />
        </div>
      </div>
    )
  }

  return (
    <div className={cn("card", className)}>
      {/* Status Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-3 h-3 rounded-full",
            config.color,
            isActive && "animate-pulse"
          )} />
          <span className={cn("font-medium", config.textColor)}>
            {config.label}
          </span>
        </div>
        <span className="text-2xl font-bold text-white">
          {Math.round(progress)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="relative h-3 bg-dark-700 rounded-full overflow-hidden mb-4">
        <div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out",
            config.color
          )}
          style={{ width: `${progress}%` }}
        />
        {isActive && (
          <div
            className="absolute inset-y-0 w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"
            style={{ left: `${Math.max(0, progress - 10)}%` }}
          />
        )}
      </div>

      {/* Current Step */}
      {currentStep && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-dark-300">{currentStep}</span>
          {totalSteps && currentStepNumber && (
            <span className="text-dark-400">
              Step {currentStepNumber} of {totalSteps}
            </span>
          )}
        </div>
      )}

      {/* Step Indicators */}
      {totalSteps && totalSteps > 1 && (
        <div className="flex items-center gap-1 mt-4">
          {Array.from({ length: totalSteps }).map((_, index) => {
            const stepNumber = index + 1
            const isCompleted = currentStepNumber && stepNumber < currentStepNumber
            const isCurrent = currentStepNumber === stepNumber
            const isPending = currentStepNumber && stepNumber > currentStepNumber

            return (
              <div
                key={index}
                className={cn(
                  "flex-1 h-1.5 rounded-full transition-colors",
                  isCompleted && config.color,
                  isCurrent && config.color,
                  isPending && "bg-dark-700"
                )}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

export default ProgressIndicator
