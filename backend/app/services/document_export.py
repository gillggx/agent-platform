from typing import List, Optional
import io
from dataclasses import dataclass
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
import mistune
import re

from app.models.artifact import Artifact


@dataclass
class DocElement:
    """Intermediate document element"""
    type: str  # heading | paragraph | list | table | code
    content: str
    level: Optional[int] = None  # for headings
    items: Optional[List[str]] = None  # for lists
    headers: Optional[List[str]] = None  # for tables  
    rows: Optional[List[List[str]]] = None  # for tables
    language: Optional[str] = None  # for code blocks


class MarkdownRenderer(mistune.HTMLRenderer):
    """Custom Mistune renderer to extract document structure"""
    
    def __init__(self):
        super().__init__()
        self.elements = []
    
    def heading(self, text, level, **kwargs):
        self.elements.append(DocElement(
            type="heading",
            content=re.sub(r'<[^>]+>', '', text).strip(),
            level=level
        ))
        return ""

    def paragraph(self, text):
        if text.strip():
            self.elements.append(DocElement(
                type="paragraph", 
                content=text
            ))
        return ""
    
    def list(self, text, ordered, **kwargs):
        # mistune 3.x passes depth/level as kwargs — accept and ignore extra args
        items = re.findall(r'<li>(.*?)</li>', text, re.DOTALL)
        if items:
            self.elements.append(DocElement(
                type="list",
                content="",
                items=[re.sub(r'<[^>]+>', '', i).strip() for i in items]
            ))
        return ""

    def list_item(self, text, **kwargs):
        return f"<li>{text}</li>"
    
    def table(self, text):
        # Parse table from rendered rows
        rows = []
        headers = None
        
        # Extract table rows (simplified parsing)
        row_matches = re.findall(r'<tr>(.*?)</tr>', text)
        for i, row_text in enumerate(row_matches):
            cell_matches = re.findall(r'<t[hd]>(.*?)</t[hd]>', row_text)
            if i == 0:
                headers = cell_matches
            else:
                rows.append(cell_matches)
        
        if headers or rows:
            self.elements.append(DocElement(
                type="table",
                content="",
                headers=headers,
                rows=rows
            ))
        return ""
    
    def table_head(self, text):
        return f"<thead>{text}</thead>"
    
    def table_body(self, text):
        return f"<tbody>{text}</tbody>"
    
    def table_row(self, text):
        return f"<tr>{text}</tr>"
    
    def table_cell(self, text, align=None, is_head=False, **kwargs):
        tag = "th" if is_head else "td"
        return f"<{tag}>{text}</{tag}>"

    def block_code(self, code, info=None, **kwargs):
        self.elements.append(DocElement(
            type="code",
            content=code,
            language=info
        ))
        return ""
    
    def strong(self, text):
        return f"**{text}**"
    
    def emphasis(self, text):
        return f"*{text}*"
    
    def codespan(self, text):
        return f"`{text}`"


