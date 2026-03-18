"""
Tests for document generation (Phase 3).

Test Coverage:
- Markdown parsing
- Document generation
- Style application
- Artifact storage
- DOCX export

Type annotations: 100%
Docstrings: 100%
"""

from __future__ import annotations

import pytest
from datetime import datetime
from io import BytesIO

from app.output.document_generator import (
    MarkdownParser,
    MarkdownBlock,
    BlockType,
    DocumentGenerator,
    ArtifactStore,
    DocxExporter,
)
from app.schemas.artifact import (
    ArtifactSchema,
    ArtifactType,
    ArtifactMetadata,
)


# ============================================================================
# Markdown Parser Tests
# ============================================================================

class TestMarkdownParser:
    """Test Markdown parsing."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = MarkdownParser()

    def test_parse_heading(self) -> None:
        """Test heading parsing."""
        content = "# Title\n## Subtitle\n### Sub-subtitle"
        blocks = self.parser.parse(content)

        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.HEADING_1
        assert blocks[0].content == "Title"
        assert blocks[1].block_type == BlockType.HEADING_2
        assert blocks[1].content == "Subtitle"
        assert blocks[2].block_type == BlockType.HEADING_3

    def test_parse_paragraph(self) -> None:
        """Test paragraph parsing."""
        content = "This is a paragraph.\nAnother paragraph."
        blocks = self.parser.parse(content)

        assert len(blocks) >= 2
        assert blocks[0].block_type == BlockType.PARAGRAPH
        assert blocks[0].content == "This is a paragraph."

    def test_parse_code_block(self) -> None:
        """Test code block parsing."""
        content = "```python\ndef hello():\n    print('hello')\n```"
        blocks = self.parser.parse(content)

        code_blocks = [b for b in blocks if b.block_type == BlockType.CODE_BLOCK]
        assert len(code_blocks) == 1
        assert code_blocks[0].language == "python"
        assert "print" in code_blocks[0].content

    def test_parse_unordered_list(self) -> None:
        """Test unordered list parsing."""
        content = "- Item 1\n- Item 2\n- Item 3"
        blocks = self.parser.parse(content)

        list_blocks = [b for b in blocks if b.block_type == BlockType.UNORDERED_LIST]
        assert len(list_blocks) >= 1
        assert len(list_blocks[0].children) == 3

    def test_parse_ordered_list(self) -> None:
        """Test ordered list parsing."""
        content = "1. First\n2. Second\n3. Third"
        blocks = self.parser.parse(content)

        list_blocks = [b for b in blocks if b.block_type == BlockType.ORDERED_LIST]
        assert len(list_blocks) >= 1
        assert len(list_blocks[0].children) == 3

    def test_parse_table(self) -> None:
        """Test table parsing."""
        content = """| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |
| Cell 3 | Cell 4 |"""
        blocks = self.parser.parse(content)

        table_blocks = [b for b in blocks if b.block_type == BlockType.TABLE]
        assert len(table_blocks) >= 1
        assert table_blocks[0].metadata["headers"] == ["Header 1", "Header 2"]
        assert len(table_blocks[0].metadata["rows"]) == 2

    def test_parse_horizontal_rule(self) -> None:
        """Test horizontal rule parsing."""
        content = "---"
        blocks = self.parser.parse(content)

        hr_blocks = [b for b in blocks if b.block_type == BlockType.HORIZONTAL_RULE]
        assert len(hr_blocks) == 1

    def test_parse_blockquote(self) -> None:
        """Test blockquote parsing."""
        content = "> This is a quote"
        blocks = self.parser.parse(content)

        quote_blocks = [b for b in blocks if b.block_type == BlockType.BLOCKQUOTE]
        assert len(quote_blocks) >= 1
        assert "quote" in quote_blocks[0].content

    def test_parse_complex_document(self) -> None:
        """Test parsing a complex document."""
        content = """# Product Specification

## Overview
This is an overview paragraph.

## Features

- Feature 1
- Feature 2
- Feature 3

## Code Example

```python
def example():
    return "test"
```

## Requirements

| Requirement | Status |
| --- | --- |
| Auth | Done |
| API | In Progress |

