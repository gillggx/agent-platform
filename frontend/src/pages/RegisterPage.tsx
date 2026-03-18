import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Alert, Space, Divider } from 'antd'
import { UserOutlined, LockOutlined, TeamOutlined, MailOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { authApi } from '@/services/api'
import type { RegisterForm } from '@/types'

const { Title, Text } = Typography

export default function RegisterPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const registerMutation = useMutation({
    mutationFn: authApi.register,
    onSuccess: async (tokenResponse) => {
      // Get user info
      try {
        const user = await authApi.me()
        login(tokenResponse.access_token, user)
        navigate('/')
      } catch (err) {
        setError('註冊後獲取用戶資訊失敗')
      }
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '註冊失敗，請稍後再試')
    },
  })

  const handleSubmit = (values: RegisterForm) => {
    setError(null)
    registerMutation.mutate(values)
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: '100%', 
          maxWidth: '420px',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Title level={2} style={{ marginBottom: '8px' }}>
            註冊帳號
          </Title>
          <Text type="secondary">
            開始使用 Multi-Agent 協作平台
          </Text>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: '16px' }}
          />
        )}

        <Form
          name="register"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="full_name"
            label="姓名"
            rules={[
              { required: true, message: '請輸入姓名' },
              { min: 2, message: '姓名至少需要 2 個字符' }
            ]}
          >
            <Input 
              prefix={<UserOutlined />} 
              placeholder="請輸入您的姓名"
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="電子郵件"
            rules={[
              { required: true, message: '請輸入電子郵件' },
              { type: 'email', message: '請輸入有效的電子郵件格式' }
            ]}
          >
            <Input 
              prefix={<MailOutlined />} 
              placeholder="your@email.com"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密碼"
            rules={[
              { required: true, message: '請輸入密碼' },
              { min: 6, message: '密碼至少需要 6 個字符' }
            ]}
          >
            <Input.Password 
              prefix={<LockOutlined />} 
              placeholder="請輸入密碼（至少6位）"
            />
          </Form.Item>

          <Form.Item
            name="organization_name"
            label="組織名稱"
            rules={[
              { required: true, message: '請輸入組織名稱' },
              { min: 2, message: '組織名稱至少需要 2 個字符' }
            ]}
          >
            <Input 
              prefix={<TeamOutlined />} 
              placeholder="您的公司或組織名稱"
            />
          </Form.Item>

          <Form.Item style={{ marginTop: '24px' }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              block
              loading={registerMutation.isPending}
            >
              註冊
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <div style={{ textAlign: 'center' }}>
          <Space>
            <Text type="secondary">已有帳號？</Text>
            <Link to="/login">
              <Button type="link" size="small">
                立即登入
              </Button>
            </Link>
          </Space>
        </div>
      </Card>
    </div>
  )
}