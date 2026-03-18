"""
Unit Tests for WorkflowEngine — DAG execution, topological sort, cycle detection.

Test Cases:
- Topological sort (normal DAG)
- Circular dependency detection
- Isolated nodes handling
- Concurrent execution order
- Error propagation
- Dynamic routing (via callbacks)
"""

import asyncio
import pytest
from datetime import datetime
from app.core import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    StepContext,
    StepOutput,
    StepStatus,
    WorkflowStatus,
    create_workflow_engine,
)


class TestTopologicalSort:
    """Test Kahn's topological sort implementation."""

    def test_simple_linear_dag(self):
        """Test simple linear DAG: step1 → step2 → step3."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s2"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf1",
            name="Linear Workflow",
            description="Test",
            steps=steps,
        )
        
        batches = engine._topological_sort(workflow)
        
        # Should have 3 batches (one step per batch in linear DAG)
        assert len(batches) == 3
        assert batches[0] == ["s1"]
        assert batches[1] == ["s2"]
        assert batches[2] == ["s3"]

    def test_parallel_dag(self):
        """Test DAG with parallel execution: s1 → {s2, s3} → s4."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s1"]),
            WorkflowStep(id="s4", agent_role="director", task_type="decision", depends_on=["s2", "s3"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf2",
            name="Parallel Workflow",
            description="Test",
            steps=steps,
        )
        
        batches = engine._topological_sort(workflow)
        
        # Should have 3 batches: [s1], [s2, s3], [s4]
        assert len(batches) == 3
        assert batches[0] == ["s1"]
        assert set(batches[1]) == {"s2", "s3"}
        assert batches[2] == ["s4"]

    def test_isolated_steps(self):
        """Test handling of isolated steps (no dependencies)."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design"),  # No dependency
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf3",
            name="Isolated Steps Workflow",
            description="Test",
            steps=steps,
        )
        
        batches = engine._topological_sort(workflow)
        
        # First batch should contain independent steps (s1 and s2)
        assert len(batches) >= 2
        assert "s1" in batches[0]
        assert "s2" in batches[0]


class TestCycleDetection:
    """Test cycle detection in DAGs."""

    def test_no_cycle_simple(self):
        """Test simple DAG with no cycles."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        assert not engine._has_cycle(workflow)

    def test_direct_cycle(self):
        """Test detection of direct cycle: s1 → s2 → s1."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis", depends_on=["s2"]),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        assert engine._has_cycle(workflow)

    def test_self_cycle(self):
        """Test detection of self-cycle: s1 → s1."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        assert engine._has_cycle(workflow)

    def test_indirect_cycle(self):
        """Test detection of indirect cycle: s1 → s2 → s3 → s1."""
        engine = create_workflow_engine()
        
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis", depends_on=["s3"]),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s2"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        assert engine._has_cycle(workflow)


class TestWorkflowExecution:
    """Test workflow execution with concurrent processing."""

    @pytest.mark.asyncio
    async def test_simple_execution(self):
        """Test simple linear workflow execution."""
        engine = create_workflow_engine()
        
        # Register a simple executor
        async def dummy_executor(context: StepContext) -> StepOutput:
            """Dummy executor that returns success."""
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content=f"Output from {context.step_id}",
            )
        
        engine.register_step_executor(dummy_executor)
        
        # Create simple workflow
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify
        assert result.is_success()
        assert len(result.step_outputs) == 2
        assert result.step_outputs["s1"].status == StepStatus.COMPLETED
        assert result.step_outputs["s2"].status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execution_fails_without_executor(self):
        """Test that execution fails without registered executor."""
        engine = create_workflow_engine()
        
        steps = [WorkflowStep(id="s1", agent_role="pm", task_type="analysis")]
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Step executor not registered"):
            await engine.execute(workflow, {})

    @pytest.mark.asyncio
    async def test_execution_with_cycle_fails(self):
        """Test that cyclic workflow raises ValueError."""
        engine = create_workflow_engine()
        
        async def dummy_executor(context: StepContext) -> StepOutput:
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content="output",
            )
        
        engine.register_step_executor(dummy_executor)
        
        # Create cyclic workflow
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis", depends_on=["s2"]),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Circular dependency"):
            await engine.execute(workflow, {})

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test that parallel steps execute concurrently."""
        engine = create_workflow_engine()
        
        execution_times: dict = {}
        
        async def tracked_executor(context: StepContext) -> StepOutput:
            """Executor that records execution time."""
            execution_times[context.step_id] = datetime.now()
            await asyncio.sleep(0.1)  # Simulate work
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content="output",
            )
        
        engine.register_step_executor(tracked_executor)
        
        # Create workflow: s1 → {s2, s3}
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
            WorkflowStep(id="s3", agent_role="qa", task_type="review", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify
        assert result.is_success()
        # s2 and s3 should have similar execution times (parallel)
        time_s2 = execution_times["s2"]
        time_s3 = execution_times["s3"]
        time_diff = abs((time_s2 - time_s3).total_seconds())
        assert time_diff < 0.1  # Should execute at nearly the same time

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test that step errors are captured."""
        engine = create_workflow_engine()
        
        async def failing_executor(context: StepContext) -> StepOutput:
            """Executor that fails."""
            if context.step_id == "s2":
                raise Exception("Test error")
            return StepOutput(
                step_id=context.step_id,
                role="test",
                status=StepStatus.COMPLETED,
                output_type="text",
                content="output",
            )
        
        engine.register_step_executor(failing_executor)
        
        # Create workflow with failing step
        steps = [
            WorkflowStep(id="s1", agent_role="pm", task_type="analysis"),
            WorkflowStep(id="s2", agent_role="architect", task_type="design", depends_on=["s1"]),
        ]
        
        workflow = WorkflowDefinition(
            id="wf",
            name="Test",
            description="Test",
            steps=steps,
        )
        
        # Execute
        result = await engine.execute(workflow, {})
        
        # Verify
        assert not result.is_success()
        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
        assert result.step_outputs["s2"].status == StepStatus.FAILED


class TestStepContext:
    """Test StepContext utilities."""

    def test_get_upstream_output(self):
        """Test retrieving upstream output."""
        output = StepOutput(
            step_id="s1",
            role="pm",
            status=StepStatus.COMPLETED,
            output_type="text",
            content="test output",
        )
        
        context = StepContext(
            step_id="s2",
            workflow_id="wf",
            inputs={},
            previous_outputs={"s1": output},
        )
        
        assert context.get_upstream_output("s1") == output
        assert context.get_upstream_content("s1") == "test output"
        assert context.get_upstream_output("s3") is None


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
