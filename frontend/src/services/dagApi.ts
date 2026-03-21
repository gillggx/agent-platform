/**
 * DAG API Service
 * 
 * API calls for DAG workflow operations.
 */

import api from './api';
import { Workflow } from '@/types/dag';

/**
 * Fetch a workflow by ID
 */
export const fetchWorkflow = async (workflowId: string): Promise<Workflow> => {
  const response = await api.get(`/workflows/${workflowId}`);
  return response.data;
};

/**
 * Fetch all workflows
 */
export const fetchWorkflows = async (): Promise<Workflow[]> => {
  const response = await api.get('/workflows');
  return response.data;
};

/**
 * Create a new workflow
 */
export const createWorkflow = async (workflow: Workflow): Promise<Workflow> => {
  const response = await api.post('/workflows', workflow);
  return response.data;
};

/**
 * Update an existing workflow
 */
export const updateWorkflow = async (
  workflowId: string,
  workflow: Partial<Workflow>
): Promise<Workflow> => {
  const response = await api.put(`/workflows/${workflowId}`, workflow);
  return response.data;
};

/**
 * Delete a workflow
 */
export const deleteWorkflow = async (workflowId: string): Promise<void> => {
  await api.delete(`/workflows/${workflowId}`);
};

/**
 * Validate a workflow
 */
export const validateWorkflow = async (workflow: Workflow) => {
  const response = await api.post('/workflows/validate', workflow);
  return response.data;
};

/**
 * Execute a workflow
 */
export const executeWorkflow = async (
  workflowId: string,
  input?: any
) => {
  const response = await api.post(`/workflows/${workflowId}/execute`, { input });
  return response.data;
};

/**
 * Get workflow execution status
 */
export const getWorkflowStatus = async (executionId: string) => {
  const response = await api.get(`/workflows/executions/${executionId}`);
  return response.data;
};

export default {
  fetchWorkflow,
  fetchWorkflows,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  validateWorkflow,
  executeWorkflow,
  getWorkflowStatus,
};
