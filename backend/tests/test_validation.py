from app.services.validation_service import validate_invoice_record
from app.models import ReviewStatus, IssueSeverity
from app.database import SessionLocal

def test_validation_clean_invoice():
    db = SessionLocal()
    try:
        inv_data = {
            "vendor_name": "Infospectrum Tech",
            "invoice_number": "INV-1001",
            "invoice_date": "2026-09-20",
            "due_date": "2026-10-20",
            "subtotal": 1000.0,
            "tax_amount": 180.0,
            "shipping_amount": 0.0,
            "discount_amount": 0.0,
            "total_amount": 1180.0
        }
        lines = [
            {"description": "Item 1", "quantity": 2.0, "unit_price": 500.0, "line_total": 1000.0}
        ]
        status, issues, is_high, is_dup = validate_invoice_record(inv_data, lines, user_id=1, db=db, alert_threshold=50000.0)
        assert status == ReviewStatus.APPROVED
        assert len(issues) == 0
        assert is_high is False
    finally:
        db.close()

def test_validation_math_mismatch():
    db = SessionLocal()
    try:
        inv_data = {
            "vendor_name": "Apex Office",
            "invoice_number": "INV-3390",
            "invoice_date": "2026-09-20",
            "due_date": "2026-10-20",
            "subtotal": 1000.0,
            "tax_amount": 180.0,
            "shipping_amount": 0.0,
            "discount_amount": 0.0,
            "total_amount": 1500.0 # Intentionally wrong total (1000+180=1180 != 1500)
        }
        lines = [
            # Line math error (2 x 500 = 1000, but says 800)
            {"description": "Item 1", "quantity": 2.0, "unit_price": 500.0, "line_total": 800.0}
        ]
        status, issues, is_high, is_dup = validate_invoice_record(inv_data, lines, user_id=1, db=db, alert_threshold=50000.0)
        assert status == ReviewStatus.FLAGGED
        assert any(i["issue_code"] == "TOTAL_AMOUNT_MISMATCH" for i in issues)
        assert any(i["issue_code"] == "LINE_ITEM_MATH_MISMATCH" for i in issues)
    finally:
        db.close()