## Notes
> Important note here
"""
        blocks = self.parser.parse(content)

        assert len(blocks) > 5
        assert any(b.block_type == BlockType.HEADING_1 for b in blocks)
        assert any(b.block_type == BlockType.HEADING_2 for b in blocks)
        assert any(b.block_type == BlockType.CODE_BLOCK for b in blocks)
        assert any(b.block_type == BlockType.TABLE for b in blocks)


# ============================================================================
# Artifact Store Tests
# ============================================================================

@pytest.mark.asyncio
class TestArtifactStore:
    """Test artifact storage."""

    async def test_save_and_get_artifact(self) -> None:
        """Test saving and retrieving artifacts."""
        store = ArtifactStore()

        metadata = ArtifactMetadata(
            title="Test Artifact",
            author="test",
            workflow_run_id="run-123"
        )

        artifact = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.PRODUCT_SPEC,
            content="# Test\n\nTest content",
            metadata=metadata
        )

        artifact_id = await store.save_artifact("run-123", artifact)
        assert artifact_id == artifact.artifact_id

        retrieved = await store.get_artifact(artifact_id)
        assert retrieved is not None
        assert retrieved.content == artifact.content
        assert retrieved.metadata.title == "Test Artifact"

    async def test_list_artifacts_by_workflow(self) -> None:
        """Test listing artifacts by workflow."""
        store = ArtifactStore()

        metadata1 = ArtifactMetadata(
            title="Artifact 1",
            author="test",
            workflow_run_id="run-123"
        )
        artifact1 = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.PRODUCT_SPEC,
            content="Content 1",
            metadata=metadata1
        )

        metadata2 = ArtifactMetadata(
            title="Artifact 2",
            author="test",
            workflow_run_id="run-123"
        )
        artifact2 = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.TECHNICAL_DESIGN,
            content="Content 2",
            metadata=metadata2
        )

        await store.save_artifact("run-123", artifact1)
        await store.save_artifact("run-123", artifact2)

        artifacts = await store.list_artifacts("run-123")
        assert len(artifacts) == 2

    async def test_delete_artifact(self) -> None:
        """Test deleting artifacts."""
        store = ArtifactStore()

        metadata = ArtifactMetadata(
            title="Test",
            author="test",
            workflow_run_id="run-123"
        )
        artifact = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.PRODUCT_SPEC,
            content="Content",
            metadata=metadata
        )

        artifact_id = await store.save_artifact("run-123", artifact)
        
        # Delete
        deleted = await store.delete_artifact(artifact_id)
        assert deleted is True

        # Verify it's gone
        retrieved = await store.get_artifact(artifact_id)
        assert retrieved is None


# ============================================================================
# Document Generator Tests
# ============================================================================

@pytest.mark.asyncio
class TestDocumentGenerator:
    """Test document generation."""

    async def test_generate_docx_from_markdown(self) -> None:
        """Test generating DOCX from Markdown."""
        generator = DocumentGenerator()

        markdown_content = """# Test Document

## Section 1

This is a paragraph with **bold** and *italic* text.

### Subsection

- Bullet point 1
- Bullet point 2

```python
def test():
    return True
```

## Section 2

1. Ordered item 1
2. Ordered item 2
"""

        metadata = ArtifactMetadata(
            title="Test Document",
            author="test_user",
            workflow_run_id="run-123"
        )

        docx_bytes = await generator.generate_docx_from_markdown(
            markdown_content,
            metadata
        )

        # Verify we got bytes
        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0
        # DOCX files start with PK (ZIP format)
        assert docx_bytes[:2] == b"PK"

    async def test_generate_docx_from_artifact(self) -> None:
        """Test generating DOCX from artifact."""
        generator = DocumentGenerator()

        metadata = ArtifactMetadata(
            title="Artifact Document",
            author="test",
            workflow_run_id="run-123"
        )

        artifact = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.PRODUCT_SPEC,
            content="# Product Spec\n\nThis is the product spec content.",
            metadata=metadata
        )

        docx_bytes = await generator.generate_docx(artifact)

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0
        assert docx_bytes[:2] == b"PK"

    async def test_generate_docx_with_table(self) -> None:
        """Test generating DOCX with table."""
        generator = DocumentGenerator()

        markdown_content = """# Requirements

