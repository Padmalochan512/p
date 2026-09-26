from typing import List, Tuple, Optional
from datetime import datetime
from app.models import (
    ExtractedInvoiceData,
    ValidationIssue,
    ValidationStatus,
    Severity
)
from app.config import settings
from app.database import check_is_duplicate

def validate_invoice_data(
    data: ExtractedInvoiceData,
    invoice_id: Optional[str] = None
) -> Tuple[ValidationStatus, List[ValidationIssue], bool, bool, List[str]]:
    """
    Performs comprehensive financial and structural cross-check validations on extracted data.
    Returns: (status, issues_list, is_high_value, is_duplicate, alerts_list)
    """
    issues: List[ValidationIssue] = []
    alerts: List[str] = []
    
    # 1. Mandatory Fields Check
    if not data.vendor_name or data.vendor_name.strip() in ["Unknown Vendor", ""]:
        issues.append(ValidationIssue(
            code="MISSING_VENDOR",
            message="Vendor name is missing or unidentified.",
            severity=Severity.CRITICAL,
            field="vendor_name"
        ))
        
    if not data.invoice_number or data.invoice_number.strip() in ["INV-UNKNOWN", ""]:
        issues.append(ValidationIssue(
            code="MISSING_INVOICE_NUM",
            message="Invoice number could not be extracted.",
            severity=Severity.WARNING,
            field="invoice_number"
        ))
        
    if not data.invoice_date:
        issues.append(ValidationIssue(
            code="MISSING_DATE",
            message="Invoice issue date is missing.",
            severity=Severity.WARNING,
            field="invoice_date"
        ))

    # 2. Date Format and Logical Date Sequence Check
    inv_date_obj = None
    if data.invoice_date:
        try:
            inv_date_obj = datetime.strptime(data.invoice_date, "%Y-%m-%d")
        except ValueError:
            issues.append(ValidationIssue(
                code="INVALID_DATE_FORMAT",
                message=f"Invoice date '{data.invoice_date}' is not standard ISO YYYY-MM-DD.",
                severity=Severity.WARNING,
                field="invoice_date",
                actual=data.invoice_date
            ))
            
    if data.due_date:
        try:
            due_date_obj = datetime.strptime(data.due_date, "%Y-%m-%d")
            if inv_date_obj and due_date_obj < inv_date_obj:
                issues.append(ValidationIssue(
                    code="DUE_DATE_PRECEDES_INVOICE_DATE",
                    message=f"Due date ({data.due_date}) is prior to Invoice issue date ({data.invoice_date}).",
                    severity=Severity.WARNING,
                    field="due_date",
                    expected=f">= {data.invoice_date}",
                    actual=data.due_date
                ))
        except ValueError:
            issues.append(ValidationIssue(
                code="INVALID_DUE_DATE_FORMAT",
                message=f"Due date '{data.due_date}' is not standard ISO YYYY-MM-DD.",
                severity=Severity.WARNING,
                field="due_date",
                actual=data.due_date
            ))

    # 3. Line Items Math Validation (Quantity * Unit Price == Amount)
    computed_line_sum = 0.0
    for idx, item in enumerate(data.line_items):
        expected_line_amt = round(item.quantity * item.unit_price, 2)
        item.calculated_amount = expected_line_amt
        computed_line_sum += item.amount
        
        if abs(expected_line_amt - item.amount) > 0.05 and item.unit_price > 0:
            item.math_match = False
            issues.append(ValidationIssue(
                code="LINE_ITEM_MATH_MISMATCH",
                message=f"Line {idx + 1} ('{item.description[:25]}'): Qty ({item.quantity}) × Unit Price (${item.unit_price:.2f}) = ${expected_line_amt:.2f}, but found ${item.amount:.2f}.",
                severity=Severity.CRITICAL,
                field=f"line_items[{idx}]",
                expected=expected_line_amt,
                actual=item.amount
            ))
        else:
            item.math_match = True

    computed_line_sum = round(computed_line_sum, 2)

    # 4. Line Items Sum vs Subtotal Check
    if data.subtotal > 0 and len(data.line_items) > 0:
        if abs(computed_line_sum - data.subtotal) > 0.05:
            issues.append(ValidationIssue(
                code="SUBTOTAL_MISMATCH",
                message=f"Sum of line items (${computed_line_sum:.2f}) does not match Subtotal (${data.subtotal:.2f}). Discrepancy: ${abs(computed_line_sum - data.subtotal):.2f}.",
                severity=Severity.CRITICAL,
                field="subtotal",
                expected=computed_line_sum,
                actual=data.subtotal
            ))

    # 5. Grand Total Math Check (Subtotal + Tax + Shipping - Discount == Total)
    expected_grand_total = round(
        data.subtotal + data.tax_amount + data.shipping_amount - data.discount_amount, 2
    )
    if data.total_amount <= 0:
        issues.append(ValidationIssue(
            code="ZERO_TOTAL_AMOUNT",
            message="Invoice grand total is 0 or negative.",
            severity=Severity.CRITICAL,
            field="total_amount",
            actual=data.total_amount
        ))
    elif abs(expected_grand_total - data.total_amount) > 0.05:
        issues.append(ValidationIssue(
            code="TOTAL_MATH_MISMATCH",
            message=f"Grand Total (${data.total_amount:.2f}) does not equal Subtotal (${data.subtotal:.2f}) + Tax (${data.tax_amount:.2f}) + Shipping (${data.shipping_amount:.2f}) - Discount (${data.discount_amount:.2f}) = ${expected_grand_total:.2f}.",
            severity=Severity.CRITICAL,
            field="total_amount",
            expected=expected_grand_total,
            actual=data.total_amount
        ))

    # 6. High-Value Alert Check
    is_high_value = data.total_amount >= settings.high_value_threshold
    if is_high_value:
        alerts.append(
            f"HIGH-VALUE INVOICE: Total amount ${data.total_amount:,.2f} exceeds policy threshold of ${settings.high_value_threshold:,.2f}."
        )

    # 7. Duplicate Detection Check
    is_duplicate = False
    if settings.duplicate_check_enabled and data.vendor_name and data.invoice_number:
        is_duplicate = check_is_duplicate(data.vendor_name, data.invoice_number, exclude_id=invoice_id)
        if is_duplicate:
            issues.append(ValidationIssue(
                code="DUPLICATE_INVOICE",
                message=f"Possible duplicate: An invoice from vendor '{data.vendor_name}' with number '{data.invoice_number}' already exists in database.",
                severity=Severity.CRITICAL,
                field="invoice_number"
            ))
            alerts.append(f"DUPLICATE DETECTED: Vendor '{data.vendor_name}' & #{data.invoice_number} already recorded.")

    # 8. Determine Overall Validation Status
    has_critical = any(issue.severity == Severity.CRITICAL for issue in issues)
    has_warning = any(issue.severity == Severity.WARNING for issue in issues)
    
    if has_critical:
        status = ValidationStatus.FLAGGED
        alerts.append(f"INVOICE FLAGGED: {len([i for i in issues if i.severity == Severity.CRITICAL])} critical validation discrepancies detected.")
    elif has_warning or is_high_value:
        status = ValidationStatus.PENDING_REVIEW
        if is_high_value and not has_critical:
            alerts.append("PENDING APPROVAL: High-value invoice requires manager sign-off.")
    else:
        status = ValidationStatus.APPROVED

    return status, issues, is_high_value, is_duplicate, alerts
