import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Card,
  Typography,
  Spin,
  Alert,
  Tag,
  Button,
  Modal,
  Input,
  Space,
  Divider,
  message,
  Steps,
} from 'antd'
import {
  CheckCircleOutlined,
  LoadingOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  UserOutlined,
  UpOutlined,
  DownOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { workflowsApi, artifactsApi } from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input

const AGENT_COLOR: Record<string, string> = {
  pm: 'blue', architect: 'purple', qa: 'green', devops: 'orange', director: 'volcano', system: 'default',
}
const AGENT_EMOJI: Record<string, string> = {
  pm: '📋', architect: '🏗️', qa: '🧪', devops: '🚀', director: '🎯', system: '⚙️',
}
const AGENT_LABEL: Record<string, string> = {
  pm: 'PM', architect: 'Architect', qa: 'QA', devops: 'DevOps', director: 'Director', system: 'System',
}
const TASK_LABEL: Record<string, string> = {
  draft: '起草', review: '審核', revise: '修改', approve: '批准', export: '匯出',
}
const ARTIFACT_TYPE_LABEL: Record<string, string> = {
  product_spec: '產品規格', tech_design: '技術設計', deployment_plan: '部署方案',
  qa_checklist: 'QA 清單', review_report: '審核報告', document: '文件',
}

const fadeInStyle = `
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .artifact-appear { animation: fadeInUp 0.4s ease; }
`

function MarkdownView({ content }: { content: string }) {
  return (
    <div style={{ fontSize: '14px', lineHeight: '1.8', color: '#333', padding: '4px 0' }}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => <h1 style={{ fontSize: '20px', fontWeight: 700, borderBottom: '2px solid #e8e8e8', paddingBottom: 8, marginBottom: 16 }}>{children}</h1>,
          h2: ({ children }) => <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#1890ff', marginTop: 20, marginBottom: 10 }}>{children}</h2>,
          h3: ({ children }) => <h3 style={{ fontSize: '14px', fontWeight: 600, marginTop: 14, marginBottom: 6 }}>{children}</h3>,
          p: ({ children }) => <p style={{ marginBottom: 10 }}>{children}</p>,
          ul: ({ children }) => <ul style={{ paddingLeft: 20, marginBottom: 10 }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ paddingLeft: 20, marginBottom: 10 }}>{children}</ol>,
          li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
          strong: ({ children }) => <strong style={{ color: '#262626' }}>{children}</strong>,
          code: ({ children }) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 3, fontFamily: 'monospace', fontSize: '13px' }}>{children}</code>,
          blockquote: ({ children }) => <blockquote style={{ borderLeft: '4px solid #1890ff', paddingLeft: 12, color: '#666', margin: '10px 0' }}>{children}</blockquote>,
          table: ({ children }) => <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 12 }}>{children}</table>,
          th: ({ children }) => <th style={{ border: '1px solid #e8e8e8', padding: '6px 12px', background: '#fafafa', textAlign: 'left' }}>{children}</th>,
          td: ({ children }) => <td style={{ border: '1px solid #e8e8e8', padding: '6px 12px' }}>{children}</td>,
          hr: () => <hr style={{ border: 'none', borderTop: '1px solid #e8e8e8', margin: '16px 0' }} />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function StepCard({
  step, exec, isActive, isCompleted, isFailed, isWaiting, onDownload,
}: {
  step: any; exec: any; isActive: boolean; isCompleted: boolean; isFailed: boolean
  isWaiting: boolean; onDownload: (id: string, name: string) => void
}) {
  // Auto-expand: running steps and completed steps with output are open by default
  // User can manually toggle to collapse/expand
  const artifactId: string | undefined = exec?.artifact_id
  const hasOutput = !!artifactId
  const isExportStep = step.agent_role === 'system' || step.task_type === 'export'

  const [collapsed, setCollapsed] = useState(false)
  const shouldShowBody = !collapsed && (isActive || (isCompleted && hasOutput && !isExportStep))

  const { data: artifactDetail } = useQuery({
    queryKey: ['artifact-detail', artifactId],
    queryFn: () => artifactsApi.get(artifactId!),
    enabled: !!artifactId && isCompleted,
    staleTime: Infinity,
  })

  let borderColor = '#d9d9d9'
  let statusText = '等待中'
  let statusBadgeColor = '#aaa'
  if (isCompleted && !isWaiting) { borderColor = '#52c41a'; statusText = '已完成'; statusBadgeColor = '#52c41a' }
  else if (isActive) { borderColor = '#1890ff'; statusText = '執行中'; statusBadgeColor = '#1890ff' }
  else if (isWaiting) { borderColor = '#faad14'; statusText = '等待審批'; statusBadgeColor = '#faad14' }
  else if (isFailed) { borderColor = '#ff4d4f'; statusText = '執行失敗'; statusBadgeColor = '#ff4d4f' }

  const isDimmed = !isActive && !isCompleted && !isFailed && !isWaiting

  return (
    <Card
      size="small"
      style={{ marginBottom: 12, borderLeft: `4px solid ${borderColor}`, opacity: isDimmed ? 0.45 : 1, transition: 'opacity 0.3s' }}
      styles={{ body: { padding: 0 } }}
    >
      {/* Header row — always visible, click to collapse */}
      <div
        style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, cursor: hasOutput && isCompleted ? 'pointer' : 'default' }}
        onClick={() => { if (hasOutput && isCompleted && !isExportStep) setCollapsed(c => !c) }}
      >
        <Space wrap size={6}>
          <span style={{ fontSize: '18px' }}>{AGENT_EMOJI[step.agent_role] ?? '🤖'}</span>
          <Text strong style={{ fontSize: '14px' }}>{step.id}</Text>
          <Tag color={AGENT_COLOR[step.agent_role] ?? 'default'}>{AGENT_LABEL[step.agent_role] ?? step.agent_role}</Tag>
          <Tag color="blue">{TASK_LABEL[step.task_type] ?? step.task_type}</Tag>
          {/* Status dot */}
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 13 }}>
            {isActive && <LoadingOutlined style={{ color: statusBadgeColor }} />}
            {!isActive && <span style={{ width: 8, height: 8, borderRadius: '50%', background: statusBadgeColor, display: 'inline-block' }} />}
            <Text style={{ fontSize: '13px', color: statusBadgeColor }}>{statusText}</Text>
          </span>
          {exec?.count > 1 && <Text type="secondary" style={{ fontSize: '12px' }}>（第 {exec.count} 次執行）</Text>}
        </Space>
        <Space size={6}>
          {isCompleted && hasOutput && !isExportStep && (
            <Button
              size="small"
              type="text"
              icon={collapsed ? <DownOutlined /> : <UpOutlined />}
              onClick={(e) => { e.stopPropagation(); setCollapsed(c => !c) }}
            >
              {collapsed ? '展開' : '收起'}
            </Button>
          )}
          {isCompleted && hasOutput && !isExportStep && (
            <Button size="small" icon={<DownloadOutlined />}
              onClick={(e) => { e.stopPropagation(); onDownload(artifactId!, `${step.id}_v${exec?.count ?? 1}.md`) }}>
              下載
            </Button>
          )}
          {isExportStep && isCompleted && <Tag color="green" icon={<CheckCircleOutlined />}>文件已產出</Tag>}
        </Space>
      </div>

      {/* Body — auto-expanded */}
      {shouldShowBody && (
        <div style={{ borderTop: `1px solid ${borderColor}22`, padding: '0 16px 16px' }}>
          {/* Running placeholder */}
          {isActive && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '16px 0 4px', color: '#1890ff' }}>
              <LoadingOutlined />
              <Text style={{ color: '#1890ff' }}>Agent 正在撰寫中，請稍候...</Text>
            </div>
          )}

          {/* Completed artifact content */}
          {isCompleted && artifactDetail && (
            <div className="artifact-appear" style={{ marginTop: 12 }}>
              <Space size={6} style={{ marginBottom: 10 }}>
                <FileTextOutlined style={{ color: '#1890ff' }} />
                <Tag color={AGENT_COLOR[artifactDetail.agent_role] ?? 'default'}>
                  {ARTIFACT_TYPE_LABEL[artifactDetail.artifact_type] ?? artifactDetail.artifact_type}
                </Tag>
                <Tag>v{artifactDetail.version}</Tag>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {new Date(artifactDetail.created_at).toLocaleString('zh-TW')}
                </Text>
              </Space>
              <div style={{
                background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6,
                padding: '16px 20px', maxHeight: 480, overflowY: 'auto',
              }}>
                <MarkdownView content={artifactDetail.content_md} />
              </div>
            </div>
          )}

          {/* Loading spinner while fetching artifact */}
          {isCompleted && hasOutput && !artifactDetail && (
            <div style={{ textAlign: 'center', padding: 20 }}><Spin size="small" /></div>
          )}
        </div>
      )}
    </Card>
  )
}

