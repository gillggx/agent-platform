import { useQuery } from '@tanstack/react-query'
import { projectsApi, workflowsApi } from '@/services/api'
import ProjectSidebar from '@/components/ProjectSidebar'
import ChatPanel from '@/components/ChatPanel'

export default function DashboardPage() {
  const { data: projects = [], isLoading: projectsLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
    refetchInterval: (query) => {
      const hasRunning = query.state.data?.some((p: any) => p.status === 'running')
      return hasRunning ? 3000 : false
    },
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: workflowsApi.listTemplates,
  })

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <ProjectSidebar
        projects={projects}
        templates={templates}
        projectsLoading={projectsLoading}
      />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ChatPanel projects={projects} />
      </div>
    </div>
  )
}
