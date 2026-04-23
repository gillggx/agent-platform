import axios from 'axios'
import { getClientId } from '@/utils/clientId'
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
  ArchitectStatus,
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
    llm_base_url?: string
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

// Attach per-browser anonymous ID to every request.
// Backend uses X-Client-ID to scope chat history / memory / projects per browser.
api.interceptors.request.use((config) => {
  config.headers = config.headers ?? {}
  config.headers['X-Client-ID'] = getClientId()
  return config
})

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

  architectStatus: (id: string): Promise<ArchitectStatus> =>
    api.get(`/projects/${id}/architect-status`).then((res) => res.data),

  wakeArchitect: (id: string): Promise<{ triggered: boolean; job_id?: string }> =>
    api.post(`/projects/${id}/wake-architect`).then((res) => res.data),
}

// Workflows API
export const workflowsApi = {
  listTemplates: (): Promise<WorkflowTemplate[]> =>
    api.get('/workflows/templates').then((res) => res.data),

  getTemplate: (id: string): Promise<WorkflowTemplate> =>
    api.get(`/workflows/templates/${id}`).then((res) => res.data),

  createTemplate: (data: { name: string; description?: string; definition: any }): Promise<WorkflowTemplate> =>
    api.post('/workflows/templates', data).then((res) => res.data),

  updateTemplate: (id: string, data: { name?: string; description?: string; definition?: any }): Promise<WorkflowTemplate> =>
    api.put(`/workflows/templates/${id}`, data).then((res) => res.data),

  deleteTemplate: (id: string): Promise<void> =>
    api.delete(`/workflows/templates/${id}`).then(() => undefined),

  cloneTemplate: (id: string): Promise<WorkflowTemplate> =>
    api.post(`/workflows/templates/${id}/clone`).then((res) => res.data),

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

// Chat API
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  project_context_ids: string[]
  created_at: string
}

export const chatApi = {
  history: (limit = 50): Promise<ChatMessage[]> =>
    api.get('/chat/history', { params: { limit } }).then((res) => res.data),

  clearHistory: (): Promise<void> =>
    api.delete('/chat/history').then(() => undefined),

  memory: (): Promise<{ global_memory: string; updated_at: string | null }> =>
    api.get('/chat/memory').then((res) => res.data),

  startProject: (
    projectName: string,
    projectDescription: string,
    templateId?: string,
  ): Promise<{ project_id: string; run_id: string; project_name: string; template_name: string }> =>
    api.post('/chat/start-project', {
      project_name: projectName,
      project_description: projectDescription,
      template_id: templateId,
    }).then((res) => res.data),

  /**
   * Stream a message to PM Agent via SSE.
   * onDelta: called with each text chunk
   * onDone: called when stream ends, with project_context_ids
   * onError: called on error
   */
  streamMessage: (
    message: string,
    onDelta: (text: string) => void,
    onDone: (contextIds: string[]) => void,
    onError: (msg: string) => void,
    onIntakeComplete?: (projectName: string, projectDescription: string) => void,
    intakeAlreadyTriggered?: boolean,
  ): AbortController => {
    const controller = new AbortController()

    fetch('/api/v1/chat/message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Client-ID': getClientId(),
      },
      body: JSON.stringify({ message, intake_already_triggered: intakeAlreadyTriggered ?? false }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const reader = res.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'delta') onDelta(event.content)
              else if (event.type === 'done') onDone(event.project_context_ids ?? [])
              else if (event.type === 'error') onError(event.content)
              else if (event.type === 'intake_complete' && onIntakeComplete)
                onIntakeComplete(event.project_name, event.project_description ?? '')
            } catch {
              // ignore malformed SSE line
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError(String(err))
      })

    return controller
  },
}

// Health check
export const healthApi = {
  check: (): Promise<any> =>
    api.get('/health', { baseURL: '' }).then((res) => res.data),
}

export default api
