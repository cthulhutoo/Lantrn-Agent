import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '@/services/api'
import type { Agent } from '@/types'

export const queryKeys = {
  stats: ['stats'] as const,
  agents: ['agents'] as const,
  agent: (id: string) => ['agents', id] as const,
  models: ['models'] as const,
  model: (id: string) => ['models', id] as const,
  runs: ['runs'] as const,
  run: (id: string) => ['runs', id] as const,
  runTraces: (runId: string) => ['runs', runId, 'traces'] as const,
  blueprints: ['blueprints'] as const,
  blueprint: (id: string) => ['blueprints', id] as const,
  buildProgress: (runId: string) => ['builds', runId, 'progress'] as const,
  buildLogs: (runId: string) => ['builds', runId, 'logs'] as const,
}

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: api.getDashboardStats,
    refetchInterval: 30000,
  })
}

export function useAgents() {
  return useQuery({
    queryKey: queryKeys.agents,
    queryFn: api.getAgents,
  })
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: queryKeys.agent(id),
    queryFn: () => api.getAgent(id),
    enabled: !!id,
  })
}

export function useCreateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents })
    },
  })
}

export function useUpdateAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Agent> }) =>
      api.updateAgent(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents })
      queryClient.invalidateQueries({ queryKey: queryKeys.agent(id) })
    },
  })
}

export function useDeleteAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.deleteAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents })
    },
  })
}

export function useModels() {
  return useQuery({
    queryKey: queryKeys.models,
    queryFn: api.getModels,
  })
}

export function useModel(id: string) {
  return useQuery({
    queryKey: queryKeys.model(id),
    queryFn: () => api.getModel(id),
    enabled: !!id,
  })
}

export function usePullModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.pullModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.models })
    },
  })
}

export function useRuns(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: [...queryKeys.runs, page, pageSize],
    queryFn: () => api.getRuns(page, pageSize),
  })
}

export function useRun(id: string) {
  return useQuery({
    queryKey: queryKeys.run(id),
    queryFn: () => api.getRun(id),
    enabled: !!id,
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: queryKeys.stats })
    },
  })
}

export function useCancelRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.cancelRun,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: queryKeys.run(id) })
    },
  })
}

export function useRunTraces(runId: string) {
  return useQuery({
    queryKey: queryKeys.runTraces(runId),
    queryFn: () => api.getRunTraces(runId),
    enabled: !!runId,
  })
}

export function useBlueprints() {
  return useQuery({
    queryKey: queryKeys.blueprints,
    queryFn: api.getBlueprints,
  })
}

export function useBlueprint(id: string) {
  return useQuery({
    queryKey: queryKeys.blueprint(id),
    queryFn: () => api.getBlueprint(id),
    enabled: !!id,
  })
}

export function useCreateBlueprint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createBlueprint,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.blueprints })
    },
  })
}

export function useValidateBlueprint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.validateBlueprint,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.blueprint(id) })
    },
  })
}

export function useExecuteBlueprint() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.executeBlueprint,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.blueprints })
      queryClient.invalidateQueries({ queryKey: queryKeys.runs })
      queryClient.invalidateQueries({ queryKey: queryKeys.stats })
    },
  })
}

export function useBuildProgress(runId: string) {
  return useQuery({
    queryKey: queryKeys.buildProgress(runId),
    queryFn: () => api.getBuildProgress(runId),
    enabled: !!runId,
    refetchInterval: 2000,
  })
}

export function useBuildLogs(runId: string) {
  return useQuery({
    queryKey: queryKeys.buildLogs(runId),
    queryFn: () => api.getBuildLogs(runId),
    enabled: !!runId,
  })
}
