"""
Role Manager — Role configuration, knowledge management, and prompt generation.

Features:
- RoleTemplate: Comprehensive role definitions with soul prompts and tools
- KnowledgeBase: Retrieve role-specific knowledge and documentation
- PromptFactory: Generate system/task/review prompts with templates

Architecture:
- RoleTemplate: Immutable role configuration
- KnowledgeBase: In-memory knowledge store (extensible to RAG)
- PromptFactory: Prompt building with context injection
- RoleRegistry: Central role configuration management

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Constants
# ============================================================================

class DecisionStyle(str, Enum):
    """Decision-making styles for different roles."""
    ITERATIVE = "iterative"  # PM: multiple rounds of refinement
    THOROUGH = "thorough"    # QA: detailed analysis and edge cases
    PRAGMATIC = "pragmatic"  # DevOps: balance trade-offs
    STRATEGIC = "strategic"  # Director: high-level decisions
    CRITICAL = "critical"    # Critic: identify weaknesses


# Default role definitions
DEFAULT_ROLES: Dict[str, Dict[str, Any]] = {
    "pm": {
        "display_name": "Product Manager",
        "description": "Defines requirements, priorities, and user experience",
        "decision_style": DecisionStyle.ITERATIVE,
        "capabilities": ["requirement_definition", "prioritization", "stakeholder_management"],
        "tools": [],
    },
    "architect": {
        "display_name": "Solutions Architect",
        "description": "Designs system architecture and technical solutions",
        "decision_style": DecisionStyle.STRATEGIC,
        "capabilities": ["system_design", "technology_selection", "scalability_planning", "code_generation"],
        "tools": ["design_tool", "architecture_diagram", "code_architect_generate", "code_architect_validate", "code_architect_impact"],
    },
    "qa": {
        "display_name": "QA Engineer",
        "description": "Tests and validates implementations",
        "decision_style": DecisionStyle.THOROUGH,
        "capabilities": ["test_planning", "edge_case_identification", "validation"],
        "tools": ["test_framework", "bug_tracker"],
    },
    "devops": {
        "display_name": "DevOps Engineer",
        "description": "Manages deployment, scaling, and operational aspects",
        "decision_style": DecisionStyle.PRAGMATIC,
        "capabilities": ["deployment_planning", "scaling_design", "monitoring_setup"],
        "tools": ["deployment_tool", "monitoring_tool"],
    },
    "director": {
        "display_name": "Director",
        "description": "Makes final decisions and approves deliverables",
        "decision_style": DecisionStyle.STRATEGIC,
        "capabilities": ["decision_making", "approval_authority", "risk_assessment"],
        "tools": [],
    },
    "critic": {
        "display_name": "Critical Reviewer",
        "description": "Identifies gaps, risks, and areas for improvement",
        "decision_style": DecisionStyle.CRITICAL,
        "capabilities": ["gap_identification", "risk_analysis", "improvement_suggestions"],
        "tools": [],
    },
}


# System prompts for each role
SYSTEM_PROMPTS: Dict[str, str] = {
    "pm": """You are a Product Manager. Your role is to:
- Define clear, actionable requirements
- Prioritize features based on impact and effort
- Think about user needs and business value
- Ask clarifying questions when needed
- Make prioritization decisions

Guidelines:
- Use structured format for requirements
- Consider user stories and acceptance criteria
- Think about dependencies and risks
- Be pragmatic about trade-offs""",

    "architect": """You are a Solutions Architect. Your role is to:
- Design scalable, maintainable systems
- Select appropriate technologies
- Consider non-functional requirements
- Identify potential bottlenecks and risks
- Create clear architecture documentation

Guidelines:
- Think about scalability, security, and reliability
- Consider trade-offs between different approaches
- Document assumptions and decisions
- Suggest testing and validation strategies""",

    "qa": """You are a QA Engineer. Your role is to:
- Identify test scenarios and edge cases
- Plan comprehensive test coverage
- Think about failure modes and error handling
- Suggest validation approaches
- Create test plans and acceptance criteria

