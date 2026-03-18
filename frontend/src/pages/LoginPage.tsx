import { useState } from 'react'
import { Form, Input, Button, Card, Typography, Alert, Space, Divider } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { authApi } from '@/services/api'
import type { LoginForm } from '@/types'

const { Title, Text } = Typography

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (tokenResponse) => {
      // Get user info
      try {
        const user = await authApi.me()
        login(tokenResponse.access_token, user)
        navigate('/')
      } catch (err) {
        setError('登入後獲取用戶資訊失敗')
      }
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '登入失敗，請檢查帳號密碼')
    },
  })

  const handleSubmit = (values: LoginForm) => {
    setError(null)
    loginMutation.mutate(values)
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
          maxWidth: '400px',
          boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Title level={2} style={{ marginBottom: '8px' }}>
            登入
          </Title>
          <Text type="secondary">
            Multi-Agent 協作平台
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
          name="login"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="email"
            label="電子郵件"
            rules={[
              { required: true, message: '請輸入電子郵件' },
              { type: 'email', message: '請輸入有效的電子郵件格式' }
            ]}
          >
            <Input 
              prefix={<UserOutlined />} 
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
              placeholder="請輸入密碼"
            />
          </Form.Item>

          <Form.Item style={{ marginTop: '24px' }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              block
              loading={loginMutation.isPending}
            >
              登入
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <div style={{ textAlign: 'center' }}>
          <Space>
            <Text type="secondary">還沒有帳號？</Text>
            <Link to="/register">
              <Button type="link" size="small">
                立即註冊
              </Button>
            </Link>
          </Space>
        </div>
      </Card>
    </div>
  )
}