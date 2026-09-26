import pdfplumber
import pypdfium2 as pdfium
from pathlib import Path
from typing import Dict, Any, List, Optional
import io
from PIL import Image

def extract_pdf_content(file_path: Path) -> Dict[str, Any]:
    """
    Extracts plain text, layout text, structured tables, and page metadata from a PDF file.
    """
    text_content = []
    tables_content = []
    page_count = 0
    
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            plain_text = page.extract_text() or ""
            layout_text = page.extract_text(layout=True) or ""
            
            # Combine plain text and layout text for maximum coverage
            text_content.append(f"--- PAGE {idx + 1} ---\n{plain_text}\n\n--- LAYOUT ---\n{layout_text}")
            
            # Extract structured tables if present
            extracted_tables = page.extract_tables()
            for table in extracted_tables:
                if table and len(table) > 1:
                    tables_content.append(table)
                    
    full_text = "\n\n".join(text_content)
    
    return {
        "text": full_text,
        "tables": tables_content,
        "page_count": page_count
    }

def render_pdf_page_image(file_path: Path, page_index: int = 0, scale: float = 2.0) -> Optional[bytes]:
    """
    Renders a PDF page to a PNG image byte stream for browser display or LLM Vision.
    """
    try:
        pdf = pdfium.PdfDocument(file_path)
        if page_index >= len(pdf):
            page_index = 0
        page = pdf[page_index]
        image = page.render(scale=scale).to_pil()
        
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"Error rendering PDF page: {e}")
        return None
