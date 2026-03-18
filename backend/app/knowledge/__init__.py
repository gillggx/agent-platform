"""
Knowledge Module — Role management, knowledge bases, and prompt generation.

Exports:
- RoleRegistry: Central role management
- RoleTemplate: Role definitions
- KnowledgeBase: Knowledge storage and retrieval
- KnowledgeDocument: Knowledge document format
- PromptFactory: Prompt generation with templates
- DecisionStyle: Role decision-making styles
"""

from .role_manager import (
    RoleRegistry,
    RoleTemplate,
    KnowledgeBase,
    KnowledgeDocument,
    PromptFactory,
    DecisionStyle,
    DEFAULT_ROLES,
    SYSTEM_PROMPTS,
)

__all__ = [
    # Registry
    "RoleRegistry",
    # Roles
    "RoleTemplate",
    "DecisionStyle",
    "DEFAULT_ROLES",
    # Knowledge
    "KnowledgeBase",
    "KnowledgeDocument",
    # Prompts
    "PromptFactory",
    "SYSTEM_PROMPTS",
]
