import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Response
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    settings,
    UPLOAD_DIR,
    INBOX_DIR,
    STATIC_DIR,
    EXPORTS_DIR
)
from app.database import (
    init_db,
    save_invoice,
    get_invoice_by_id,
    get_all_invoices,
    delete_invoice,
    get_dashboard_metrics,
    export_invoices_csv,
    export_line_items_csv
)
from app.models import (
    InvoiceRecord,
    ValidationStatus,
    ExtractedInvoiceData,
    InvoiceUpdateRequest,
    SettingsUpdateRequest,
    LineItem
)
from app.extractor.orchestrator import orchestrate_extraction
from app.extractor.pdf_parser import render_pdf_page_image
from app.validator import validate_invoice_data
from app.alerts import dispatch_webhook_alert
from app.watcher import watcher_service
from app.sample_generator import generate_all_preset_samples

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Watcher
    init_db()
    if settings.auto_watch_inbox:
        try:
            watcher_service.start()
        except Exception as e:
            print(f"Watcher startup notice: {e}")
    yield
    # Shutdown
    watcher_service.stop()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_file_into_record(file_path: Path, original_filename: str, forced_provider: Optional[str] = None) -> InvoiceRecord:
    doc_id = f"doc_{uuid.uuid4().hex[:10]}"
    ext = file_path.suffix.lower()
    
    # 1. Extract
    extracted_data = orchestrate_extraction(file_path, forced_provider=forced_provider)
    
    # 2. Validate
    status, issues, is_high_val, is_dup, alerts = validate_invoice_data(extracted_data, invoice_id=doc_id)
    
    now_iso = datetime.now().isoformat()
    record = InvoiceRecord(
        id=doc_id,
        filename=file_path.name,
        original_filename=original_filename,
        file_path=str(file_path),
        file_type=ext.replace(".", "").upper(),
        file_size_bytes=file_path.stat().st_size,
        created_at=now_iso,
        updated_at=now_iso,
        status=status,
        data=extracted_data,
        validation_issues=issues,
        is_high_value=is_high_val,
        is_duplicate=is_dup,
        alerts_triggered=alerts
    )
    
    save_invoice(record)
    if alerts:
        dispatch_webhook_alert(record.model_dump(), alerts)
        
    return record

# API Routes
@app.get("/api/stats")
def get_stats():
    return get_dashboard_metrics()

@app.get("/api/invoices", response_model=List[InvoiceRecord])
def list_invoices(status: Optional[str] = None, q: Optional[str] = None):
    return get_all_invoices(status_filter=status, search_query=q)

@app.get("/api/invoices/{invoice_id}", response_model=InvoiceRecord)
def get_invoice(invoice_id: str):
    record = get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return record

@app.post("/api/upload")
async def upload_invoices(
    files: List[UploadFile] = File(...),
    provider: Optional[str] = Form(None)
):
    processed = []
    for file in files:
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"]:
            continue
            
        file_id = f"doc_{uuid.uuid4().hex[:10]}"
        dest_filename = f"{file_id}_{file.filename}"
        dest_path = UPLOAD_DIR / dest_filename
        
        with open(dest_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        record = process_file_into_record(dest_path, file.filename, forced_provider=provider)
        processed.append(record)
        
    return {"message": f"Successfully processed {len(processed)} document(s)", "records": processed}

@app.post("/api/invoices/{invoice_id}/review")
def review_and_update_invoice(invoice_id: str, payload: InvoiceUpdateRequest):
    record = get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Update data fields
    if payload.vendor_name is not None:
        record.data.vendor_name = payload.vendor_name
    if payload.invoice_number is not None:
        record.data.invoice_number = payload.invoice_number
    if payload.invoice_date is not None:
        record.data.invoice_date = payload.invoice_date
    if payload.due_date is not None:
        record.data.due_date = payload.due_date
    if payload.po_number is not None:
        record.data.po_number = payload.po_number
    if payload.currency is not None:
        record.data.currency = payload.currency
    if payload.subtotal is not None:
        record.data.subtotal = payload.subtotal
    if payload.tax_amount is not None:
        record.data.tax_amount = payload.tax_amount
    if payload.shipping_amount is not None:
        record.data.shipping_amount = payload.shipping_amount
    if payload.discount_amount is not None:
        record.data.discount_amount = payload.discount_amount
    if payload.total_amount is not None:
        record.data.total_amount = payload.total_amount
    if payload.line_items is not None:
        record.data.line_items = payload.line_items
    if payload.reviewer_notes is not None:
        record.reviewer_notes = payload.reviewer_notes

    # Re-run validation cross-checks
    status, issues, is_high_val, is_dup, alerts = validate_invoice_data(record.data, invoice_id=record.id)
    
    # If reviewer explicitly forced status, respect it
    if payload.status:
        record.status = payload.status
    else:
        record.status = status
        
    record.validation_issues = issues
    record.is_high_value = is_high_val
    record.is_duplicate = is_dup
    record.alerts_triggered = alerts
    record.manual_reviewed = True
    record.updated_at = datetime.now().isoformat()
    
    save_invoice(record)
    return {"message": "Invoice successfully updated and re-validated", "record": record}

@app.post("/api/invoices/{invoice_id}/reprocess")
def reprocess_invoice(invoice_id: str, provider: Optional[str] = None):
    record = get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=400, detail="Original document file not found on disk")
        
    extracted_data = orchestrate_extraction(file_path, forced_provider=provider)
    status, issues, is_high_val, is_dup, alerts = validate_invoice_data(extracted_data, invoice_id=record.id)
    
    record.data = extracted_data
    record.status = status
    record.validation_issues = issues
    record.is_high_value = is_high_val
    record.is_duplicate = is_dup
    record.alerts_triggered = alerts
    record.updated_at = datetime.now().isoformat()
    
    save_invoice(record)
    return {"message": "Invoice reprocessed successfully", "record": record}

