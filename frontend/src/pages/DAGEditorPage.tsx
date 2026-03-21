/**
 * DAG Editor Page
 *
 * Full-page DAG editor for creating and editing workflow templates.
 */

import React, { useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { message } from 'antd'
import DAGEditor from '@/components/DAGEditor/DAGEditor'
import { workflowsApi } from '@/services/api'
import { useDagStore } from '@/store/dagStore'

export const DAGEditorPage: React.FC = () => {
  const { workflowId } = useParams<{ workflowId?: string }>()
  const navigate = useNavigate()
  const { setWorkflow, createWorkflow } = useDagStore()

  useEffect(() => {
    if (workflowId) {
      workflowsApi.getTemplate(workflowId).then((template) => {
        const def = template.definition as any
        // If definition is a DAG-format workflow (has nodes array), load it directly
        if (def && Array.isArray(def.nodes)) {
          setWorkflow({ ...def, id: template.id, name: template.name })
        } else {
          // Backend step-format template: create a named workflow stub
          createWorkflow(template.name)
        }
        message.success(`已載入「${template.name}」`)
      }).catch(() => {
        message.error('無法載入流程模板')
        navigate('/workflows/manage')
      })
    }
  }, [workflowId])

  const handleSave = useCallback(async (workflow: any) => {
    if (workflowId) {
      await workflowsApi.updateTemplate(workflowId, {
        name: workflow.name,
        definition: workflow,
      })
    } else {
      const created = await workflowsApi.createTemplate({
        name: workflow.name || '未命名流程',
        definition: workflow,
      })
      navigate(`/workflow-editor/${created.id}`, { replace: true })
    }
    navigate('/workflows/manage')
  }, [workflowId, navigate])

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <DAGEditor workflowId={workflowId} onSave={handleSave} />
    </div>
  )
}

export default DAGEditorPage