class DocxExporter:
    """Markdown → .docx converter"""
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize with optional template
        
        Args:
            template_path: Path to .docx template file
        """
        self.template_path = template_path
    
    def export(
        self,
        artifacts: List[Artifact],
        project_name: str,
        metadata: Optional[dict] = None,
    ) -> bytes:
        """
        Export artifacts to .docx
        
        Args:
            artifacts: List of artifacts to include
            project_name: Project name for document
            metadata: Additional metadata
        
        Returns:
            .docx file as bytes
        """
        
        # Create document
        if self.template_path:
            doc = Document(self.template_path)
        else:
            doc = Document()
            self._setup_default_styles(doc)
        
        # Add title page
        self._add_title_page(doc, project_name, metadata)
        
        # Add each artifact
        for artifact in artifacts:
            self._add_artifact(doc, artifact)
        
        # Add footer with page numbers and date
        self._add_footer(doc)
        
        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def _setup_default_styles(self, doc: Document):
        """Setup default styles for document"""
        
        styles = doc.styles
        
        # Title style
        try:
            title_style = styles['Title']
        except KeyError:
            title_style = styles.add_style('Title', WD_STYLE_TYPE.PARAGRAPH)
        
        title_format = title_style.font
        title_format.name = 'Arial'
        title_format.size = Pt(24)
        title_format.bold = True
        
        # Heading styles
        for level in range(1, 5):
            try:
                heading_style = styles[f'Heading {level}']
            except KeyError:
                heading_style = styles.add_style(f'Heading {level}', WD_STYLE_TYPE.PARAGRAPH)
            
            heading_format = heading_style.font
            heading_format.name = 'Arial'
            heading_format.size = Pt(18 - level * 2)
            heading_format.bold = True
    
    def _add_title_page(self, doc: Document, project_name: str, metadata: Optional[dict]):
        """Add title page to document"""
        
        # Title
        title = doc.add_heading(project_name, 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Subtitle
        subtitle = doc.add_paragraph("專案規格文件")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle_format = subtitle.runs[0].font
        subtitle_format.size = Pt(16)
        subtitle_format.italic = True
        
        # Add some space
        doc.add_paragraph()
        doc.add_paragraph()
        
        # Metadata table
        if metadata:
            table = doc.add_table(rows=0, cols=2)
            table.style = 'Table Grid'
            
            for key, value in metadata.items():
                row = table.add_row().cells
                row[0].text = key
                row[1].text = str(value)
        
        # Date
        date_para = doc.add_paragraph(f"產出日期：{datetime.now().strftime('%Y-%m-%d')}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Page break
        doc.add_page_break()
    
    def _add_artifact(self, doc: Document, artifact: Artifact):
        """Add artifact content to document"""
        
        # Parse markdown
        elements = self._parse_markdown(artifact.content_md)
        
        # Add artifact header
        doc.add_heading(f"{artifact.agent_role.title()} - {artifact.artifact_type.replace('_', ' ').title()}", 1)
        
        if artifact.extra_metadata:
            version_info = doc.add_paragraph(f"版本：v{artifact.version}")
            version_info.italic = True
        
        # Render elements
        for element in elements:
            self._render_element(doc, element)
        
        # Add separation
        doc.add_paragraph()
    
    def _parse_markdown(self, markdown: str) -> List[DocElement]:
        """Parse markdown into document elements"""
        
        renderer = MarkdownRenderer()
        markdown_parser = mistune.create_markdown(renderer=renderer)
        
        # Parse markdown
        markdown_parser(markdown)
        
        return renderer.elements
    
    def _render_element(self, doc: Document, element: DocElement):
        """Render a document element to docx"""
        
        if element.type == "heading":
            heading = doc.add_heading(element.content, element.level)
            
        elif element.type == "paragraph":
            para = doc.add_paragraph()
            self._add_formatted_text(para, element.content)
            
        elif element.type == "list":
            for item in element.items or []:
                para = doc.add_paragraph()
                para.style = 'List Bullet'
                self._add_formatted_text(para, item)
                
        elif element.type == "table":
            if element.headers or element.rows:
                row_count = len(element.rows or [])
                if element.headers:
                    row_count += 1
                
                col_count = len(element.headers or element.rows[0] if element.rows else [])
                
                if col_count > 0:
                    table = doc.add_table(rows=row_count, cols=col_count)
                    table.style = 'Table Grid'
                    
                    row_idx = 0
                    
                    # Add headers
                    if element.headers:
                        header_row = table.rows[row_idx]
                        for col_idx, header in enumerate(element.headers):
                            if col_idx < len(header_row.cells):
                                header_row.cells[col_idx].text = header
                                # Make header bold
                                for paragraph in header_row.cells[col_idx].paragraphs:
                                    for run in paragraph.runs:
                                        run.font.bold = True
                        row_idx += 1
                    
                    # Add data rows
                    for row_data in element.rows or []:
                        if row_idx < len(table.rows):
                            table_row = table.rows[row_idx]
                            for col_idx, cell_data in enumerate(row_data):
                                if col_idx < len(table_row.cells):
                                    table_row.cells[col_idx].text = str(cell_data)
                            row_idx += 1
                            
        elif element.type == "code":
            para = doc.add_paragraph(element.content)
            para.style = 'Normal'  # Could create a specific code style
            # Make monospace
            for run in para.runs:
                run.font.name = 'Courier New'
                run.font.size = Pt(10)
    
    def _add_formatted_text(self, paragraph, text: str):
        """Add text with basic formatting to paragraph"""
        
        # Simple regex-based formatting
        parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)
        
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # Bold
                run = paragraph.add_run(part[2:-2])
                run.font.bold = True
            elif part.startswith('*') and part.endswith('*') and not part.startswith('**'):
                # Italic
                run = paragraph.add_run(part[1:-1]) 
                run.font.italic = True
            elif part.startswith('`') and part.endswith('`'):
                # Code
                run = paragraph.add_run(part[1:-1])
                run.font.name = 'Courier New'
            else:
                # Normal text
                paragraph.add_run(part)
    
    def _add_footer(self, doc: Document):
        """Add footer with page numbers and date"""
        
        section = doc.sections[0]
        footer = section.footer
        
        # Add page number and date
        footer_para = footer.paragraphs[0]
        footer_para.text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER


# Global instance
docx_exporter = DocxExporter()