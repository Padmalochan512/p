import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Document, Invoice, InvoiceLineItem, ValidationIssue, ProcessingStatus, ProcessingLog
from app.schemas import DocumentResponse
from app.utils.security import get_current_user
from app.utils.file_validation import validate_uploaded_file, generate_unique_filename
from app.config import settings
from app.services.ocr_service import process_document_ocr
from app.services.extraction_service import extract_invoice_data
from app.services.validation_service import validate_invoice_record
from app.services.notification_service import create_system_notification

router = APIRouter(prefix="/documents", tags=["Documents"])

def execute_document_pipeline(document: Document, user: User, db: Session) -> Invoice:
    document.processing_status = ProcessingStatus.PROCESSING
    db.commit()

    file_path = Path(document.file_path)
    if not file_path.exists():
        document.processing_status = ProcessingStatus.FAILED
        document.error_message = "File not found on storage."
        db.commit()
        raise HTTPException(status_code=400, detail="Physical document file missing.")

    # 1. OCR Stage
    ocr_result = process_document_ocr(file_path)
    document.raw_ocr_text = ocr_result.get("text", "")
    document.page_count = ocr_result.get("page_count", 1)

    # 2. AI / Heuristic Extraction Stage
    extracted = extract_invoice_data(
        raw_text=document.raw_ocr_text,
        preview_bytes=ocr_result.get("preview_bytes"),
        default_currency=user.default_currency or settings.DEFAULT_CURRENCY
    )

    # 3. Financial Validation Stage
    line_items_data = extracted.get("line_items", [])
    review_status, issues, is_high_val, is_dup = validate_invoice_record(
        invoice_data=extracted,
        line_items=line_items_data,
        user_id=user.id,
        db=db,
        alert_threshold=user.alert_threshold
    )

    # 4. Save Invoice Record
    inv_id = f"inv_{uuid.uuid4().hex[:10]}"
    invoice = Invoice(
        id=inv_id,
        document_id=document.id,
        user_id=user.id,
        vendor_name=extracted.get("vendor_name", "Unknown Vendor"),
        vendor_address=extracted.get("vendor_address"),
        vendor_tax_id=extracted.get("vendor_tax_id"),
        vendor_email=extracted.get("vendor_email"),
        vendor_phone=extracted.get("vendor_phone"),
        customer_name=extracted.get("customer_name"),
        customer_address=extracted.get("customer_address"),
        invoice_number=extracted.get("invoice_number", "INV-UNKNOWN"),
        po_number=extracted.get("po_number"),
        invoice_date=extracted.get("invoice_date"),
        due_date=extracted.get("due_date"),
        payment_terms=extracted.get("payment_terms"),
        currency=extracted.get("currency", user.default_currency or "INR"),
        subtotal=extracted.get("subtotal", 0.0),
        tax_amount=extracted.get("tax_amount", 0.0),
        tax_rate=extracted.get("tax_rate"),
        shipping_amount=extracted.get("shipping_amount", 0.0),
        discount_amount=extracted.get("discount_amount", 0.0),
        total_amount=extracted.get("total_amount", 0.0),
        review_status=review_status,
        is_high_value=is_high_val,
        is_duplicate=is_dup,
        confidence_score=extracted.get("confidence_score", 0.95),
        extraction_method=extracted.get("extraction_method", "Rule-based OCR"),
        raw_json=str(extracted)
    )
    db.add(invoice)
    db.flush()

    # Save Line Items
    for idx, item in enumerate(line_items_data):
        li = InvoiceLineItem(
            invoice_id=invoice.id,
            item_number=idx + 1,
            description=item.get("description", "Item"),
            quantity=float(item.get("quantity", 1.0) or 1.0),
            unit_price=float(item.get("unit_price", 0.0) or 0.0),
            tax_rate=float(item.get("tax_rate", 0.0) or 0.0),
            line_total=float(item.get("line_total", 0.0) or 0.0),
            calculated_total=round(float(item.get("quantity", 1.0) or 1.0) * float(item.get("unit_price", 0.0) or 0.0), 2),
            is_math_match=item.get("is_math_match", True)
        )
        db.add(li)

    # Save Validation Issues
    for iss in issues:
        vi = ValidationIssue(
            invoice_id=invoice.id,
            issue_code=iss["issue_code"],
            field_name=iss.get("field_name"),
            expected_value=iss.get("expected_value"),
            actual_value=iss.get("actual_value"),
            message=iss["message"],
            severity=iss["severity"]
        )
        db.add(vi)

    # Trigger Notifications if Issues or High Value
    if is_high_val:
        create_system_notification(
            db=db,
            user_id=user.id,
            invoice_id=invoice.id,
            title=f"High-Value Invoice Alert (#{invoice.invoice_number})",
            message=f"Invoice total of {invoice.currency} {invoice.total_amount:,.2f} from '{invoice.vendor_name}' requires approval.",
            notification_type="HIGH_VALUE",
            severity="WARNING"
        )
    if is_dup:
        create_system_notification(
            db=db,
            user_id=user.id,
            invoice_id=invoice.id,
            title=f"Duplicate Invoice Detected (#{invoice.invoice_number})",
            message=f"Duplicate invoice number '{invoice.invoice_number}' detected for vendor '{invoice.vendor_name}'.",
            notification_type="DUPLICATE",
            severity="CRITICAL"
        )
    if issues and not is_high_val and not is_dup:
        create_system_notification(
            db=db,
            user_id=user.id,
            invoice_id=invoice.id,
            title=f"Validation Discrepancy (#{invoice.invoice_number})",
            message=f"{len(issues)} validation issue(s) detected during document extraction.",
            notification_type="VALIDATION_ERROR",
            severity="WARNING"
        )

    document.processing_status = ProcessingStatus.COMPLETED
    db.commit()
    db.refresh(document)
    db.refresh(invoice)
    return invoice

