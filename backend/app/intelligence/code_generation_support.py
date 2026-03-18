"""
Code Generation Support — Format, display, and handle code generation artifacts.

Features:
- Code block formatting (markdown, Python, etc.)
- Code artifact creation and management
- Validation result formatting
- Impact analysis presentation
- Code diff visualization

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Constants
# ============================================================================

class CodeLanguage(str, Enum):
    """Programming languages for code formatting."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    SQL = "sql"
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    BASH = "bash"
    DOCKERFILE = "dockerfile"
    HTML = "html"
    CSS = "css"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class CodeArtifact:
    """
    Represents a code artifact (file or code block).
    
    Attributes:
        artifact_id: Unique identifier
        file_path: File path or name
        language: Programming language
        content: Code content
        description: Human-readable description
        created_at: Creation timestamp
        metadata: Additional metadata
    """
    artifact_id: str
    file_path: str
    language: CodeLanguage
    content: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "file_path": self.file_path,
            "language": self.language.value,
            "content": self.content,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Format as markdown code block."""
        lang = self.language.value
        return f"```{lang}\n{self.content}\n```"


@dataclass
class CodeDiff:
    """
    Represents a code diff.
    
    Attributes:
        file_path: File path
        original_content: Original content
        new_content: New content
        diff_lines: Unified diff format
    """
    file_path: str
    original_content: Optional[str]
    new_content: Optional[str]
    diff_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "original_content": self.original_content,
            "new_content": self.new_content,
            "diff_lines": self.diff_lines,
        }

    def to_markdown(self) -> str:
        """Format as markdown diff block."""
        lines = ["```diff"]
        lines.extend(self.diff_lines)
        lines.append("```")
        return "\n".join(lines)


@dataclass
class ValidationResultPresentation:
    """Formatted validation result for display."""
    valid: bool
    summary: str
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "summary": self.summary,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "info": self.info,
            "suggestions": self.suggestions,
            "patterns_matched": self.patterns_matched,
        }

    def to_markdown(self) -> str:
        """Format as markdown."""
        lines = []

        # Status
        status_emoji = "✅" if self.valid else "❌"
        lines.append(f"## {status_emoji} Validation Result\n")

        # Summary
        lines.append(f"**Summary:** {self.summary}\n")

        # Critical Issues
        if self.critical_issues:
            lines.append("### 🔴 Critical Issues")
            for issue in self.critical_issues:
                lines.append(f"- {issue}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("### 🟡 Warnings")
            for warning in self.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Info
        if self.info:
            lines.append("### 🔵 Info")
            for item in self.info:
                lines.append(f"- {item}")
            lines.append("")

        # Suggestions
        if self.suggestions:
            lines.append("### 💡 Suggestions")
            for suggestion in self.suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")

        # Patterns Matched
        if self.patterns_matched:
            lines.append("### 📋 Patterns Matched")
            for pattern in self.patterns_matched:
                lines.append(f"- {pattern}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class ImpactAnalysisPresentation:
    """Formatted impact analysis for display."""
    impact_score: float  # 0.0 to 1.0
    risk_level: str      # low, medium, high
    summary: str
    affected_modules: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    test_impact: str = ""
    performance_impact: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "impact_score": self.impact_score,
            "risk_level": self.risk_level,
            "summary": self.summary,
            "affected_modules": self.affected_modules,
            "breaking_changes": self.breaking_changes,
            "test_impact": self.test_impact,
            "performance_impact": self.performance_impact,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        """Format as markdown."""
        lines = []

        # Title and risk level
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(self.risk_level, "❓")
        lines.append(f"## {risk_emoji} Impact Analysis\n")

        # Score and summary
        score_pct = int(self.impact_score * 100)
        lines.append(f"**Impact Score:** {score_pct}%")
        lines.append(f"**Risk Level:** {self.risk_level}")
        lines.append(f"**Summary:** {self.summary}\n")

        # Affected modules
        if self.affected_modules:
            lines.append("### 📦 Affected Modules")
            for module in self.affected_modules:
                lines.append(f"- {module}")
            lines.append("")

        # Breaking changes
        if self.breaking_changes:
            lines.append("### ⚠️ Breaking Changes")
            for change in self.breaking_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Test impact
        if self.test_impact:
            lines.append(f"### 🧪 Test Impact\n{self.test_impact}\n")

        # Performance impact
        if self.performance_impact:
            lines.append(f"### ⚡ Performance Impact\n{self.performance_impact}\n")

        # Recommendations
        if self.recommendations:
            lines.append("### 💭 Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        return "\n".join(lines)


# ============================================================================
# Formatting Functions
# ============================================================================

def format_code_block(
    content: str,
    language: CodeLanguage = CodeLanguage.PYTHON,
    title: Optional[str] = None,
    line_numbers: bool = False,
) -> str:
    """
    Format code block for markdown display.
    
    Args:
        content: Code content
        language: Programming language
        title: Optional title/filename
        line_numbers: Whether to include line numbers
        
    Returns:
        Formatted markdown code block
    """
    lines = []

    if title:
        lines.append(f"**File:** `{title}`")

    # Code block with language
    lines.append(f"```{language.value}")

    if line_numbers:
        # Add line numbers
        for i, line in enumerate(content.split("\n"), 1):
            lines.append(f"{i:4d} {line}")
    else:
        lines.append(content)

    lines.append("```")

    return "\n".join(lines)


def format_validation_issues(
    issues: List[Dict[str, Any]],
) -> ValidationResultPresentation:
    """
    Format validation issues into presentation.
    
    Args:
        issues: List of validation issues
        
    Returns:
        ValidationResultPresentation
    """
    critical = []
    warnings = []
    info = []

    for issue in issues:
        severity = issue.get("severity", "info").lower()
        message = issue.get("message", "")
        file = issue.get("file", "")
        line = issue.get("line")

        # Format issue message
        if file and line:
            formatted = f"{file}:{line} - {message}"
        elif file:
            formatted = f"{file} - {message}"
        else:
            formatted = message

        if severity == "error":
            critical.append(formatted)
        elif severity == "warning":
            warnings.append(formatted)
        else:
            info.append(formatted)

    return ValidationResultPresentation(
        valid=len(critical) == 0,
        summary=f"Found {len(critical)} errors, {len(warnings)} warnings",
        critical_issues=critical,
        warnings=warnings,
        info=info,
    )


def format_impact_analysis(
    impact_data: Dict[str, Any],
) -> ImpactAnalysisPresentation:
    """
    Format impact analysis into presentation.
    
    Args:
        impact_data: Impact analysis data from Code Architect
        
    Returns:
        ImpactAnalysisPresentation
    """
    impact_score = impact_data.get("impact_score", 0.5)

    # Determine risk level
    if impact_score < 0.3:
        risk_level = "low"
    elif impact_score < 0.7:
        risk_level = "medium"
    else:
        risk_level = "high"

    # Format recommendations
    recommendations = []
    if impact_data.get("breaking_changes"):
        recommendations.append("Prepare migration guide for breaking changes")
    if risk_level == "high":
        recommendations.append("Consider phased rollout")
        recommendations.append("Ensure comprehensive testing before deployment")
    if impact_data.get("test_coverage_impact") == "high":
        recommendations.append("Review and expand test coverage")

    return ImpactAnalysisPresentation(
        impact_score=impact_score,
        risk_level=risk_level,
        summary=impact_data.get("summary", ""),
        affected_modules=impact_data.get("affected_modules", []),
        breaking_changes=impact_data.get("breaking_changes", []),
        test_impact=f"Coverage impact: {impact_data.get('test_coverage_impact', 'medium')}",
        performance_impact=f"Performance: {impact_data.get('performance_impact', 'none')}",
        recommendations=recommendations,
    )


def create_code_artifact(
    file_path: str,
    content: str,
    language: Optional[CodeLanguage] = None,
    description: str = "",
) -> CodeArtifact:
    """
    Create a code artifact from file and content.
    
    Args:
        file_path: File path or name
        content: Code content
        language: Programming language (auto-detected if None)
        description: Human-readable description
        
    Returns:
        CodeArtifact
    """
    # Auto-detect language if not provided
    if language is None:
        language = detect_language_from_filename(file_path)

    from uuid import uuid4

    artifact = CodeArtifact(
        artifact_id=str(uuid4()),
        file_path=file_path,
        language=language,
        content=content,
        description=description,
    )

    return artifact


def detect_language_from_filename(filename: str) -> CodeLanguage:
    """
    Detect programming language from filename.
    
    Args:
        filename: File name or path
        
    Returns:
        Detected CodeLanguage
    """
    import os

    _, ext = os.path.splitext(filename.lower())

    # Map file extensions to languages
    ext_map = {
        ".py": CodeLanguage.PYTHON,
        ".js": CodeLanguage.JAVASCRIPT,
        ".ts": CodeLanguage.TYPESCRIPT,
        ".tsx": CodeLanguage.TYPESCRIPT,
        ".jsx": CodeLanguage.JAVASCRIPT,
        ".java": CodeLanguage.JAVA,
        ".cpp": CodeLanguage.CPP,
        ".cc": CodeLanguage.CPP,
        ".c++": CodeLanguage.CPP,
        ".go": CodeLanguage.GO,
        ".rs": CodeLanguage.RUST,
        ".sql": CodeLanguage.SQL,
        ".yml": CodeLanguage.YAML,
        ".yaml": CodeLanguage.YAML,
        ".json": CodeLanguage.JSON,
        ".md": CodeLanguage.MARKDOWN,
        ".sh": CodeLanguage.BASH,
        ".bash": CodeLanguage.BASH,
        ".dockerfile": CodeLanguage.DOCKERFILE,
        ".html": CodeLanguage.HTML,
        ".htm": CodeLanguage.HTML,
        ".css": CodeLanguage.CSS,
        ".scss": CodeLanguage.CSS,
    }

    return ext_map.get(ext, CodeLanguage.PYTHON)


# ============================================================================
# Message Formatting for Agent Conversation
# ============================================================================

def format_code_generation_message(
    task: str,
    result: Dict[str, Any],
) -> str:
    """
    Format code generation result as agent message.
    
    Args:
        task: Original task description
        result: Code generation result
        
    Returns:
        Formatted message
    """
    lines = []

    lines.append(f"## Code Generation Result\n")
    lines.append(f"**Task:** {task}\n")

    # Changes summary
    changes = result.get("changes", [])
    if changes:
        lines.append(f"**Changes:** {len(changes)} file(s)")
        for change in changes:
            action = change.get("action", "unknown")
            file = change.get("file", "unknown")
            lines.append(f"  - {action}: `{file}`")
        lines.append("")

    # Explanation
    if result.get("explanation"):
        lines.append(f"**Explanation:**\n{result['explanation']}\n")

    # Plan
    if result.get("plan"):
        lines.append("**Implementation Plan:**")
        for item in result["plan"]:
            lines.append(f"  - {item}")
        lines.append("")

    # Patterns used
    if result.get("patterns_used"):
        lines.append("**Patterns Used:**")
        for pattern in result["patterns_used"]:
            lines.append(f"  - {pattern}")
        lines.append("")

    # Tests suggested
    if result.get("tests_suggested"):
        lines.append("**Suggested Tests:**")
        for test in result["tests_suggested"]:
            lines.append(f"  - {test}")
        lines.append("")

    return "\n".join(lines)


def format_validation_message(result: Dict[str, Any]) -> str:
    """
    Format validation result as agent message.
    
    Args:
        result: Validation result
        
    Returns:
        Formatted message
    """
    presentation = ValidationResultPresentation(
        valid=result.get("valid", True),
        summary=result.get("summary", ""),
        critical_issues=[
            i["message"]
            for i in result.get("issues", [])
            if i.get("severity") == "error"
        ],
        warnings=[
            i["message"]
            for i in result.get("issues", [])
            if i.get("severity") == "warning"
        ],
        patterns_matched=result.get("patterns_matched", []),
    )

    return presentation.to_markdown()


def format_impact_message(result: Dict[str, Any]) -> str:
    """
    Format impact analysis as agent message.
    
    Args:
        result: Impact analysis result
        
    Returns:
        Formatted message
    """
    presentation = format_impact_analysis(result)
    return presentation.to_markdown()
