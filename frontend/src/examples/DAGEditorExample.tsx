/**
 * DAG Editor Usage Example
 * 
 * Demonstrates how to integrate and use the DAG Editor component.
 */

import React from 'react';
import { message } from 'antd';
import DAGEditor from '@/components/DAGEditor/DAGEditor';
import { useDagStore } from '@/store/dagStore';

/**
 * Simple example page showing DAG Editor
 */
export const DAGEditorExample: React.FC = () => {
  const { workflow } = useDagStore();

  const handleSave = async (wf: any) => {
    console.log('Saving workflow:', wf);
    // In real app, send to API
    return new Promise((resolve) => {
      setTimeout(() => {
        message.success('Workflow saved successfully');
        resolve(undefined);
      }, 1000);
    });
  };

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <DAGEditor
        onSave={handleSave}
      />
      {workflow && (
        <div style={{ position: 'fixed', bottom: 20, right: 20, background: '#fff', padding: '12px 16px', borderRadius: '4px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', maxWidth: '300px', maxHeight: '200px', overflow: 'auto' }}>
          <strong>當前工作流</strong>
          <pre style={{ fontSize: '12px', marginTop: '8px' }}>
            {JSON.stringify({ id: workflow.id, nodes: workflow.nodes.length, edges: workflow.edges.length }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default DAGEditorExample;
