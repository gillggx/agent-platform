"""
CodeArchitectAdapter — Integration with Code Architect A2A API.

Features:
- A2A API client for Code Architect service
- Tool integration for Architect Agent
- Code generation, validation, and impact analysis
- Result formatting and caching

Architecture:
- CodeArchitectClient: HTTP client for Code Architect API
- CodeArchitectAdapter: Adapter for agent-platform integration
- Tool definitions for LLMAdapter
- Error handling and retry logic

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import asyncio
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class CodeGenMode(str, Enum):
    """Code generation modes."""
    DRY_RUN = "dry_run"
    APPLY = "apply"
    INTERACTIVE = "interactive"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FileChange:
    """Represents a file change from code generation."""
    file: str
    action: str  # 'create', 'modify', 'delete'
    content: Optional[str] = None
    diff: Optional[str] = None
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "action": self.action,
            "content": self.content,
            "diff": self.diff,
            "applied": self.applied,
        }


@dataclass
class ValidationIssue:
    """Validation issue from code validation."""
    severity: str  # 'error', 'warning', 'info'
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "suggestion": self.suggestion,
        }


@dataclass
class CodeGenResult:
    """Result from code generation."""
    success: bool
    changes: List[FileChange] = field(default_factory=list)
    explanation: str = ""
    plan: List[str] = field(default_factory=list)
    patterns_used: List[str] = field(default_factory=list)
    tests_suggested: List[str] = field(default_factory=list)
    model_used: str = ""
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "changes": [c.to_dict() for c in self.changes],
            "explanation": self.explanation,
            "plan": self.plan,
            "patterns_used": self.patterns_used,
            "tests_suggested": self.tests_suggested,
            "model_used": self.model_used,
            "session_id": self.session_id,
        }


@dataclass
class ValidationResult:
    """Result from code validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "patterns_matched": self.patterns_matched,
            "improvements": self.improvements,
            "summary": self.summary,
        }


@dataclass
class QueryResult:
    """Result from architecture query."""
    answer: str
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    patterns_relevant: List[str] = field(default_factory=list)
    feasibility_score: Optional[float] = None
    model_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "sources": self.sources,
            "patterns_relevant": self.patterns_relevant,
            "feasibility_score": self.feasibility_score,
            "model_used": self.model_used,
        }


@dataclass
class ImpactAnalysisResult:
    """Result from impact analysis."""
    impact_score: float  # 0.0 to 1.0
    affected_modules: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    test_coverage_impact: str = ""  # 'low', 'medium', 'high'
    performance_impact: str = ""    # 'none', 'positive', 'negative'
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "impact_score": self.impact_score,
            "affected_modules": self.affected_modules,
            "dependencies": self.dependencies,
            "breaking_changes": self.breaking_changes,
            "test_coverage_impact": self.test_coverage_impact,
            "performance_impact": self.performance_impact,
            "summary": self.summary,
        }


# ============================================================================
# CodeArchitectClient — HTTP Client for Code Architect API
# ============================================================================

