/**
 * Node Panel Component
 * 
 * Side panel for editing selected node properties.
 */

import React, { useMemo } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Drawer,
  Space,
  Divider,
  Tag,
} from 'antd';
import { DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import { useDagStore } from '@/store/dagStore';
import { DAGNode as DAGNodeType, AgentRole } from '@/types/dag';
import './styles/node-panel.css';

interface NodePanelProps {
  visible: boolean;
  onClose: () => void;
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

export const NodePanel: React.FC<NodePanelProps> = ({ visible, onClose }) => {
  const { workflow, selectedNode, updateNode, removeNode } = useDagStore();
  const [form] = Form.useForm();

  const currentNode = useMemo(() => {
    if (!workflow || !selectedNode) return null;
    return workflow.nodes.find((n) => n.id === selectedNode);
  }, [workflow, selectedNode]);

  // Populate form when node changes
  React.useEffect(() => {
    if (currentNode) {
      form.setFieldsValue({
        title: currentNode.data.title,
        role: currentNode.role,
        llm_model: currentNode.data.config.llm_model,
        temperature: currentNode.data.config.temperature,
        max_tokens: currentNode.data.config.max_tokens,
        top_p: currentNode.data.config.top_p,
        system_prompt: currentNode.data.config.system_prompt,
      });
    } else {
      form.resetFields();
    }
  }, [currentNode, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      if (!currentNode) return;

      const updated: DAGNodeType = {
        ...currentNode,
        data: {
          ...currentNode.data,
          title: values.title,
          config: {
            ...currentNode.data.config,
            llm_model: values.llm_model,
            temperature: values.temperature,
            max_tokens: values.max_tokens,
            top_p: values.top_p,
            system_prompt: values.system_prompt,
          },
        },
        role: values.role,
      };

      updateNode(updated);
      onClose();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleDelete = () => {
    if (currentNode && window.confirm(`確定要刪除節點「${currentNode.data.title}」嗎?`)) {
      removeNode(currentNode.id);
      onClose();
    }
  };

  return (
    <Drawer
      title="編輯節點屬性"
      placement="right"
      onClose={onClose}
      open={visible}
      width={380}
      className="node-panel-drawer"
    >
      {currentNode ? (
        <Form form={form} layout="vertical" autoComplete="off">
          {/* Node ID */}
          <Form.Item label="節點 ID">
            <Input value={currentNode.id} disabled />
          </Form.Item>

          {/* Title */}
          <Form.Item
            label="節點標題"
            name="title"
            rules={[{ required: true, message: '請輸入節點標題' }]}
          >
            <Input placeholder="如：數據提取" />
          </Form.Item>

          {/* Role */}
          <Form.Item
            label="Agent 角色"
            name="role"
            rules={[{ required: true, message: '請選擇角色' }]}
          >
            <Select placeholder="選擇角色">
              {AGENT_ROLES.map((role) => (
                <Select.Option key={role} value={role}>
                  {ROLE_NAMES[role]}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Divider>LLM 配置</Divider>

          {/* LLM Model */}
          <Form.Item
            label="模型"
            name="llm_model"
            rules={[{ required: true, message: '請選擇 LLM 模型' }]}
          >
            <Select placeholder="選擇 LLM 模型">
              <Select.Option value="gpt-4">GPT-4</Select.Option>
              <Select.Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Select.Option>
              <Select.Option value="claude-3-opus">Claude 3 Opus</Select.Option>
              <Select.Option value="claude-3-sonnet">Claude 3 Sonnet</Select.Option>
              <Select.Option value="gemini-pro">Gemini Pro</Select.Option>
            </Select>
          </Form.Item>

          {/* Temperature */}
          <Form.Item
            label="Temperature (0-2)"
            name="temperature"
            rules={[
              { required: true, message: '請設定 temperature' },
              { type: 'number', min: 0, max: 2, message: 'Temperature 必須在 0-2 之間' },
            ]}
          >
            <InputNumber min={0} max={2} step={0.1} />
          </Form.Item>

          {/* Max Tokens */}
          <Form.Item
            label="Max Tokens"
            name="max_tokens"
            rules={[
              { required: true, message: '請設定 max_tokens' },
              { type: 'number', min: 100, message: 'Max tokens 最少 100' },
            ]}
          >
            <InputNumber min={100} step={100} placeholder="2048" />
          </Form.Item>

          {/* Top P */}
          <Form.Item
            label="Top P (0-1)"
            name="top_p"
            rules={[{ type: 'number', min: 0, max: 1, message: 'Top P 必須在 0-1 之間' }]}
          >
            <InputNumber min={0} max={1} step={0.05} />
          </Form.Item>

          {/* System Prompt */}
          <Form.Item label="系統提示詞" name="system_prompt">
            <Input.TextArea rows={3} placeholder="輸入系統提示詞..." />
          </Form.Item>

          <Divider>輸入/輸出</Divider>

          {/* Inputs */}
          <Form.Item label="輸入">
            <div className="io-list">
              {currentNode.data.inputs.length > 0 ? (
                currentNode.data.inputs.map((input, idx) => (
                  <Tag key={idx} color="blue">
                    {input}
                  </Tag>
                ))
              ) : (
                <span className="empty-state">無輸入接口</span>
              )}
            </div>
          </Form.Item>

          {/* Outputs */}
          <Form.Item label="輸出">
            <div className="io-list">
              {currentNode.data.outputs.length > 0 ? (
                currentNode.data.outputs.map((output, idx) => (
                  <Tag key={idx} color="green">
                    {output}
                  </Tag>
                ))
              ) : (
                <span className="empty-state">無輸出接口</span>
              )}
            </div>
          </Form.Item>

          {/* Actions */}
          <Space style={{ width: '100%', marginTop: 24 }}>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSave}
              style={{ flex: 1 }}
            >
              保存
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              style={{ flex: 1 }}
            >
              刪除
            </Button>
          </Space>
        </Form>
      ) : (
        <div className="empty-state">未選擇節點</div>
      )}
    </Drawer>
  );
};

export default NodePanel;
