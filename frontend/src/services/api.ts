import axios from 'axios'
import type {
  User,
  Project,
  ProjectDetail,
  WorkflowTemplate,
  WorkflowRun,
  WorkflowRunDetail,
  Artifact,
  ArtifactDetail,
  CreateProjectForm,
  StartWorkflowForm,
} from '@/types'

export interface AgentDef {
  id: string
  role: string
  display_name: string
  description: string
  soul: string
  config: {
    temperature?: number
    max_tokens?: number
    llm_model?: string
    llm_provider?: string
    llm_api_key?: string
    [key: string]: any
  }
  is_system: string
}

export interface UpdateAgentData {
  display_name?: string
  description?: string
  soul?: string
  config?: Record<string, any>
}

// Create axios instance
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,  // 60s for LLM calls
})

// No auth interceptors needed for prototype

// Auth API (minimal — no real auth)
export const authApi = {
  me: (): Promise<User> =>
    api.get('/auth/me').then((res) => res.data),
}

// Projects API
export const projectsApi = {
  list: (): Promise<Project[]> =>
    api.get('/projects').then((res) => res.data),

  get: (id: string): Promise<ProjectDetail> =>
    api.get(`/projects/${id}`).then((res) => res.data),

  create: (data: CreateProjectForm): Promise<Project> =>
    api.post('/projects', data).then((res) => res.data),

  delete: (id: string): Promise<void> =>
    api.delete(`/projects/${id}`).then(() => undefined),
}

// Workflows API
export const workflowsApi = {
  listTemplates: (): Promise<WorkflowTemplate[]> =>
    api.get('/workflows/templates').then((res) => res.data),

  getTemplate: (id: string): Promise<WorkflowTemplate> =>
    api.get(`/workflows/templates/${id}`).then((res) => res.data),

  startWorkflow: (data: StartWorkflowForm): Promise<WorkflowRun> =>
    api.post('/workflows/runs', data).then((res) => res.data),

  getRun: (id: string): Promise<WorkflowRunDetail> =>
    api.get(`/workflows/runs/${id}`).then((res) => res.data),

  listProjectRuns: (projectId: string): Promise<WorkflowRun[]> =>
    api.get(`/workflows/projects/${projectId}/runs`).then((res) => res.data),

  approve: (runId: string, approved: boolean, feedback?: string): Promise<void> =>
    api.post(`/workflows/runs/${runId}/approve`, { approved, feedback }).then(() => undefined),
}

// Artifacts API
export const artifactsApi = {
  listProject: (projectId: string): Promise<Artifact[]> =>
    api.get(`/artifacts/projects/${projectId}/artifacts`).then((res) => res.data),

  get: (id: string): Promise<ArtifactDetail> =>
    api.get(`/artifacts/${id}`).then((res) => res.data),

  download: (id: string): Promise<Blob> =>
    api.get(`/artifacts/${id}/download`, { responseType: 'blob' }).then((res) => res.data),

  downloadProject: (projectId: string): Promise<Blob> =>
    api.get(`/artifacts/projects/${projectId}/download`, { responseType: 'blob' }).then((res) => res.data),
}

// Agents API
export const agentsApi = {
  list: (): Promise<AgentDef[]> =>
    api.get('/agents').then((res) => res.data),

  get: (role: string): Promise<AgentDef> =>
    api.get(`/agents/${role}`).then((res) => res.data),

  update: (role: string, data: UpdateAgentData): Promise<AgentDef> =>
    api.put(`/agents/${role}`, data).then((res) => res.data),
}

// Health check
export const healthApi = {
  check: (): Promise<any> =>
    api.get('/health', { baseURL: '' }).then((res) => res.data),
}

export default api
