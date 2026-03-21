/**
 * DAG Editor Types
 * 
 * Core type definitions for the DAG editor, including nodes, edges, and workflows.
 */

/**
 * Supported agent roles in the workflow
 */
export type AgentRole = 
  | 'product_manager'
  | 'architect'
  | 'qa'
  | 'devops'
  | 'director';

/**
 * Node represents an agent in the DAG
 */
export interface DAGNode {
  id: string;
  type: 'agent' | 'tool';
  role: AgentRole;
  position: {
    x: number;
    y: number;
  };
  data: {
    title: string;
    color?: string;
    inputs: string[];
    outputs: string[];
    config: NodeConfig;
  };
}

/**
 * Configuration for each node
 */
export interface NodeConfig {
  llm_model: string;
  temperature: number;
  max_tokens: number;
  top_p?: number;
  system_prompt?: string;
  [key: string]: any;
}

/**
 * Edge represents a connection between nodes
 */
export interface DAGEdge {
  id: string;
  source: string;
  target: string;
  data?: {
    label?: string;
    type?: string;
    format?: string;
    validation?: boolean;
  };
  style?: {
    stroke?: string;
    strokeWidth?: number;
  };
}

/**
 * Workflow configuration
 */
export interface WorkflowConfig {
  timeout_seconds: number;
  max_retries: number;
  parallelism: number;
  cost_limit_usd: number;
  [key: string]: any;
}

/**
 * Complete workflow definition
 */
export interface Workflow {
  id: string;
  name: string;
  version: string;
  created_at: string;
  updated_at: string;
  config: WorkflowConfig;
  nodes: DAGNode[];
  edges: DAGEdge[];
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  type: 'cycle' | 'missing_config' | 'type_mismatch' | 'missing_edge';
  nodeId?: string;
  edgeId?: string;
  message: string;
}

export interface ValidationWarning {
  type: 'isolated_node' | 'missing_output' | 'high_cost';
  nodeId?: string;
  message: string;
}

/**
 * Undo/Redo action
 */
export type DAGAction = 
  | { type: 'ADD_NODE'; payload: DAGNode }
  | { type: 'REMOVE_NODE'; payload: string }
  | { type: 'UPDATE_NODE'; payload: DAGNode }
  | { type: 'ADD_EDGE'; payload: DAGEdge }
  | { type: 'REMOVE_EDGE'; payload: string }
  | { type: 'UPDATE_EDGE'; payload: DAGEdge }
  | { type: 'UPDATE_WORKFLOW'; payload: Partial<Workflow> }
  | { type: 'CLEAR' };

/**
 * Editor state
 */
export interface DAGEditorState {
  workflow: Workflow | null;
  selectedNode: string | null;
  selectedEdge: string | null;
  validation: ValidationResult;
  isDirty: boolean;
  isSaving: boolean;
  error: string | null;
}
