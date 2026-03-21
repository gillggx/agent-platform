import { useState } from 'react'
import {
  Button, Modal, Form, Input, Tag, Typography, Tooltip,
  Space, Divider,
} from 'antd'
import {
  PlusOutlined, ProjectOutlined, SettingOutlined,
  FolderOpenOutlined, ApartmentOutlined, SyncOutlined, BranchesOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { projectsApi, workflowsApi } from '@/services/api'
import type { Project, WorkflowTemplate, CreateProjectForm } from '@/types'
import { message, Radio } from 'antd'

const { Text } = Typography
const { TextArea } = Input

const STATUS_COLOR: Record<string, string> = {
  draft: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  waiting_approval: 'warning',
}

const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  running: '進行中',
  completed: '完成',
  failed: '失敗',
  waiting_approval: '待審批',
}

interface Props {
  projects: Project[]
  templates: WorkflowTemplate[]
  projectsLoading: boolean
}

export default function ProjectSidebar({ projects, templates, projectsLoading }: Props) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showStartModal, setShowStartModal] = useState(false)
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [projectMode, setProjectMode] = useState<'new' | 'existing'>('new')
  const [createForm] = Form.useForm()
  const [workflowForm] = Form.useForm()

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      message.success('專案建立成功')
      setShowCreateModal(false)
      setProjectMode('new')
      createForm.resetFields()
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
    onError: (err: any) => message.error(err.response?.data?.detail || '建立失敗'),
  })

  const wakeArchitectMutation = useMutation({
    mutationFn: (id: string) => projectsApi.wakeArchitect(id),
    onSuccess: () => message.success('Code Architect 已觸發重新分析'),
    onError: () => message.error('無法連接 Code Architect'),
  })

  const startWorkflowMutation = useMutation({
    mutationFn: workflowsApi.startWorkflow,
    onSuccess: (run) => {
      message.success('工作流程已啟動')
      setShowStartModal(false)
      workflowForm.resetFields()
      setSelectedTemplateId(null)
      navigate(`/workflows/${run.id}`)
    },
    onError: (err: any) => message.error(err.response?.data?.detail || '啟動失敗'),
  })

  const openStartModal = (project: Project, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedProject(project)
    setSelectedTemplateId(null)
    workflowForm.resetFields()
    setShowStartModal(true)
  }

  return (
    <>
      <div style={{
        width: 260,
        minWidth: 260,
        height: '100vh',
        borderRight: '1px solid #f0f0f0',
        display: 'flex',
        flexDirection: 'column',
        background: '#fafafa',
        overflow: 'hidden',
      }}>
        {/* Logo */}
        <div style={{ padding: '20px 16px 12px', borderBottom: '1px solid #f0f0f0' }}>
          <Text strong style={{ fontSize: 16 }}>🤖 Agent Platform</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 11 }}>PM Co-pilot</Text>
        </div>

        {/* New Project */}
        <div style={{ padding: '12px 16px' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => setShowCreateModal(true)}
          >
            新建專案
          </Button>
        </div>

        <Divider style={{ margin: '0 16px', width: 'auto', minWidth: 'auto' }} />

        {/* Project List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          <Text type="secondary" style={{ fontSize: 11, padding: '4px 16px', display: 'block' }}>
            專案
          </Text>

          {projectsLoading && (
            <div style={{ padding: '8px 16px' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>載入中...</Text>
            </div>
          )}

          {projects.map((project) => (
            <div
              key={project.id}
              style={{
                padding: '8px 16px',
                cursor: 'pointer',
                borderRadius: 6,
                margin: '2px 8px',
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ProjectOutlined style={{ color: '#1677ff', flexShrink: 0 }} />
                    <Text
                      ellipsis
                      style={{ fontSize: 13, fontWeight: 500 }}
                    >
                      {project.name}
                    </Text>
                    {project.codebase_path && (
                      <Tooltip title={project.codebase_path}>
                        <ApartmentOutlined style={{ color: '#722ed1', fontSize: 11, flexShrink: 0 }} />
                      </Tooltip>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                    <Tag
                      color={STATUS_COLOR[project.status] || 'default'}
                      style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
                    >
                      {STATUS_LABEL[project.status] || project.status}
                    </Tag>
                  </div>
                </div>

                {/* Actions */}
                <Space size={2} onClick={(e) => e.stopPropagation()}>
                  {project.codebase_path && (
                    <Tooltip title="重新分析程式碼">
                      <Button
                        size="small"
                        type="text"
                        icon={<SyncOutlined />}
                        loading={wakeArchitectMutation.isPending}
                        onClick={() => wakeArchitectMutation.mutate(project.id)}
                      />
                    </Tooltip>
                  )}
                  <Tooltip title="查看執行記錄">
                    <Button
                      size="small"
                      type="text"
                      icon={<FolderOpenOutlined />}
                      onClick={() => navigate(`/projects/${project.id}`)}
                    />
                  </Tooltip>
                  <Tooltip title="啟動工作流程">
                    <Button
                      size="small"
                      type="text"
                      icon={<ApartmentOutlined />}
                      onClick={(e) => openStartModal(project, e)}
                    />
                  </Tooltip>
                </Space>
              </div>
            </div>
          ))}

          {!projectsLoading && projects.length === 0 && (
            <div style={{ padding: '16px', textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                還沒有專案，點擊新建專案開始
              </Text>
            </div>
          )}
        </div>

        {/* Bottom Links */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #f0f0f0' }}>
          <Button
            type="text"
            icon={<BranchesOutlined />}
            block
            style={{ textAlign: 'left', color: '#666', marginBottom: 4 }}
            onClick={() => navigate('/workflows/manage')}
          >
            流程管理
          </Button>
          <Button
            type="text"
            icon={<SettingOutlined />}
            block
            style={{ textAlign: 'left', color: '#666' }}
            onClick={() => navigate('/agents')}
          >
            Agent 設定
          </Button>
        </div>
      </div>

      {/* Create Project Modal */}
      <Modal
        title="新建專案"
        open={showCreateModal}
        onCancel={() => {
          setShowCreateModal(false)
          setProjectMode('new')
          createForm.resetFields()
        }}
        footer={null}
        width={520}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={(values: CreateProjectForm) => createMutation.mutate(values)}
          style={{ marginTop: 20 }}
        >
          <Form.Item label="專案類型" required>
            <Radio.Group
              value={projectMode}
              onChange={(e) => {
                setProjectMode(e.target.value)
                createForm.setFieldValue('codebase_path', undefined)
              }}
            >
              <Radio.Button value="new">✨ 全新專案</Radio.Button>
              <Radio.Button value="existing">
                <FolderOpenOutlined /> 現有程式碼庫
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          {projectMode === 'existing' && (
            <Form.Item
              name="codebase_path"
              label="程式碼路徑"
              extra="本機絕對路徑，Code Architect 將自動分析"
              rules={[{ required: true, message: '請輸入程式碼路徑' }]}
            >
              <Input
                prefix={<FolderOpenOutlined />}
                placeholder="/Users/yourname/projects/my-app"
              />
            </Form.Item>
          )}

          <Form.Item
            name="name"
            label="專案名稱"
            rules={[
              { required: true, message: '請輸入專案名稱' },
              { min: 2, message: '至少 2 個字符' },
            ]}
          >
            <Input placeholder="輸入專案名稱" />
          </Form.Item>

          <Form.Item name="description" label="專案描述">
            <TextArea placeholder="描述專案目標（選填）" rows={3} />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                建立專案
              </Button>
              <Button onClick={() => { setShowCreateModal(false); createForm.resetFields() }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Start Workflow Modal */}
      <Modal
        title={`啟動工作流程 — ${selectedProject?.name}`}
        open={showStartModal}
        onCancel={() => {
          setShowStartModal(false)
          workflowForm.resetFields()
          setSelectedTemplateId(null)
        }}
        footer={null}
        width={580}
      >
        <Form
          form={workflowForm}
          layout="vertical"
          onFinish={(values) => {
            if (!selectedProject || !selectedTemplateId) {
              message.warning('請選擇工作流程模板')
              return
            }
            startWorkflowMutation.mutate({
              project_id: selectedProject.id,
              template_id: selectedTemplateId,
              user_input: values.user_input,
            })
          }}
          style={{ marginTop: 20 }}
        >
          <Form.Item label="選擇工作流程模板" required>
            <div style={{ display: 'grid', gap: 8 }}>
              {templates.map((t) => (
                <div
                  key={t.id}
                  style={{
                    padding: '10px 14px',
                    border: selectedTemplateId === t.id ? '2px solid #1677ff' : '1px solid #d9d9d9',
                    borderRadius: 8,
                    cursor: 'pointer',
                    background: selectedTemplateId === t.id ? '#f0f7ff' : '#fff',
                  }}
                  onClick={() => setSelectedTemplateId(t.id)}
                >
                  <Text strong style={{ fontSize: 13 }}>{t.name}</Text>
                  {t.is_system && <Tag color="blue" style={{ marginLeft: 8, fontSize: 10 }}>系統</Tag>}
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>{t.description}</Text>
                </div>
              ))}
            </div>
          </Form.Item>

          <Form.Item
            name="user_input"
            label="需求描述"
            rules={[
              { required: true, message: '請輸入需求描述' },
              { min: 10, message: '至少 10 個字符' },
            ]}
          >
            <TextArea
              placeholder="請描述這次的需求..."
              rows={4}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={startWorkflowMutation.isPending}
                disabled={!selectedTemplateId}
              >
                啟動工作流程
              </Button>
              <Button onClick={() => { setShowStartModal(false); setSelectedTemplateId(null) }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
