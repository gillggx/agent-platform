import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Layout } from 'antd'
import DashboardPage from '@/pages/DashboardPage'
import ProjectPage from '@/pages/ProjectPage'
import WorkflowPage from '@/pages/WorkflowPage'
import AgentSettingsPage from '@/pages/AgentSettingsPage'
import DAGEditorPage from '@/pages/DAGEditorPage'
import WorkflowManagePage from '@/pages/WorkflowManagePage'
import AppHeader from '@/components/AppHeader'

const { Content } = Layout

function App() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  // Home page: full-screen copilot layout (no header, no padding)
  if (isHome) {
    return (
      <Routes>
        <Route path="/" element={<DashboardPage />} />
      </Routes>
    )
  }

  return (
    <Layout className="min-h-screen">
      <AppHeader />
      <Content style={{ padding: '24px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <Routes>
            <Route path="/projects/:id" element={<ProjectPage />} />
            <Route path="/workflows/:runId" element={<WorkflowPage />} />
            <Route path="/workflows/manage" element={<WorkflowManagePage />} />
            <Route path="/workflow-editor" element={<DAGEditorPage />} />
            <Route path="/workflow-editor/:workflowId" element={<DAGEditorPage />} />
            <Route path="/agents" element={<AgentSettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Content>
    </Layout>
  )
}

export default App
