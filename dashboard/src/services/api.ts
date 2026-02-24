import axios from 'axios'
import type { 
  Agent, 
  Model, 
  Run, 
  Blueprint, 
  Trace, 
  BuildProgress,
  DashboardStats,
  ApiResponse,
  PaginatedResponse 
} from '@/types'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// Dashboard stats
export const getDashboardStats = async (): Promise<DashboardStats> => {
  const { data } = await api.get<DashboardStats>('/stats')
  return data
}

// Agents
export const getAgents = async (): Promise<Agent[]> => {
  const { data } = await api.get<Agent[]>('/agents')
  return data
}

export const getAgent = async (id: string): Promise<Agent> => {
  const { data } = await api.get<Agent>(`/agents/${id}`)
  return data
}

export const createAgent = async (agent: Partial<Agent>): Promise<Agent> => {
  const { data } = await api.post<Agent>('/agents', agent)
  return data
}

export const updateAgent = async (id: string, agent: Partial<Agent>): Promise<Agent> => {
  const { data } = await api.put<Agent>(`/agents/${id}`, agent)
  return data
}

export const deleteAgent = async (id: string): Promise<void> => {
  await api.delete(`/agents/${id}`)
}

// Models
export const getModels = async (): Promise<Model[]> => {
  const { data } = await api.get<Model[]>('/models')
  return data
}

export const getModel = async (id: string): Promise<Model> => {
  const { data } = await api.get<Model>(`/models/${id}`)
  return data
}

export const pullModel = async (name: string): Promise<{ status: string }> => {
  const { data } = await api.post<{ status: string }>('/models/pull', { name })
  return data
}

// Runs
export const getRuns = async (page = 1, pageSize = 20): Promise<PaginatedResponse<Run>> => {
  const { data } = await api.get<PaginatedResponse<Run>>('/runs', {
    params: { page, page_size: pageSize },
  })
  return data
}

export const getRun = async (id: string): Promise<Run> => {
  const { data } = await api.get<Run>(`/runs/${id}`)
  return data
}

export const createRun = async (request: string): Promise<Run> => {
  const { data } = await api.post<Run>('/runs', { request })
  return data
}

export const cancelRun = async (id: string): Promise<void> => {
  await api.post(`/runs/${id}/cancel`)
}

export const getRunTraces = async (runId: string): Promise<Trace[]> => {
  const { data } = await api.get<Trace[]>(`/runs/${runId}/traces`)
  return data
}

// Blueprints
export const getBlueprints = async (): Promise<Blueprint[]> => {
  const { data } = await api.get<Blueprint[]>('/blueprints')
  return data
}

export const getBlueprint = async (id: string): Promise<Blueprint> => {
  const { data } = await api.get<Blueprint>(`/blueprints/${id}`)
  return data
}

export const createBlueprint = async (request: string): Promise<Blueprint> => {
  const { data } = await api.post<Blueprint>('/blueprints', { request })
  return data
}

export const validateBlueprint = async (id: string): Promise<ApiResponse<Blueprint>> => {
  const { data } = await api.post<ApiResponse<Blueprint>>(`/blueprints/${id}/validate`)
  return data
}

export const executeBlueprint = async (id: string): Promise<Run> => {
  const { data } = await api.post<Run>(`/blueprints/${id}/execute`)
  return data
}

// Build Progress
export const getBuildProgress = async (runId: string): Promise<BuildProgress> => {
  const { data } = await api.get<BuildProgress>(`/builds/${runId}/progress`)
  return data
}

export const getBuildLogs = async (runId: string): Promise<BuildProgress['logs']> => {
  const { data } = await api.get<BuildProgress['logs']>(`/builds/${runId}/logs`)
  return data
}

export default api