@router.post("/upload", response_model=List[DocumentResponse])
async def upload_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    created_docs = []
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    for file in files:
        validate_uploaded_file(file)
        
        contents = await file.read()
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
            )

        unique_name = generate_unique_filename(file.filename)
        dest_path = settings.UPLOAD_DIR / unique_name

        with open(dest_path, "wb") as f:
            f.write(contents)

        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        ext = dest_path.suffix.lower().replace(".", "").upper()

        doc = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=unique_name,
            original_filename=file.filename,
            file_path=str(dest_path),
            file_type=ext,
            file_size_bytes=len(contents),
            mime_type=file.content_type or "application/octet-stream",
            processing_status=ProcessingStatus.PENDING
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Process pipeline immediately
        try:
            execute_document_pipeline(doc, current_user, db)
        except Exception as e:
            doc.processing_status = ProcessingStatus.FAILED
            doc.error_message = str(e)
            db.commit()

        created_docs.append(doc)

    return created_docs

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).order_by(Document.created_at.desc()).all()
    return docs

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc

@router.get("/{document_id}/preview")
def get_document_preview(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical document file missing on disk.")

    ocr_res = process_document_ocr(file_path)
    preview_bytes = ocr_res.get("preview_bytes")
    if preview_bytes:
        return Response(content=preview_bytes, media_type="image/png")

    if doc.file_type.lower() in ["png", "jpg", "jpeg", "webp"]:
        return FileResponse(file_path)

    raise HTTPException(status_code=400, detail="Preview unavailable for this document.")

@router.get("/{document_id}/file")
def get_raw_document_file(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk.")

    media_type = "application/pdf" if doc.file_type.lower() == "pdf" else "image/png"
    return FileResponse(file_path, media_type=media_type, filename=doc.original_filename)

@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        f_path = Path(doc.file_path)
        if f_path.exists():
            f_path.unlink()
    except Exception:
        pass

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully."}
