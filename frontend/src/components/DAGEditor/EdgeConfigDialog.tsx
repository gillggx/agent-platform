/**
 * Edge Config Dialog Component
 * 
 * Dialog for configuring edge properties and data types.
 */

import React, { useMemo } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Button,
  Space,
  Divider,
} from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useDagStore } from '@/store/dagStore';
import { DAGEdge as DAGEdgeType } from '@/types/dag';
import './styles/edge-config.css';

interface EdgeConfigDialogProps {
  visible: boolean;
  onClose: () => void;
}

const DATA_TYPES = [
  'text',
  'json',
  'file',
  'image',
  'number',
  'boolean',
  'array',
  'object',
];

export const EdgeConfigDialog: React.FC<EdgeConfigDialogProps> = ({
  visible,
  onClose,
}) => {
  const { workflow, selectedEdge, updateEdge, removeEdge } = useDagStore();
  const [form] = Form.useForm();

  const currentEdge = useMemo(() => {
    if (!workflow || !selectedEdge) return null;
    return workflow.edges.find((e) => e.id === selectedEdge);
  }, [workflow, selectedEdge]);

  React.useEffect(() => {
    if (currentEdge && visible) {
      form.setFieldsValue({
        label: currentEdge.data?.label || '',
        type: currentEdge.data?.type || 'data',
        format: currentEdge.data?.format || 'json',
        validation: currentEdge.data?.validation ?? false,
      });
    } else {
      form.resetFields();
    }
  }, [currentEdge, visible, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      if (!currentEdge) return;

      const updated: DAGEdgeType = {
        ...currentEdge,
        data: {
          ...currentEdge.data,
          label: values.label,
          type: values.type,
          format: values.format,
          validation: values.validation,
        },
      };

      updateEdge(updated);
      onClose();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleDelete = () => {
    if (currentEdge && window.confirm('確定要刪除這條邊界嗎?')) {
      removeEdge(currentEdge.id);
      onClose();
    }
  };

  return (
    <Modal
      title="編輯邊界配置"
      open={visible}
      onOk={handleSave}
      onCancel={onClose}
      width={500}
      className="edge-config-modal"
    >
      {currentEdge ? (
        <Form form={form} layout="vertical" autoComplete="off">
          {/* Edge ID */}
          <Form.Item label="邊界 ID">
            <Input value={currentEdge.id} disabled />
          </Form.Item>

          {/* Source & Target */}
          <Form.Item label="連接">
            <Input
              value={`${currentEdge.source} → ${currentEdge.target}`}
              disabled
            />
          </Form.Item>

          <Divider>數據配置</Divider>

          {/* Label */}
          <Form.Item
            label="標籤"
            name="label"
            rules={[{ required: true, message: '請輸入標籤' }]}
          >
            <Input placeholder="如：文本輸出" />
          </Form.Item>

          {/* Type */}
          <Form.Item
            label="數據類型"
            name="type"
            rules={[{ required: true, message: '請選擇數據類型' }]}
          >
            <Select placeholder="選擇數據類型">
              <Select.Option value="data">數據</Select.Option>
              <Select.Option value="control">控制流</Select.Option>
              <Select.Option value="feedback">反饋</Select.Option>
            </Select>
          </Form.Item>

          {/* Format */}
          <Form.Item
            label="格式"
            name="format"
            rules={[{ required: true, message: '請選擇格式' }]}
          >
            <Select placeholder="選擇數據格式">
              {DATA_TYPES.map((type) => (
                <Select.Option key={type} value={type}>
                  {type.toUpperCase()}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          {/* Validation */}
          <Form.Item label="啟用驗證" name="validation" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Divider>操作</Divider>

          {/* Delete Button */}
          <Space style={{ width: '100%' }}>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              style={{ flex: 1 }}
            >
              刪除邊界
            </Button>
          </Space>
        </Form>
      ) : (
        <div className="empty-state">未選擇邊界</div>
      )}
    </Modal>
  );
};

export default EdgeConfigDialog;
