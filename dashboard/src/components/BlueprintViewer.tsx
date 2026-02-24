import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronRight, FileCode, Users, Cpu, Wrench } from 'lucide-react'
import { cn } from '@/utils'
import type { Blueprint, BlueprintAgent } from '@/types'

interface BlueprintViewerProps {
  blueprint: Blueprint | null
  isLoading?: boolean
  className?: string
}

export function BlueprintViewer({ blueprint, isLoading, className }: BlueprintViewerProps) {
  const [copied, setCopied] = useState(false)
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set())

  const copyToClipboard = async () => {
    if (blueprint?.yaml_content) {
      await navigator.clipboard.writeText(blueprint.yaml_content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const toggleAgent = (agentId: string) => {
    const newExpanded = new Set(expandedAgents)
    if (newExpanded.has(agentId)) {
      newExpanded.delete(agentId)
    } else {
      newExpanded.add(agentId)
    }
    setExpandedAgents(newExpanded)
  }

  if (isLoading) {
    return (
      <div className={cn("card", className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-dark-700 rounded w-1/3" />
          <div className="h-32 bg-dark-700 rounded" />
          <div className="h-32 bg-dark-700 rounded" />
        </div>
      </div>
    )
  }

  if (!blueprint) {
    return (
      <div className={cn("card text-center py-12", className)}>
        <FileCode className="w-12 h-12 text-dark-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-dark-300 mb-2">No Blueprint Generated</h3>
        <p className="text-sm text-dark-400">
          Submit a planning request to generate an agent blueprint
        </p>
      </div>
    )
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">{blueprint.name}</h3>
            <p className="text-sm text-dark-400 mt-1">{blueprint.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "px-2 py-1 text-xs font-medium rounded-full",
              blueprint.status === 'validated' ? "bg-green-500/20 text-green-400" :
              blueprint.status === 'executing' ? "bg-purple-500/20 text-purple-400" :
              blueprint.status === 'completed' ? "bg-blue-500/20 text-blue-400" :
              blueprint.status === 'failed' ? "bg-red-500/20 text-red-400" :
              "bg-gray-500/20 text-gray-400"
            )}>
              {blueprint.status.charAt(0).toUpperCase() + blueprint.status.slice(1)}
            </span>
          </div>
        </div>

        {/* YAML Content */}
        <div className="relative">
          <div className="absolute top-2 right-2 z-10">
            <button
              onClick={copyToClipboard}
              className="p-2 rounded-lg bg-dark-700 hover:bg-dark-600 transition-colors"
              title="Copy YAML"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-400" />
              ) : (
                <Copy className="w-4 h-4 text-dark-300" />
              )}
            </button>
          </div>
          <pre className="bg-dark-900 rounded-lg p-4 overflow-x-auto text-sm scrollbar-thin">
            <code className="text-dark-200 font-mono whitespace-pre">
              {blueprint.yaml_content}
            </code>
          </pre>
        </div>
      </div>

      {/* Agents */}
      {blueprint.agents && blueprint.agents.length > 0 && (
        <div className="card">
          <h4 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-400" />
            Agents ({blueprint.agents.length})
          </h4>
          <div className="space-y-2">
            {blueprint.agents.map((agent) => (
              <AgentSection
                key={agent.id}
                agent={agent}
                isExpanded={expandedAgents.has(agent.id)}
                onToggle={() => toggleAgent(agent.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface AgentSectionProps {
  agent: BlueprintAgent
  isExpanded: boolean
  onToggle: () => void
}

function AgentSection({ agent, isExpanded, onToggle }: AgentSectionProps) {
  return (
    <div className="border border-dark-700 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-dark-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-dark-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-dark-400" />
          )}
          <span className="font-medium text-white">{agent.name}</span>
          <span className="text-sm text-dark-400">{agent.role}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-dark-400">
          <Cpu className="w-4 h-4" />
          <span>{agent.model}</span>
        </div>
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-dark-700">
          {agent.tools && agent.tools.length > 0 && (
            <div className="pt-3">
              <div className="flex items-center gap-2 text-sm text-dark-400 mb-2">
                <Wrench className="w-4 h-4" />
                Tools
              </div>
              <div className="flex flex-wrap gap-1">
                {agent.tools.map((tool) => (
                  <span 
                    key={tool}
                    className="px-2 py-0.5 text-xs bg-primary-500/20 text-primary-300 rounded"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {agent.dependencies && agent.dependencies.length > 0 && (
            <div>
              <div className="text-sm text-dark-400 mb-2">Dependencies</div>
              <div className="flex flex-wrap gap-1">
                {agent.dependencies.map((dep) => (
                  <span 
                    key={dep}
                    className="px-2 py-0.5 text-xs bg-dark-700 text-dark-300 rounded"
                  >
                    {dep}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default BlueprintViewer
