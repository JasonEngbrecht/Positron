"""
Generate PDF version of DISTRIBUTION_README.md for inclusion in the distribution.

This script creates a professionally formatted PDF user manual from the markdown README.
Run this before building with PyInstaller to ensure the latest README is included.

Usage:
    python generate_readme_pdf.py
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.platypus import Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import re


def markdown_to_pdf(md_file, pdf_file):
    """Convert markdown README to PDF with basic formatting."""
    
    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2a6ab0'),
        spaceAfter=10,
        spaceBefore=16,
        fontName='Helvetica-Bold'
    )
    
    h3_style = ParagraphStyle(
        'CustomH3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#3a7ac0'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )
    
    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontSize=9,
        leftIndent=20,
        fontName='Courier',
        textColor=colors.HexColor('#333333'),
        backColor=colors.HexColor('#f5f5f5'),
        spaceAfter=6
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['BodyText'],
        fontSize=10,
        leftIndent=20,
        bulletIndent=10,
        spaceAfter=4
    )
    
    # Process the markdown content
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Main title (first # line)
        if line.startswith('# ') and i < 5:  # Only first few lines
            title_text = line[2:].strip()
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.2*inch))
            i += 1
            continue
        
        # H3 headers (###)
        if line.startswith('### '):
            header_text = line[4:].strip()
            elements.append(Paragraph(header_text, h3_style))
            i += 1
            continue
        
        # H2 headers (##)
        if line.startswith('## '):
            header_text = line[3:].strip()
            elements.append(Paragraph(header_text, h2_style))
            i += 1
            continue
        
        # H1 headers (#)
        if line.startswith('# '):
            header_text = line[2:].strip()
            elements.append(Paragraph(header_text, h1_style))
            i += 1
            continue
        
        # Horizontal rules
        if line.startswith('---'):
            elements.append(Spacer(1, 0.2*inch))
            i += 1
            continue
        
        # Bold text markers
        if line.startswith('**') and line.endswith('**'):
            text = line[2:-2]
            elements.append(Paragraph(f'<b>{text}</b>', body_style))
            i += 1
            continue
        
        # Bullet points
        if line.startswith('- ') or line.startswith('* '):
            bullet_text = line[2:].strip()
            # Clean up markdown formatting
            bullet_text = bullet_text.replace('**', '<b>').replace('**', '</b>')
            bullet_text = bullet_text.replace('`', '<font name="Courier">')
            bullet_text = bullet_text.replace('`', '</font>')
            elements.append(Paragraph(f'• {bullet_text}', bullet_style))
            i += 1
            continue
        
        # Numbered lists
        if re.match(r'^\d+\.\s', line):
            list_text = re.sub(r'^\d+\.\s', '', line)
            list_text = list_text.replace('**', '<b>').replace('**', '</b>')
            elements.append(Paragraph(f'{line[:3]} {list_text}', bullet_style))
            i += 1
            continue
        
        # Code blocks (```)
        if line.startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if code_lines:
                code_text = '\n'.join(code_lines)
                # Escape special characters
                code_text = code_text.replace('<', '&lt;').replace('>', '&gt;')
                elements.append(Paragraph(f'<font name="Courier">{code_text}</font>', code_style))
            i += 1
            continue
        
        # Regular paragraphs
        if line:
            # Clean up markdown formatting
            text = line.replace('**', '<b>').replace('**', '</b>')
            text = text.replace('`', '<font name="Courier">')
            text = text.replace('`', '</font>')
            # Convert markdown links to text
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            elements.append(Paragraph(text, body_style))
        
        i += 1
    
    # Build PDF
    doc.build(elements)
    print(f"PDF generated successfully: {pdf_file}")


if __name__ == '__main__':
    markdown_to_pdf('DISTRIBUTION_README.md', 'Positron_User_Manual.pdf')
