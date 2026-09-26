from typing import List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Invoice, ValidationIssue, ReviewStatus, IssueSeverity
from app.config import settings

def validate_invoice_record(
    invoice_data: Dict[str, Any],
    line_items: List[Dict[str, Any]],
    user_id: int,
    db: Session,
    exclude_invoice_id: str = None,
    alert_threshold: float = None
) -> Tuple[ReviewStatus, List[Dict[str, Any]], bool, bool]:
    """
    Executes financial, arithmetic, temporal, and completeness cross-checks.
    Returns: (review_status, issues_list, is_high_value, is_duplicate)
    """
    issues = []
    threshold = alert_threshold or settings.HIGH_VALUE_THRESHOLD

    # 1. Missing Vendor Name
    vendor_name = (invoice_data.get("vendor_name") or "").strip()
    if not vendor_name or vendor_name in ["Unknown Vendor", "N/A", ""]:
        issues.append({
            "issue_code": "MISSING_VENDOR_NAME",
            "field_name": "vendor_name",
            "expected_value": "Valid Business Name",
            "actual_value": vendor_name or "Empty",
            "message": "Vendor name is missing or unidentified.",
            "severity": IssueSeverity.CRITICAL
        })

    # 2. Missing Invoice Number
    invoice_number = (invoice_data.get("invoice_number") or "").strip()
    if not invoice_number or invoice_number in ["INV-UNKNOWN", "N/A", ""]:
        issues.append({
            "issue_code": "MISSING_INVOICE_NUMBER",
            "field_name": "invoice_number",
            "expected_value": "Unique Invoice Identifier",
            "actual_value": invoice_number or "Empty",
            "message": "Invoice number is missing.",
            "severity": IssueSeverity.WARNING
        })

    # 3. Invalid or Illogical Dates
    inv_date_str = invoice_data.get("invoice_date")
    due_date_str = invoice_data.get("due_date")
    inv_dt = None

    if not inv_date_str:
        issues.append({
            "issue_code": "MISSING_INVOICE_DATE",
            "field_name": "invoice_date",
            "expected_value": "YYYY-MM-DD",
            "actual_value": "None",
            "message": "Invoice issue date is missing.",
            "severity": IssueSeverity.WARNING
        })
    else:
        try:
            inv_dt = datetime.strptime(inv_date_str, "%Y-%m-%d")
        except ValueError:
            issues.append({
                "issue_code": "INVALID_DATE_FORMAT",
                "field_name": "invoice_date",
                "expected_value": "YYYY-MM-DD",
                "actual_value": str(inv_date_str),
                "message": f"Invoice date '{inv_date_str}' is not in standard ISO YYYY-MM-DD format.",
                "severity": IssueSeverity.WARNING
            })

    if due_date_str:
        try:
            due_dt = datetime.strptime(due_date_str, "%Y-%m-%d")
            if inv_dt and due_dt < inv_dt:
                issues.append({
                    "issue_code": "DUE_DATE_BEFORE_INVOICE_DATE",
                    "field_name": "due_date",
                    "expected_value": f">= {inv_date_str}",
                    "actual_value": str(due_date_str),
                    "message": f"Due date ({due_date_str}) precedes Invoice date ({inv_date_str}).",
                    "severity": IssueSeverity.WARNING
                })
        except ValueError:
            issues.append({
                "issue_code": "INVALID_DUE_DATE_FORMAT",
                "field_name": "due_date",
                "expected_value": "YYYY-MM-DD",
                "actual_value": str(due_date_str),
                "message": f"Due date '{due_date_str}' is not in standard ISO format.",
                "severity": IssueSeverity.WARNING
            })

    # 4. Line Items Math Cross-Check (Qty * Unit Price == Line Total)
    calculated_subtotal = 0.0
    for idx, item in enumerate(line_items):
        qty = float(item.get("quantity", 1.0) or 1.0)
        price = float(item.get("unit_price", 0.0) or 0.0)
        total = float(item.get("line_total", 0.0) or 0.0)
        expected_total = round(qty * price, 2)
        calculated_subtotal += total

        if abs(expected_total - total) > 0.05 and price > 0:
            item["is_math_match"] = False
            issues.append({
                "issue_code": "LINE_ITEM_MATH_MISMATCH",
                "field_name": f"line_items[{idx}]",
                "expected_value": f"{expected_total:.2f}",
                "actual_value": f"{total:.2f}",
                "message": f"Line {idx + 1} ('{item.get('description', 'Item')[:25]}'): {qty} × {price:.2f} = {expected_total:.2f}, but found {total:.2f}.",
                "severity": IssueSeverity.CRITICAL
            })
        else:
            item["is_math_match"] = True

    calculated_subtotal = round(calculated_subtotal, 2)

    # 5. Line Items Sum vs Subtotal Check
    subtotal = float(invoice_data.get("subtotal", 0.0) or 0.0)
    if subtotal > 0 and len(line_items) > 0:
        if abs(calculated_subtotal - subtotal) > 0.05:
            issues.append({
                "issue_code": "SUBTOTAL_MISMATCH",
                "field_name": "subtotal",
                "expected_value": f"{calculated_subtotal:.2f}",
                "actual_value": f"{subtotal:.2f}",
                "message": f"Sum of line items ({calculated_subtotal:.2f}) does not match invoice Subtotal ({subtotal:.2f}).",
                "severity": IssueSeverity.CRITICAL
            })

    # 6. Grand Total Equation (Subtotal + Tax + Shipping - Discount == Total)
    tax_amount = float(invoice_data.get("tax_amount", 0.0) or 0.0)
    shipping = float(invoice_data.get("shipping_amount", 0.0) or 0.0)
    discount = float(invoice_data.get("discount_amount", 0.0) or 0.0)
    total_amount = float(invoice_data.get("total_amount", 0.0) or 0.0)

    expected_grand_total = round(subtotal + tax_amount + shipping - discount, 2)

    if total_amount <= 0:
        issues.append({
            "issue_code": "ZERO_TOTAL_AMOUNT",
            "field_name": "total_amount",
            "expected_value": "> 0.00",
            "actual_value": f"{total_amount:.2f}",
            "message": "Grand total amount must be positive.",
            "severity": IssueSeverity.CRITICAL
        })
    elif abs(expected_grand_total - total_amount) > 0.05:
        issues.append({
            "issue_code": "TOTAL_AMOUNT_MISMATCH",
            "field_name": "total_amount",
            "expected_value": f"{expected_grand_total:.2f}",
            "actual_value": f"{total_amount:.2f}",
            "message": f"Total ({total_amount:.2f}) does not equal Subtotal ({subtotal:.2f}) + Tax ({tax_amount:.2f}) + Shipping ({shipping:.2f}) - Discount ({discount:.2f}) = {expected_grand_total:.2f}.",
            "severity": IssueSeverity.CRITICAL
        })

    # 7. High Value Threshold Check
    is_high_value = total_amount >= threshold
    if is_high_value:
        issues.append({
            "issue_code": "HIGH_VALUE_ALERT",
            "field_name": "total_amount",
            "expected_value": f"< {threshold:,.2f}",
            "actual_value": f"{total_amount:,.2f}",
            "message": f"High-value invoice: Total {total_amount:,.2f} exceeds configured policy limit of {threshold:,.2f}.",
            "severity": IssueSeverity.INFO
        })

    # 8. Duplicate Detection Check
    is_duplicate = False
    if vendor_name and invoice_number and invoice_number not in ["INV-UNKNOWN", "N/A", ""]:
        query = db.query(Invoice).filter(
            Invoice.user_id == user_id,
            Invoice.vendor_name.ilike(vendor_name.strip()),
            Invoice.invoice_number.ilike(invoice_number.strip())
        )
        if exclude_invoice_id:
            query = query.filter(Invoice.id != exclude_invoice_id)
        if query.first():
            is_duplicate = True
            issues.append({
                "issue_code": "DUPLICATE_INVOICE_NUMBER",
                "field_name": "invoice_number",
                "expected_value": "Unique Invoice Number",
                "actual_value": invoice_number,
                "message": f"Duplicate detected: An invoice with number '{invoice_number}' for vendor '{vendor_name}' already exists in your records.",
                "severity": IssueSeverity.CRITICAL
            })

    # 9. Determine Review Status
    has_critical = any(i["severity"] == IssueSeverity.CRITICAL for i in issues)
    has_warning = any(i["severity"] == IssueSeverity.WARNING for i in issues)

    if has_critical:
        review_status = ReviewStatus.FLAGGED
    elif has_warning or is_high_value:
        review_status = ReviewStatus.NEEDS_REVIEW
    else:
        review_status = ReviewStatus.APPROVED

    return review_status, issues, is_high_value, is_duplicate
