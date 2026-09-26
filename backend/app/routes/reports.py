import io
import csv
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Invoice, InvoiceLineItem, ReviewStatus
from app.utils.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/summary")
def get_reports_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)

    invoices = query.all()
    total_spend = sum(i.total_amount for i in invoices)
    total_tax = sum(i.tax_amount for i in invoices)
    total_count = len(invoices)

    # Monthly breakdown
    monthly_dict = {}
    for inv in invoices:
        m_str = inv.invoice_date[:7] if inv.invoice_date and len(inv.invoice_date) >= 7 else "Unspecified"
        if m_str not in monthly_dict:
            monthly_dict[m_str] = {"count": 0, "amount": 0.0, "tax": 0.0}
        monthly_dict[m_str]["count"] += 1
        monthly_dict[m_str]["amount"] += inv.total_amount
        monthly_dict[m_str]["tax"] += inv.tax_amount

    monthly = [
        {"month": k, "count": v["count"], "total_amount": round(v["amount"], 2), "tax_amount": round(v["tax"], 2)}
        for k, v in sorted(monthly_dict.items())
    ]

    # Vendor breakdown
    vendor_dict = {}
    for inv in invoices:
        v_name = inv.vendor_name or "Unknown"
        if v_name not in vendor_dict:
            vendor_dict[v_name] = {"count": 0, "amount": 0.0}
        vendor_dict[v_name]["count"] += 1
        vendor_dict[v_name]["amount"] += inv.total_amount

    vendor_summary = [
        {"vendor": k, "count": v["count"], "total_amount": round(v["amount"], 2)}
        for k, v in sorted(vendor_dict.items(), key=lambda x: x[1]["amount"], reverse=True)
    ]

    return {
        "total_invoices": total_count,
        "total_spend": round(total_spend, 2),
        "total_tax": round(total_tax, 2),
        "currency": current_user.default_currency or "INR",
        "monthly_breakdown": monthly,
        "vendor_breakdown": vendor_summary
    }

@router.get("/export")
def export_invoices_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)
    if status and status != "ALL":
        query = query.filter(Invoice.review_status == status)

    invoices = query.order_by(Invoice.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice ID", "Invoice Number", "Vendor Name", "Vendor Tax/GST",
        "Customer Name", "Invoice Date", "Due Date", "Currency",
        "Subtotal", "Tax Amount", "Shipping", "Discount", "Total Amount",
        "Review Status", "High Value", "Duplicate", "Confidence (%)",
        "Extraction Method", "Reviewer Notes", "Created At"
    ])

    for r in invoices:
        writer.writerow([
            r.id, r.invoice_number, r.vendor_name, r.vendor_tax_id or "",
            r.customer_name or "", r.invoice_date or "", r.due_date or "", r.currency,
            f"{r.subtotal:.2f}", f"{r.tax_amount:.2f}", f"{r.shipping_amount:.2f}",
            f"{r.discount_amount:.2f}", f"{r.total_amount:.2f}",
            r.review_status.value if hasattr(r.review_status, "value") else str(r.review_status),
            "Yes" if r.is_high_value else "No", "Yes" if r.is_duplicate else "No",
            round((r.confidence_score or 1.0) * 100, 1), r.extraction_method,
            r.reviewer_notes or "", r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
        ])

    csv_data = output.getvalue()
    filename = f"invoices_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/line-items-export")
def export_line_items_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = (
        db.query(InvoiceLineItem, Invoice)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .filter(Invoice.user_id == current_user.id)
        .order_by(Invoice.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice ID", "Invoice Number", "Vendor Name", "Item #",
        "Description", "Quantity", "Unit Price", "Tax Rate (%)",
        "Line Total", "Math Match"
    ])

    for li, inv in items:
        writer.writerow([
            inv.id, inv.invoice_number, inv.vendor_name, li.item_number,
            li.description, li.quantity, f"{li.unit_price:.2f}",
            f"{li.tax_rate:.2f}", f"{li.line_total:.2f}",
            "Yes" if li.is_math_match else "Mismatch"
        ])

    csv_data = output.getvalue()
    filename = f"line_items_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