| Feature | Status | Owner |
| --- | --- | --- |
| Auth | Done | Alice |
| API | In Progress | Bob |
| UI | Pending | Charlie |
"""

        metadata = ArtifactMetadata(
            title="Requirements",
            author="test",
            workflow_run_id="run-123"
        )

        docx_bytes = await generator.generate_docx_from_markdown(
            markdown_content,
            metadata
        )

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0

    async def test_generate_docx_with_code_blocks(self) -> None:
        """Test generating DOCX with code blocks."""
        generator = DocumentGenerator()

        markdown_content = """# Technical Design

## Implementation

```typescript
interface User {
    id: string;
    name: string;
    email: string;
}

async function getUser(id: string): Promise<User> {
    return await api.get(`/users/${id}`);
}
```

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255)
);
```
"""

        metadata = ArtifactMetadata(
            title="Technical Design",
            author="test",
            workflow_run_id="run-123"
        )

        docx_bytes = await generator.generate_docx_from_markdown(
            markdown_content,
            metadata
        )

        assert isinstance(docx_bytes, bytes)
        assert len(docx_bytes) > 0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestPhase3Integration:
    """Integration tests for Phase 3."""

    async def test_complete_artifact_workflow(self) -> None:
        """Test complete workflow: create artifact → store → generate DOCX."""
        store = ArtifactStore()
        generator = DocumentGenerator()

        # Create artifact
        metadata = ArtifactMetadata(
            title="Complete Workflow Test",
            author="system",
            workflow_run_id="run-123"
        )

        artifact = ArtifactSchema(
            workflow_run_id="run-123",
            artifact_type=ArtifactType.QA_CHECKLIST,
            content="""# QA Checklist

## Functional Tests

- [ ] User can sign up
- [ ] User can log in
- [ ] User can create project
- [ ] User can edit project
- [ ] User can delete project

## Performance Tests

- [ ] Page load < 2s
- [ ] API response < 200ms
- [ ] Database query < 100ms
""",
            metadata=metadata
        )

        # Save to store
        artifact_id = await store.save_artifact("run-123", artifact)
        assert artifact_id is not None

        # Retrieve from store
        retrieved = await store.get_artifact(artifact_id)
        assert retrieved is not None

        # Generate DOCX
        docx_bytes = await store.export_to_docx(artifact_id)
        assert docx_bytes is not None
        assert len(docx_bytes) > 0

        # List artifacts
        artifacts = await store.list_artifacts("run-123")
        assert len(artifacts) == 1
        assert artifacts[0].artifact_id == artifact_id

    async def test_multiple_artifacts_from_workflow(self) -> None:
        """Test creating multiple artifacts from one workflow."""
        store = ArtifactStore()
        generator = DocumentGenerator()

        artifacts_data = [
            {
                "type": ArtifactType.PRODUCT_SPEC,
                "title": "Product Spec",
                "content": "# Product Spec\n\n## Overview\nProduct details here."
            },
            {
                "type": ArtifactType.TECHNICAL_DESIGN,
                "title": "Technical Design",
                "content": "# Technical Design\n\n## Architecture\nArchitecture details here."
            },
            {
                "type": ArtifactType.QA_CHECKLIST,
                "title": "QA Checklist",
                "content": "# QA Checklist\n\n- [ ] Test 1\n- [ ] Test 2"
            },
        ]

        workflow_run_id = "run-456"
        artifact_ids = []

        # Create and save all artifacts
        for data in artifacts_data:
            metadata = ArtifactMetadata(
                title=data["title"],
                author="system",
                workflow_run_id=workflow_run_id
            )

            artifact = ArtifactSchema(
                workflow_run_id=workflow_run_id,
                artifact_type=data["type"],
                content=data["content"],
                metadata=metadata
            )

            artifact_id = await store.save_artifact(workflow_run_id, artifact)
            artifact_ids.append(artifact_id)

        # Verify all saved
        artifacts = await store.list_artifacts(workflow_run_id)
        assert len(artifacts) == 3

        # Verify all can be exported
        for artifact_id in artifact_ids:
            docx_bytes = await store.export_to_docx(artifact_id)
            assert docx_bytes is not None
            assert len(docx_bytes) > 0