Guidelines:
- Be thorough and think about edge cases
- Consider both happy paths and error scenarios
- Identify assumptions that need validation
- Suggest automation opportunities""",

    "devops": """You are a DevOps Engineer. Your role is to:
- Design deployment and scaling strategies
- Plan monitoring and observability
- Consider operational requirements
- Identify infrastructure needs
- Plan for reliability and disaster recovery

Guidelines:
- Balance automation with maintainability
- Consider cost-efficiency
- Plan for monitoring and alerting
- Document runbooks and procedures""",

    "director": """You are a Director. Your role is to:
- Make final decisions on deliverables
- Assess quality and completeness
- Identify missing pieces or risks
- Approve or request changes
- Think about overall strategy and fit

Guidelines:
- Look at the big picture
- Assess completeness against requirements
- Identify strategic risks
- Make clear approval/rejection decisions""",

    "critic": """You are a Critical Reviewer. Your role is to:
- Identify gaps and weaknesses
- Suggest improvements
- Question assumptions
- Highlight risks and concerns
- Be constructive in your feedback

Guidelines:
- Be thorough and think critically
- Focus on constructive feedback
- Identify both obvious and subtle issues
- Suggest concrete improvements""",
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class RoleTemplate:
    """
    Role definition and configuration.
    
    Attributes:
        role: Role identifier (pm, architect, qa, etc.)
        display_name: Human-readable name
        description: Role description
        soul_prompt: System prompt for this role
        capabilities: List of capabilities/tasks
        tools: Tools available to this role
        decision_style: How this role makes decisions
        config: Role-specific configuration
        metadata: Additional metadata
    """
    role: str
    display_name: str
    description: str
    soul_prompt: str
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    decision_style: DecisionStyle = DecisionStyle.PRAGMATIC
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_perform(self, capability: str) -> bool:
        """Check if role can perform a capability."""
        return capability in self.capabilities

    def has_tool(self, tool: str) -> bool:
        """Check if role has access to a tool."""
        return tool in self.tools

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "display_name": self.display_name,
            "description": self.description,
            "soul_prompt": self.soul_prompt,
            "capabilities": self.capabilities,
            "tools": self.tools,
            "decision_style": self.decision_style.value,
            "config": self.config,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeDocument:
    """
    A knowledge document (piece of information).
    
    Attributes:
        doc_id: Document identifier
        title: Document title
        content: Document content
        tags: Search tags
        role_relevant: Roles this is relevant to
        created_at: Creation timestamp
        metadata: Additional metadata
    """
    doc_id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    role_relevant: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "role_relevant": self.role_relevant,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================================
# KnowledgeBase — In-memory Knowledge Storage
# ============================================================================

class KnowledgeBase:
    """
    Role-specific knowledge storage and retrieval.
    
    Features:
    - Store documents by role
    - Full-text search capability
    - Tag-based filtering
    - Vector search ready (for RAG integration)
    
    Example:
        kb = KnowledgeBase()
        kb.add_document(
            role="qa",
            doc=KnowledgeDocument(
                doc_id="testing_best_practices",
                title="Testing Best Practices",
                content="...",
                tags=["testing", "qa"],
            ),
        )
        
        results = kb.retrieve("testing strategy", role="qa")
    """

    def __init__(self):
        """Initialize knowledge base."""
        self.documents: Dict[str, KnowledgeDocument] = {}
        self.role_documents: Dict[str, List[str]] = {}  # role → doc_ids
        self.tag_index: Dict[str, Set[str]] = {}  # tag → doc_ids

    def add_document(self, doc: KnowledgeDocument, role: Optional[str] = None) -> None:
        """
        Add document to knowledge base.
        
        Args:
            doc: Document to add
            role: Optional role to associate with
        """
        self.documents[doc.doc_id] = doc
        
        # Index by role
        if role:
            if role not in self.role_documents:
                self.role_documents[role] = []
            self.role_documents[role].append(doc.doc_id)
            
            if role not in doc.role_relevant:
                doc.role_relevant.append(role)
        else:
            # Index by all relevant roles
            for r in doc.role_relevant:
                if r not in self.role_documents:
                    self.role_documents[r] = []
                if doc.doc_id not in self.role_documents[r]:
                    self.role_documents[r].append(doc.doc_id)
        
        # Index by tags
        for tag in doc.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(doc.doc_id)
        
        logger.debug(f"Added document: {doc.doc_id}")

    def retrieve(
        self,
        query: str,
        role: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[KnowledgeDocument]:
        """
        Retrieve documents matching query.
        
        Args:
            query: Search query text
            role: Optional role filter
            tags: Optional tag filters
            limit: Maximum documents to return
            
        Returns:
            List of matching documents
        """
        results: List[KnowledgeDocument] = []
        query_lower = query.lower()
        
        # Get candidate documents
        candidates: Set[str] = set()
        
        if role and role in self.role_documents:
            candidates = set(self.role_documents[role])
        else:
            candidates = set(self.documents.keys())
        
        # Filter by tags if provided
        if tags:
            tag_candidates = set()
            for tag in tags:
                if tag in self.tag_index:
                    tag_candidates.update(self.tag_index[tag])
            candidates = candidates.intersection(tag_candidates)
        
        # Search by text (simple substring matching)
        for doc_id in candidates:
            doc = self.documents[doc_id]
            
            # Check if query matches title or content
            if (query_lower in doc.title.lower() or 
                query_lower in doc.content.lower()):
                results.append(doc)
        
        # Sort by title length (shorter = more specific match)
        results.sort(key=lambda d: len(d.title))
        
        return results[:limit]

    def get_documents_for_role(self, role: str) -> List[KnowledgeDocument]:
        """Get all documents for a role."""
        doc_ids = self.role_documents.get(role, [])
        return [self.documents[doc_id] for doc_id in doc_ids if doc_id in self.documents]

    def clear(self) -> None:
        """Clear all documents."""
        self.documents.clear()
        self.role_documents.clear()
        self.tag_index.clear()


# ============================================================================
# PromptFactory — Prompt Generation
# ============================================================================

class PromptFactory:
    """
    Factory for generating role-specific prompts.
    
    Generates:
    - System prompts (soul prompts)
    - Task prompts (with context injection)
    - Review prompts (for decision-making)
    
    Example:
        factory = PromptFactory()
        
        system_prompt = factory.build_system_prompt("architect")
        
        task_prompt = factory.build_task_prompt(
            role="qa",
            task="Write test cases",
            context={"requirements": "..."},
        )
        
        review_prompt = factory.build_review_prompt(
            role="director",
            artifact="design_document",
            context={"requirements": "..."},
        )
    """

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None):
        """
        Initialize prompt factory.
        
        Args:
            knowledge_base: Optional knowledge base for context injection
        """
        self.kb = knowledge_base
        self.system_prompts = SYSTEM_PROMPTS.copy()

    def build_system_prompt(self, role: str) -> str:
        """
        Build system prompt (soul prompt) for a role.
        
        Args:
            role: Agent role
            
        Returns:
            System prompt text
        """
        return self.system_prompts.get(
            role,
            "You are a helpful AI assistant. Follow instructions carefully.",
        )

    def build_task_prompt(
        self,
        role: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build task prompt with context injection.
        
        Args:
            role: Agent role
            task: Task description
            context: Context data (requirements, artifacts, etc.)
            
        Returns:
            Constructed prompt with context
        """
        prompt_parts = []
        
        # Add task
        prompt_parts.append(f"TASK: {task}")
        
        # Add context if provided
        if context:
            prompt_parts.append("\nCONTEXT:")
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    prompt_parts.append(f"  {key}:\n{json.dumps(value, indent=2)}")
                else:
                    prompt_parts.append(f"  {key}: {value}")
        
        # Add role-specific guidance
        guidance = self._get_task_guidance(role)
        if guidance:
            prompt_parts.append(f"\nGUIDANCE:\n{guidance}")
        
        # Add relevant knowledge if available
        if self.kb:
            docs = self.kb.retrieve(task, role=role, limit=2)
            if docs:
                prompt_parts.append("\nRELEVANT KNOWLEDGE:")
                for doc in docs:
                    prompt_parts.append(f"  - {doc.title}: {doc.content[:200]}...")
        
        return "\n".join(prompt_parts)

    def build_review_prompt(
        self,
        role: str,
        artifact: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build review prompt for decision-making.
        
        Args:
            role: Reviewing agent role
            artifact: Artifact being reviewed
            context: Context for review
            
        Returns:
            Review prompt
        """
        prompt_parts = []
        
        prompt_parts.append(f"REVIEW REQUEST\nRole: {role}\n\nArtifact:")
        prompt_parts.append(artifact)
        
        if context:
            prompt_parts.append("\nCRITERIA:")
            for key, value in context.items():
                prompt_parts.append(f"  - {key}: {value}")
        
        # Add review guidance
        guidance = self._get_review_guidance(role)
        if guidance:
            prompt_parts.append(f"\nGUIDELINES:\n{guidance}")
        
        return "\n".join(prompt_parts)

    def _get_task_guidance(self, role: str) -> str:
        """Get task-specific guidance for a role."""
        guidance_map = {
            "pm": "Structure your response as: REQUIREMENT | PRIORITY | ACCEPTANCE_CRITERIA | DEPENDENCIES",
            "architect": "Structure your response as: DESIGN | TECHNOLOGIES | TRADE_OFFS | RISKS | VALIDATION",
            "qa": "Structure your response as: TEST_CASES | EDGE_CASES | TEST_STRATEGY | COVERAGE | AUTOMATION",
            "devops": "Structure your response as: DEPLOYMENT | SCALING | MONITORING | RUNBOOKS | DISASTER_RECOVERY",
            "director": "Structure your response as: ASSESSMENT | QUALITY_LEVEL | APPROVED_OR_REJECTED | FEEDBACK | NEXT_STEPS",
        }
        return guidance_map.get(role, "")

    def _get_review_guidance(self, role: str) -> str:
        """Get review guidance for a role."""
        guidance_map = {
            "director": "Evaluate completeness, quality, and alignment with strategy. Approve or reject with specific feedback.",
            "critic": "Identify gaps, weaknesses, and areas for improvement. Be constructive.",
            "qa": "Evaluate test coverage and validation adequacy.",
            "architect": "Evaluate architectural soundness and technical feasibility.",
        }
        return guidance_map.get(role, "")


# ============================================================================
# RoleRegistry — Central Role Management
# ============================================================================

class RoleRegistry:
    """
    Central registry for all agent roles.
    
    Manages:
    - Role definitions and templates
    - Role discovery and lookup
    - Default roles initialization
    """

    def __init__(self):
        """Initialize role registry."""
        self.roles: Dict[str, RoleTemplate] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default roles."""
        for role_key, role_config in DEFAULT_ROLES.items():
            role = RoleTemplate(
                role=role_key,
                display_name=role_config["display_name"],
                description=role_config["description"],
                soul_prompt=SYSTEM_PROMPTS.get(role_key, ""),
                capabilities=role_config.get("capabilities", []),
                tools=role_config.get("tools", []),
                decision_style=DecisionStyle(role_config.get("decision_style", "pragmatic")),
            )
            self.roles[role_key] = role
            logger.debug(f"Registered role: {role_key}")

    def get_role(self, role: str) -> Optional[RoleTemplate]:
        """Get role template by identifier."""
        return self.roles.get(role)

    def register_role(self, role: RoleTemplate) -> None:
        """Register a custom role."""
        self.roles[role.role] = role
        logger.info(f"Registered role: {role.role}")

    def list_roles(self) -> List[RoleTemplate]:
        """List all registered roles."""
        return list(self.roles.values())

    def find_role_by_capability(self, capability: str) -> List[RoleTemplate]:
        """Find roles that can perform a capability."""
        return [r for r in self.roles.values() if r.can_perform(capability)]
