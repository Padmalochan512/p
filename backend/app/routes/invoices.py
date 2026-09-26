import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.database import get_db
from app.models import User, Document, Invoice, InvoiceLineItem, ValidationIssue, ReviewStatus, ProcessingStatus
from app.schemas import InvoiceResponse, InvoiceListResponse, InvoiceUpdate
from app.utils.security import get_current_user
from app.services.validation_service import validate_invoice_record
from app.services.extraction_service import extract_invoice_data
from app.services.ocr_service import process_document_ocr
from app.services.notification_service import create_system_notification
from app.config import settings

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.post("/generate-samples", response_model=List[InvoiceResponse])
def generate_sample_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import sys
    root_dir = settings.BACKEND_DIR.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    
    from sample_documents.generate_samples import generate_samples, SAMPLE_DIR
    generate_samples()
    
    # Import execution helper
    from app.routes.documents import execute_document_pipeline

    created_invoices = []
    for sample_pdf in sorted(SAMPLE_DIR.glob("*.pdf")):
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        unique_name = f"{doc_id}_{sample_pdf.name}"
        dest_path = settings.UPLOAD_DIR / unique_name
        shutil.copy2(sample_pdf, dest_path)

        doc = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=unique_name,
            original_filename=sample_pdf.name,
            file_path=str(dest_path),
            file_type="PDF",
            file_size_bytes=dest_path.stat().st_size,
            mime_type="application/pdf",
            processing_status=ProcessingStatus.PENDING
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        inv = execute_document_pipeline(doc, current_user, db)
        created_invoices.append(inv)

    return [InvoiceResponse.model_validate(inv) for inv in created_invoices]


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    q: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)

    # Search filter
    if q:
        search_fmt = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Invoice.vendor_name.ilike(search_fmt),
                Invoice.invoice_number.ilike(search_fmt),
                Invoice.vendor_tax_id.ilike(search_fmt)
            )
        )

    # Status filter
    if status and status != "ALL":
        query = query.filter(Invoice.review_status == status)

    # Date range filter
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)

    # Total count
    total = query.count()

    # Sorting
    sort_col = getattr(Invoice, sort_by, Invoice.created_at)
    if order == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Pagination
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    total_pages = max(1, (total + limit - 1) // limit)

    return InvoiceListResponse(
        items=[InvoiceResponse.model_validate(inv) for inv in items],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return InvoiceResponse.model_validate(inv)

@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    # Update invoice fields
    for field, val in payload.model_dump(exclude_unset=True).items():
        if field not in ["line_items", "review_status"] and hasattr(inv, field):
            setattr(inv, field, val)

    # Update line items if provided
    if payload.line_items is not None:
        db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == inv.id).delete()
        for idx, item in enumerate(payload.line_items):
            li = InvoiceLineItem(
                invoice_id=inv.id,
                item_number=idx + 1,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate or 0.0,
                line_total=item.line_total,
                calculated_total=round(item.quantity * item.unit_price, 2),
                is_math_match=abs((item.quantity * item.unit_price) - item.line_total) < 0.05
            )
            db.add(li)

    # Re-run validation cross-checks
    items_dicts = [
        {
            "description": li.description,
            "quantity": li.quantity,
            "unit_price": li.unit_price,
            "line_total": li.line_total,
            "is_math_match": li.is_math_match
        } for li in inv.line_items
    ]
    auto_status, issues, is_high_val, is_dup = validate_invoice_record(
        invoice_data=inv.__dict__,
        line_items=items_dicts,
        user_id=current_user.id,
        db=db,
        exclude_invoice_id=inv.id,
        alert_threshold=current_user.alert_threshold
    )

    # Clear old validation issues and persist new
    db.query(ValidationIssue).filter(ValidationIssue.invoice_id == inv.id).delete()
    for iss in issues:
        vi = ValidationIssue(
            invoice_id=inv.id,
            issue_code=iss["issue_code"],
            field_name=iss.get("field_name"),
            expected_value=iss.get("expected_value"),
            actual_value=iss.get("actual_value"),
            message=iss["message"],
            severity=iss["severity"]
        )
        db.add(vi)

    inv.is_high_value = is_high_val
    inv.is_duplicate = is_dup

    if payload.review_status:
        inv.review_status = payload.review_status
    else:
        inv.review_status = auto_status

    inv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return InvoiceResponse.model_validate(inv)

@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
def approve_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    inv.review_status = ReviewStatus.APPROVED
    inv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return InvoiceResponse.model_validate(inv)

@router.post("/{invoice_id}/review", response_model=InvoiceResponse)
def mark_for_review(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    inv.review_status = ReviewStatus.NEEDS_REVIEW
    inv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return InvoiceResponse.model_validate(inv)

@router.post("/{invoice_id}/reprocess", response_model=InvoiceResponse)
def reprocess_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv or not inv.document:
        raise HTTPException(status_code=404, detail="Invoice or underlying document not found.")

    file_path = Path(inv.document.file_path)
    ocr_result = process_document_ocr(file_path)
    inv.document.raw_ocr_text = ocr_result.get("text", "")

    extracted = extract_invoice_data(
        raw_text=inv.document.raw_ocr_text,
        preview_bytes=ocr_result.get("preview_bytes"),
        default_currency=inv.currency or current_user.default_currency or "INR"
    )

    # Update extracted properties
    inv.vendor_name = extracted.get("vendor_name", inv.vendor_name)
    inv.invoice_number = extracted.get("invoice_number", inv.invoice_number)
    inv.invoice_date = extracted.get("invoice_date", inv.invoice_date)
    inv.due_date = extracted.get("due_date", inv.due_date)
    inv.subtotal = extracted.get("subtotal", inv.subtotal)
    inv.tax_amount = extracted.get("tax_amount", inv.tax_amount)
    inv.total_amount = extracted.get("total_amount", inv.total_amount)
    inv.confidence_score = extracted.get("confidence_score", inv.confidence_score)
    inv.extraction_method = extracted.get("extraction_method", inv.extraction_method)

    # Repopulate line items
    db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == inv.id).delete()
    for idx, item in enumerate(extracted.get("line_items", [])):
        li = InvoiceLineItem(
            invoice_id=inv.id,
            item_number=idx + 1,
            description=item.get("description", "Item"),
            quantity=float(item.get("quantity", 1.0) or 1.0),
            unit_price=float(item.get("unit_price", 0.0) or 0.0),
            tax_rate=float(item.get("tax_rate", 0.0) or 0.0),
            line_total=float(item.get("line_total", 0.0) or 0.0),
            calculated_total=round(float(item.get("quantity", 1.0) or 1.0) * float(item.get("unit_price", 0.0) or 0.0), 2),
            is_math_match=True
        )
        db.add(li)

    # Re-validate
    auto_status, issues, is_high_val, is_dup = validate_invoice_record(
        invoice_data=extracted,
        line_items=extracted.get("line_items", []),
        user_id=current_user.id,
        db=db,
        exclude_invoice_id=inv.id,
        alert_threshold=current_user.alert_threshold
    )

    db.query(ValidationIssue).filter(ValidationIssue.invoice_id == inv.id).delete()
    for iss in issues:
        vi = ValidationIssue(
            invoice_id=inv.id,
            issue_code=iss["issue_code"],
            field_name=iss.get("field_name"),
            expected_value=iss.get("expected_value"),
            actual_value=iss.get("actual_value"),
            message=iss["message"],
            severity=iss["severity"]
        )
        db.add(vi)

    inv.review_status = auto_status
    inv.is_high_value = is_high_val
    inv.is_duplicate = is_dup
    inv.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inv)
    return InvoiceResponse.model_validate(inv)

@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    # Delete underlying document
    if inv.document:
        try:
            f_path = Path(inv.document.file_path)
            if f_path.exists():
                f_path.unlink()
        except Exception:
            pass
        db.delete(inv.document)

    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted successfully."}
