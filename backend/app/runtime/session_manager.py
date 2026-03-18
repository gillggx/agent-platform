from typing import List, Dict, Optional, Any
import uuid
import json
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.agent_session import AgentSession
from app.models.agent_definition import AgentDefinition
from app.models.knowledge_pack import KnowledgePack
from app.models.artifact import Artifact
from app.models.agent_memory import AgentMemory
from app.models.organization import Organization
from app.models.project import Project
from app.services.llm_adapter import llm_adapter, LLMResponse
from app.services.cache import cache
from app.core.config import settings


@dataclass
class Context:
    """Agent execution context"""
    project_id: str
    user_input: Optional[str]
    upstream_artifacts: List[Dict[str, Any]]
    director_notes: Optional[str]
    iteration: int
    max_iterations: int
    org_llm_config: Optional[Dict[str, Any]] = None  # 2.3.4: org-level LLM override


@dataclass
class Message:
    """Chat message"""
    role: str  # system | user | assistant
    content: str


class SessionManager:
    """Manages Agent Session lifecycle and LLM interactions"""
    
    def __init__(self):
        # Using in-memory cache instead of Redis
        self.cache = cache
    
    async def create_session(
        self,
        db: AsyncSession,
        project_id: str,
        agent_def_id: str,
        run_id: str,
    ) -> AgentSession:
        """Create new agent session and initialize memory"""
        
        memory_key = f"session:{uuid.uuid4()}:memory"
        
        # Create session record
        session = AgentSession(
            project_id=project_id,
            agent_def_id=agent_def_id,
            run_id=run_id,
            status="created",
            memory_key=memory_key,
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Initialize empty memory in cache
        await self.cache.set(
            session.memory_key,
            json.dumps([]),
            ex=int(timedelta(hours=24).total_seconds())  # 24 hour TTL
        )
        
        return session
    
    async def dispatch(
        self,
        db: AsyncSession,
        session_id: str,
        context: Context,
        task_type: str = "draft",
    ) -> Optional[Artifact]:
        """
        Execute agent: load knowledge, call LLM, create artifact
        
        Args:
            db: Database session
            session_id: Agent session ID
            context: Execution context
            task_type: Type of task (draft | review | revise | approve)
        
        Returns:
            Generated artifact or None if failed
        """
        
        # Load session
        result = await db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # 2.2.3 — Validate legal state transition (only created → active is valid)
        VALID_START_STATES = {"created"}
        if session.status not in VALID_START_STATES:
            raise ValueError(
                f"Invalid state transition: cannot dispatch session in '{session.status}' state. "
                f"Expected one of {VALID_START_STATES}."
            )

        # 2.2.4 — Session timeout check
        timeout_minutes = settings.agent_session_timeout_minutes
        if session.created_at and timeout_minutes:
            elapsed = datetime.utcnow() - session.created_at
            if elapsed > timedelta(minutes=timeout_minutes):
                session.status = "error"
                await db.commit()
                raise TimeoutError(
                    f"Session {session_id} has timed out after {elapsed.seconds // 60} minutes "
                    f"(limit: {timeout_minutes} min)"
                )

        try:
            # Update session status
            session.status = "active"
            await db.commit()
            
            # Build context window
            messages = await self._build_context_window(db, session, context, task_type)
            
            # 2.3.4 — Resolve org LLM config (from context or load from DB)
            org_config = context.org_llm_config
            if org_config is None:
                project_result = await db.execute(
                    select(Project).where(Project.id == session.project_id)
                )
                project = project_result.scalar_one_or_none()
                if project:
                    org_result = await db.execute(
                        select(Organization).where(Organization.id == project.org_id)
                    )
                    org = org_result.scalar_one_or_none()
                    org_config = (org.llm_config or {}) if org else None

            # Per-agent LLM config overrides (model/provider/api_key from agent_def.config)
            agent_def_result = await db.execute(
                select(AgentDefinition).where(AgentDefinition.id == session.agent_def_id)
            )
            _agent_def_for_llm = agent_def_result.scalar_one_or_none()
            agent_llm_config = {}
            if _agent_def_for_llm and _agent_def_for_llm.config:
                for key in ("llm_model", "llm_provider", "llm_api_key"):
                    if _agent_def_for_llm.config.get(key):
                        agent_llm_config[key] = _agent_def_for_llm.config[key]
            # Agent config takes precedence over org config
            effective_config = {**(org_config or {}), **agent_llm_config} or None

            # Call LLM
            temperature = (_agent_def_for_llm.config.get("temperature", 0.7)
                           if _agent_def_for_llm and _agent_def_for_llm.config else 0.7)
            max_tokens = (_agent_def_for_llm.config.get("max_tokens", 4096)
                          if _agent_def_for_llm and _agent_def_for_llm.config else 4096)
            llm_response = await llm_adapter.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                org_config=effective_config,
            )
            
            # Create artifact from LLM response
            artifact = await self._create_artifact(
                db, session, llm_response.content, task_type, context
            )
            
            # Update memory
            await self._update_memory(session, messages, llm_response.content)
            
            # Update session status
            session.status = "produced"
            await db.commit()
            
            return artifact
            
        except Exception as e:
            # Update session status to error
            session.status = "error"
            await db.commit()
            raise e
    
    async def _build_context_window(
        self,
        db: AsyncSession,
        session: AgentSession,
        context: Context,
        task_type: str,
    ) -> List[Dict[str, str]]:
        """Build context window with system prompt, knowledge, and input"""
        
        messages = []
        
        # Load agent definition and knowledge pack
        result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.id == session.agent_def_id)
        )
        agent_def = result.scalar_one()
        
        knowledge_pack = None
        if agent_def.knowledge_pack_id:
            result = await db.execute(
                select(KnowledgePack).where(KnowledgePack.id == agent_def.knowledge_pack_id)
            )
            knowledge_pack = result.scalar_one_or_none()
        
        # 1. System prompt
        system_prompt = self._get_system_prompt(agent_def, knowledge_pack)
        messages.append({"role": "system", "content": system_prompt})
        
        # 2. Task-specific prompt
        task_prompt = self._get_task_prompt(knowledge_pack, task_type, agent_def.role)
        if task_prompt:
            messages.append({"role": "system", "content": task_prompt})
        
        # 3. Load long-term memory
        memory_context = await self._load_longterm_memory(db, session)
        if memory_context:
            messages.append({"role": "system", "content": f"Previous context and decisions: {memory_context}"})
        
        # 4. User input and upstream artifacts
        if context.user_input:
            messages.append({"role": "user", "content": f"Original requirement: {context.user_input}"})
        
        # 5. Upstream artifacts (from previous agents)
        for artifact_data in context.upstream_artifacts:
            content = artifact_data.get("content_md", "")
            agent_role = artifact_data.get("agent_role", "unknown")
            artifact_type = artifact_data.get("artifact_type", "unknown")
            
            # Summarize large content
            if len(content) > 8000:  # ~2K tokens
                content = content[:8000] + "\n\n[Content truncated...]"
            
            messages.append({
                "role": "user",
                "content": f"Input from {agent_role} ({artifact_type}):\n\n{content}"
            })
        
        # 6. Director notes (if any)
        if context.director_notes:
            messages.append({"role": "user", "content": f"Director instructions: {context.director_notes}"})
        
        # 7. Current task instruction
        task_instruction = self._get_task_instruction(task_type, agent_def.role, context.iteration)
        messages.append({"role": "user", "content": task_instruction})
        
        return messages
    
    def _get_system_prompt(self, agent_def: AgentDefinition, knowledge_pack: Optional[KnowledgePack]) -> str:
        """Get system prompt for agent"""
        if knowledge_pack and knowledge_pack.system_prompt:
            return knowledge_pack.system_prompt

        # Use soul if defined (takes precedence over hardcoded defaults)
        if agent_def.soul:
            return agent_def.soul
        
        # Default system prompts for built-in agents
        default_prompts = {
            "pm": """You are a Product Manager Agent. Your role is to:
- Write clear, detailed product specifications
- Define user stories and acceptance criteria
- Consider business value and user needs
- Collaborate with technical teams

Write your output in clear Markdown format.""",
            
            "architect": """You are an Architect Agent. Your role is to:
- Review product requirements for technical feasibility
- Design system architecture and technical solutions
- Identify technical risks and constraints
- Recommend best practices and patterns

Write your output in clear Markdown format with technical details.""",
            
            "devops": """You are a DevOps Agent. Your role is to:
- Review requirements for deployment and operational considerations
- Design infrastructure and deployment strategies
- Consider scalability, security, and monitoring needs
- Recommend tools and processes

Write your output in clear Markdown format.""",
            
            "qa": """You are a QA Agent. Your role is to:
- Create comprehensive test plans and strategies
- Define test cases and acceptance criteria
- Identify edge cases and potential issues
- Ensure quality standards are met

Write your output in clear Markdown format.""",
            
            "director": """You are a Director Agent. Your role is to:
- Review all outputs for completeness and quality
- Make decisions on next steps in the workflow
- Provide feedback and guidance to other agents
- Ensure final deliverables meet standards

Provide clear, actionable feedback.""",
        }
        
        return default_prompts.get(agent_def.role, "You are an AI assistant helping with project collaboration.")
    
    def _get_task_prompt(self, knowledge_pack: Optional[KnowledgePack], task_type: str, agent_role: str) -> Optional[str]:
        """Get task-specific prompt"""
        if knowledge_pack and knowledge_pack.task_prompts:
            return knowledge_pack.task_prompts.get(task_type)
        
        # Default task prompts
        if task_type == "review":
            return f"Review the provided materials and provide feedback. If you find issues, suggest specific improvements. If everything looks good, approve it to proceed."
        elif task_type == "revise":
            return f"Based on the feedback provided, revise and improve your previous output. Address all concerns raised."
        elif task_type == "approve":
            return f"Make final approval decision. If approved, respond with 'APPROVED'. If changes needed, provide specific feedback."
        
        return None
    
    def _get_task_instruction(self, task_type: str, agent_role: str, iteration: int) -> str:
        """Get specific task instruction"""
        if iteration > 1:
            return f"This is iteration {iteration}. Please {task_type} based on the feedback provided above."
        
        if task_type == "draft":
            return f"Please create your initial {agent_role} output based on the requirements and inputs above."
        else:
            return f"Please {task_type} the provided materials."
    
    async def _load_longterm_memory(self, db: AsyncSession, session: AgentSession) -> Optional[str]:
        """Load long-term memory for the agent in this project"""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.project_id == session.project_id,
                AgentMemory.agent_def_id == session.agent_def_id,
            )
            .order_by(AgentMemory.created_at.desc())
            .limit(3)  # Last 3 memories
        )
        memories = result.scalars().all()
        
        if not memories:
            return None
        
        # Combine memory summaries
        memory_text = "\n".join([
            f"Previous session: {memory.summary}"
            for memory in memories
        ])
        
        return memory_text
    
    async def _create_artifact(
        self,
        db: AsyncSession,
        session: AgentSession,
        content: str,
        task_type: str,
        context: Context,
    ) -> Artifact:
        """Create artifact from LLM output"""
        
        # Load agent definition to get role
        result = await db.execute(
            select(AgentDefinition).where(AgentDefinition.id == session.agent_def_id)
        )
        agent_def = result.scalar_one()
        
        # Determine artifact type based on agent role and task type
        artifact_type_map = {
            "pm": "product_spec",
            "architect": "tech_design", 
            "devops": "deployment_plan",
            "qa": "qa_checklist",
            "director": "review_report",
        }
        
        artifact_type = artifact_type_map.get(agent_def.role, "document")
        
        # Check if there's a previous version to supersede
        result = await db.execute(
            select(Artifact)
            .where(
                Artifact.project_id == session.project_id,
                Artifact.agent_role == agent_def.role,
                Artifact.artifact_type == artifact_type,
                Artifact.status == "draft",
            )
            .order_by(Artifact.version.desc())
        )
        existing_artifact = result.scalar_one_or_none()
        
        version = 1
        if existing_artifact:
            # Mark previous as superseded
            existing_artifact.status = "superseded"
            version = existing_artifact.version + 1
        
        # Create new artifact
        artifact = Artifact(
            project_id=session.project_id,
            session_id=session.id,
            agent_role=agent_def.role,
            artifact_type=artifact_type,
            version=version,
            content_md=content,
            status="draft",
            metadata={
                "task_type": task_type,
                "iteration": context.iteration,
                "created_by": agent_def.display_name,
            }
        )
        
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        
        return artifact
    
    async def _update_memory(self, session: AgentSession, messages: List[Dict], response: str):
        """Update short-term memory in cache"""
        try:
            # Load existing memory
            memory_data = await self.cache.get(session.memory_key)
            if memory_data:
                memory = json.loads(memory_data)
            else:
                memory = []
            
            # Add new interaction
            memory.append({
                "timestamp": datetime.utcnow().isoformat(),
                "messages": messages[-2:] if len(messages) >= 2 else messages,  # Last user message
                "response": response[:1000],  # Truncate long responses
            })
            
            # Keep only last 10 interactions
            if len(memory) > 10:
                memory = memory[-10:]
            
            # Save back to cache
            await self.cache.set(
                session.memory_key,
                json.dumps(memory),
                ex=int(timedelta(hours=24).total_seconds())
            )
            
        except Exception as e:
            print(f"Failed to update memory: {e}")
    
    async def terminate_session(self, db: AsyncSession, session_id: str):
        """Terminate session and persist memory to long-term storage"""
        
        # Load session
        result = await db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return
        
        try:
            # Load short-term memory
            memory_data = await self.cache.get(session.memory_key)
            if memory_data:
                memory = json.loads(memory_data)
                
                # Generate summary using LLM
                summary = await self._generate_memory_summary(memory)
                
                # Extract key decisions from session responses
                key_decisions = self._extract_key_decisions(memory)

                # Save to long-term storage
                agent_memory = AgentMemory(
                    project_id=session.project_id,
                    agent_def_id=session.agent_def_id,
                    session_id=session.id,
                    summary=summary,
                    key_decisions=key_decisions,
                )
                
                db.add(agent_memory)
                
                # Clean up cache
                await self.cache.delete(session.memory_key)
            
            # Update session status
            session.status = "done"
            await db.commit()
            
        except Exception as e:
            print(f"Failed to terminate session: {e}")
    
    def _extract_key_decisions(self, memory: List[Dict]) -> List[str]:
        """Extract key decisions from session memory interactions."""
        decisions = []
        keywords = ["決定", "決策", "approved", "rejected", "建議", "recommend", "APPROVED", "REJECTED", "chosen", "選擇"]
        for interaction in memory:
            response_text = interaction.get("response", "")
            for line in response_text.split("\n"):
                line = line.strip()
                if any(kw.lower() in line.lower() for kw in keywords) and len(line) > 10:
                    decisions.append(line[:200])
                    if len(decisions) >= 5:
                        return decisions
        return decisions

    async def _generate_memory_summary(self, memory: List[Dict]) -> str:
        """Generate summary of session memory using LLM"""
        try:
            # Prepare context for summarization
            context_text = "\n".join([
                f"Interaction {i+1}: {interaction.get('response', '')[:200]}..."
                for i, interaction in enumerate(memory[-5:])  # Last 5 interactions
            ])
            
            if not context_text.strip():
                return "No significant interactions to summarize."
            
            response = await llm_adapter.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize the key points and decisions from this agent session. Be concise but capture important insights."
                    },
                    {
                        "role": "user", 
                        "content": f"Agent session interactions:\n\n{context_text}"
                    }
                ],
                max_tokens=200,
            )
            
            return response.content
            
        except Exception as e:
            return f"Summary generation failed: {str(e)}"


# Global instance
session_manager = SessionManager()