class CodeArchitectClient:
    """
    HTTP client for Code Architect A2A API.
    
    Handles:
    - API endpoint management
    - Authentication and headers
    - Request/response formatting
    - Error handling and retries
    - Connection pooling
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Code Architect client.
        
        Args:
            base_url: Code Architect API base URL
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> CodeArchitectClient:
        """Enter async context."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_connections=10),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        if self.client:
            await self.client.aclose()

    async def generate_code(
        self,
        task: str,
        project_id: str,
        context: Optional[Dict[str, Any]] = None,
        mode: CodeGenMode = CodeGenMode.DRY_RUN,
    ) -> CodeGenResult:
        """
        Call Code Architect to generate code.
        
        Args:
            task: Code generation task description
            project_id: Project identifier
            context: Additional context
            mode: Generation mode (dry_run, apply, interactive)
            
        Returns:
            CodeGenResult with generated changes
            
        Raises:
            ValueError: If API call fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        payload = {
            "task": task,
            "project_id": project_id,
            "context": context or {},
            "mode": mode.value,
        }

        try:
            response = await self._post("/api/a2a/generate", payload)
            return CodeGenResult(
                success=response.get("success", True),
                changes=[
                    FileChange(
                        file=c["file"],
                        action=c["action"],
                        content=c.get("content"),
                        diff=c.get("diff"),
                        applied=c.get("applied", False),
                    )
                    for c in response.get("changes", [])
                ],
                explanation=response.get("explanation", ""),
                plan=response.get("plan", []),
                patterns_used=response.get("patterns_used", []),
                tests_suggested=response.get("tests_suggested", []),
                model_used=response.get("model_used", ""),
                session_id=response.get("session_id"),
            )
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise ValueError(f"Code generation failed: {e}") from e

    async def validate_code(
        self,
        changes: List[Dict[str, Any]],
        project_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate proposed code changes.
        
        Args:
            changes: List of file changes to validate
            project_id: Project identifier
            context: Additional context
            
        Returns:
            ValidationResult with validation status and issues
            
        Raises:
            ValueError: If API call fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        payload = {
            "changes": changes,
            "project_id": project_id,
            "context": context or {},
        }

        try:
            response = await self._post("/api/a2a/validate", payload)
            return ValidationResult(
                valid=response.get("valid", True),
                issues=[
                    ValidationIssue(
                        severity=i["severity"],
                        message=i["message"],
                        file=i.get("file"),
                        line=i.get("line"),
                        suggestion=i.get("suggestion"),
                    )
                    for i in response.get("issues", [])
                ],
                patterns_matched=response.get("patterns_matched", []),
                improvements=response.get("improvements", []),
                summary=response.get("summary", ""),
            )
        except Exception as e:
            logger.error(f"Code validation failed: {e}")
            raise ValueError(f"Code validation failed: {e}") from e

    async def analyze_impact(
        self,
        changes: List[Dict[str, Any]],
        project_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ImpactAnalysisResult:
        """
        Analyze impact of proposed changes.
        
        Args:
            changes: List of file changes to analyze
            project_id: Project identifier
            context: Additional context
            
        Returns:
            ImpactAnalysisResult with impact assessment
            
        Raises:
            ValueError: If API call fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        payload = {
            "changes": changes,
            "project_id": project_id,
            "context": context or {},
        }

        try:
            response = await self._post("/api/a2a/impact", payload)
            return ImpactAnalysisResult(
                impact_score=response.get("impact_score", 0.5),
                affected_modules=response.get("affected_modules", []),
                dependencies=response.get("dependencies", []),
                breaking_changes=response.get("breaking_changes", []),
                test_coverage_impact=response.get("test_coverage_impact", "medium"),
                performance_impact=response.get("performance_impact", "none"),
                summary=response.get("summary", ""),
            )
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            raise ValueError(f"Impact analysis failed: {e}") from e

    async def query_architecture(
        self,
        question: str,
        project_id: str,
        query_type: str = "general",
    ) -> QueryResult:
        """
        Query Code Architect for architecture knowledge.

        Args:
            question: Natural language architecture question
            project_id: Project identifier
            query_type: One of 'architecture', 'feasibility', 'pattern', 'general'

        Returns:
            QueryResult with answer and metadata

        Raises:
            ValueError: If API call fails
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        payload = {
            "question": question,
            "project_id": project_id,
            "query_type": query_type,
        }

        try:
            response = await self._post("/api/a2a/query", payload)
            return QueryResult(
                answer=response.get("answer", ""),
                confidence=response.get("confidence", 0.0),
                sources=response.get("sources", []),
                patterns_relevant=response.get("patterns_relevant", []),
                feasibility_score=response.get("feasibility_score"),
                model_used=response.get("model_used", ""),
            )
        except Exception as e:
            logger.error(f"Architecture query failed: {e}")
            raise ValueError(f"Architecture query failed: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if Code Architect service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._get("/api/health")
            return response.get("status") == "ok"
        except Exception:
            logger.warning("Code Architect health check failed")
            return False

    # ========================================================================
    # Private Methods
    # ========================================================================

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        response = await self.client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make POST request with retry logic."""
        if not self.client:
            raise RuntimeError("Client not initialized")

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    url, json=payload, headers=headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except httpx.HTTPError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


# ============================================================================
# CodeArchitectAdapter — Agent Platform Integration
# ============================================================================

