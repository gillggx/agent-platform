/**
 * Validation Panel Component
 * 
 * Displays validation results, errors, and warnings for the DAG workflow.
 */

import React from 'react';
import { Alert, Empty, Card, Space, Tag } from 'antd';
import { CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useDagStore } from '@/store/dagStore';
import { ValidationError, ValidationWarning } from '@/types/dag';
import './styles/validation-panel.css';

interface ValidationPanelProps {
  compact?: boolean;
}

const ERROR_TYPE_NAMES: Record<string, string> = {
  cycle: '迴圈檢測',
  missing_config: '缺少配置',
  type_mismatch: '類型不匹配',
  missing_edge: '缺少邊界',
};

const WARNING_TYPE_NAMES: Record<string, string> = {
  isolated_node: '孤立節點',
  missing_output: '缺少輸出',
  high_cost: '高成本',
};

export const ValidationPanel: React.FC<ValidationPanelProps> = ({ compact = false }) => {
  const { validation, workflow } = useDagStore();

  if (!workflow) {
    return <Empty description="無工作流" />;
  }

  const { valid, errors, warnings } = validation;

  // Compact view for toolbar
  if (compact) {
    return (
      <Space>
        {valid ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            驗證通過
          </Tag>
        ) : (
          <>
            {errors.length > 0 && (
              <Tag icon={<CloseCircleOutlined />} color="error">
                {errors.length} 個錯誤
              </Tag>
            )}
            {warnings.length > 0 && (
              <Tag icon={<ExclamationCircleOutlined />} color="warning">
                {warnings.length} 個警告
              </Tag>
            )}
          </>
        )}
      </Space>
    );
  }

  // Full view
  return (
    <div className="validation-panel">
      {/* Status banner */}
      {valid ? (
        <Alert
          message="工作流驗證通過"
          description="所有節點和邊界配置正確，可以執行。"
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
        />
      ) : (
        <>
          {errors.length > 0 && (
            <Alert
              message={`發現 ${errors.length} 個錯誤`}
              description="請修復下列問題才能執行工作流。"
              type="error"
              showIcon
              icon={<CloseCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}
          {warnings.length > 0 && !errors.length && (
            <Alert
              message={`發現 ${warnings.length} 個警告`}
              description="工作流可以執行，但建議修復這些問題。"
              type="warning"
              showIcon
              icon={<ExclamationCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}
        </>
      )}

      {/* Errors section */}
      {errors.length > 0 && (
        <Card
          title={`錯誤 (${errors.length})`}
          className="error-card"
          style={{ marginBottom: 16 }}
        >
          <div className="error-list">
            {errors.map((error, idx) => (
              <ErrorItem key={idx} error={error} />
            ))}
          </div>
        </Card>
      )}

      {/* Warnings section */}
      {warnings.length > 0 && (
        <Card
          title={`警告 (${warnings.length})`}
          className="warning-card"
        >
          <div className="warning-list">
            {warnings.map((warning, idx) => (
              <WarningItem key={idx} warning={warning} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

interface ErrorItemProps {
  error: ValidationError;
}

const ErrorItem: React.FC<ErrorItemProps> = ({ error }) => {
  const { selectNode } = useDagStore();

  const handleClick = () => {
    if (error.nodeId) {
      selectNode(error.nodeId);
    }
  };

  return (
    <div className="error-item" onClick={handleClick} style={{ cursor: error.nodeId ? 'pointer' : 'default' }}>
      <Tag color="error">{ERROR_TYPE_NAMES[error.type] || error.type}</Tag>
      <span className="error-message">{error.message}</span>
      {error.nodeId && <span className="error-node-id">節點: {error.nodeId}</span>}
    </div>
  );
};

interface WarningItemProps {
  warning: ValidationWarning;
}

const WarningItem: React.FC<WarningItemProps> = ({ warning }) => {
  const { selectNode } = useDagStore();

  const handleClick = () => {
    if (warning.nodeId) {
      selectNode(warning.nodeId);
    }
  };

  return (
    <div className="warning-item" onClick={handleClick} style={{ cursor: warning.nodeId ? 'pointer' : 'default' }}>
      <Tag color="warning">{WARNING_TYPE_NAMES[warning.type] || warning.type}</Tag>
      <span className="warning-message">{warning.message}</span>
      {warning.nodeId && <span className="warning-node-id">節點: {warning.nodeId}</span>}
    </div>
  );
};

export default ValidationPanel;