export default function WorkflowPage() {
  const { runId } = useParams<{ runId: string }>()
  const queryClient = useQueryClient()
  const [approvalModalOpen, setApprovalModalOpen] = useState(false)
  const [approvalFeedback, setApprovalFeedback] = useState('')

  const { data: workflowRun, isLoading, error } = useQuery({
    queryKey: ['workflow-run', runId],
    queryFn: () => workflowsApi.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query: { state: { data?: { status?: string } } }) => {
      const s = query.state.data?.status
      return s === 'running' || s === 'waiting_approval' ? 2000 : false
    },
  })

  const approveMutation = useMutation({
    mutationFn: ({ approved, feedback }: { approved: boolean; feedback?: string }) =>
      workflowsApi.approve(runId!, approved, feedback),
    onSuccess: () => {
      message.success('已送出審批決定')
      setApprovalModalOpen(false)
      setApprovalFeedback('')
      queryClient.invalidateQueries({ queryKey: ['workflow-run', runId] })
    },
    onError: (err: any) => { message.error(err.response?.data?.detail || '審批送出失敗') },
  })

  const handleDownloadAll = async () => {
    if (!workflowRun?.project_id) return
    try {
      const blob = await artifactsApi.downloadProject(workflowRun.project_id)
      const url = URL.createObjectURL(blob)
      // Backend returns a .zip (Final_Delivery package); name accordingly.
      const a = document.createElement('a'); a.href = url; a.download = '最終交付包.zip'; a.click()
      URL.revokeObjectURL(url)
    } catch { message.error('下載失敗') }
  }

  const handleDownloadArtifact = async (artifactId: string, filename: string) => {
    try {
      const blob = await artifactsApi.download(artifactId)
      const url = URL.createObjectURL(blob)
      // Backend serves this endpoint as markdown (.md); keep that extension.
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
    } catch { message.error('下載失敗') }
  }

  if (isLoading) return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
  if (error || !workflowRun) return <Alert message="工作流程載入失敗" type="error" showIcon />

  const steps = workflowRun.template_snapshot?.workflow?.steps ?? []
  const requireHumanApproval: string[] = workflowRun.template_snapshot?.workflow?.guardrails?.require_human_approval ?? []
  const se = workflowRun.step_executions ?? {}

  const getStatusColor = (s: string) =>
    ({ running: 'processing', completed: 'success', failed: 'error', timeout: 'warning', waiting_approval: 'warning' }[s] ?? 'default') as any
  const getStatusText = (s: string) =>
    ({ running: '執行中', completed: '已完成', failed: '執行失敗', timeout: '執行超時', waiting_approval: '等待人工審批' }[s] ?? s)

  // Progress bar: derive step status directly from step_executions + current_steps
  const stepsBarItems = steps.map((s: any) => {
    const exec = se[s.id]
    const isCurrent = workflowRun.current_steps.includes(s.id)
    let icon = undefined
    let stepStatus: 'finish' | 'process' | 'wait' | 'error' = 'wait'
    if (exec?.last_status === 'completed') { stepStatus = 'finish'; icon = <CheckCircleOutlined /> }
    else if (exec?.last_status === 'failed') { stepStatus = 'error'; icon = <ExclamationCircleOutlined /> }
    else if (isCurrent) { stepStatus = 'process'; icon = <LoadingOutlined /> }
    return {
      title: AGENT_LABEL[s.agent_role] ?? s.agent_role,
      description: TASK_LABEL[s.task_type] ?? s.task_type,
      status: stepStatus,
      icon,
    }
  })

  const currentIndex = steps.findIndex((s: any) => workflowRun.current_steps.includes(s.id))
  const completedCount = steps.filter((s: any) => se[s.id]?.last_status === 'completed').length

  return (
    <div>
      <style>{fadeInStyle}</style>

      <div style={{ marginBottom: 20 }}>
        <Title level={2} style={{ marginBottom: 4 }}>工作流程執行</Title>
        <Space split={<Divider type="vertical" />}>
          <Text type="secondary">ID: {workflowRun.id.slice(0, 8)}...</Text>
          <Tag color={getStatusColor(workflowRun.status)}>{getStatusText(workflowRun.status)}</Tag>
          <Text type="secondary">{new Date(workflowRun.created_at).toLocaleString('zh-TW')}</Text>
          {(workflowRun.status === 'completed' || workflowRun.status === 'waiting_approval') && (
            <Button size="small" type="primary" icon={<DownloadOutlined />} onClick={handleDownloadAll}>下載完整文件</Button>
          )}
        </Space>
      </div>

      {workflowRun.status === 'waiting_approval' && (
        <Alert style={{ marginBottom: 20 }} type="warning" showIcon message="需要人工審批"
          description="Director Agent 已完成審核，請確認產出物品質並決定是否批准繼續。"
          action={<Button type="primary" onClick={() => setApprovalModalOpen(true)}>前往審批</Button>}
        />
      )}

      <Card size="small" style={{ marginBottom: 16 }} styles={{ body: { padding: '10px 16px' } }}>
        <Space><UserOutlined /><Text type="secondary" style={{ fontSize: 13 }}>{workflowRun.user_input}</Text></Space>
      </Card>

      {/* Progress bar — each step has its own status, handles loops */}
      <Card size="small" style={{ marginBottom: 16 }} styles={{ body: { padding: '16px 24px' } }}>
        <Steps size="small"
          current={currentIndex >= 0 ? currentIndex : completedCount}
          items={stepsBarItems}
        />
      </Card>

      {/* Step cards — auto-expand active & completed steps */}
      <div>
        {steps.map((step: any) => {
          const exec = se[step.id]
          const isActive = workflowRun.current_steps.includes(step.id)
          const isCompleted = exec?.last_status === 'completed'
          const isFailed = exec?.last_status === 'failed'
          const isWaiting = exec?.waiting_approval === true
          const needsApproval = requireHumanApproval.includes(step.id)
          return (
            <div key={step.id}>
              {needsApproval && (
                <div style={{ textAlign: 'center', margin: '4px 0' }}>
                  <Tag color="orange" style={{ fontSize: '11px' }}>⬇ 此步驟需人工審批</Tag>
                </div>
              )}
              <StepCard
                step={step} exec={exec}
                isActive={isActive} isCompleted={isCompleted}
                isFailed={isFailed} isWaiting={isWaiting}
                onDownload={handleDownloadArtifact}
              />
            </div>
          )
        })}
      </div>

      {/* Activity Log */}
      {(() => {
        const logs: { time: string; msg: string }[] = se['_log'] ?? []
        if (logs.length === 0) return null
        return (
          <Card
            title={<Space><LoadingOutlined spin={workflowRun.status === 'running'} style={{ color: '#1890ff' }} /><span>執行記錄</span></Space>}
            size="small"
            style={{ marginTop: 8 }}
            styles={{ body: { padding: 0 } }}
          >
            <div style={{
              maxHeight: 200, overflowY: 'auto', padding: '8px 16px',
              background: '#141414', borderRadius: '0 0 6px 6px',
              fontFamily: 'monospace', fontSize: 13,
            }}>
              {[...logs].reverse().map((entry, i) => (
                <div key={i} style={{ color: '#d4d4d4', lineHeight: '1.8' }}>
                  <span style={{ color: '#6a9955', marginRight: 8 }}>[{entry.time}]</span>
                  {entry.msg}
                </div>
              ))}
            </div>
          </Card>
        )
      })()}

      {workflowRun.status === 'completed' && (
        <Card style={{ textAlign: 'center', marginTop: 12, background: '#f6ffed', border: '1px solid #b7eb8f' }}>
          <CheckCircleOutlined style={{ fontSize: 32, color: '#52c41a' }} />
          <div style={{ marginTop: 8 }}>
            <Text style={{ fontSize: '16px', color: '#52c41a', fontWeight: 600 }}>工作流程執行完成！</Text>
          </div>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<DownloadOutlined />} size="large" onClick={handleDownloadAll}>
              下載完整規格文件 (.docx)
            </Button>
          </div>
        </Card>
      )}

      <Modal title="人工審批" open={approvalModalOpen}
        onCancel={() => { setApprovalModalOpen(false); setApprovalFeedback('') }}
        footer={null} width={560}
      >
        <Text>請確認所有 Agent 產出物品質，決定是否批准繼續匯出，或退回修改。</Text>
        <Divider />
        <div style={{ marginBottom: 16 }}>
          <Text strong>意見回饋（退回時必填）</Text>
          <TextArea style={{ marginTop: 8 }} rows={4} placeholder="如需退回，請說明需要改善的地方..."
            value={approvalFeedback} onChange={(e) => setApprovalFeedback(e.target.value)}
          />
        </div>
        <Space>
          <Button type="primary" loading={approveMutation.isPending}
            onClick={() => approveMutation.mutate({ approved: true, feedback: approvalFeedback || undefined })}>
            批准，產出文件
          </Button>
          <Button danger loading={approveMutation.isPending}
            onClick={() => {
              if (!approvalFeedback.trim()) { message.warning('退回時請填寫意見回饋'); return }
              approveMutation.mutate({ approved: false, feedback: approvalFeedback })
            }}>
            退回修改
          </Button>
          <Button onClick={() => setApprovalModalOpen(false)}>取消</Button>
        </Space>
      </Modal>
    </div>
  )
}
