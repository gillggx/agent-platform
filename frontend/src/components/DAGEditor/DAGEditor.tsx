/**
 * DAG Editor Component
 * 
 * Main container component that integrates canvas, toolbar, and side panels.
 */

import React, { useState, useCallback } from 'react';
import { Layout, message } from 'antd';
import { useDagStore } from '@/store/dagStore';
import DAGCanvas from './DAGCanvas';
import Toolbar from './Toolbar';
import NodePanel from './NodePanel';
import EdgeConfigDialog from './EdgeConfigDialog';
import './styles/dag-editor.css';

interface DAGEditorProps {
  workflowId?: string;
  onSave?: (workflow: any) => Promise<void>;
  readOnly?: boolean;
}

export const DAGEditor: React.FC<DAGEditorProps> = ({
  onSave,
  readOnly = false,
}) => {
  const { workflow, setSaving, setError, createWorkflow } = useDagStore();
  const [nodePanelVisible, setNodePanelVisible] = useState(false);
  const [edgeConfigVisible, setEdgeConfigVisible] = useState(false);

  // Initialize workflow if workflowId provided
  React.useEffect(() => {
    if (!workflow) {
      createWorkflow('未命名工作流');
    }
  }, []);

  // Handle node selection
  const handleNodeSelect = useCallback((nodeId: string | null) => {
    if (nodeId) {
      setNodePanelVisible(true);
      setEdgeConfigVisible(false);
    } else {
      setNodePanelVisible(false);
    }
  }, []);

  // Handle edge selection
  const handleEdgeSelect = useCallback((edgeId: string | null) => {
    if (edgeId) {
      setEdgeConfigVisible(true);
      setNodePanelVisible(false);
    } else {
      setEdgeConfigVisible(false);
    }
  }, []);

  // Handle save
  const handleSave = useCallback(async () => {
    if (!workflow) {
      setError('無工作流可保存');
      return;
    }

    setSaving(true);

    try {
      if (onSave) {
        await onSave(workflow);
      }
      message.success('工作流已保存');
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '保存失敗';
      message.error(errorMsg);
      setError(errorMsg);
    } finally {
      setSaving(false);
    }
  }, [workflow, onSave, setSaving, setError]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (readOnly) return;

      // Ctrl+S / Cmd+S: Save
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, readOnly]);

  if (!workflow) {
    return <div className="dag-editor-loading">加載中...</div>;
  }

  return (
    <div className="dag-editor-container">
      <Layout className="dag-editor-layout">
        {/* Toolbar */}
        <Toolbar onSave={handleSave} />

        {/* Main Content */}
        <Layout.Content className="dag-editor-content">
          <div className="dag-editor-main">
            {/* Canvas */}
            <DAGCanvas
              onNodeSelect={handleNodeSelect}
              onEdgeSelect={handleEdgeSelect}
            />
          </div>
        </Layout.Content>
      </Layout>

      {/* Node Edit Panel */}
      <NodePanel
        visible={nodePanelVisible && !readOnly}
        onClose={() => setNodePanelVisible(false)}
      />

      {/* Edge Config Dialog */}
      <EdgeConfigDialog
        visible={edgeConfigVisible && !readOnly}
        onClose={() => setEdgeConfigVisible(false)}
      />
    </div>
  );
};

export default DAGEditor;
