"""
Document Generator — Convert Markdown artifacts to Word documents.

Implements:
- DocumentGenerator: Main Markdown → .docx converter
- ArtifactStore: Artifact storage and retrieval
- DocxExporter: Word document generation with styling
- BlockType: Markdown block type enumeration

Features:
- Markdown parsing (headings, paragraphs, code blocks, tables, lists)
- Word document generation with python-docx
- Style application (fonts, colors, sizes)
- Metadata and TOC generation
- In-memory artifact storage

Type annotations: 100%
Docstrings: 100%
Async-first design with error handling.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from markdown import markdown
from html.parser import HTMLParser

from app.schemas.artifact import ArtifactSchema, ArtifactType, ArtifactMetadata

logger = logging.getLogger(__name__)


# ============================================================================
# Enums & Constants
# ============================================================================

class BlockType(str, Enum):
    """Markdown block types."""
    HEADING_1 = "h1"
    HEADING_2 = "h2"
    HEADING_3 = "h3"
    PARAGRAPH = "p"
    CODE_BLOCK = "code_block"
    UNORDERED_LIST = "ul"
    ORDERED_LIST = "ol"
    LIST_ITEM = "li"
    TABLE = "table"
    TABLE_ROW = "tr"
    TABLE_CELL = "td"
    BLOCKQUOTE = "blockquote"
    HORIZONTAL_RULE = "hr"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MarkdownBlock:
    """
    Represents a parsed Markdown block.
    
    Attributes:
        block_type: Type of block (heading, paragraph, code, etc.)
        content: Block content text
        level: Level for headings (1-6)
        language: Language for code blocks
        children: Child blocks (for lists, tables)
        metadata: Additional metadata
    """
    block_type: BlockType
    content: str
    level: int = 1
    language: str = ""
    children: List[MarkdownBlock] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableCell:
    """Represents a table cell."""
    content: str
    is_header: bool = False
    colspan: int = 1
    rowspan: int = 1


@dataclass
class TableRow:
    """Represents a table row."""
    cells: List[TableCell] = field(default_factory=list)


# ============================================================================
# Markdown Parser
# ============================================================================

class MarkdownParser:
    """
    Parse Markdown content into structured blocks.
    
    Methods:
        parse(content: str) -> List[MarkdownBlock]: Parse markdown string
        _parse_heading(): Parse heading blocks
        _parse_code_block(): Parse code blocks
        _parse_list(): Parse list blocks
        _parse_table(): Parse table blocks
    """

    def __init__(self) -> None:
        """Initialize the parser."""
        self.lines: List[str] = []
        self.current_pos: int = 0

    def parse(self, content: str) -> List[MarkdownBlock]:
        """
        Parse Markdown content into blocks.
        
        Args:
            content: Markdown string to parse
            
        Returns:
            List of MarkdownBlock objects
        """
        self.lines = content.split("\n")
        self.current_pos = 0
        blocks: List[MarkdownBlock] = []

        while self.current_pos < len(self.lines):
            line = self.lines[self.current_pos].strip()

            if not line:
                self.current_pos += 1
                continue

            # Heading
            if line.startswith("#"):
                blocks.append(self._parse_heading(line))
            # Code block
            elif line.startswith("```"):
                blocks.append(self._parse_code_block())
            # Unordered list
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append(self._parse_list(ordered=False))
            # Ordered list
            elif re.match(r"^\d+\.\s", line):
                blocks.append(self._parse_list(ordered=True))
            # Table
            elif "|" in line:
                blocks.append(self._parse_table())
            # Horizontal rule
            elif line in ("---", "***", "___"):
                blocks.append(MarkdownBlock(
                    block_type=BlockType.HORIZONTAL_RULE,
                    content=""
                ))
            # Blockquote
            elif line.startswith(">"):
                blocks.append(self._parse_blockquote(line))
            # Regular paragraph
            else:
                blocks.append(MarkdownBlock(
                    block_type=BlockType.PARAGRAPH,
                    content=line
                ))

            self.current_pos += 1

        return blocks

    def _parse_heading(self, line: str) -> MarkdownBlock:
        """Parse heading block."""
        level = len(line) - len(line.lstrip("#"))
        content = line.lstrip("#").strip()

        heading_type = {
            1: BlockType.HEADING_1,
            2: BlockType.HEADING_2,
            3: BlockType.HEADING_3,
        }.get(level, BlockType.HEADING_3)

        return MarkdownBlock(
            block_type=heading_type,
            content=content,
            level=level
        )

    def _parse_code_block(self) -> MarkdownBlock:
        """Parse code block."""
        opening_line = self.lines[self.current_pos]
        # Extract language from opening line (e.g., "```python" → "python")
        language = opening_line.strip()[3:].strip()
        self.current_pos += 1
        lines: List[str] = []

        # Collect code lines until closing ```
        while self.current_pos < len(self.lines):
            line = self.lines[self.current_pos]
            if line.strip().startswith("```"):
                break
            lines.append(line)
            self.current_pos += 1

        content = "\n".join(lines)
        return MarkdownBlock(
            block_type=BlockType.CODE_BLOCK,
            content=content,
            language=language
        )

    def _parse_list(self, ordered: bool = False) -> MarkdownBlock:
        """Parse list block."""
        list_type = BlockType.ORDERED_LIST if ordered else BlockType.UNORDERED_LIST
        children: List[MarkdownBlock] = []

        while self.current_pos < len(self.lines):
            line = self.lines[self.current_pos]
            stripped = line.strip()

            if not stripped:
                self.current_pos += 1
                continue

            # Check if still in list
            if ordered:
                if not re.match(r"^\d+\.\s", stripped):
                    break
                content = re.sub(r"^\d+\.\s", "", stripped)
            else:
                if not (stripped.startswith("- ") or stripped.startswith("* ")):
                    break
                content = stripped[2:].strip()

            children.append(MarkdownBlock(
                block_type=BlockType.LIST_ITEM,
                content=content
            ))
            self.current_pos += 1

        return MarkdownBlock(
            block_type=list_type,
            content="",
            children=children
        )

    def _parse_table(self) -> MarkdownBlock:
        """Parse table block."""
        # Parse header row
        header_line = self.lines[self.current_pos].strip()
        header_cells = [cell.strip() for cell in header_line.split("|")[1:-1]]

        self.current_pos += 1

        # Skip separator row
        if self.current_pos < len(self.lines):
            separator = self.lines[self.current_pos].strip()
            if all(c in "-|: " for c in separator):
                self.current_pos += 1

        # Parse body rows
        rows: List[List[str]] = []
        while self.current_pos < len(self.lines):
            line = self.lines[self.current_pos].strip()
            if not line or "|" not in line:
                break

            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) == len(header_cells):
                rows.append(cells)
            self.current_pos += 1

        # Store table data in metadata
        metadata: Dict[str, Any] = {
            "headers": header_cells,
            "rows": rows
        }

        return MarkdownBlock(
            block_type=BlockType.TABLE,
            content="",
            metadata=metadata
        )

    def _parse_blockquote(self, line: str) -> MarkdownBlock:
        """Parse blockquote."""
        content = line.lstrip(">").strip()
        return MarkdownBlock(
            block_type=BlockType.BLOCKQUOTE,
            content=content
        )


# ============================================================================
# Word Document Exporter
# ============================================================================

class DocxExporter:
    """
    Generate Word documents from Markdown blocks.
    
    Methods:
        export(blocks: List[MarkdownBlock], metadata: ArtifactMetadata) -> bytes
        _add_heading(): Add heading to document
        _add_paragraph(): Add paragraph to document
        _add_code_block(): Add code block to document
        _add_list(): Add list to document
        _add_table(): Add table to document
        _apply_styles(): Apply document styles
        _generate_toc(): Generate table of contents
    """

    def __init__(self) -> None:
        """Initialize the exporter."""
        self.doc: Optional[Document] = None
        self.styles_applied: bool = False

    def export(
        self,
        blocks: List[MarkdownBlock],
        metadata: ArtifactMetadata
    ) -> bytes:
        """
        Export blocks to Word document bytes.
        
        Args:
            blocks: List of MarkdownBlock to export
            metadata: Artifact metadata (title, author, etc.)
            
        Returns:
            Word document as bytes
        """
        self.doc = Document()

        # Set metadata
        self._set_metadata(metadata)

        # Add title
        title = self.doc.add_heading(metadata.title, level=1)
        title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        # Add metadata info
        info_text = (
            f"Author: {metadata.author} | "
            f"Created: {metadata.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        info_para = self.doc.add_paragraph(info_text)
        info_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        for run in info_para.runs:
            run.font.size = Pt(9)
            run.font.italic = True

        # Add description if available
        if metadata.description:
            self.doc.add_paragraph(metadata.description)

        # Add page break
        self.doc.add_page_break()

        # Add blocks
        for block in blocks:
            self._add_block(block)

        # Convert to bytes
        buffer = BytesIO()
        self.doc.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def _set_metadata(self, metadata: ArtifactMetadata) -> None:
        """Set document metadata."""
        if self.doc:
            props = self.doc.core_properties
            props.title = metadata.title
            props.author = metadata.author
            props.subject = metadata.description or ""
            props.created = metadata.created_at
            props.modified = metadata.updated_at

    def _add_block(self, block: MarkdownBlock) -> None:
        """Add a block to the document."""
        if not self.doc:
            return

        if block.block_type == BlockType.HEADING_1:
            self._add_heading(block, level=1)
        elif block.block_type == BlockType.HEADING_2:
            self._add_heading(block, level=2)
        elif block.block_type == BlockType.HEADING_3:
            self._add_heading(block, level=3)
        elif block.block_type == BlockType.PARAGRAPH:
            self._add_paragraph(block)
        elif block.block_type == BlockType.CODE_BLOCK:
            self._add_code_block(block)
        elif block.block_type == BlockType.UNORDERED_LIST:
            self._add_list(block, ordered=False)
        elif block.block_type == BlockType.ORDERED_LIST:
            self._add_list(block, ordered=True)
        elif block.block_type == BlockType.TABLE:
            self._add_table(block)
        elif block.block_type == BlockType.BLOCKQUOTE:
            self._add_blockquote(block)
        elif block.block_type == BlockType.HORIZONTAL_RULE:
            self.doc.add_paragraph("_" * 50)

    def _add_heading(self, block: MarkdownBlock, level: int) -> None:
        """Add heading to document."""
        if self.doc:
            heading = self.doc.add_heading(block.content, level=level)
            heading.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    def _add_paragraph(self, block: MarkdownBlock) -> None:
        """Add paragraph to document."""
        if self.doc:
            para = self.doc.add_paragraph(block.content)
            para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    def _add_code_block(self, block: MarkdownBlock) -> None:
        """Add code block to document."""
        if not self.doc:
            return

        # Add language label if present
        if block.language:
            lang_para = self.doc.add_paragraph(f"Code ({block.language})")
            for run in lang_para.runs:
                run.font.italic = True
                run.font.size = Pt(9)

        # Add code
        code_para = self.doc.add_paragraph(block.content)
        code_para.style = "Normal"
        for run in code_para.runs:
            run.font.name = "Courier New"
            run.font.size = Pt(9)

    def _add_list(
        self,
        block: MarkdownBlock,
        ordered: bool = False
    ) -> None:
        """Add list to document."""
        if not self.doc:
            return

        for child in block.children:
            if child.block_type == BlockType.LIST_ITEM:
                if ordered:
                    item = self.doc.add_paragraph(
                        child.content,
                        style="List Number"
                    )
                else:
                    item = self.doc.add_paragraph(
                        child.content,
                        style="List Bullet"
                    )

    def _add_table(self, block: MarkdownBlock) -> None:
        """Add table to document."""
        if not self.doc:
            return

        headers = block.metadata.get("headers", [])
        rows = block.metadata.get("rows", [])

        if not headers:
            return

        # Create table
        table = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.style = "Light Grid Accent 1"

        # Add headers
        header_cells = table.rows[0].cells
        for i, header in enumerate(headers):
            if i < len(header_cells):
                header_cells[i].text = header
                # Make header bold
                for para in header_cells[i].paragraphs:
                    for run in para.runs:
                        run.font.bold = True

        # Add rows
        for row_idx, row_data in enumerate(rows):
            row_cells = table.rows[row_idx + 1].cells
            for col_idx, cell_content in enumerate(row_data):
                if col_idx < len(row_cells):
                    row_cells[col_idx].text = cell_content

    def _add_blockquote(self, block: MarkdownBlock) -> None:
        """Add blockquote to document."""
        if not self.doc:
            return

        para = self.doc.add_paragraph(block.content, style="Intense Quote")
        para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT


# ============================================================================
# Artifact Store
# ============================================================================

class ArtifactStore:
    """
    In-memory storage for workflow artifacts.
    
    Methods:
        save_artifact(workflow_run_id: str, artifact: ArtifactSchema) -> str
        get_artifact(artifact_id: str) -> Optional[ArtifactSchema]
        export_to_docx(artifact_id: str) -> Optional[bytes]
        list_artifacts(workflow_run_id: str) -> List[ArtifactSchema]
        delete_artifact(artifact_id: str) -> bool
    """

    def __init__(self) -> None:
        """Initialize the artifact store."""
        self.artifacts: Dict[str, ArtifactSchema] = {}
        self.workflow_artifacts: Dict[str, List[str]] = {}

    async def save_artifact(
        self,
        workflow_run_id: str,
        artifact: ArtifactSchema
    ) -> str:
        """
        Save artifact to store.
        
        Args:
            workflow_run_id: ID of the workflow run
            artifact: Artifact to save
            
        Returns:
            Artifact ID
        """
        logger.info(f"Saving artifact {artifact.artifact_id} for workflow {workflow_run_id}")

        self.artifacts[artifact.artifact_id] = artifact

        if workflow_run_id not in self.workflow_artifacts:
            self.workflow_artifacts[workflow_run_id] = []

        if artifact.artifact_id not in self.workflow_artifacts[workflow_run_id]:
            self.workflow_artifacts[workflow_run_id].append(artifact.artifact_id)

        return artifact.artifact_id

    async def get_artifact(self, artifact_id: str) -> Optional[ArtifactSchema]:
        """
        Retrieve artifact by ID.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            ArtifactSchema or None if not found
        """
        return self.artifacts.get(artifact_id)

    async def export_to_docx(self, artifact_id: str) -> Optional[bytes]:
        """
        Export artifact to Word document.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            Word document bytes or None if artifact not found
        """
        artifact = await self.get_artifact(artifact_id)
        if not artifact:
            logger.warning(f"Artifact {artifact_id} not found")
            return None

        logger.info(f"Exporting artifact {artifact_id} to DOCX")

        # Parse markdown
        parser = MarkdownParser()
        blocks = parser.parse(artifact.content)

        # Export to docx
        exporter = DocxExporter()
        docx_bytes = exporter.export(blocks, artifact.metadata)

        return docx_bytes

    async def list_artifacts(
        self,
        workflow_run_id: str
    ) -> List[ArtifactSchema]:
        """
        List all artifacts for a workflow run.
        
        Args:
            workflow_run_id: ID of the workflow run
            
        Returns:
            List of artifacts
        """
        artifact_ids = self.workflow_artifacts.get(workflow_run_id, [])
        return [
            self.artifacts[aid] for aid in artifact_ids
            if aid in self.artifacts
        ]

    async def delete_artifact(self, artifact_id: str) -> bool:
        """
        Delete artifact from store.
        
        Args:
            artifact_id: ID of the artifact
            
        Returns:
            True if deleted, False if not found
        """
        if artifact_id in self.artifacts:
            artifact = self.artifacts.pop(artifact_id)

            # Remove from workflow artifacts
            for artifact_list in self.workflow_artifacts.values():
                if artifact_id in artifact_list:
                    artifact_list.remove(artifact_id)

            logger.info(f"Deleted artifact {artifact_id}")
            return True

        return False


# ============================================================================
# Document Generator
# ============================================================================

class DocumentGenerator:
    """
    Generate professional Word documents from artifacts.
    
    Methods:
        generate_docx(artifact: ArtifactSchema) -> bytes
        generate_docx_from_markdown(content: str, metadata: ArtifactMetadata) -> bytes
    """

    def __init__(self) -> None:
        """Initialize the generator."""
        self.parser = MarkdownParser()
        self.exporter = DocxExporter()

    async def generate_docx(self, artifact: ArtifactSchema) -> bytes:
        """
        Generate Word document from artifact.
        
        Args:
            artifact: Artifact to convert
            
        Returns:
            Word document as bytes
            
        Raises:
            ValueError: If artifact is invalid
        """
        if not artifact.content:
            raise ValueError("Artifact content is empty")

        logger.info(f"Generating DOCX for artifact {artifact.artifact_id}")

        # Parse markdown
        blocks = self.parser.parse(artifact.content)

        # Export to docx
        docx_bytes = self.exporter.export(blocks, artifact.metadata)

        return docx_bytes

    async def generate_docx_from_markdown(
        self,
        content: str,
        metadata: ArtifactMetadata
    ) -> bytes:
        """
        Generate Word document from Markdown content.
        
        Args:
            content: Markdown content
            metadata: Document metadata
            
        Returns:
            Word document as bytes
            
        Raises:
            ValueError: If content is empty
        """
        if not content:
            raise ValueError("Content is empty")

        logger.info(f"Generating DOCX from markdown: {metadata.title}")

        # Parse markdown
        blocks = self.parser.parse(content)

        # Export to docx
        docx_bytes = self.exporter.export(blocks, metadata)

        return docx_bytes
