import { useParams, useNavigate } from 'react-router-dom'
import { Card, Typography, Spin, Alert, Button, Tag, Space, Table } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { projectsApi } from '@/services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography

const STATUS_COLOR: Record<string, string> = {
  running: 'processing', completed: 'success', failed: 'error',
  waiting_approval: 'warning', timeout: 'warning', draft: 'default',
}
const STATUS_TEXT: Record<string, string> = {
  running: '執行中', completed: '已完成', failed: '執行失敗',
  waiting_approval: '等待審批', timeout: '執行超時', draft: '草稿',
}

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => projectsApi.get(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.workflow_runs?.some((r: any) => r.status === 'running' || r.status === 'waiting_approval')
      return hasRunning ? 3000 : false
    },
  })

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" /></div>
  }

  if (error || !project) {
    return <Alert message="專案載入失敗" description="無法載入專案資訊，請稍後再試" type="error" showIcon />
  }

  const columns = [
    {
      title: '執行 ID',
      dataIndex: 'id',
      key: 'id',
      render: (runId: string) => (
        <Button type="link" style={{ padding: 0, fontFamily: 'monospace', fontSize: 13 }}
          onClick={() => navigate(`/workflows/${runId}`)}>
          {runId.slice(0, 8)}…
        </Button>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={STATUS_COLOR[s] ?? 'default'}>{STATUS_TEXT[s] ?? s}</Tag>,
    },
    {
      title: '需求描述',
      dataIndex: 'user_input',
      key: 'user_input',
      ellipsis: true,
      render: (text: string) => <Text type="secondary" style={{ fontSize: 13 }}>{text}</Text>,
    },
    {
      title: '開始時間',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '',
      key: 'action',
      render: (_: unknown, record: any) => (
        <Button size="small" type="primary" onClick={() => navigate(`/workflows/${record.id}`)}>
          查看執行
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={2} style={{ marginBottom: 4 }}>{project.name}</Title>
        <Space>
          <Tag color={STATUS_COLOR[project.status] ?? 'default'}>{STATUS_TEXT[project.status] ?? project.status}</Tag>
          {project.description && <Text type="secondary">{project.description}</Text>}
          <Text type="secondary" style={{ fontSize: 12 }}>建立於 {dayjs(project.created_at).format('YYYY-MM-DD HH:mm')}</Text>
        </Space>
      </div>

      <Card title={`工作流程執行記錄（共 ${project.workflow_runs?.length ?? 0} 次）`}>
        {project.workflow_runs?.length > 0 ? (
          <Table
            columns={columns}
            dataSource={project.workflow_runs}
            rowKey="id"
            pagination={false}
            size="small"
            onRow={(record) => ({ onClick: () => navigate(`/workflows/${record.id}`), style: { cursor: 'pointer' } })}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#aaa' }}>
            尚未有工作流程執行記錄
          </div>
        )}
      </Card>
    </div>
  )
}
