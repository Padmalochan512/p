import uuid
import re
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp"
}

def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^\w\s\.-]", "", filename).strip()
    return cleaned or "document.pdf"

def validate_uploaded_file(file: UploadFile) -> None:
    # 1. Extension check
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: PDF, PNG, JPG, JPEG, WEBP."
        )

def generate_unique_filename(original_filename: str) -> str:
    sanitized = sanitize_filename(original_filename)
    ext = Path(sanitized).suffix.lower()
    stem = Path(sanitized).stem[:30]
    unique_id = uuid.uuid4().hex[:10]
    return f"{stem}_{unique_id}{ext}"
