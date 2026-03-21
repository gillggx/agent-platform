/**
 * Agent Node Component
 * 
 * Custom React Flow node for displaying agent nodes in the DAG editor.
 */

import React from 'react';
import { Handle, Position } from 'reactflow';
import { Badge } from 'antd';
import './styles/agent-node.css';

interface AgentNodeProps {
  data: {
    label: string;
    role?: string;
    color?: string;
    inputs?: string[];
    outputs?: string[];
    config?: any;
  };
  isConnecting?: boolean;
  selected?: boolean;
}

const ROLE_COLORS: Record<string, string> = {
  product_manager: '#FF6B6B',
  architect: '#4ECDC4',
  qa: '#45B7D1',
  devops: '#FFA07A',
  director: '#98D8C8',
};

export const AgentNode: React.FC<AgentNodeProps> = ({
  data,
  isConnecting,
  selected,
}) => {
  const role = data.role || 'unknown';
  const roleColor = ROLE_COLORS[role] || '#1890ff';

  return (
    <div
      className={`agent-node ${selected ? 'selected' : ''} ${isConnecting ? 'connecting' : ''}`}
      style={{ borderColor: roleColor }}
    >
      {/* Input handles for incoming edges */}
      {(data.inputs || []).map((input, idx) => (
        <Handle
          key={`input-${idx}`}
          type="target"
          position={Position.Top}
          id={`${data.label}-input-${idx}`}
          style={{
            top: `${10 + idx * 20}px`,
            background: roleColor,
          }}
          title={input}
        />
      ))}

      {/* Node content */}
      <div className="agent-node-content">
        <Badge
          count={role}
          style={{
            backgroundColor: roleColor,
            fontSize: '10px',
            padding: '0 4px',
          }}
        />
        <div className="agent-node-title">{data.label}</div>
        <div className="agent-node-meta">
          {data.config?.llm_model && (
            <span className="meta-item">{data.config.llm_model}</span>
          )}
        </div>
      </div>

      {/* Output handles for outgoing edges */}
      {(data.outputs || []).map((output, idx) => (
        <Handle
          key={`output-${idx}`}
          type="source"
          position={Position.Bottom}
          id={`${data.label}-output-${idx}`}
          style={{
            bottom: `${10 + idx * 20}px`,
            background: roleColor,
          }}
          title={output}
        />
      ))}
    </div>
  );
};

export default AgentNode;
