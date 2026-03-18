// API Response types
export interface User {
  id: string
  email: string
  full_name: string
  role: string
  org_id: string
  organization_name: string
}

export interface Project {
  id: string
  name: string
  description?: string
  status: string
  codebase_path?: string
  latest_run_id?: string
  created_by: string
  created_at: string
  updated_at?: string
}

export interface ArchitectStatus {
  linked: boolean
  codebase_path: string | null
  has_memory: boolean
  architect_url?: string
  error?: string
}

export interface ProjectDetail extends Project {
  workflow_runs: WorkflowRun[]
}

export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  is_system: boolean
  definition: WorkflowDefinition
}

export interface WorkflowDefinition {
  workflow: {
    id: string
    name: string
    description: string
    version: number
    steps: WorkflowStep[]
    guardrails: {
      max_total_steps: number
      timeout_minutes: number
      require_human_approval: string[]
    }
  }
}

export interface WorkflowStep {
  id: string
  agent_role: string
  task_type: string
  depends_on: string[]
  routing: {
    type: 'static' | 'llm_decision'
    next_steps?: string[]
    decision_prompt?: string
    options?: {
      label: string
      target_step: string
      condition_hint: string
    }[]
  }
  loop?: {
    enabled: boolean
    max_iterations: number
    escalate_to?: string
  }
}

export interface WorkflowRun {
  id: string
  project_id: string
  template_id: string
  status: string
  user_input: string
  current_steps: string[]
  created_at: string
}

export interface WorkflowRunDetail extends WorkflowRun {
  step_executions: Record<string, any>
  template_snapshot: WorkflowDefinition
}

export interface Artifact {
  id: string
  project_id: string
  agent_role: string
  artifact_type: string
  version: number
  status: string
  content_preview: string
  metadata: Record<string, any>
  created_at: string
}

export interface ArtifactDetail extends Artifact {
  content_md: string
}

// Form types
export interface CreateProjectForm {
  name: string
  description?: string
  codebase_path?: string
}

export interface StartWorkflowForm {
  project_id: string
  template_id: string
  user_input: string
}

// Auth types (kept for compatibility)
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// Store types
export interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
}

// Chat message types
export interface ChatMessage {
  id: string
  agent_role: string
  agent_name: string
  content: string
  timestamp: string
  type: 'draft' | 'review' | 'revise' | 'approve'
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'agent_message' | 'step_complete' | 'workflow_complete' | 'error'
  data: any
}
