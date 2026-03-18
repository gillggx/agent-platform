import { Layout, Button, Space } from 'antd'
import { DashboardOutlined, RobotOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header } = Layout

export default function AppHeader() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: '#fff',
      boxShadow: '0 1px 4px rgba(0,21,41,.08)'
    }}>
      <h1
        style={{
          margin: 0,
          fontSize: '20px',
          fontWeight: 600,
          cursor: 'pointer',
          color: '#1890ff'
        }}
        onClick={() => navigate('/')}
      >
        🤖 Multi-Agent 協作平台
      </h1>

      <Space>
        <Button
          type={location.pathname === '/' ? 'primary' : 'text'}
          icon={<DashboardOutlined />}
          onClick={() => navigate('/')}
        >
          首頁
        </Button>
        <Button
          type={location.pathname === '/agents' ? 'primary' : 'text'}
          icon={<RobotOutlined />}
          onClick={() => navigate('/agents')}
        >
          Agent 設定
        </Button>
      </Space>
    </Header>
  )
}
