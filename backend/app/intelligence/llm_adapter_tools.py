"""
LLM Adapter Tools — Tool definitions and handling for LLMAdapterV2.

Features:
- Tool definitions for function calling
- Code generation tool definitions
- Tool call formatting and parsing
- Result handling and formatting

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Tool Definitions
# ============================================================================

def get_built_in_tools() -> List[Dict[str, Any]]:
    """
    Get built-in tool definitions for all roles.
    
    Returns:
        List of tool definitions
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "Search the knowledge base for relevant information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "roles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by relevant roles",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_project_context",
                "description": "Get current project context and state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project identifier",
                        },
                    },
                    "required": ["project_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_artifacts",
                "description": "List artifacts from current workflow",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "artifact_type": {
                            "type": "string",
                            "enum": ["requirement", "design", "code", "test", "all"],
                            "description": "Type of artifacts to list",
                        },
                    },
                    "required": ["artifact_type"],
                },
            },
        },
    ]


def get_code_generation_tools() -> List[Dict[str, Any]]:
    """
    Get code generation tool definitions.
    
    These are integrated from CodeArchitectAdapter.
    
    Returns:
        List of code generation tool definitions
    """
    return [
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
                "name": "code_architect_generate",
                "description": "Generate code using Code Architect to implement a feature or fix",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Detailed description of what code to generate",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project identifier",
                        },
                        "context": {
                            "type": "object",
                            "description": "Additional context for code generation",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["dry_run", "apply"],
                            "description": "dry_run shows changes without applying; apply executes them",
                            "default": "dry_run",
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
                "description": "Validate proposed code changes against project patterns and conventions",
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
                        "context": {
                            "type": "object",
                            "description": "Additional context for validation",
                        },
                    },
                    "required": ["changes", "project_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "code_architect_impact",
                "description": "Analyze the impact of proposed code changes on the project",
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
                        "context": {
                            "type": "object",
                            "description": "Additional context for impact analysis",
                        },
                    },
                    "required": ["changes", "project_id"],
                },
            },
        },
    ]


# ============================================================================
# Tool Call Formatting
# ============================================================================

@dataclass
class ToolCall:
    """
    Represents a tool call from LLM.
    
    Attributes:
        tool_id: Unique identifier for this tool call
        tool_name: Name of the tool being called
        parameters: Parameters passed to the tool
        timestamp: When the call was made
    """
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
        }


@dataclass
class ToolResult:
    """
    Represents the result of a tool call.
    
    Attributes:
        tool_id: ID of the tool call
        tool_name: Name of the tool
        success: Whether the call succeeded
        result: The result data
        error: Error message if failed
    """
    tool_id: str
    tool_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


# ============================================================================
# Tool Execution Manager
# ============================================================================