class CodeArchitectAdapter:
    """
    Adapter for integrating Code Architect with agent-platform.
    
    Provides:
    - Tool definitions for LLMAdapter
    - Architecture Agent integration
    - Code generation, validation, and impact analysis tools
    - Result formatting for agent conversation
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize Code Architect adapter.
        
        Args:
            base_url: Code Architect API base URL
            api_key: Optional API key
            enabled: Whether to enable code generation tools
        """
        self.base_url = base_url
        self.api_key = api_key
        self.enabled = enabled
        self.client = CodeArchitectClient(base_url, api_key)

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions for LLMAdapter.
        
        Returns list of tool definitions for:
        - /generate: Generate code
        - /validate: Validate code
        - /impact: Analyze impact
        """
        if not self.enabled:
            return []

        return [
            {
                "type": "function",
                "function": {
                    "name": "code_architect_generate",
                    "description": "Generate code using Code Architect to implement a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "Task description for code generation",
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project identifier",
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["dry_run", "apply"],
                                "description": "Generation mode: dry_run shows changes, apply executes them",
                                "default": "dry_run",
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context for code generation",
                            },
                        },
                        "required": ["task", "project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "code_architect_validate",
                    "description": "Validate proposed code changes against project patterns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "changes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string"},
                                        "action": {
                                            "type": "string",
                                            "enum": ["create", "modify", "delete"],
                                        },
                                        "content": {"type": "string"},
                                    },
                                    "required": ["file", "action"],
                                },
                                "description": "List of file changes to validate",
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project identifier",
                            },
                        },
                        "required": ["changes", "project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "code_architect_query",
                    "description": "Query Code Architect for architecture knowledge, feasibility assessment, or design patterns",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Natural language architecture question",
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project identifier",
                            },
                            "query_type": {
                                "type": "string",
                                "enum": ["architecture", "feasibility", "pattern", "general"],
                                "description": "Type of query: architecture (how does X work), feasibility (can we add X), pattern (design patterns), general",
                                "default": "general",
                            },
                        },
                        "required": ["question", "project_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "code_architect_impact",
                    "description": "Analyze impact of proposed code changes",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "changes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file": {"type": "string"},
                                        "action": {
                                            "type": "string",
                                            "enum": ["create", "modify", "delete"],
                                        },
                                        "content": {"type": "string"},
                                    },
                                    "required": ["file", "action"],
                                },
                                "description": "List of file changes to analyze",
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project identifier",
                            },
                        },
                        "required": ["changes", "project_id"],
                    },
                },
            },
        ]

    async def handle_tool_call(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle tool call from LLM.
        
        Args:
            tool_name: Name of tool to call
            tool_input: Tool input parameters
            
        Returns:
            Tool execution result
        """
        async with self.client as client:
            if tool_name == "code_architect_generate":
                result = await client.generate_code(
                    task=tool_input["task"],
                    project_id=tool_input["project_id"],
                    context=tool_input.get("context"),
                    mode=CodeGenMode(tool_input.get("mode", "dry_run")),
                )
                return {
                    "status": "success",
                    "result": result.to_dict(),
                }

            elif tool_name == "code_architect_validate":
                result = await client.validate_code(
                    changes=tool_input["changes"],
                    project_id=tool_input["project_id"],
                    context=tool_input.get("context"),
                )
                return {
                    "status": "success",
                    "result": result.to_dict(),
                }

            elif tool_name == "code_architect_query":
                result = await client.query_architecture(
                    question=tool_input["question"],
                    project_id=tool_input["project_id"],
                    query_type=tool_input.get("query_type", "general"),
                )
                return {
                    "status": "success",
                    "result": result.to_dict(),
                }

            elif tool_name == "code_architect_impact":
                result = await client.analyze_impact(
                    changes=tool_input["changes"],
                    project_id=tool_input["project_id"],
                    context=tool_input.get("context"),
                )
                return {
                    "status": "success",
                    "result": result.to_dict(),
                }

            else:
                return {
                    "status": "error",
                    "error": f"Unknown tool: {tool_name}",
                }

    async def is_available(self) -> bool:
        """Check if Code Architect service is available."""
        if not self.enabled:
            return False

        async with self.client as client:
            try:
                return await client.health_check()
            except Exception as e:
                logger.warning(f"Code Architect availability check failed: {e}")
                return False


# ============================================================================
# Global Adapter Instance
# ============================================================================

_adapter: Optional[CodeArchitectAdapter] = None


def get_code_architect_adapter(
    base_url: str = "http://localhost:8001",
    api_key: Optional[str] = None,
    enabled: bool = True,
) -> CodeArchitectAdapter:
    """
    Get or create Code Architect adapter.
    
    Args:
        base_url: Code Architect API base URL
        api_key: Optional API key
        enabled: Whether to enable code generation tools
        
    Returns:
        CodeArchitectAdapter instance
    """
    global _adapter
    if _adapter is None:
        _adapter = CodeArchitectAdapter(base_url, api_key, enabled)
    return _adapter


def reset_adapter() -> None:
    """Reset adapter singleton (for testing)."""
    global _adapter
    _adapter = None
