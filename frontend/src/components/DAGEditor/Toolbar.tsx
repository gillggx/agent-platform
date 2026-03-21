/**
 * DAG Editor Toolbar Component
 * 
 * Provides controls for managing nodes, edges, and workflow operations.
 */

import React, { useState } from 'react';
import {
  Button,
  Space,
  Dropdown,
  MenuProps,
  Input,
  Tooltip,
  Modal,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  UndoOutlined,
  RedoOutlined,
  SaveOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useDagStore } from '@/store/dagStore';
import { DAGNode } from '@/types/dag';
import { AgentRole } from '@/types/dag';
import ValidationPanel from './ValidationPanel';
import './styles/toolbar.css';

interface ToolbarProps {
  onAddNode?: (node: DAGNode) => void;
  onSave?: () => void;
}

const AGENT_ROLES: AgentRole[] = [
  'product_manager',
  'architect',
  'qa',
  'devops',
  'director',
];

const ROLE_NAMES: Record<AgentRole, string> = {
  product_manager: '產品經理',
  architect: '架構師',
  qa: 'QA',
  devops: 'DevOps',
  director: '總監',
};

const ROLE_COLORS: Record<AgentRole, string> = {
  product_manager: '#FF6B6B',
  architect: '#4ECDC4',
  qa: '#45B7D1',
  devops: '#FFA07A',
  director: '#98D8C8',
};

export const Toolbar: React.FC<ToolbarProps> = ({ onAddNode, onSave }) => {
  const {
    workflow,
    validation,
    addNode,
    undo,
    redo,
    createWorkflow,
    validateWorkflow,
  } = useDagStore();

  const [workflowName, setWorkflowName] = useState('新工作流');
  const [showNewWorkflowModal, setShowNewWorkflowModal] = useState(false);

  // Add Node Menu
  const addNodeMenuItems: MenuProps['items'] = AGENT_ROLES.map((role) => ({
    key: role,
    label: `添加 ${ROLE_NAMES[role]}`,
    onClick: () => handleAddNode(role),
  }));

  const handleAddNode = (role: AgentRole) => {
    const newNode: DAGNode = {
      id: `node-${Date.now()}`,
      type: 'agent',
      role,
      position: {
        x: Math.random() * 500,
        y: Math.random() * 400,
      },
      data: {
        title: ROLE_NAMES[role],
        color: ROLE_COLORS[role],
        inputs: ['input'],
        outputs: ['output'],
        config: {
          llm_model: 'gpt-4',
          temperature: 0.7,
          max_tokens: 2048,
          top_p: 0.95,
        },
      },
    };

    addNode(newNode);
    onAddNode?.(newNode);
  };

  const handleCreateWorkflow = () => {
    createWorkflow(workflowName);
    setShowNewWorkflowModal(false);
    validateWorkflow();
  };

  const handleExportWorkflow = () => {
    if (!workflow) {
      alert('無工作流可導出');
      return;
    }

    const json = JSON.stringify(workflow, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleValidate = () => {
    validateWorkflow();
    alert(validation.valid ? '工作流驗證通過！' : '工作流驗證失敗，請查看驗證面板。');
  };

  // More menu
  const moreMenuItems: MenuProps['items'] = [
    {
      key: 'export',
      label: '導出工作流',
      icon: <DownloadOutlined />,
      onClick: handleExportWorkflow,
    },
    {
      key: 'validate',
      label: '驗證工作流',
      icon: <CheckCircleOutlined />,
      onClick: handleValidate,
    },
    {
      key: 'new',
      label: '新建工作流',
      icon: <PlusOutlined />,
      onClick: () => setShowNewWorkflowModal(true),
    },
  ];

  return (
    <>
      <div className="dag-toolbar">
        <Space className="toolbar-left">
          {/* Workflow Name */}
          {workflow && (
            <div className="workflow-name">
              <span>{workflow.name}</span>
              <span className="version">{workflow.version}</span>
            </div>
          )}
        </Space>

        <Space className="toolbar-center" split={<Divider type="vertical" />}>
          {/* Node Operations */}
          <Dropdown menu={{ items: addNodeMenuItems }} trigger={['click']}>
            <Button type="primary" icon={<PlusOutlined />}>
              添加節點
            </Button>
          </Dropdown>

          {/* Edit Operations */}
          <Space>
            <Tooltip title="撤銷 (Ctrl+Z)">
              <Button icon={<UndoOutlined />} onClick={undo} />
            </Tooltip>
            <Tooltip title="重做 (Ctrl+Y)">
              <Button icon={<RedoOutlined />} onClick={redo} />
            </Tooltip>
          </Space>

          {/* Validation Status */}
          <ValidationPanel compact={true} />
        </Space>

        <Space className="toolbar-right">
          {/* Save Button */}
          <Tooltip title="保存工作流">
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={onSave}
              loading={false}
            >
              保存
            </Button>
          </Tooltip>

          {/* More Menu */}
          <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
            <Button>更多</Button>
          </Dropdown>
        </Space>
      </div>

      {/* Validation Panel */}
      <div className="toolbar-validation">
        <ValidationPanel />
      </div>

      {/* New Workflow Modal */}
      <Modal
        title="創建新工作流"
        open={showNewWorkflowModal}
        onOk={handleCreateWorkflow}
        onCancel={() => setShowNewWorkflowModal(false)}
      >
        <Input
          placeholder="工作流名稱"
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleCreateWorkflow();
            }
          }}
        />
      </Modal>
    </>
  );
};

export default Toolbar;
