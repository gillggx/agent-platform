import { useState } from 'react'
import { 
  Row, 
  Col, 
  Card, 
  Button, 
  Table, 
  Modal, 
  Form, 
  Input, 
  message, 
  Typography,
  Space,
  Tag,
} from 'antd'
import {
  PlusOutlined,
  ProjectOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, workflowsApi, artifactsApi } from '@/services/api'
import dayjs from 'dayjs'
import type { Project, CreateProjectForm, WorkflowTemplate } from '@/types'

const { Title, Text } = Typography
const { TextArea } = Input

export default function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showStartModal, setShowStartModal] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [form] = Form.useForm()
  const [workflowForm] = Form.useForm()

  // Queries
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.some((p: any) => p.status === 'running')
      return hasRunning ? 3000 : false
    },
  })

  const { data: templates } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: workflowsApi.listTemplates,
  })

  // Mutations
  const createProjectMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      message.success('專案建立成功')
      setShowCreateModal(false)
      form.resetFields()
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '建立專案失敗')
    },
  })

  const deleteProjectMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => {
      message.success('專案已刪除')
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: () => {
      message.error('刪除失敗，請稍後再試')
    },
  })

  const startWorkflowMutation = useMutation({
    mutationFn: workflowsApi.startWorkflow,
    onSuccess: (workflowRun) => {
      message.success('工作流程已啟動')
      setShowStartModal(false)
      workflowForm.resetFields()
      setSelectedTemplateId(null)
      navigate(`/workflows/${workflowRun.id}`)
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '啟動工作流程失敗')
    },
  })

  // Handlers
  const handleCreateProject = (values: CreateProjectForm) => {
    createProjectMutation.mutate(values)
  }

  const handleStartWorkflow = (values: any) => {
    if (!selectedProject || !selectedTemplateId) {
      message.warning('請選擇工作流程模板')
      return
    }
    
    startWorkflowMutation.mutate({
      project_id: selectedProject.id,
      template_id: selectedTemplateId,
      user_input: values.user_input,
    })
  }

  const openStartModal = (project: Project) => {
    setSelectedProject(project)
    setShowStartModal(true)
    setSelectedTemplateId(null)
    workflowForm.resetFields()
  }

  const handleDownloadProject = async (projectId: string, projectName: string) => {
    try {
      const blob = await artifactsApi.downloadProject(projectId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${projectName}_規格文件.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      message.error('下載失敗，請確認文件已產出')
    }
  }

  // Table columns
  const columns = [
    {
      title: '專案名稱',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Project) => (
        <Button 
          type="link" 
          style={{ padding: 0 }}
          onClick={() => navigate(`/projects/${record.id}`)}
        >
          <ProjectOutlined style={{ marginRight: 8 }} />
          {text}
        </Button>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (text: string) => text || <Text type="secondary">無描述</Text>,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          draft: 'default',
          running: 'processing', 
          completed: 'success',
          failed: 'error',
        }
        const labelMap: Record<string, string> = {
          draft: '草稿',
          running: '進行中',
          completed: '已完成',
          failed: '失敗',
        }
        return <Tag color={colorMap[status]}>{labelMap[status] || status}</Tag>
      },
    },
    {
      title: '建立時間',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Project) => (
        <Space wrap size={4}>
          {record.status === 'completed' && (
            <Button
              size="small"
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadProject(record.id, record.name)}
            >
              下載文件
            </Button>
          )}
          {record.latest_run_id && (
            <Button
              size="small"
              onClick={() => navigate(`/workflows/${record.latest_run_id}`)}
            >
              查看執行
            </Button>
          )}
          <Button
            size="small"
            icon={record.status === 'completed' || record.status === 'failed' ? <ReloadOutlined /> : <PlayCircleOutlined />}
            onClick={() => openStartModal(record)}
          >
            {record.status === 'completed' || record.status === 'failed' ? '重跑' : '啟動流程'}
          </Button>
          <Button
            size="small"
            onClick={() => navigate(`/projects/${record.id}`)}
          >
            歷史記錄
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={deleteProjectMutation.isPending}
            onClick={() => {
              Modal.confirm({
                title: '確認刪除',
                content: `確定要刪除專案「${record.name}」嗎？此操作無法復原。`,
                okText: '刪除',
                okType: 'danger',
                cancelText: '取消',
                onOk: () => deleteProjectMutation.mutate(record.id),
              })
            }}
          >
            刪除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>🤖 專案管理</Title>
        <Text type="secondary">
          輸入需求，讓 AI Agent 團隊自動產出規格文件
        </Text>
      </div>

      {/* Stats Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <ProjectOutlined 
                style={{ 
                  fontSize: 24, 
                  color: '#1890ff', 
                  marginRight: 12 
                }} 
              />
              <div>
                <Text type="secondary">總專案數</Text>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {projects?.length || 0}
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <PlayCircleOutlined 
                style={{ 
                  fontSize: 24, 
                  color: '#52c41a', 
                  marginRight: 12 
                }} 
              />
              <div>
                <Text type="secondary">執行中</Text>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {projects?.filter(p => p.status === 'running').length || 0}
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <FileTextOutlined 
                style={{ 
                  fontSize: 24, 
                  color: '#fa8c16', 
                  marginRight: 12 
                }} 
              />
              <div>
                <Text type="secondary">已完成</Text>
                <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                  {projects?.filter(p => p.status === 'completed').length || 0}
                </div>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Projects Table */}
      <Card
        title="專案列表"
        extra={
          <Button 
            type="primary" 
            icon={<PlusOutlined />}
            onClick={() => setShowCreateModal(true)}
          >
            新建專案
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={projectsLoading}
          pagination={false}
          locale={{
            emptyText: '尚無專案，點擊右上角新建專案開始使用',
          }}
        />
      </Card>

      {/* Create Project Modal */}
      <Modal
        title="新建專案"
        open={showCreateModal}
        onCancel={() => {
          setShowCreateModal(false)
          form.resetFields()
        }}
        footer={null}
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateProject}
          style={{ marginTop: 20 }}
        >
          <Form.Item
            name="name"
            label="專案名稱"
            rules={[
              { required: true, message: '請輸入專案名稱' },
              { min: 2, message: '專案名稱至少需要 2 個字符' }
            ]}
          >
            <Input placeholder="輸入專案名稱" />
          </Form.Item>

          <Form.Item
            name="description"
            label="專案描述"
          >
            <TextArea 
              placeholder="描述專案的目標和內容（選填）"
              rows={3}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={createProjectMutation.isPending}
              >
                建立專案
              </Button>
              <Button 
                onClick={() => {
                  setShowCreateModal(false)
                  form.resetFields()
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Start Workflow Modal */}
      <Modal
        title={`啟動工作流程 - ${selectedProject?.name}`}
        open={showStartModal}
        onCancel={() => {
          setShowStartModal(false)
          workflowForm.resetFields()
          setSelectedTemplateId(null)
        }}
        footer={null}
        width={600}
      >
        <Form
          form={workflowForm}
          layout="vertical"
          onFinish={handleStartWorkflow}
          style={{ marginTop: 20 }}
        >
          <Form.Item
            label="選擇工作流程模板"
            required
          >
            <div style={{ display: 'grid', gap: '12px' }}>
              {templates?.map((template: WorkflowTemplate) => (
                <Card 
                  key={template.id}
                  size="small"
                  hoverable
                  style={{ 
                    cursor: 'pointer',
                    border: selectedTemplateId === template.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                  }}
                  onClick={() => setSelectedTemplateId(template.id)}
                >
                  <div>
                    <Text strong>{template.name}</Text>
                    {template.is_system && <Tag color="blue" style={{ marginLeft: 8 }}>系統模板</Tag>}
                    <br />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {template.description}
                    </Text>
                  </div>
                </Card>
              ))}
            </div>
          </Form.Item>

          <Form.Item
            name="user_input"
            label="需求描述"
            rules={[
              { required: true, message: '請輸入需求描述' },
              { min: 10, message: '需求描述至少需要 10 個字符' }
            ]}
          >
            <TextArea 
              placeholder="請詳細描述您的需求，例如：我要做一個設備監控 dashboard，包含即時數據顯示、告警功能..."
              rows={4}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={startWorkflowMutation.isPending}
                icon={<PlayCircleOutlined />}
                disabled={!selectedTemplateId}
              >
                啟動工作流程
              </Button>
              <Button 
                onClick={() => {
                  setShowStartModal(false)
                  workflowForm.resetFields()
                  setSelectedTemplateId(null)
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
