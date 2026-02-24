// Agent types
export interface Agent {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'running' | 'error' | 'completed';
  model: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

// Model types
export interface Model {
  id: string;
  name: string;
  provider: string;
  status: 'available' | 'loading' | 'error';
  parameters: {
    context_length: number;
    embedding_length?: number;
    num_params?: string;
    quantization?: string;
  };
  capabilities: string[];
}

// Run types
export interface Run {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  request: string;
  blueprint_id?: string;
  agents: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
  result?: string;
  error?: string;
}

// Blueprint types
export interface Blueprint {
  id: string;
  name: string;
  description: string;
  yaml_content: string;
  agents: BlueprintAgent[];
  created_at: string;
  status: 'draft' | 'validated' | 'executing' | 'completed' | 'failed';
}

export interface BlueprintAgent {
  id: string;
  name: string;
  role: string;
  model: string;
  tools: string[];
  dependencies: string[];
}

// Trace types
export interface Trace {
  id: string;
  run_id: string;
  agent_id: string;
  timestamp: string;
  type: 'thought' | 'action' | 'observation' | 'error';
  content: string;
  metadata?: Record<string, unknown>;
}

// Build types
export interface BuildProgress {
  id: string;
  run_id: string;
  status: 'initializing' | 'planning' | 'building' | 'testing' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  total_steps: number;
  logs: LogEntry[];
  started_at: string;
  updated_at: string;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  source?: string;
}

// WebSocket types
export type WSMessageType = 
  | 'agent_status'
  | 'run_update'
  | 'build_progress'
  | 'trace'
  | 'log'
  | 'model_update';

export interface WSMessage<T = unknown> {
  type: WSMessageType;
  payload: T;
  timestamp: string;
}

export interface AgentStatusPayload {
  agent_id: string;
  status: Agent['status'];
  message?: string;
}

export interface RunUpdatePayload {
  run_id: string;
  status: Run['status'];
  progress?: number;
  result?: string;
  error?: string;
}

export interface BuildProgressPayload {
  build_id: string;
  status: BuildProgress['status'];
  progress: number;
  current_step: string;
  log?: LogEntry;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Dashboard stats
export interface DashboardStats {
  total_agents: number;
  active_agents: number;
  total_models: number;
  total_runs: number;
  running_runs: number;
  completed_runs: number;
  failed_runs: number;
}

// WebSocket status
export type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'error';
