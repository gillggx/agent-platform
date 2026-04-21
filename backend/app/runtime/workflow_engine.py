from typing import Dict, List, Optional, Any, Set
import uuid
import asyncio
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta

from app.models.workflow_run import WorkflowRun, StepExecution
from app.models.workflow_template import WorkflowTemplate
from app.models.agent_definition import AgentDefinition
from app.models.project import Project
from app.models.artifact import Artifact
from app.runtime.session_manager import session_manager, Context
from app.services.llm_adapter import llm_adapter
from app.core.config import settings
from app.db.base import AsyncSessionLocal

# Keep strong references to background tasks so GC doesn't collect them mid-execution.
# Python 3.10+ only keeps weak refs to tasks; without this they can be GC'd before completing.
_background_tasks: Set[asyncio.Task] = set()


def _create_background_task(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


@dataclass
class WorkflowStep:
    """Workflow step definition"""
    id: str
    agent_role: str
    task_type: str
    prompt_override: Optional[str]
    depends_on: List[str]
    routing: Dict[str, Any]
    loop: Dict[str, Any]
    config: Dict[str, Any] = None  # extra step config (e.g. dialogue min_rounds)


@dataclass 
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    guardrails: Dict[str, Any]


class WorkflowEngine:
    """DAG + LLM dynamic routing workflow engine"""

    def __init__(self):
        pass

    def _add_log(self, step_executions: dict, message: str):
        """Append a log entry to step_executions['_log'] in-memory (no commit — caller commits)"""
        log = list(step_executions.get("_log", []))
        log.append({"time": datetime.utcnow().strftime("%H:%M:%S"), "msg": message})
        step_executions["_log"] = log[-50:]

    async def start_workflow(
        self,
        db: AsyncSession,
        project_id: str,
        template_id: str,
        user_input: str,
        user_id: str,
    ) -> WorkflowRun:
        """
        Start a new workflow execution
        """
        
        # Load template
        result = await db.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        template = result.scalar_one()
        
        # Parse workflow definition
        workflow_def = self._parse_workflow_definition(template.definition)
        
        # Create workflow run
        workflow_run = WorkflowRun(
            project_id=project_id,
            template_id=template_id,
            template_snapshot=template.definition,
            user_input=user_input,
            status="running",
            step_executions={},
            current_steps=[],
        )
        
        db.add(workflow_run)
        await db.commit()
        await db.refresh(workflow_run)
        
        # Find root steps (no dependencies)
        root_steps = [step for step in workflow_def.steps if not step.depends_on]
        
        # Get project org_id for agent lookup
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one()
        
        # Start root steps asynchronously
        run_id = workflow_run.id
        print(f"\n{'*'*60}")
        print(f"[WORKFLOW START] 🚀 {workflow_def.name}  Run: {run_id}")
        print(f"{'*'*60}\n")

        # Seed initial log
        se = dict(workflow_run.step_executions or {})
        se["_log"] = [{"time": datetime.utcnow().strftime("%H:%M:%S"), "msg": f"🚀 工作流程啟動：{workflow_def.name}"}]
        workflow_run.step_executions = se
        flag_modified(workflow_run, "step_executions")
        await db.commit()

        for step in root_steps:
            _create_background_task(
                self._execute_step_in_new_session(
                    run_id, step, workflow_def, user_input, project.org_id
                )
            )

        return workflow_run
    
    async def _execute_step_in_new_session(
        self,
        run_id: str,
        step: WorkflowStep,
        workflow_def: WorkflowDefinition,
        user_input: str,
        org_id: str,
    ):
        """Execute a step using a fresh DB session (for async tasks)"""
        import traceback
        async with AsyncSessionLocal() as db:
            try:
                await self._dispatch_step(db, run_id, step, workflow_def, user_input, org_id)
            except Exception as e:
                err_msg = f"❌ [{step.id}] 執行失敗：{e}"
                print(f"\n[STEP ERROR] {err_msg}")
                traceback.print_exc()
                # Write failure into DB so it's visible in the workflow UI
                try:
                    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
                    wf = result.scalar_one_or_none()
                    if wf:
                        se = dict(wf.step_executions or {})
                        self._add_log(se, err_msg)
                        wf.step_executions = se
                        flag_modified(wf, "step_executions")
                        wf.status = "failed"
                        await db.commit()
                except Exception as db_err:
                    print(f"[STEP ERROR] Failed to write error to DB: {db_err}")
    
    async def on_step_complete(
        self,
        db: AsyncSession,
        run_id: str,
        step_id: str,
        artifact: Artifact,
        workflow_def: WorkflowDefinition,
        org_id: str,
    ):
        """Handle step completion and determine next steps"""

        # Load workflow run
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == run_id)
        )
        workflow_run = result.scalar_one()

        completed_step = next((s for s in workflow_def.steps if s.id == step_id), None)
        if not completed_step:
            return

        # Update step execution count
        step_executions = dict(workflow_run.step_executions or {})
        if step_id not in step_executions:
            step_executions[step_id] = {}
        current_count = step_executions[step_id].get("count", 0)
        step_executions[step_id]["count"] = current_count + 1
        step_executions[step_id]["last_status"] = "completed"
        step_executions[step_id]["artifact_id"] = str(artifact.id)

        # Embed done log inline (no separate commit)
        log_done = f"✅ [{step_id}] 完成，產出 {len(artifact.content_md)} 字"
        self._add_log(step_executions, log_done)
        print(f"\n[AGENT DONE] {log_done}\n")

        # Remove from current steps
        current_steps = list(workflow_run.current_steps or [])
        if step_id in current_steps:
            current_steps.remove(step_id)

        # Check guardrails — max_total_steps (skip _log and other non-dict entries)
        total_steps = sum(
            v.get("count", 0) for v in step_executions.values() if isinstance(v, dict)
        )
        if total_steps >= workflow_def.guardrails.get("max_total_steps", settings.max_workflow_steps):
            workflow_run.status = "failed"
            workflow_run.step_executions = step_executions
            workflow_run.current_steps = current_steps
            await db.commit()
            return

        # Check guardrails — timeout_minutes (3.5.5)
        timeout_minutes = workflow_def.guardrails.get("timeout_minutes")
        if timeout_minutes and workflow_run.created_at:
            elapsed = datetime.utcnow() - workflow_run.created_at
            if elapsed > timedelta(minutes=timeout_minutes):
                workflow_run.status = "timeout"
                workflow_run.step_executions = step_executions
                workflow_run.current_steps = current_steps
                await db.commit()
                return

        # Check if this step requires human approval before continuing
        require_human_approval = workflow_def.guardrails.get("require_human_approval", [])
        if step_id in require_human_approval:
            # Pause and wait for human approval
            step_executions[step_id]["waiting_approval"] = True
            log_wait = f"⏸️ [{step_id}] 等待人工審批..."
            step_executions.setdefault("_log", []).append({"time": datetime.utcnow().strftime("%H:%M:%S"), "msg": log_wait})
            print(f"[APPROVAL WAIT] {log_wait}")
            workflow_run.status = "waiting_approval"
            workflow_run.step_executions = step_executions
            flag_modified(workflow_run, "step_executions")
            workflow_run.current_steps = current_steps
            await db.commit()
            return

        # PRE-UPDATE: expose our locally-built step_executions to workflow_run BEFORE
        # calling _determine_next_steps, so _llm_route reads and mutates the complete state
        workflow_run.step_executions = step_executions
        flag_modified(workflow_run, "step_executions")

        # Determine next steps based on routing (_llm_route may append to step_executions in-memory)
        next_step_ids = await self._determine_next_steps(
            db, workflow_run, completed_step, artifact, workflow_def
        )

        # Use latest in-memory state (may have been updated by _llm_route)
        step_executions = workflow_run.step_executions or {}

        # Collect steps to dispatch (but DON'T create tasks yet — must commit first)
        steps_to_dispatch = []
        for next_step_id in next_step_ids:
            next_step = next((s for s in workflow_def.steps if s.id == next_step_id), None)
            if not next_step:
                continue

            # Check if all dependencies are satisfied
            if self._check_dependencies_satisfied(next_step, step_executions):
                current_steps.append(next_step_id)
                steps_to_dispatch.append(next_step)

        # Commit all state changes FIRST — before dispatching new tasks
        # (tasks use fresh sessions; they must read committed state, not a racing write)
        workflow_run.step_executions = step_executions
        flag_modified(workflow_run, "step_executions")
        workflow_run.current_steps = current_steps

        # Check if workflow is complete
        if not current_steps and not self._has_pending_steps(workflow_def, step_executions):
            workflow_run.status = "completed"
            log_end = "🎉 所有 Agent 完成，工作流程結束！"
            step_executions.setdefault("_log", []).append({"time": datetime.utcnow().strftime("%H:%M:%S"), "msg": log_end})
            print(f"\n{'*'*60}\n[WORKFLOW DONE] {log_end}\n{'*'*60}\n")

        await db.commit()

        # NOW dispatch next steps — DB is committed, fresh sessions will read correct state
        for next_step in steps_to_dispatch:
            _create_background_task(
                self._execute_step_in_new_session(
                    run_id, next_step, workflow_def, workflow_run.user_input, org_id
                )
            )

    async def resume_after_approval(
        self,
        db: AsyncSession,
        run_id: str,
        approved: bool,
        feedback: Optional[str],
    ):
        """Resume workflow after human approval decision"""

        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.id == run_id)
        )
        workflow_run = result.scalar_one_or_none()
        if not workflow_run or workflow_run.status != "waiting_approval":
            return False

        # Find the step that was waiting for approval
        step_executions = dict(workflow_run.step_executions or {})
        waiting_step_id = None
        for sid, info in step_executions.items():
            if isinstance(info, dict) and info.get("waiting_approval"):
                waiting_step_id = sid
                break

        if not waiting_step_id:
            return False

        # Clear the waiting flag
        step_executions[waiting_step_id].pop("waiting_approval", None)
        if feedback:
            step_executions[waiting_step_id]["human_feedback"] = feedback

        workflow_run.status = "running"
        workflow_run.step_executions = step_executions
        flag_modified(workflow_run, "step_executions")
        await db.commit()

        # Parse workflow definition
        workflow_def = self._parse_workflow_definition(workflow_run.template_snapshot)
        completed_step = next((s for s in workflow_def.steps if s.id == waiting_step_id), None)
        if not completed_step:
            return False

        # Get project org_id
        project_result = await db.execute(
            select(Project).where(Project.id == workflow_run.project_id)
        )
        project = project_result.scalar_one()

        if approved:
            # Load artifact for routing decision
            artifact_id = step_executions[waiting_step_id].get("artifact_id")
            artifact = None
            if artifact_id:
                artifact_result = await db.execute(
                    select(Artifact).where(Artifact.id == artifact_id)
                )
                artifact = artifact_result.scalar_one_or_none()

            if artifact:
                next_step_ids = await self._determine_next_steps(
                    db, workflow_run, completed_step, artifact, workflow_def
                )
                # Use latest in-memory state (may have been updated by _llm_route)
                step_executions = workflow_run.step_executions or {}
                current_steps = list(workflow_run.current_steps or [])
                steps_to_dispatch_resume = []
                for next_step_id in next_step_ids:
                    next_step = next((s for s in workflow_def.steps if s.id == next_step_id), None)
                    if next_step and self._check_dependencies_satisfied(next_step, step_executions):
                        current_steps.append(next_step_id)
                        steps_to_dispatch_resume.append(next_step)
                workflow_run.step_executions = step_executions
                flag_modified(workflow_run, "step_executions")
                workflow_run.current_steps = current_steps
                if not current_steps and not self._has_pending_steps(workflow_def, step_executions):
                    workflow_run.status = "completed"
                await db.commit()
                # Dispatch AFTER commit
                for next_step in steps_to_dispatch_resume:
                    _create_background_task(
                        self._execute_step_in_new_session(
                            run_id, next_step, workflow_def, workflow_run.user_input, project.org_id
                        )
                    )
        else:
            # Rejected: find pm_revise step (or first step that handles revisions)
            revise_step = next(
                (s for s in workflow_def.steps if s.task_type == "revise" and s.agent_role == "pm"),
                None
            )
            if revise_step:
                current_steps = list(workflow_run.current_steps or [])
                current_steps.append(revise_step.id)
                workflow_run.current_steps = current_steps
                # Pass feedback as director_notes via context
                user_input = workflow_run.user_input or ""
                if feedback:
                    user_input = f"{user_input}\n\n[Director 反饋]: {feedback}"
                _create_background_task(
                    self._execute_step_in_new_session(
                        run_id, revise_step, workflow_def, user_input, project.org_id
                    )
                )
                await db.commit()

        return True
    
    async def _determine_next_steps(
        self,
        db: AsyncSession,
        workflow_run: WorkflowRun,
        completed_step: WorkflowStep,
        artifact: Artifact,
        workflow_def: WorkflowDefinition,
    ) -> List[str]:
        """Determine next steps based on routing configuration"""
        
        routing = completed_step.routing
        
        if routing.get("type") == "static":
            return routing.get("next_steps", [])
        
        elif routing.get("type") == "llm_decision":
            return await self._llm_route(db, workflow_run, completed_step, artifact, workflow_def)
        
        else:
            return []
    
    def _extract_decision_marker(self, content: str) -> Optional[str]:
        """
        Scan artifact content for an explicit decision marker.
        Looks for patterns like:
          **決策：APPROVE**
          **決策：RETURN_TO_PM**
          **決策：REJECT**
          **Decision: APPROVE**
        Returns the last match (since final decision is usually at the end),
        or None if no marker found.
        """
        import re
        # Allow for optional spaces, both 中英文 colons, and **Decision** variant
        pattern = re.compile(
            r"\*\*\s*(?:決策|Decision)\s*[:：]\s*(APPROVE|RETURN_TO_PM|REJECT)\s*\*\*",
            re.IGNORECASE,
        )
        matches = pattern.findall(content or "")
        return matches[-1].upper() if matches else None

    def _match_option_by_label(self, label: str, options: List[dict]) -> Optional[dict]:
        """Find option whose 'label' matches the decision keyword (case-insensitive)."""
        lbl = (label or "").strip().upper()
        for opt in options:
            if (opt.get("label") or "").strip().upper() == lbl:
                return opt
        return None

    async def _llm_route(
        self,
        db: AsyncSession,
        workflow_run: WorkflowRun,
        completed_step: WorkflowStep,
        artifact: Artifact,
        workflow_def: WorkflowDefinition,
    ) -> List[str]:
        """Route next step based on the agent's decision marker.

        Strategy (layered, cheap → expensive):
          1. Regex for **決策：XXX** marker in the artifact (primary).
          2. LLM classifier on artifact TAIL (last 2000 chars) as fallback.
          3. Static default = first option (usually APPROVE).
        """
        routing = completed_step.routing
        decision_prompt = routing.get("decision_prompt", "Decide the next step in the workflow.")
        options = routing.get("options", [])

        if not options:
            return []

        content = artifact.content_md or ""
        chosen_option: Optional[dict] = None
        decision_source = "default"
        raw_choice = ""

        # ── Layer 1: Regex marker extraction ─────────────────────────────
        marker = self._extract_decision_marker(content)
        if marker:
            matched = self._match_option_by_label(marker, options)
            if matched:
                chosen_option = matched
                decision_source = "regex_marker"
                raw_choice = marker

        # ── Layer 2: LLM classifier on the TAIL of the artifact ──────────
        if chosen_option is None:
            tail = content[-2000:] if len(content) > 2000 else content
            context_parts = [
                f"Workflow: {workflow_def.name}",
                f"Completed step: {completed_step.id} ({completed_step.agent_role})",
                f"Generated artifact type: {artifact.artifact_type}",
                "",
                "Artifact ending (the decision marker, if any, is here):",
                "---",
                tail,
                "---",
                "",
                decision_prompt,
                "",
                "Available options (pick the one matching the agent's actual decision):",
            ]
            for i, option in enumerate(options):
                context_parts.append(
                    f"{i+1}. {option['label']}: {option.get('condition_hint', '')}"
                )
            context_parts += [
                "",
                "If the artifact contains a marker like **決策：APPROVE** or "
                "**決策：RETURN_TO_PM**, use it. If multiple markers exist, use the LAST.",
                "Respond with ONLY the option number (1, 2, ...).",
            ]

            try:
                response = await llm_adapter.complete(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a routing classifier. Pick the option matching the agent's actual decision. Reply with a single number.",
                        },
                        {"role": "user", "content": "\n".join(context_parts)},
                    ],
                    max_tokens=10,
                    temperature=0.0,
                )
                raw_choice = response.content.strip()
                try:
                    choice_num = int(raw_choice)
                    if 1 <= choice_num <= len(options):
                        chosen_option = options[choice_num - 1]
                        decision_source = "llm_classifier"
                except ValueError:
                    pass
            except Exception as e:
                print(f"[ROUTING] LLM classifier failed: {e}")

        # ── Layer 3: Default to first option ─────────────────────────────
        if chosen_option is None:
            chosen_option = options[0]
            decision_source = "default_first_option"

        try:
            log_route = (
                f"🔀 [{completed_step.id}] 路由決策：{chosen_option['label']} → "
                f"{chosen_option['target_step']}（來源：{decision_source}）"
            )
            print(f"[ROUTING] {log_route}")

            # Embed route log + routing_decision in-memory (no separate commit — caller commits)
            se = workflow_run.step_executions or {}
            self._add_log(se, log_route)
            if completed_step.id not in se:
                se[completed_step.id] = {}
            se[completed_step.id]["routing_decision"] = {
                "raw_response": raw_choice,
                "chosen_label": chosen_option["label"],
                "target_step": chosen_option["target_step"],
                "decided_at": datetime.utcnow().isoformat(),
                "source": decision_source,
            }
            workflow_run.step_executions = se
            flag_modified(workflow_run, "step_executions")

            # Also persist to the most recent StepExecution row for this step
            await db.execute(
                update(StepExecution)
                .where(
                    StepExecution.run_id == workflow_run.id,
                    StepExecution.step_id == completed_step.id,
                    StepExecution.routing_decision.is_(None),
                )
                .values(routing_decision=se[completed_step.id]["routing_decision"])
            )

            return [chosen_option["target_step"]]

        except Exception as e:
            print(f"LLM routing failed: {e}")
            return [options[0]["target_step"]] if options else []
    
    def _check_dependencies_satisfied(
        self,
        step: WorkflowStep,
        step_executions: Dict[str, Any],
    ) -> bool:
        """Check if all dependencies for a step are satisfied"""
        
        if not step.depends_on:
            return True
        
        for dep_step_id in step.depends_on:
            if dep_step_id not in step_executions:
                return False
            if step_executions[dep_step_id]["last_status"] != "completed":
                return False
        
        return True
    
    async def _dispatch_step(
        self,
        db: AsyncSession,
        run_id: str,
        step: WorkflowStep,
        workflow_def: WorkflowDefinition,
        user_input: str,
        org_id: str,
    ):
        """Dispatch a workflow step to an agent"""

        try:
            # Load workflow run
            result = await db.execute(
                select(WorkflowRun).where(WorkflowRun.id == run_id)
            )
            workflow_run = result.scalar_one()

            # Handle dialogue step — two-PM back-and-forth
            if step.task_type == "dialogue":
                await self._execute_dialogue_step(db, run_id, step, workflow_def, user_input, org_id)
                return

            # Handle system/export step — no LLM needed, just mark complete
            if step.agent_role == "system" or step.task_type == "export":
                step_executions = dict(workflow_run.step_executions or {})
                if step.id not in step_executions:
                    step_executions[step.id] = {"count": 0, "last_status": "completed"}
                step_executions[step.id]["count"] += 1
                step_executions[step.id]["last_status"] = "completed"
                current_steps = list(workflow_run.current_steps or [])
                if step.id in current_steps:
                    current_steps.remove(step.id)
                workflow_run.step_executions = step_executions
                workflow_run.current_steps = current_steps
                if not current_steps and not self._has_pending_steps(workflow_def, step_executions):
                    workflow_run.status = "completed"
                    log_end = "🎉 所有 Agent 完成，工作流程結束！"
                    self._add_log(step_executions, log_end)
                    workflow_run.step_executions = step_executions
                    flag_modified(workflow_run, "step_executions")
                    print(f"\n{'*'*60}\n[WORKFLOW DONE] {log_end}\n{'*'*60}\n")
                await db.commit()
                return

            # Find agent definition for this step (system agents have org_id=NULL)
            result = await db.execute(
                select(AgentDefinition).where(
                    AgentDefinition.role == step.agent_role,
                    AgentDefinition.is_system == "true",
                )
            )
            agent_def = result.scalar_one_or_none()

            if not agent_def:
                print(f"No agent definition found for role: {step.agent_role}")
                return
            
            # Check loop constraints
            step_executions = dict(workflow_run.step_executions or {})
            current_iteration = step_executions.get(step.id, {}).get("count", 0) + 1
            max_iterations = step.loop.get("max_iterations", settings.max_loop_iterations)
            
            if current_iteration > max_iterations:
                # Escalate to configured step, or mark workflow completed if no escalation
                escalate_to = step.loop.get("escalate_to")
                escalate_step = next((s for s in workflow_def.steps if s.id == escalate_to), None) if escalate_to else None
                if escalate_step:
                    await self._dispatch_step(db, run_id, escalate_step, workflow_def, user_input, org_id)
                else:
                    # No escalation defined: force-complete the workflow
                    log_max = f"⚠️ [{step.id}] 已達最大迭代次數 ({max_iterations})，工作流程強制完成"
                    print(f"\n[LOOP MAX] {log_max}\n")
                    se = dict(workflow_run.step_executions or {})
                    self._add_log(se, log_max)
                    workflow_run.step_executions = se
                    flag_modified(workflow_run, "step_executions")
                    workflow_run.status = "completed"
                    await db.commit()
                return
            
            # Update current_steps AND embed start log — all in one commit
            log_start = f"🤖 [{step.id}] {agent_def.display_name} 開始執行（{step.task_type}）"
            current_steps = list(workflow_run.current_steps or [])
            if step.id not in current_steps:
                current_steps.append(step.id)
            se = dict(workflow_run.step_executions or {})
            self._add_log(se, log_start)
            workflow_run.current_steps = current_steps
            workflow_run.step_executions = se
            flag_modified(workflow_run, "step_executions")
            print(f"\n{'='*60}\n[AGENT START] {log_start}\n{'='*60}")
            await db.commit()

            # Create agent session
            session = await session_manager.create_session(
                db, workflow_run.project_id, agent_def.id, workflow_run.id
            )

            # Create step execution record
            step_execution = StepExecution(
                run_id=workflow_run.id,
                step_id=step.id,
                iteration=current_iteration,
                session_id=session.id,
                status="running",
                started_at=datetime.utcnow(),
            )

            db.add(step_execution)
            await db.commit()

            # Load upstream artifacts
            upstream_artifacts = await self._load_upstream_artifacts(db, workflow_run, step)

            # Build context
            context = Context(
                project_id=workflow_run.project_id,
                user_input=user_input,
                upstream_artifacts=upstream_artifacts,
                director_notes=None,
                iteration=current_iteration,
                max_iterations=max_iterations,
            )

            # Execute agent
            artifact = await session_manager.dispatch(db, session.id, context, step.task_type)

            if artifact:
                # Mark step execution as completed (done log is embedded inside on_step_complete)
                step_execution.status = "completed"
                step_execution.completed_at = datetime.utcnow()
                await db.commit()

                # Trigger next steps (done log embedded inside on_step_complete)
                await self.on_step_complete(db, run_id, step.id, artifact, workflow_def, org_id)
            else:
                # Mark as failed — embed fail log in the same commit
                log_fail = f"❌ [{step.id}] {agent_def.display_name} 執行失敗（無產出）"
                print(f"\n[AGENT FAIL] {log_fail}\n")
                step_execution.status = "failed"
                se2 = dict(workflow_run.step_executions or {})
                self._add_log(se2, log_fail)
                workflow_run.step_executions = se2
                flag_modified(workflow_run, "step_executions")
                await db.commit()

        except Exception as e:
            print(f"\n[AGENT ERROR] 💥 {step.id}: {e}")
            import traceback
            traceback.print_exc()
    
    async def _execute_dialogue_step(
        self,
        db: AsyncSession,
        run_id: str,
        step: WorkflowStep,
        workflow_def: WorkflowDefinition,
        user_input: str,
        org_id: str,
    ):
        """Two-PM dialogue: PM proposes, PM Critic challenges, N rounds, final clean synthesis"""
        from app.models.organization import Organization

        result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
        workflow_run = result.scalar_one()

        config = step.config or {}
        min_rounds = config.get("min_rounds", 5)

        # Mark step as running
        se = dict(workflow_run.step_executions or {})
        current_steps = list(workflow_run.current_steps or [])
        if step.id not in current_steps:
            current_steps.append(step.id)
        self._add_log(se, f"🤖 [{step.id}] PM 雙人協作開始（目標 {min_rounds} 輪對談）")
        workflow_run.current_steps = current_steps
        workflow_run.step_executions = se
        flag_modified(workflow_run, "step_executions")
        await db.commit()

        # Load agent souls
        pm_result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.role == "pm", AgentDefinition.is_system == "true")
        )
        pm_agent = pm_result.scalar_one_or_none()
        critic_result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.role == "pm_critic", AgentDefinition.is_system == "true")
        )
        critic_agent = critic_result.scalar_one_or_none()

        pm_soul = (pm_agent.soul if pm_agent and pm_agent.soul else
                   "你是資深產品經理，負責撰寫清晰、可落地的 Product Spec，使用繁體中文。")
        critic_soul = (critic_agent.soul if critic_agent and critic_agent.soul else
                       "你是魔鬼代言人型 PM，負責從各角度挑戰並完善 Product Spec，使用繁體中文。")
        pm_config = (pm_agent.config or {}) if pm_agent else {}
        temperature = pm_config.get("temperature", 0.7)
        max_tokens = pm_config.get("max_tokens", 4096)

        # Resolve org LLM config
        project_result = await db.execute(select(Project).where(Project.id == workflow_run.project_id))
        project = project_result.scalar_one_or_none()
        org_config = None
        if project:
            org_result = await db.execute(select(Organization).where(Organization.id == project.org_id))
            org = org_result.scalar_one_or_none()
            org_config = (org.llm_config or {}) if org else None

        # Load upstream artifacts
        upstream_artifacts = await self._load_upstream_artifacts(db, workflow_run, step)
        upstream_context = ""
        for a in upstream_artifacts:
            upstream_context += f"\n\n[{a['agent_role']} - {a['artifact_type']}]\n{a['content_md'][:3000]}"

        dialogue_history = []  # [{"speaker": "pm"|"critic", "content": str}]

        def build_ctx():
            parts = []
            for t in dialogue_history:
                label = "【PM 提案者】" if t["speaker"] == "pm" else "【PM 挑戰者】"
                parts.append(f"{label}\n{t['content']}")
            return "\n\n---\n\n".join(parts)

        async def log(msg):
            wf = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))).scalar_one()
            s = dict(wf.step_executions or {})
            self._add_log(s, msg)
            wf.step_executions = s
            flag_modified(wf, "step_executions")
            await db.commit()

        # Round 0: PM initial draft (structure-level spec, not exhaustive)
        await log(f"📝 [{step.id}] PM 起草初版 spec 架構...")
        init_prompt = (
            f"使用者需求：{user_input}"
            + (f"\n\n上游資料：{upstream_context}" if upstream_context else "")
            + "\n\n請起草初版 Product Spec 架構。包含主要功能模組、核心 User Story 及關鍵驗收標準。"
            "這份草稿將接受挑戰者逐輪審視，請先建立骨架，細節後續補強。"
        )
        r0 = await llm_adapter.complete(
            messages=[{"role": "system", "content": pm_soul}, {"role": "user", "content": init_prompt}],
            temperature=temperature, max_tokens=3500, org_config=org_config,
        )
        initial_draft = r0.content
        dialogue_history.append({"speaker": "pm", "content": initial_draft, "label": "初版草稿"})
        await log(f"💬 [{step.id}] 初稿完成，開始 {min_rounds} 輪雙人討論...")

        # Alternating rounds — critic challenges, PM responds to specific points only
        for rnd in range(1, min_rounds + 1):
            # Critic: challenges specific aspects, based on initial draft + PM responses so far
            await log(f"🔍 第 {rnd}/{min_rounds} 輪：PM 挑戰者審視中...")
            prev_critic_pts = "\n".join(
                f"- 第{i+1}輪：{t['content'][:200]}"
                for i, t in enumerate(t for t in dialogue_history if t["speaker"] == "critic")
            )
            rc = await llm_adapter.complete(
                messages=[
                    {"role": "system", "content": critic_soul},
                    {"role": "user", "content": (
                        f"使用者需求：{user_input}\n\n"
                        f"PM 初版草稿：\n\n{initial_draft[:2000]}\n\n"
                        + (f"PM 前幾輪的補充回應摘要：\n" + "\n".join(
                            f"第{i+1}輪PM回應：{t['content'][:300]}"
                            for i, t in enumerate(x for x in dialogue_history if x["speaker"] == "pm" and x.get("label") != "初版草稿")
                        ) + "\n\n" if any(x["speaker"] == "pm" and x.get("label") != "初版草稿" for x in dialogue_history) else "")
                        + (f"前幾輪已提出的挑戰（不要重複這些面向）：\n{prev_critic_pts}\n\n" if prev_critic_pts else "")
                        + f"請從**新的角度**提出 2-4 個具體挑戰問題（第 {rnd}/{min_rounds} 輪）。"
                    )},
                ],
                temperature=temperature, max_tokens=800, org_config=org_config,
            )
            dialogue_history.append({"speaker": "critic", "content": rc.content, "label": f"第{rnd}輪挑戰"})

            # PM responds — focused response to THIS round's challenges only, no full rewrite
            await log(f"✏️ 第 {rnd}/{min_rounds} 輪：PM 回應挑戰中...")
            rp = await llm_adapter.complete(
                messages=[
                    {"role": "system", "content": pm_soul},
                    {"role": "user", "content": (
                        f"使用者需求：{user_input}\n\n"
                        f"挑戰者在第 {rnd} 輪提出以下問題：\n\n{rc.content}\n\n"
                        "請**逐點回應**這些挑戰，說明你的設計決策或補充規格細節。"
                        "不需要重寫完整 spec，只針對這輪的問題作出具體回應。"
                    )},
                ],
                temperature=temperature, max_tokens=1200, org_config=org_config,
            )
            dialogue_history.append({"speaker": "pm", "content": rp.content, "label": f"第{rnd}輪回應"})

        # Final synthesis: PM writes clean final spec incorporating all discussion points
        await log(f"✅ [{step.id}] {min_rounds} 輪討論完成，PM 整合產出最終版 spec...")
        # Build compact discussion summary for synthesis reference
        discussion_summary = "\n\n".join(
            f"**{t['label']}**\n{t['content'][:500]}"
            for t in dialogue_history
            if t.get("label") != "初版草稿"
        )
        final_r = await llm_adapter.complete(
            messages=[
                {"role": "system", "content": pm_soul},
                {"role": "user", "content": (
                    f"使用者需求：{user_input}\n\n"
                    f"你的初版草稿架構：\n\n{initial_draft[:1500]}\n\n"
                    f"討論過程中補充的要點（{min_rounds} 輪）：\n\n{discussion_summary[:2000]}\n\n"
                    "請整合以上所有內容，輸出正式的最終版 Product Spec。要求：\n"
                    "1. 直接輸出規格正文，無 meta 說明\n"
                    "2. 完整 Markdown 格式（標題、表格、清單）\n"
                    "3. 繁體中文\n"
                    "4. 初版骨架 + 討論補強的細節都要納入"
                )},
            ],
            temperature=temperature * 0.8, max_tokens=6000, org_config=org_config,
        )

        # Build dialogue record for artifact
        dialogue_md_parts = [f"# 雙 PM 協作討論記錄\n\n**討論輪數**：{min_rounds} 輪\n"]
        for t in dialogue_history:
            if t["speaker"] == "pm":
                dialogue_md_parts.append(f"### 🖊️ PM 提案者 — {t.get('label', '')}\n\n{t['content']}\n")
            else:
                dialogue_md_parts.append(f"### 🔍 PM 挑戰者 — {t.get('label', '')}\n\n{t['content']}\n")
        dialogue_md_parts.append("---\n\n# 最終版 Product Spec\n\n" + final_r.content)
        full_content = "\n\n".join(dialogue_md_parts)

        # Create artifact
        existing_r = await db.execute(
            select(Artifact).where(
                Artifact.project_id == workflow_run.project_id,
                Artifact.agent_role == "pm",
                Artifact.artifact_type == "product_spec",
                Artifact.status == "draft",
            ).order_by(Artifact.version.desc())
        )
        existing = existing_r.scalar_one_or_none()
        version = 1
        if existing:
            existing.status = "superseded"
            version = existing.version + 1

        artifact = Artifact(
            project_id=workflow_run.project_id,
            session_id=None,
            agent_role="pm",
            artifact_type="product_spec",
            version=version,
            content_md=full_content,
            status="draft",
            metadata={"task_type": "dialogue", "dialogue_rounds": min_rounds, "turns": len(dialogue_history)},
        )
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        # Update step_executions
        wf2 = (await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))).scalar_one()
        se2 = dict(wf2.step_executions or {})
        se2[step.id] = {
            "count": se2.get(step.id, {}).get("count", 0) + 1,
            "last_status": "completed",
            "artifact_id": str(artifact.id),
        }
        self._add_log(se2, f"📄 [{step.id}] PM 雙人協作完成，產出 v{version} spec")
        wf2.step_executions = se2
        flag_modified(wf2, "step_executions")
        cur = list(wf2.current_steps or [])
        if step.id in cur:
            cur.remove(step.id)
        wf2.current_steps = cur
        await db.commit()

        # Trigger next steps
        await self.on_step_complete(db, run_id, step.id, artifact, workflow_def, org_id)

    async def _load_upstream_artifacts(
        self,
        db: AsyncSession,
        workflow_run: WorkflowRun,
        current_step: WorkflowStep,
    ) -> List[Dict[str, Any]]:
        """Load artifacts from upstream steps"""
        
        artifacts = []
        
        for dep_step_id in current_step.depends_on:
            artifact = None

            # Fast path: dialogue steps store artifact_id directly in step_executions
            se = workflow_run.step_executions or {}
            direct_artifact_id = se.get(dep_step_id, {}).get("artifact_id") if isinstance(se.get(dep_step_id), dict) else None
            if direct_artifact_id:
                art_result = await db.execute(select(Artifact).where(Artifact.id == direct_artifact_id))
                artifact = art_result.scalar_one_or_none()

            # Fallback: find via StepExecution → session join
            if not artifact:
                result = await db.execute(
                    select(Artifact)
                    .join(StepExecution, Artifact.session_id == StepExecution.session_id)
                    .where(
                        StepExecution.run_id == workflow_run.id,
                        StepExecution.step_id == dep_step_id,
                        StepExecution.status == "completed",
                    )
                    .order_by(Artifact.created_at.desc())
                    .limit(1)
                )
                artifact = result.scalar_one_or_none()

            if artifact:
                artifacts.append({
                    "id": str(artifact.id),
                    "agent_role": artifact.agent_role,
                    "artifact_type": artifact.artifact_type,
                    "content_md": artifact.content_md,
                    "version": artifact.version,
                })
        
        return artifacts
    
    def _parse_workflow_definition(self, definition: Dict[str, Any]) -> WorkflowDefinition:
        """Parse JSON workflow definition into structured objects"""

        steps = []
        for step_data in definition["workflow"]["steps"]:
            step = WorkflowStep(
                id=step_data["id"],
                agent_role=step_data["agent_role"],
                task_type=step_data["task_type"],
                prompt_override=step_data.get("prompt_override"),
                depends_on=step_data.get("depends_on", []),
                routing=step_data.get("routing", {"type": "static", "next_steps": []}),
                loop=step_data.get("loop", {"enabled": False, "max_iterations": 2}),
                config=step_data.get("config", {}),
            )
            steps.append(step)

        workflow_def = WorkflowDefinition(
            id=definition["workflow"]["id"],
            name=definition["workflow"]["name"],
            description=definition["workflow"]["description"],
            steps=steps,
            guardrails=definition["workflow"].get("guardrails", {}),
        )

        # 3.1.3 — Detect circular dependencies via DFS
        cycle = self._detect_cycle(workflow_def)
        if cycle:
            raise ValueError(f"Circular dependency detected in workflow: {' -> '.join(cycle)}")

        return workflow_def

    def _detect_cycle(self, workflow_def: WorkflowDefinition) -> Optional[List[str]]:
        """DFS cycle detection on depends_on edges. Returns the cycle path if found, else None."""
        adjacency: Dict[str, List[str]] = {s.id: list(s.depends_on) for s in workflow_def.steps}
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            path.append(node)
            for neighbour in adjacency.get(node, []):
                if neighbour not in visited:
                    if dfs(neighbour):
                        return True
                elif neighbour in in_stack:
                    path.append(neighbour)
                    return True
            in_stack.discard(node)
            path.pop()
            return False

        for step in workflow_def.steps:
            if step.id not in visited:
                if dfs(step.id):
                    return path
        return None
    
    def _has_pending_steps(
        self,
        workflow_def: WorkflowDefinition,
        step_executions: Dict[str, Any],
    ) -> bool:
        """
        Return True only if there are steps whose ALL dependencies are completed
        but the step itself has not been dispatched yet.
        Steps that are unreachable via the chosen routing path are ignored.
        Non-root steps that were never dispatched are assumed unreachable (routing chose
        a different path). Only root steps that never ran are genuinely pending.
        """
        for step in workflow_def.steps:
            if step.id in step_executions:
                continue  # already executed or in progress
            # Root steps (no deps) that never ran are pending
            if not step.depends_on:
                return True
            # Non-root steps: if they weren't dispatched (not in step_executions or current_steps),
            # they are unreachable via the chosen routing path — do NOT treat as pending
        return False


# Global instance  
workflow_engine = WorkflowEngine()
