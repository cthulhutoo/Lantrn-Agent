import { useState } from 'react'
import { Cpu, Download, RefreshCw, CheckCircle, AlertCircle, Loader2, HardDrive, Zap, Brain } from 'lucide-react'
import { useModels, usePullModel } from '@/hooks'
import { cn } from '@/utils'

export function Models() {
  const [pullModelName, setPullModelName] = useState('')
  const { data: models, isLoading, error, refetch } = useModels()
  const pullModel = usePullModel()

  const handlePullModel = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pullModelName.trim()) return
    
    try {
      await pullModel.mutateAsync(pullModelName.trim())
      setPullModelName('')
    } catch (error) {
      console.error('Failed to pull model:', error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'available':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'loading':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />
    }
  }

  if (error) {
    return (
      <div className="card text-center py-12">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-200 mb-2">Failed to load models</h3>
        <p className="text-sm text-dark-400 mb-4">Unable to fetch models from Ollama</p>
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
          <h1 className="text-2xl font-bold text-white">Models</h1>
          <p className="text-dark-400 mt-1">Manage AI models from Ollama</p>
        </div>
        <button 
          onClick={() => refetch()} 
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="card">
        <h3 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
          <Download className="w-5 h-5 text-primary-400" />
          Pull New Model
        </h3>
        <form onSubmit={handlePullModel} className="flex gap-3">
          <input
            type="text"
            value={pullModelName}
            onChange={(e) => setPullModelName(e.target.value)}
            placeholder="Enter model name (e.g., llama2, mistral, codellama)"
            className="input flex-1"
            disabled={pullModel.isPending}
          />
          <button
            type="submit"
            disabled={!pullModelName.trim() || pullModel.isPending}
            className={cn(
              "btn-primary flex items-center gap-2",
              (!pullModelName.trim() || pullModel.isPending) && "opacity-50 cursor-not-allowed"
            )}
          >
            {pullModel.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Pulling...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Pull Model
              </>
            )}
          </button>
        </form>
        {pullModel.isError && (
          <p className="text-sm text-red-400 mt-2">
            Failed to pull model: {pullModel.error?.message}
          </p>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="card animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-dark-700 rounded-lg" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-dark-700 rounded w-2/3" />
                  <div className="h-3 bg-dark-700 rounded w-1/2" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-dark-700 rounded w-full" />
                <div className="h-3 bg-dark-700 rounded w-3/4" />
              </div>
            </div>
          ))}
        </div>
      ) : models && models.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((model) => (
            <div key={model.id} className="card-hover">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-600/10 flex items-center justify-center">
                    <Brain className="w-5 h-5 text-primary-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{model.name}</h3>
                    <p className="text-sm text-dark-400">{model.provider}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {getStatusIcon(model.status)}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <HardDrive className="w-4 h-4 text-dark-400" />
                  <span className="text-dark-300">Context:</span>
                  <span className="text-white">{model.parameters.context_length.toLocaleString()}</span>
                </div>

                {model.parameters.num_params && (
                  <div className="flex items-center gap-2 text-sm">
                    <Zap className="w-4 h-4 text-dark-400" />
                    <span className="text-dark-300">Parameters:</span>
                    <span className="text-white">{model.parameters.num_params}</span>
                  </div>
                )}

                {model.parameters.quantization && (
                  <div className="flex items-center gap-2 text-sm">
                    <Cpu className="w-4 h-4 text-dark-400" />
                    <span className="text-dark-300">Quantization:</span>
                    <span className="text-white">{model.parameters.quantization}</span>
                  </div>
                )}

                {model.capabilities && model.capabilities.length > 0 && (
                  <div className="pt-3 border-t border-dark-700">
                    <div className="flex flex-wrap gap-1">
                      {model.capabilities.map((cap) => (
                        <span 
                          key={cap}
                          className="px-2 py-0.5 text-xs bg-primary-500/20 text-primary-300 rounded"
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card text-center py-12">
          <Cpu className="w-12 h-12 text-dark-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-dark-300 mb-2">No Models Available</h3>
          <p className="text-sm text-dark-400 mb-4">
            Pull your first model from Ollama to get started
          </p>
          <p className="text-xs text-dark-500">
            Try: llama2, mistral, codellama, or any other Ollama model
          </p>
        </div>
      )}
    </div>
  )
}

export default Models
