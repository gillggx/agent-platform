/**
 * DAG Editor Store (Zustand)
 * 
 * Centralized state management for the DAG editor
 */

import { create } from 'zustand';
import { DAGNode, DAGEdge, Workflow, DAGEditorState } from '../types/dag';
import { validateDAG } from '../utils/validation';

interface DAGStore extends DAGEditorState {
  // Workflow operations
  setWorkflow: (workflow: Workflow) => void;
  createWorkflow: (name: string, config?: any) => void;
  
  // Node operations
  addNode: (node: DAGNode) => void;
  updateNode: (node: DAGNode) => void;
  removeNode: (nodeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  
  // Edge operations
  addEdge: (edge: DAGEdge) => void;
  updateEdge: (edge: DAGEdge) => void;
  removeEdge: (edgeId: string) => void;
  selectEdge: (edgeId: string | null) => void;
  
  // Workflow operations
  updateWorkflowConfig: (config: any) => void;
  validateWorkflow: () => void;
  
  // State management
  setError: (error: string | null) => void;
  setSaving: (saving: boolean) => void;
  
  // Undo/Redo
  undo: () => void;
  redo: () => void;
  clearHistory: () => void;
}

const initialState: DAGEditorState = {
  workflow: null,
  selectedNode: null,
  selectedEdge: null,
  validation: {
    valid: true,
    errors: [],
    warnings: [],
  },
  isDirty: false,
  isSaving: false,
  error: null,
};

export const useDagStore = create<DAGStore>((set, get) => {
  const undoStack: Workflow[] = [];
  const redoStack: Workflow[] = [];
  const maxHistorySize = 50;

  const pushToUndoStack = (workflow: Workflow) => {
    undoStack.push(JSON.parse(JSON.stringify(workflow)));
    if (undoStack.length > maxHistorySize) {
      undoStack.shift();
    }
    redoStack.length = 0; // Clear redo stack on new action
  };

  return {
    ...initialState,

    // Workflow operations
    setWorkflow: (workflow: Workflow) => {
      set((state) => {
        if (state.workflow) {
          pushToUndoStack(state.workflow);
        }
        return {
          workflow,
          isDirty: true,
        };
      });
    },

    createWorkflow: (name: string, config?: any) => {
      const workflow: Workflow = {
        id: `wf-${Date.now()}`,
        name,
        version: '1.0.0',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        config: config || {
          timeout_seconds: 3600,
          max_retries: 3,
          parallelism: 4,
          cost_limit_usd: 50.0,
        },
        nodes: [],
        edges: [],
      };
      set({ workflow, isDirty: false });
    },

    // Node operations
    addNode: (node: DAGNode) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          nodes: [...state.workflow.nodes, node],
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          isDirty: true,
        };
      });
    },

    updateNode: (node: DAGNode) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          nodes: state.workflow.nodes.map((n) => (n.id === node.id ? node : n)),
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          isDirty: true,
        };
      });
    },

    removeNode: (nodeId: string) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          nodes: state.workflow.nodes.filter((n) => n.id !== nodeId),
          edges: state.workflow.edges.filter(
            (e) => e.source !== nodeId && e.target !== nodeId
          ),
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          selectedNode: state.selectedNode === nodeId ? null : state.selectedNode,
          isDirty: true,
        };
      });
    },

    selectNode: (nodeId: string | null) => {
      set({ selectedNode: nodeId, selectedEdge: null });
    },

    // Edge operations
    addEdge: (edge: DAGEdge) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          edges: [...state.workflow.edges, edge],
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          isDirty: true,
        };
      });

      get().validateWorkflow();
    },

    updateEdge: (edge: DAGEdge) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          edges: state.workflow.edges.map((e) => (e.id === edge.id ? edge : e)),
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          isDirty: true,
        };
      });

      get().validateWorkflow();
    },

    removeEdge: (edgeId: string) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          edges: state.workflow.edges.filter((e) => e.id !== edgeId),
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          selectedEdge: state.selectedEdge === edgeId ? null : state.selectedEdge,
          isDirty: true,
        };
      });

      get().validateWorkflow();
    },

    selectEdge: (edgeId: string | null) => {
      set({ selectedEdge: edgeId, selectedNode: null });
    },

    // Workflow operations
    updateWorkflowConfig: (config: any) => {
      set((state) => {
        if (!state.workflow) return state;
        
        const updated = {
          ...state.workflow,
          config: { ...state.workflow.config, ...config },
          updated_at: new Date().toISOString(),
        };
        
        pushToUndoStack(state.workflow);
        
        return {
          workflow: updated,
          isDirty: true,
        };
      });
    },

    validateWorkflow: () => {
      set((state) => {
        if (!state.workflow) return state;
        
        const validation = validateDAG(state.workflow.nodes, state.workflow.edges);
        
        return { validation };
      });
    },

    // State management
    setError: (error: string | null) => {
      set({ error });
    },

    setSaving: (saving: boolean) => {
      set({ isSaving: saving });
    },

    // Undo/Redo
    undo: () => {
      set((state) => {
        if (undoStack.length === 0 || !state.workflow) return state;
        
        redoStack.push(state.workflow);
        const previous = undoStack.pop();
        
        return {
          workflow: previous,
          isDirty: true,
        };
      });
    },

    redo: () => {
      set((state) => {
        if (redoStack.length === 0 || !state.workflow) return state;
        
        undoStack.push(state.workflow);
        const next = redoStack.pop();
        
        return {
          workflow: next,
          isDirty: true,
        };
      });
    },

    clearHistory: () => {
      undoStack.length = 0;
      redoStack.length = 0;
    },
  };
});
