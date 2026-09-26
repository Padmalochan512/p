from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings
from app.models import ExtractedInvoiceData
from app.extractor.pdf_parser import extract_pdf_content, render_pdf_page_image
from app.extractor.image_parser import process_image_file
from app.extractor.heuristic_engine import parse_with_heuristics
from app.extractor.llm_vision_engine import (
    extract_with_gemini,
    extract_with_openai,
    extract_with_ollama
)

def orchestrate_extraction(file_path: Path, forced_provider: Optional[str] = None) -> ExtractedInvoiceData:
    """
    Unified extraction pipeline for PDFs and images with multi-tier fallbacks.
    """
    provider = forced_provider or settings.llm_provider
    extension = file_path.suffix.lower()
    
    raw_text = ""
    tables = []
    image_bytes = None
    
    # 1. Parse File Content based on type
    if extension == ".pdf":
        pdf_info = extract_pdf_content(file_path)
        raw_text = pdf_info["text"]
        tables = pdf_info["tables"]
        image_bytes = render_pdf_page_image(file_path, page_index=0)
    elif extension in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        img_info = process_image_file(file_path)
        image_bytes = img_info["bytes"]
        raw_text = ""  # If no OCR installed, vision LLM handles image directly
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception:
            raw_text = ""

    extracted_data: Optional[ExtractedInvoiceData] = None

    # 2. Attempt LLM Vision extraction if requested
    if provider == "gemini":
        extracted_data = extract_with_gemini(raw_text, image_bytes)
    elif provider == "openai":
        extracted_data = extract_with_openai(raw_text, image_bytes)
    elif provider == "ollama":
        extracted_data = extract_with_ollama(raw_text, image_bytes)

    # 3. Fallback to Heuristic Engine if LLM returns None or provider is 'heuristic'
    if extracted_data is None:
        extracted_data = parse_with_heuristics(raw_text, tables)

    return extracted_data
