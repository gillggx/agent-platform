import { useState } from 'react'
import {
  Card,
  Tabs,
  Form,
  Input,
  InputNumber,
  Button,
  Typography,
  Space,
  Tag,
  Divider,
  message,
  Tooltip,
  Row,
  Col,
  Statistic,
} from 'antd'
import { SaveOutlined, InfoCircleOutlined, RobotOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentsApi } from '@/services/api'
import type { AgentDef } from '@/services/api'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const ROLE_COLOR: Record<string, string> = {
  pm: 'blue',
  architect: 'purple',
  qa: 'green',
  devops: 'orange',
  director: 'red',
}

const ROLE_EMOJI: Record<string, string> = {
  pm: '📋',
  architect: '🏗️',
  qa: '🧪',
  devops: '🚀',
  director: '🎯',
}

function AgentEditor({ agent }: { agent: AgentDef }) {
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: (values: any) => {
      const {
        display_name, description, soul,
        temperature, max_tokens,
        llm_model, llm_provider, llm_api_key, llm_base_url,
      } = values
      return agentsApi.update(agent.role, {
        display_name,
        description,
        soul,
        config: {
          temperature,
          max_tokens,
          ...(llm_model ? { llm_model } : {}),
          ...(llm_provider ? { llm_provider } : {}),
          ...(llm_api_key ? { llm_api_key } : {}),
          ...(llm_base_url ? { llm_base_url } : {}),
        },
      })
    },
    onSuccess: () => {
      message.success(`${agent.display_name} 設定已儲存`)
      queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
    onError: () => {
      message.error('儲存失敗，請稍後再試')
    },
  })

  const initialValues = {
    display_name: agent.display_name,
    description: agent.description,
    soul: agent.soul,
    temperature: agent.config.temperature ?? 0.7,
    max_tokens: agent.config.max_tokens ?? 4096,
    llm_model: agent.config.llm_model ?? '',
    llm_provider: agent.config.llm_provider ?? '',
    llm_api_key: agent.config.llm_api_key ?? '',
    llm_base_url: (agent.config as any).llm_base_url ?? '',
  }

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues}
      onFinish={mutation.mutate}
    >
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Form.Item label="顯示名稱" name="display_name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item label="描述" name="description">
          <Input />
        </Form.Item>
      </div>

      <Divider orientation="left">
        <Space>
          <RobotOutlined />
          <Text strong>Soul（角色靈魂定義）</Text>
          <Tooltip title="Soul 是這個 Agent 的個性、價值觀和工作風格定義，直接影響 LLM 的行為。支援 Markdown 格式。">
            <InfoCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        </Space>
      </Divider>

      <Form.Item name="soul">
        <TextArea
          rows={16}
          placeholder="輸入 Agent 的靈魂定義（Markdown 格式）..."
          style={{ fontFamily: 'monospace', fontSize: '13px' }}
        />
      </Form.Item>

      <Divider orientation="left">
        <Space>
          <Text strong>LLM 設定</Text>
          <Tooltip title="留空則使用全局設定（.env 中的 LLM_MODEL）。設定後此 Agent 會使用獨立的 LLM 設定。">
            <InfoCircleOutlined style={{ color: '#999' }} />
          </Tooltip>
        </Space>
      </Divider>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Form.Item
          label="LLM Model（留空使用全局設定）"
          name="llm_model"
          tooltip="e.g. openrouter/google/gemini-2.0-flash-001, openai/gpt-4o, anthropic/claude-haiku-4-5-20251001"
        >
          <Input placeholder="openrouter/google/gemini-2.0-flash-001" />
        </Form.Item>
        <Form.Item
          label="LLM Provider（留空使用全局設定）"
          name="llm_provider"
          tooltip="e.g. openrouter, openai, anthropic"
        >
          <Input placeholder="openrouter" />
        </Form.Item>
      </div>

      <Form.Item
        label="API Key（留空使用全局設定）"
        name="llm_api_key"
        tooltip="為此 Agent 指定獨立的 API Key，適合使用不同帳號或不同 provider 的情況。內部 keyless endpoint 留空即可。"
      >
        <Input.Password placeholder="sk-or-...（內部 endpoint 可留空）" />
      </Form.Item>

      <Form.Item
        label="Base URL（留空使用全局設定）"
        name="llm_base_url"
        tooltip="自訂 API endpoint，用於公司內部或自架 OpenAI-compatible LLM。設了會覆蓋 .env 的 LLM_BASE_URL。"
      >
        <Input placeholder="https://llm.company.internal/v1" />
      </Form.Item>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Form.Item label="Temperature" name="temperature" tooltip="創意程度：0.0（保守）→ 1.0（創意）">
          <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item label="Max Tokens" name="max_tokens" tooltip="每次 LLM 回應的最大 token 數">
          <InputNumber min={256} max={32768} step={256} style={{ width: '100%' }} />
        </Form.Item>
      </div>

      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          icon={<SaveOutlined />}
          loading={mutation.isPending}
        >
          儲存設定
        </Button>
      </Form.Item>
    </Form>
  )
}

