import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import DashboardPage from '@/pages/DashboardPage'
import ProjectPage from '@/pages/ProjectPage'
import WorkflowPage from '@/pages/WorkflowPage'
import AgentSettingsPage from '@/pages/AgentSettingsPage'
import AppHeader from '@/components/AppHeader'

const { Content } = Layout

function App() {
  // No auth required — prototype mode
  return (
    <Layout className="min-h-screen">
      <AppHeader />
      <Content style={{ padding: '24px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/projects/:id" element={<ProjectPage />} />
            <Route path="/workflows/:runId" element={<WorkflowPage />} />
            <Route path="/agents" element={<AgentSettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Content>
    </Layout>
  )
}

export default App
