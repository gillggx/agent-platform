import { useState, useEffect, useRef, useCallback } from 'react'
import { Button, Input, Typography, Tag, Space, message as antMessage } from 'antd'
import { SendOutlined, LoadingOutlined, RocketOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { chatApi } from '@/services/api'
import type { ChatMessage } from '@/services/api'
import type { Project } from '@/types'
import ReactMarkdown from 'react-markdown'

const { Text } = Typography
const { TextArea } = Input

interface Props {
  projects: Project[]
}

interface LocalMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  project_context_ids: string[]
  streaming?: boolean
}

interface IntakeState {
  projectName: string
  projectDescription: string
}

function TypingDots() {
  return (
    <span style={{ display: 'inline-flex', gap: 3, alignItems: 'center', height: 16 }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#999',
            animation: 'typing-dot 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes typing-dot {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </span>
  )
}

function IntakeConfirmCard({
  intake,
  onConfirm,
  onDismiss,
  loading,
}: {
  intake: IntakeState
  onConfirm: () => void
  onDismiss: () => void
  loading: boolean
}) {
  return (
    <div style={{
      background: '#f6ffed',
      border: '1.5px solid #52c41a',
      borderRadius: 12,
      padding: '16px 20px',
      maxWidth: '72%',
      alignSelf: 'flex-start',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
        <Text strong style={{ color: '#389e0d' }}>需求已釐清，準備開始執行！</Text>
      </div>
      <div style={{ marginBottom: 4 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>專案名稱</Text>
        <br />
        <Text strong>{intake.projectName}</Text>
      </div>
      {intake.projectDescription && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>描述</Text>
          <br />
          <Text style={{ fontSize: 13 }}>{intake.projectDescription}</Text>
        </div>
      )}
      <Space>
        <Button
          type="primary"
          icon={loading ? <LoadingOutlined /> : <RocketOutlined />}
          onClick={onConfirm}
          loading={loading}
          style={{ background: '#52c41a', borderColor: '#52c41a' }}
        >
          建立專案並啟動
        </Button>
        <Button onClick={onDismiss} disabled={loading}>
          繼續討論
        </Button>
      </Space>
    </div>
  )
}

export default function ChatPanel({ projects }: Props) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingId, setStreamingId] = useState<string | null>(null)
  const [intake, setIntake] = useState<IntakeState | null>(null)
  const [intakeLoading, setIntakeLoading] = useState(false)
  const [intakeTriggered, setIntakeTriggered] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['chat-history'],
    queryFn: () => chatApi.history(50),
  })

  useEffect(() => {
    if (history) {
      setMessages(history.map((m: ChatMessage) => ({ ...m, streaming: false })))
    }
  }, [history])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming, intake])

  const projectNameMap = Object.fromEntries(projects.map((p) => [p.id, p.name]))

  const sendMessage = useCallback(() => {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    setIsStreaming(true)
    setIntake(null) // dismiss any existing intake card

    const userMsg: LocalMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      project_context_ids: [],
    }
    const aId = `a-${Date.now()}`
    setStreamingId(aId)

    const assistantMsg: LocalMessage = {
      id: aId,
      role: 'assistant',
      content: '',
      project_context_ids: [],
      streaming: true,
    }

    setMessages((prev) => [...prev, userMsg, assistantMsg])

    abortRef.current = chatApi.streamMessage(
      text,
      (delta) => {
        setMessages((prev) =>
          prev.map((m) => m.id === aId ? { ...m, content: m.content + delta } : m),
        )
      },
      (contextIds) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aId ? { ...m, streaming: false, project_context_ids: contextIds } : m,
          ),
        )
        setIsStreaming(false)
        setStreamingId(null)
        queryClient.invalidateQueries({ queryKey: ['chat-history'] })
      },
      (errMsg) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aId ? { ...m, content: `⚠️ ${errMsg}`, streaming: false } : m,
          ),
        )
        setIsStreaming(false)
        setStreamingId(null)
      },
      (projectName, projectDescription) => {
        if (!intakeTriggered) {
          setIntake({ projectName, projectDescription })
          setIntakeTriggered(true)
        }
      },
      intakeTriggered,
    )
  }, [input, isStreaming, intakeTriggered, queryClient])

  const handleConfirmIntake = async () => {
    if (!intake) return
    setIntakeLoading(true)
    try {
      const result = await chatApi.startProject(
        intake.projectName,
        intake.projectDescription,
      )
      antMessage.success(`專案「${result.project_name}」已建立，正在啟動 ${result.template_name}...`)
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setIntake(null)
      navigate(`/workflows/${result.run_id}`)
    } catch (err: any) {
      antMessage.error(err.response?.data?.detail || '建立專案失敗')
    } finally {
      setIntakeLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid #f0f0f0',
        background: '#fff',
        flexShrink: 0,
      }}>
        <Text strong style={{ fontSize: 16 }}>🤖 PM Co-pilot</Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          告訴我你想做什麼，我會幫你釐清需求、回答問題
        </Text>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}>
        {historyLoading && (
          <div style={{ textAlign: 'center', color: '#bbb', marginTop: 40 }}>
            <LoadingOutlined style={{ fontSize: 20 }} />
          </div>
        )}

        {!historyLoading && messages.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: 80, color: '#bbb' }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>💬</div>
            <Text type="secondary">開始跟 PM Co-pilot 對話吧</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              可以描述新想法、詢問專案狀態、或討論設計方向
            </Text>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '72%',
              background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
              color: msg.role === 'user' ? '#fff' : '#000',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              padding: '12px 16px',
              fontSize: 14,
              lineHeight: 1.6,
            }}>
              {msg.role === 'assistant' ? (
                <>
                  {msg.streaming && msg.content === '' ? (
                    <TypingDots />
                  ) : (
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p style={{ margin: '0 0 8px' }}>{children}</p>,
                        ul: ({ children }) => <ul style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ul>,
                        ol: ({ children }) => <ol style={{ paddingLeft: 20, margin: '4px 0' }}>{children}</ol>,
                        code: ({ children }) => (
                          <code style={{
                            background: '#e8e8e8', borderRadius: 3,
                            padding: '1px 4px', fontFamily: 'monospace', fontSize: 12,
                          }}>{children}</code>
                        ),
                        pre: ({ children }) => (
                          <pre style={{
                            background: '#e8e8e8', borderRadius: 6,
                            padding: '8px 12px', overflow: 'auto', fontSize: 12,
                          }}>{children}</pre>
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}

                  {msg.streaming && msg.content !== '' && (
                    <span style={{
                      display: 'inline-block',
                      width: 2, height: '1em',
                      background: '#666',
                      marginLeft: 2,
                      animation: 'blink 0.8s step-end infinite',
                      verticalAlign: 'text-bottom',
                    }}>
                      <style>{`@keyframes blink { 50% { opacity: 0 } }`}</style>
                    </span>
                  )}

                  {msg.project_context_ids.length > 0 && (
                    <Space size={4} wrap style={{ marginTop: 8 }}>
                      {msg.project_context_ids.map((id) => (
                        <Tag key={id} color="blue" style={{ fontSize: 11 }}>
                          📁 {projectNameMap[id] ?? id}
                        </Tag>
                      ))}
                    </Space>
                  )}
                </>
              ) : (
                <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
              )}
            </div>
          </div>
        ))}

        {/* Intake confirmation card */}
        {intake && (
          <IntakeConfirmCard
            intake={intake}
            onConfirm={handleConfirmIntake}
            onDismiss={() => { setIntake(null); setIntakeTriggered(false) }}
            loading={intakeLoading}
          />
        )}

        {/* Streaming status */}
        {isStreaming && streamingId && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#999', fontSize: 12 }}>
            <LoadingOutlined style={{ fontSize: 12 }} />
            <span>PM Co-pilot 正在回覆中...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid #f0f0f0',
        background: '#fff',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="輸入訊息… (Ctrl+Enter 送出)"
            autoSize={{ minRows: 1, maxRows: 5 }}
            style={{ flex: 1 }}
            disabled={isStreaming}
          />
          <Button
            type="primary"
            icon={isStreaming ? <LoadingOutlined /> : <SendOutlined />}
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
          >
            {isStreaming ? '回覆中' : '送出'}
          </Button>
        </div>
        <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: 'block' }}>
          Ctrl+Enter 送出
        </Text>
      </div>
    </div>
  )
}
