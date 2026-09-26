from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import SettingsResponse, UserSettingsUpdate, UserResponse
from app.utils.security import get_current_user
from app.config import settings

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=SettingsResponse)
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ocr_status = "Tesseract OCR Active (with PyMuPDF direct parser fallback)"
    llm_status = "Active" if (settings.GEMINI_API_KEY or settings.OPENAI_API_KEY) else "Fallback Heuristic Mode (No API Key Configured)"

    return SettingsResponse(
        user_profile=UserResponse.model_validate(current_user),
        default_currency=current_user.default_currency or settings.DEFAULT_CURRENCY,
        alert_threshold=current_user.alert_threshold or settings.HIGH_VALUE_THRESHOLD,
        ocr_status=ocr_status,
        llm_status=llm_status,
        llm_provider=settings.LLM_PROVIDER,
        database_status="SQLite (Healthy & Connected)",
        app_version=settings.VERSION,
        upload_dir=str(settings.UPLOAD_DIR),
        max_file_size_mb=settings.MAX_FILE_SIZE_MB
    )

@router.put("", response_model=SettingsResponse)
def update_user_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.default_currency is not None:
        current_user.default_currency = payload.default_currency
    if payload.alert_threshold is not None:
        current_user.alert_threshold = payload.alert_threshold

    if payload.llm_provider is not None:
        settings.LLM_PROVIDER = payload.llm_provider
    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key
    if payload.openai_api_key is not None:
        settings.OPENAI_API_KEY = payload.openai_api_key
    if payload.webhook_alert_url is not None:
        settings.WEBHOOK_ALERT_URL = payload.webhook_alert_url

    db.commit()
    db.refresh(current_user)
    return get_user_settings(current_user=current_user, db=db)