class ToolExecutor:
    """
    Manages tool execution for LLM calls.
    
    Handles:
    - Tool call parsing from LLM responses
    - Tool execution routing
    - Result formatting
    - Error handling
    """

    def __init__(
        self,
        code_architect_adapter=None,
        knowledge_base=None,
        project_manager=None,
    ):
        """
        Initialize tool executor.
        
        Args:
            code_architect_adapter: CodeArchitectAdapter instance
            knowledge_base: KnowledgeBase instance
            project_manager: ProjectManager instance
        """
        self.code_architect_adapter = code_architect_adapter
        self.knowledge_base = knowledge_base
        self.project_manager = project_manager

    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool call.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            
        Returns:
            ToolResult with execution result
        """
        from uuid import uuid4

        tool_id = str(uuid4())

        try:
            # Route to appropriate handler
            if tool_name.startswith("code_architect_"):
                if not self.code_architect_adapter:
                    raise ValueError("Code Architect adapter not configured")

                result = await self.code_architect_adapter.handle_tool_call(
                    tool_name, parameters
                )

                return ToolResult(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    success=result.get("status") == "success",
                    result=result.get("result"),
                    error=result.get("error"),
                )

            elif tool_name == "search_knowledge":
                return await self._execute_search_knowledge(tool_id, parameters)

            elif tool_name == "get_project_context":
                return await self._execute_get_project_context(tool_id, parameters)

            elif tool_name == "list_artifacts":
                return await self._execute_list_artifacts(tool_id, parameters)

            else:
                return ToolResult(
                    tool_id=tool_id,
                    tool_name=tool_name,
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                )

        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}")
            return ToolResult(
                tool_id=tool_id,
                tool_name=tool_name,
                success=False,
                error=str(e),
            )

    async def _execute_search_knowledge(
        self, tool_id: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute search_knowledge tool."""
        try:
            if not self.knowledge_base:
                raise ValueError("Knowledge base not configured")

            query = parameters.get("query", "")
            roles = parameters.get("roles", [])

            # Search knowledge base
            results = self.knowledge_base.search(query, limit=5)

            # Filter by roles if specified
            if roles:
                results = [
                    r
                    for r in results
                    if any(role in r.get("role_relevant", []) for role in roles)
                ]

            return ToolResult(
                tool_id=tool_id,
                tool_name="search_knowledge",
                success=True,
                result={
                    "query": query,
                    "results": results,
                    "count": len(results),
                },
            )

        except Exception as e:
            return ToolResult(
                tool_id=tool_id,
                tool_name="search_knowledge",
                success=False,
                error=str(e),
            )

    async def _execute_get_project_context(
        self, tool_id: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute get_project_context tool."""
        try:
            if not self.project_manager:
                raise ValueError("Project manager not configured")

            project_id = parameters.get("project_id", "")
            context = self.project_manager.get_project_context(project_id)

            return ToolResult(
                tool_id=tool_id,
                tool_name="get_project_context",
                success=True,
                result=context,
            )

        except Exception as e:
            return ToolResult(
                tool_id=tool_id,
                tool_name="get_project_context",
                success=False,
                error=str(e),
            )

    async def _execute_list_artifacts(
        self, tool_id: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """Execute list_artifacts tool."""
        try:
            if not self.project_manager:
                raise ValueError("Project manager not configured")

            artifact_type = parameters.get("artifact_type", "all")
            artifacts = self.project_manager.list_artifacts(artifact_type)

            return ToolResult(
                tool_id=tool_id,
                tool_name="list_artifacts",
                success=True,
                result={
                    "artifact_type": artifact_type,
                    "artifacts": artifacts,
                    "count": len(artifacts),
                },
            )

        except Exception as e:
            return ToolResult(
                tool_id=tool_id,
                tool_name="list_artifacts",
                success=False,
                error=str(e),
            )


# ============================================================================
# Tool Response Formatting
# ============================================================================

def format_tool_result_for_llm(result: ToolResult) -> str:
    """
    Format tool result for feeding back to LLM.
    
    Args:
        result: ToolResult object
        
    Returns:
        Formatted string for LLM
    """
    if result.success:
        result_data = result.result or {}
        return json.dumps(result_data, indent=2)
    else:
        return f"Error: {result.error}"


def extract_tool_calls_from_response(
    response: Dict[str, Any],
) -> List[ToolCall]:
    """
    Extract tool calls from LLM response.
    
    Args:
        response: LLM response dictionary
        
    Returns:
        List of ToolCall objects
    """
    from uuid import uuid4
    from datetime import datetime

    tool_calls = []

    # Handle OpenAI-style tool_calls in message
    message = response.get("message", {})
    if isinstance(message, dict):
        tool_calls_data = message.get("tool_calls", [])
    elif hasattr(message, "tool_calls"):
        tool_calls_data = message.tool_calls
    else:
        tool_calls_data = []

    for call_data in tool_calls_data:
        if isinstance(call_data, dict):
            tool_id = call_data.get("id", str(uuid4()))
            tool_name = call_data.get("function", {}).get("name", "")
            parameters_str = call_data.get("function", {}).get("arguments", "{}")
        else:
            # Handle object-style tool calls
            tool_id = getattr(call_data, "id", str(uuid4()))
            tool_name = getattr(call_data.function, "name", "")
            parameters_str = getattr(call_data.function, "arguments", "{}")

        try:
            parameters = json.loads(parameters_str)
        except json.JSONDecodeError:
            parameters = {}

        tool_calls.append(
            ToolCall(
                tool_id=tool_id,
                tool_name=tool_name,
                parameters=parameters,
                timestamp=datetime.utcnow().isoformat(),
            )
        )

    return tool_calls
