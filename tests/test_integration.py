"""
Integration Tests for Agent Platform Phase 1.

End-to-end workflow execution with multiple agents:
- 5-step DAG workflow
- Agent message passing
- Context propagation
- Artifact collection
"""

import pytest
import asyncio
from app.core import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    StepContext,
    StepOutput,
    StepStatus,
    WorkflowStatus,
    AgentOrchestrator,
    RoleDefinition,
    KnowledgePack,
    AgentOutput,
    create_workflow_engine,
    create_agent_orchestrator,
    create_pm_role,
    create_architect_role,
    create_qa_role,
)


class TestEndToEndWorkflow:
    """Test complete workflow execution with agents."""

    @pytest.mark.asyncio
    async def test_five_step_workflow(self):
        """
        Test 5-step DAG:
        1. PM (root) → analyzes requirements
        2. Architect (depends on PM) → designs system
        3. QA (depends on PM) → creates test plan
        4. Director (depends on Architect, QA) → makes go/no-go decision
        5. Cleanup (depends on Director) → exports results
        """
        # Create workflow
        steps = [
            WorkflowStep(
                id="pm_analysis",
                agent_role="pm",
                task_type="analysis",
                depends_on=[],
            ),
            WorkflowStep(
                id="architect_design",
                agent_role="architect",
                task_type="design",
                depends_on=["pm_analysis"],
            ),
            WorkflowStep(
                id="qa_test_plan",
                agent_role="qa",
                task_type="testing",
                depends_on=["pm_analysis"],
            ),
            WorkflowStep(
                id="director_decision",
                agent_role="director",
                task_type="decision",
                depends_on=["architect_design", "qa_test_plan"],
            ),
            WorkflowStep(
                id="export_results",
                agent_role="system",
                task_type="export",
                depends_on=["director_decision"],
            ),
        ]
        
        workflow = WorkflowDefinition(
            id="product-workflow",
            name="Product Development Workflow",
            description="Full product development pipeline",
            steps=steps,
        )
        
        # Setup workflow engine
        engine = create_workflow_engine()
        execution_log: list = []
        
        async def tracking_executor(context: StepContext) -> StepOutput:
            """Executor that tracks execution and simulates work."""
            step_id = context.step_id
            execution_log.append({
                "step": step_id,
                "upstream_count": len(context.previous_outputs),
            })
            
            # Simulate work
            await asyncio.sleep(0.01)
            
            return StepOutput(
                step_id=step_id,
                role=workflow.get_step(step_id).agent_role,
                status=StepStatus.COMPLETED,
                output_type="artifact",
                content=f"Output from {step_id}",
            )
        
        engine.register_step_executor(tracking_executor)
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify execution
        assert result.is_success()
        assert result.status == WorkflowStatus.COMPLETED
        assert len(result.step_outputs) == 5
        
        # Verify execution order
        assert len(execution_log) == 5
        assert execution_log[0]["step"] == "pm_analysis"
        assert execution_log[0]["upstream_count"] == 0
        
        # pm_analysis outputs should be available to architect_design and qa_test_plan
        arch_log = next(l for l in execution_log if l["step"] == "architect_design")
        assert arch_log["upstream_count"] == 1
        
        qa_log = next(l for l in execution_log if l["step"] == "qa_test_plan")
        assert qa_log["upstream_count"] == 1
        
        # director_decision should have 2 upstream outputs
        director_log = next(l for l in execution_log if l["step"] == "director_decision")
        assert director_log["upstream_count"] == 2

    @pytest.mark.asyncio
    async def test_workflow_with_agents(self):
        """Test workflow integrated with agent orchestrator."""
        # Create roles
        pm_role = create_pm_role()
        architect_role = create_architect_role()
        qa_role = create_qa_role()
        
        # Create workflow
        steps = [
            WorkflowStep(
                id="gather_requirements",
                agent_role="pm",
                task_type="analysis",
            ),
            WorkflowStep(
                id="design_system",
                agent_role="architect",
                task_type="design",
                depends_on=["gather_requirements"],
            ),
            WorkflowStep(
                id="create_test_plan",
                agent_role="qa",
                task_type="testing",
                depends_on=["design_system"],
            ),
        ]
        
        workflow = WorkflowDefinition(
            id="dev-workflow",
            name="Development Workflow",
            description="Simple development workflow",
            steps=steps,
        )
        
        # Setup orchestrator
        orchestrator = create_agent_orchestrator()
        sessions: dict = {}
        
        async def agent_executor(session, inputs, knowledge_pack):
            """Execute step with agent."""
            return AgentOutput(
                session_id=session.id,
                role=session.role.role,
                output_type="artifact",
                content=f"Completed: {inputs.get('task', 'unknown')}",
            )
        
        orchestrator.register_step_executor(agent_executor)
        
        # Setup workflow engine
        engine = create_workflow_engine()
        
        async def workflow_executor(context: StepContext) -> StepOutput:
            """Workflow executor that uses orchestrator."""
            step_id = context.step_id
            step = workflow.get_step(step_id)
            
            # Get or create agent session
            if step_id not in sessions:
                if step.agent_role == "pm":
                    role = pm_role
                elif step.agent_role == "architect":
                    role = architect_role
                else:
                    role = qa_role
                
                session = await orchestrator.create_agent_session(
                    role,
                    {"workflow_id": workflow.id},
                )
                sessions[step_id] = session
            
            session = sessions[step_id]
            
            # Execute through orchestrator
            knowledge_pack = KnowledgePack(
                upstream_artifacts=[
                    {
                        "step_id": s_id,
                        "content": output.content,
                    }
                    for s_id, output in context.previous_outputs.items()
                ],
            )
            
            agent_output = await orchestrator.execute_step(
                session,
                {"task": step.task_type},
                knowledge_pack,
            )
            
            return StepOutput(
                step_id=step_id,
                role=step.agent_role,
                status=StepStatus.COMPLETED,
                output_type="artifact",
                content=agent_output.content,
            )
        
        engine.register_step_executor(workflow_executor)
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify
        assert result.is_success()
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_context_propagation(self):
        """Test that context is correctly propagated through steps."""
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s2"]),
        ]
        
        workflow = WorkflowDefinition(
            id="ctx-workflow",
            name="Context Test",
            description="Test context propagation",
            steps=steps,
        )
        
        engine = create_workflow_engine()
        context_stack: list = []
        
        async def context_tracking_executor(context: StepContext) -> StepOutput:
            """Executor that tracks context."""
            context_stack.append({
                "step": context.step_id,
                "workflow": context.workflow_id,
                "previous": list(context.previous_outputs.keys()),
            })
            
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content=f"Step {context.step_id}",
            )
        
        engine.register_step_executor(context_tracking_executor)
        
        # Execute
        result = await engine.execute(
            workflow,
            {"inputs": {"project_id": "p1"}},
        )
        
        # Verify context propagation
        assert len(context_stack) == 3
        assert context_stack[0]["previous"] == []
        assert context_stack[1]["previous"] == ["s1"]
        assert context_stack[2]["previous"] == ["s2"]

    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self):
        """Test error handling and partial execution."""
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="error-workflow",
            name="Error Test",
            description="Test error handling",
            steps=steps,
        )
        
        engine = create_workflow_engine()
        
        async def selective_failing_executor(context: StepContext) -> StepOutput:
            """Executor that fails for specific steps."""
            if context.step_id == "s2":
                raise Exception("Simulated failure")
            
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content="output",
            )
        
        engine.register_step_executor(selective_failing_executor)
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify error handling
        assert not result.is_success()
        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
        assert result.step_outputs["s2"].status == StepStatus.FAILED


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
