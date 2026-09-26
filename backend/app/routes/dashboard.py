from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, Invoice, ReviewStatus
from app.schemas import DashboardSummaryResponse, DashboardActivityResponse, ActivityItem, StatusDistributionItem, VendorSpendItem
from app.utils.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).all()
    total_count = len(invoices)
    
    validated = sum(1 for i in invoices if i.review_status == ReviewStatus.APPROVED)
    needs_review = sum(1 for i in invoices if i.review_status == ReviewStatus.NEEDS_REVIEW)
    flagged = sum(1 for i in invoices if i.review_status == ReviewStatus.FLAGGED)
    total_spend = sum(i.total_amount for i in invoices)
    
    avg_conf = (sum(i.confidence_score for i in invoices) / total_count * 100) if total_count > 0 else 0.0
    high_val = sum(1 for i in invoices if i.is_high_value)
    dups = sum(1 for i in invoices if i.is_duplicate)

    return DashboardSummaryResponse(
        total_invoices=total_count,
        validated_invoices=validated,
        needs_review_invoices=needs_review,
        flagged_invoices=flagged,
        total_spend=round(total_spend, 2),
        currency=current_user.default_currency or "INR",
        avg_confidence=round(avg_conf, 1),
        high_value_count=high_val,
        duplicate_count=dups
    )

@router.get("/activity", response_model=DashboardActivityResponse)
def get_dashboard_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id).order_by(Invoice.created_at.asc()).all()
    
    # 1. Timeline by date
    timeline_dict = {}
    for inv in invoices:
        d_str = inv.created_at.strftime("%Y-%m-%d") if inv.created_at else "Unknown"
        if d_str not in timeline_dict:
            timeline_dict[d_str] = {"count": 0, "amount": 0.0}
        timeline_dict[d_str]["count"] += 1
        timeline_dict[d_str]["amount"] += inv.total_amount

    timeline = [
        ActivityItem(date=k, processed_count=v["count"], total_amount=round(v["amount"], 2))
        for k, v in timeline_dict.items()
    ]

    # 2. Status distribution
    status_counts = {
        "Approved": sum(1 for i in invoices if i.review_status == ReviewStatus.APPROVED),
        "Needs Review": sum(1 for i in invoices if i.review_status == ReviewStatus.NEEDS_REVIEW),
        "Flagged": sum(1 for i in invoices if i.review_status == ReviewStatus.FLAGGED),
        "Rejected": sum(1 for i in invoices if i.review_status == ReviewStatus.REJECTED),
    }
    colors_map = {
        "Approved": "#10b981",
        "Needs Review": "#f59e0b",
        "Flagged": "#ef4444",
        "Rejected": "#64748b"
    }
    status_distribution = [
        StatusDistributionItem(name=k, value=v, color=colors_map[k])
        for k, v in status_counts.items() if v > 0
    ]

    # 3. Top vendors by spend
    vendor_spends = (
        db.query(
            Invoice.vendor_name,
            func.count(Invoice.id).label("inv_count"),
            func.sum(Invoice.total_amount).label("tot_spend")
        )
        .filter(Invoice.user_id == current_user.id)
        .group_by(Invoice.vendor_name)
        .order_by(func.sum(Invoice.total_amount).desc())
        .limit(6)
        .all()
    )
    top_vendors = [
        VendorSpendItem(
            vendor=r[0] or "Unknown",
            count=r[1],
            total_spend=round(float(r[2] or 0.0), 2)
        )
        for r in vendor_spends
    ]

    return DashboardActivityResponse(
        timeline=timeline,
        status_distribution=status_distribution,
        top_vendors=top_vendors
    )
