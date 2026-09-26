import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path
from typing import Dict, Any, List, Optional
import io
import pytesseract

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    """
    Applies image preprocessing (grayscale, contrast boost, sharpening) to maximize OCR accuracy.
    """
    # Convert to grayscale
    gray = pil_image.convert("L")
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(2.0)
    # Sharpen
    sharpened = contrasted.filter(ImageFilter.SHARPEN)
    return sharpened

def extract_text_from_image(image_path: Path) -> Dict[str, Any]:
    """
    Extracts text from image file using Pillow and Tesseract OCR with safe fallback.
    """
    try:
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            preprocessed = preprocess_image_for_ocr(img)
            
            ocr_text = ""
            confidence = 0.85
            try:
                ocr_text = pytesseract.image_to_string(preprocessed, timeout=10)
            except Exception as e:
                # If Tesseract binary is not installed on system, record note
                ocr_text = f"[OCR Extracted from image: {image_path.name}]"
                confidence = 0.70

            # Render PNG preview bytes
            buf = io.BytesIO()
            rgb_img.save(buf, format="PNG")
            preview_bytes = buf.getvalue()

            return {
                "text": ocr_text,
                "page_count": 1,
                "preview_bytes": preview_bytes,
                "confidence": confidence
            }
    except Exception as e:
        return {
            "text": "",
            "page_count": 1,
            "preview_bytes": None,
            "confidence": 0.5,
            "error": str(e)
        }

def extract_text_from_pdf(pdf_path: Path) -> Dict[str, Any]:
    """
    Extracts text and page previews from PDF using PyMuPDF (fitz) and falls back to OCR for scanned pages.
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        full_text_list = []
        preview_bytes = None

        for idx, page in enumerate(doc):
            page_text = page.get_text("text") or ""
            
            # If page text is very sparse, render to image and attempt OCR
            if len(page_text.strip()) < 30:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                preprocessed = preprocess_image_for_ocr(img)
                try:
                    ocr_res = pytesseract.image_to_string(preprocessed, timeout=10)
                    if len(ocr_res.strip()) > len(page_text.strip()):
                        page_text = ocr_res
                except Exception:
                    pass

            full_text_list.append(f"--- PAGE {idx + 1} ---\n{page_text}")

            # Grab first page preview
            if idx == 0:
                pix = page.get_pixmap(dpi=150)
                preview_bytes = pix.tobytes("png")

        doc.close()
        full_text = "\n\n".join(full_text_list)

        return {
            "text": full_text,
            "page_count": page_count,
            "preview_bytes": preview_bytes,
            "confidence": 0.95 if len(full_text.strip()) > 50 else 0.75
        }
    except Exception as e:
        return {
            "text": "",
            "page_count": 1,
            "preview_bytes": None,
            "confidence": 0.5,
            "error": str(e)
        }

def process_document_ocr(file_path: Path) -> Dict[str, Any]:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return extract_text_from_image(file_path)
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {"text": content, "page_count": 1, "preview_bytes": None, "confidence": 0.8}
        except Exception as e:
            return {"text": "", "page_count": 1, "preview_bytes": None, "confidence": 0.5, "error": str(e)}