@app.delete("/api/invoices/{invoice_id}")
def remove_invoice(invoice_id: str):
    record = get_invoice_by_id(invoice_id)
    if not record:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Attempt removing physical file
    try:
        fpath = Path(record.file_path)
        if fpath.exists():
            fpath.unlink()
    except Exception:
        pass
        
    delete_invoice(invoice_id)
    return {"message": f"Invoice {invoice_id} deleted successfully"}

@app.post("/api/generate-samples")
def generate_samples():
    sample_dir = UPLOAD_DIR / "presets"
    generate_all_preset_samples(sample_dir)
    
    created_records = []
    for sample_file in sample_dir.glob("*.pdf"):
        # Copy to main upload dir
        dest_filename = f"sample_{uuid.uuid4().hex[:6]}_{sample_file.name}"
        dest_path = UPLOAD_DIR / dest_filename
        shutil.copy2(sample_file, dest_path)
        
        record = process_file_into_record(dest_path, sample_file.name)
        created_records.append(record)
        
    return {
        "message": f"Generated and processed {len(created_records)} realistic test invoices",
        "records": created_records
    }

@app.get("/api/files/{filename}")
def serve_file(filename: str, page: int = 0):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        # Check presets or inbox
        file_path = UPLOAD_DIR / "presets" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
    if file_path.suffix.lower() == ".pdf":
        return FileResponse(file_path, media_type="application/pdf")
    elif file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
        return FileResponse(file_path)
    return FileResponse(file_path)

@app.get("/api/render-preview/{filename}")
def render_preview(filename: str, page: int = 0):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        file_path = UPLOAD_DIR / "presets" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
    if file_path.suffix.lower() == ".pdf":
        img_bytes = render_pdf_page_image(file_path, page_index=page)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/png")
    elif file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
        return FileResponse(file_path)
        
    return HTTPException(status_code=400, detail="Cannot render preview for this file")

# Watcher and Automation endpoints
@app.get("/api/watcher/status")
def get_watcher_status():
    inbox_files = [f.name for f in INBOX_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
    return {
        "is_active": watcher_service.is_running,
        "watched_directory": str(INBOX_DIR),
        "queued_files_count": len(inbox_files),
        "queued_files": inbox_files
    }

@app.post("/api/watcher/start")
def start_watcher():
    watcher_service.start()
    return {"message": "Folder Watcher started", "is_active": watcher_service.is_running}

@app.post("/api/watcher/stop")
def stop_watcher():
    watcher_service.stop()
    return {"message": "Folder Watcher stopped", "is_active": watcher_service.is_running}

@app.post("/api/inbox/simulate-drop")
def simulate_inbox_email():
    """
    Simulates receiving an invoice via Email Attachment or SFTP drop into inbox_folder/
    """
    sample_dir = UPLOAD_DIR / "presets"
    generate_all_preset_samples(sample_dir)
    
    sample_files = list(sample_dir.glob("*.pdf"))
    if not sample_files:
        raise HTTPException(status_code=500, detail="No sample template available")
        
    import random
    picked = random.choice(sample_files)
    dest_name = f"email_drop_{uuid.uuid4().hex[:6]}_{picked.name}"
    dest_path = INBOX_DIR / dest_name
    shutil.copy2(picked, dest_path)
    
    return {
        "message": f"Simulated arrival of email invoice attachment: {dest_name}",
        "inbox_file": dest_name
    }

# Export Endpoints
@app.get("/api/export/csv")
def export_csv():
    csv_str = export_invoices_csv()
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invoices_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@app.get("/api/export/line-items-csv")
def export_lines_csv():
    csv_str = export_line_items_csv()
    return Response(
        content=csv_str,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=line_items_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@app.get("/api/export/json")
def export_json():
    invoices = get_all_invoices(limit=1000)
    data = [inv.model_dump() for inv in invoices]
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f"attachment; filename=invoices_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
    )

# Settings Endpoints
@app.get("/api/settings")
def get_settings():
    return settings.model_dump()

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    if req.high_value_threshold is not None:
        settings.high_value_threshold = req.high_value_threshold
    if req.duplicate_check_enabled is not None:
        settings.duplicate_check_enabled = req.duplicate_check_enabled
    if req.llm_provider is not None:
        settings.llm_provider = req.llm_provider
    if req.gemini_api_key is not None:
        settings.gemini_api_key = req.gemini_api_key
    if req.openai_api_key is not None:
        settings.openai_api_key = req.openai_api_key
    if req.ollama_endpoint is not None:
        settings.ollama_endpoint = req.ollama_endpoint
    if req.ollama_model is not None:
        settings.ollama_model = req.ollama_model
    if req.webhook_alert_url is not None:
        settings.webhook_alert_url = req.webhook_alert_url
        
    return {"message": "Settings updated successfully", "settings": settings.model_dump()}

# Mount Static Web App Files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
