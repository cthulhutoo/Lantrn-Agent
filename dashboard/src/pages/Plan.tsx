import { useState } from 'react'
import { Send, Loader2, FileCode, AlertCircle, CheckCircle } from 'lucide-react'
import { BlueprintViewer } from '@/components'
import { useCreateBlueprint, useValidateBlueprint, useExecuteBlueprint } from '@/hooks'
import { cn } from '@/utils'
import type { Blueprint } from '@/types'

export function Plan() {
  const [request, setRequest] = useState('')
  const [currentBlueprint, setCurrentBlueprint] = useState<Blueprint | null>(null)
  
  const createBlueprint = useCreateBlueprint()
  const validateBlueprint = useValidateBlueprint()
  const executeBlueprint = useExecuteBlueprint()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!request.trim()) return
    
    try {
      const blueprint = await createBlueprint.mutateAsync(request)
      setCurrentBlueprint(blueprint)
    } catch (error) {
      console.error('Failed to create blueprint:', error)
    }
  }

  const handleValidate = async () => {
    if (!currentBlueprint) return
    
    try {
      const result = await validateBlueprint.mutateAsync(currentBlueprint.id)
      if (result.data) {
        setCurrentBlueprint(result.data)
      }
    } catch (error) {
      console.error('Failed to validate blueprint:', error)
    }
  }

  const handleExecute = async () => {
    if (!currentBlueprint) return
    
    try {
      await executeBlueprint.mutateAsync(currentBlueprint.id)
    } catch (error) {
      console.error('Failed to execute blueprint:', error)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Plan</h1>
        <p className="text-dark-400 mt-1">Create and execute agent blueprints</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-dark-200 mb-2">
            Planning Request
          </label>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="Describe what you want to build..."
            className="input min-h-[150px] resize-y"
            disabled={createBlueprint.isPending}
          />
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-dark-400">
              Be specific about your requirements for better results
            </p>
            <button
              type="submit"
              disabled={!request.trim() || createBlueprint.isPending}
              className={cn(
                "btn-primary flex items-center gap-2",
                (!request.trim() || createBlueprint.isPending) && "opacity-50 cursor-not-allowed"
              )}
            >
              {createBlueprint.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Generate Blueprint
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {createBlueprint.isError && (
        <div className="card border-red-500/50 bg-red-500/10">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <div>
              <h3 className="font-medium text-red-400">Failed to generate blueprint</h3>
              <p className="text-sm text-dark-300 mt-1">
                {createBlueprint.error?.message || 'An unexpected error occurred'}
              </p>
            </div>
          </div>
        </div>
      )}

      <BlueprintViewer 
        blueprint={currentBlueprint} 
        isLoading={createBlueprint.isPending}
      />

      {currentBlueprint && (
        <div className="card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileCode className="w-5 h-5 text-primary-400" />
              <div>
                <h3 className="font-medium text-white">Blueprint Ready</h3>
                <p className="text-sm text-dark-400">
                  Status: {currentBlueprint.status}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleValidate}
                disabled={validateBlueprint.isPending}
                className="btn-secondary flex items-center gap-2"
              >
                {validateBlueprint.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Validate
              </button>
              <button
                onClick={handleExecute}
                disabled={executeBlueprint.isPending || currentBlueprint.status === 'executing'}
                className="btn-primary flex items-center gap-2"
              >
                {executeBlueprint.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Execute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Plan
