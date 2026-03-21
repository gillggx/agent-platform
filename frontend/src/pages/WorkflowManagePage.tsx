import {
  Button, Table, Tag, Space, Typography, Popconfirm, message, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, CopyOutlined, DeleteOutlined, ApartmentOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { workflowsApi } from '@/services/api'
import type { WorkflowTemplate } from '@/types'

const { Title, Paragraph, Text } = Typography

function stepCount(template: WorkflowTemplate): number {
  try {
    const steps = (template.definition as any)?.workflow?.steps
    return Array.isArray(steps) ? steps.length : 0
  } catch {
    return 0
  }
}

export default function WorkflowManagePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: workflowsApi.listTemplates,
  })

  const cloneMutation = useMutation({
    mutationFn: workflowsApi.cloneTemplate,
    onSuccess: (cloned) => {
      message.success(`已複製為「${cloned.name}」`)
      queryClient.invalidateQueries({ queryKey: ['workflow-templates'] })
    },
    onError: () => message.error('複製失敗'),
  })

  const deleteMutation = useMutation({
    mutationFn: workflowsApi.deleteTemplate,
    onSuccess: () => {
      message.success('流程已刪除')
      queryClient.invalidateQueries({ queryKey: ['workflow-templates'] })
    },
    onError: (err: any) => message.error(err.response?.data?.detail || '刪除失敗'),
  })

  const columns = [
    {
      title: '名稱',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: WorkflowTemplate) => (
        <Space>
          <ApartmentOutlined style={{ color: '#1677ff' }} />
          <Text strong>{name}</Text>
          {record.is_system && <Tag color="blue" style={{ fontSize: 10 }}>系統</Tag>}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => <Text type="secondary">{desc || '—'}</Text>,
    },
    {
      title: '步驟數',
      key: 'steps',
      width: 80,
      align: 'center' as const,
      render: (_: any, record: WorkflowTemplate) => {
        const count = stepCount(record)
        return count > 0 ? <Tag>{count} 步</Tag> : <Text type="secondary">—</Text>
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      render: (_: any, record: WorkflowTemplate) => (
        <Space size="small">
          {!record.is_system && (
            <Tooltip title="編輯流程">
              <Button
                size="small"
                icon={<EditOutlined />}
                onClick={() => navigate(`/workflow-editor/${record.id}`)}
              />
            </Tooltip>
          )}
          <Tooltip title="複製為自訂流程">
            <Button
              size="small"
              icon={<CopyOutlined />}
              loading={cloneMutation.isPending}
              onClick={() => cloneMutation.mutate(record.id)}
            />
          </Tooltip>
          {!record.is_system && (
            <Popconfirm
              title="確定刪除此流程？"
              description="此操作無法復原。"
              onConfirm={() => deleteMutation.mutate(record.id)}
              okText="刪除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="刪除">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteMutation.isPending}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const systemTemplates = templates.filter((t) => t.is_system)
  const customTemplates = templates.filter((t) => !t.is_system)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>流程管理</Title>
          <Paragraph type="secondary" style={{ marginTop: 8 }}>
            管理工作流程模板。系統模板為唯讀，可複製為自訂流程後修改。
          </Paragraph>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/workflow-editor')}
        >
          新建流程
        </Button>
      </div>

      {systemTemplates.length > 0 && (
        <>
          <Title level={5} style={{ color: '#666', marginBottom: 8 }}>系統流程</Title>
          <Table
            dataSource={systemTemplates}
            columns={columns}
            rowKey="id"
            loading={isLoading}
            pagination={false}
            size="middle"
            style={{ marginBottom: 32 }}
          />
        </>
      )}

      <Title level={5} style={{ color: '#666', marginBottom: 8 }}>自訂流程</Title>
      <Table
        dataSource={customTemplates}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        size="middle"
        locale={{ emptyText: '尚無自訂流程，可從系統流程複製或新建' }}
      />
    </div>
  )
}