interface HealthInfo {
  llm_model?: string
  llm_base_url?: string
  llm_configured?: boolean
}

export default function AgentSettingsPage() {
  const [activeTab, setActiveTab] = useState('pm')

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list,
  })

  // Show the server-level LLM defaults so the user knows what kicks in
  // when a per-agent override is blank.
  const { data: health } = useQuery<HealthInfo>({
    queryKey: ['health'],
    queryFn: () => fetch('/health').then((r) => r.json()),
    staleTime: 60_000,
  })

  const tabItems = (agents ?? []).map((agent) => ({
    key: agent.role,
    label: (
      <Space>
        <span>{ROLE_EMOJI[agent.role] ?? '🤖'}</span>
        <Tag color={ROLE_COLOR[agent.role] ?? 'default'} style={{ margin: 0 }}>
          {agent.display_name}
        </Tag>
      </Space>
    ),
    children: (
      <Card bordered={false}>
        <AgentEditor key={agent.id} agent={agent} />
      </Card>
    ),
  }))

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2}>Agent 設定</Title>
        <Paragraph type="secondary">
          為每個 Agent 定義靈魂（Soul）、個性、工作風格，以及獨立的 LLM 模型設定。
          Soul 是 Agent 的 System Prompt，直接決定 AI 的行為模式。
        </Paragraph>

        {health && (
          <Card size="small" style={{ marginTop: 12, background: '#f6ffed', borderColor: '#b7eb8f' }}>
            <Space size="large" wrap>
              <Space size={4}>
                <ThunderboltOutlined style={{ color: '#52c41a' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>全局預設 LLM：</Text>
                <Text code style={{ fontSize: 12 }}>{health.llm_model ?? '—'}</Text>
              </Space>
              <Space size={4}>
                <Text type="secondary" style={{ fontSize: 12 }}>Base URL：</Text>
                <Text code style={{ fontSize: 12 }}>{health.llm_base_url ?? '—'}</Text>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                （下方 agent 留白 = 使用這些全局設定）
              </Text>
            </Space>
          </Card>
        )}
      </div>

      {/* Overview cards */}
      {!isLoading && (agents ?? []).length > 0 && (
        <Row gutter={[12, 12]} style={{ marginBottom: 24 }}>
          {(agents ?? []).map((agent) => (
            <Col key={agent.role} xs={24} sm={12} md={8} lg={6} xl={4}>
              <Card
                size="small"
                hoverable
                style={{
                  cursor: 'pointer',
                  borderColor: activeTab === agent.role ? '#1677ff' : undefined,
                  background: activeTab === agent.role ? '#f0f7ff' : undefined,
                }}
                onClick={() => setActiveTab(agent.role)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontSize: 20 }}>{ROLE_EMOJI[agent.role] ?? '🤖'}</span>
                  <Tag color={ROLE_COLOR[agent.role] ?? 'default'} style={{ margin: 0 }}>
                    {agent.display_name}
                  </Tag>
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                  <Statistic
                    title="Temp"
                    value={agent.config.temperature ?? 0.7}
                    precision={1}
                    valueStyle={{ fontSize: 14 }}
                  />
                  <Statistic
                    title="Max Tokens"
                    value={agent.config.max_tokens ?? 4096}
                    valueStyle={{ fontSize: 14 }}
                  />
                </div>
                {agent.config.llm_model && (
                  <div style={{ marginTop: 6 }}>
                    <ThunderboltOutlined style={{ color: '#faad14', fontSize: 11 }} />
                    {' '}
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {agent.config.llm_model.split('/').pop()}
                    </Text>
                  </div>
                )}
              </Card>
            </Col>
          ))}
        </Row>
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={isLoading ? [] : tabItems}
        type="card"
      />
    </div>
  )
}
