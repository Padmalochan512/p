import sqlite3
import json
import csv
import io
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.config import DB_PATH
from app.models import InvoiceRecord, ExtractedInvoiceData, ValidationStatus, ValidationIssue, LineItem

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Invoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL,
        vendor_name TEXT,
        invoice_number TEXT,
        invoice_date TEXT,
        due_date TEXT,
        currency TEXT DEFAULT 'USD',
        subtotal REAL DEFAULT 0.0,
        tax_amount REAL DEFAULT 0.0,
        shipping_amount REAL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        total_amount REAL DEFAULT 0.0,
        is_high_value INTEGER DEFAULT 0,
        is_duplicate INTEGER DEFAULT 0,
        confidence_score REAL DEFAULT 1.0,
        extraction_method TEXT,
        manual_reviewed INTEGER DEFAULT 0,
        reviewer_notes TEXT,
        raw_data_json TEXT NOT NULL,
        validation_issues_json TEXT NOT NULL,
        alerts_triggered_json TEXT NOT NULL
    );
    """)

    # Alerts log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    );
    """)

    # System activity audit table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

def save_invoice(record: InvoiceRecord):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    raw_data_json = record.data.model_dump_json()
    validation_issues_json = json.dumps([v.model_dump() for v in record.validation_issues])
    alerts_triggered_json = json.dumps(record.alerts_triggered)

    cursor.execute("""
    INSERT OR REPLACE INTO invoices (
        id, filename, original_filename, file_path, file_type, file_size_bytes,
        created_at, updated_at, status, vendor_name, invoice_number, invoice_date,
        due_date, currency, subtotal, tax_amount, shipping_amount, discount_amount,
        total_amount, is_high_value, is_duplicate, confidence_score, extraction_method,
        manual_reviewed, reviewer_notes, raw_data_json, validation_issues_json, alerts_triggered_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.id, record.filename, record.original_filename, record.file_path,
        record.file_type, record.file_size_bytes, record.created_at, record.updated_at,
        record.status.value if isinstance(record.status, ValidationStatus) else str(record.status),
        record.data.vendor_name, record.data.invoice_number, record.data.invoice_date,
        record.data.due_date, record.data.currency, record.data.subtotal,
        record.data.tax_amount, record.data.shipping_amount, record.data.discount_amount,
        record.data.total_amount, 1 if record.is_high_value else 0,
        1 if record.is_duplicate else 0, record.data.confidence_score,
        record.data.extraction_method, 1 if record.manual_reviewed else 0,
        record.reviewer_notes, raw_data_json, validation_issues_json, alerts_triggered_json
    ))
    
    # Save alerts into alerts table
    for alert_msg in record.alerts_triggered:
        cursor.execute("""
        INSERT INTO alerts (invoice_id, alert_type, title, message, severity, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            "HIGH_VALUE" if "high-value" in alert_msg.lower() else "FLAGGED",
            f"Alert on {record.data.invoice_number}",
            alert_msg,
            "CRITICAL" if "error" in alert_msg.lower() or "discrepancy" in alert_msg.lower() else "WARNING",
            record.created_at
        ))

    conn.commit()
    conn.close()

def parse_invoice_row(row: sqlite3.Row) -> InvoiceRecord:
    raw_data = json.loads(row["raw_data_json"])
    validation_issues = [ValidationIssue(**item) for item in json.loads(row["validation_issues_json"])]
    alerts = json.loads(row["alerts_triggered_json"])
    
    return InvoiceRecord(
        id=row["id"],
        filename=row["filename"],
        original_filename=row["original_filename"],
        file_path=row["file_path"],
        file_type=row["file_type"],
        file_size_bytes=row["file_size_bytes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        status=ValidationStatus(row["status"]),
        data=ExtractedInvoiceData(**raw_data),
        validation_issues=validation_issues,
        is_high_value=bool(row["is_high_value"]),
        is_duplicate=bool(row["is_duplicate"]),
        alerts_triggered=alerts,
        manual_reviewed=bool(row["manual_reviewed"]),
        reviewer_notes=row["reviewer_notes"]
    )

def get_invoice_by_id(invoice_id: str) -> Optional[InvoiceRecord]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return parse_invoice_row(row)

def get_all_invoices(
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
) -> List[InvoiceRecord]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM invoices WHERE 1=1"
    params = []
    
    if status_filter and status_filter != "ALL":
        query += " AND status = ?"
        params.append(status_filter)
        
    if search_query:
        query += " AND (vendor_name LIKE ? OR invoice_number LIKE ? OR original_filename LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard])
        
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [parse_invoice_row(r) for r in rows]

def check_is_duplicate(vendor_name: str, invoice_number: str, exclude_id: Optional[str] = None) -> bool:
    if not vendor_name or not invoice_number or invoice_number in ["INV-UNKNOWN", "N/A", ""]:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT id FROM invoices WHERE LOWER(vendor_name) = LOWER(?) AND LOWER(invoice_number) = LOWER(?)"
    params = [vendor_name.strip(), invoice_number.strip()]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)
    cursor.execute(query, params)
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def delete_invoice(invoice_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_dashboard_metrics() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT 
        COUNT(*) as total_count,
        COALESCE(SUM(total_amount), 0.0) as total_spend,
        COALESCE(AVG(confidence_score), 0.0) as avg_confidence,
        SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
        SUM(CASE WHEN status = 'FLAGGED' THEN 1 ELSE 0 END) as flagged_count,
        SUM(CASE WHEN status = 'PENDING_REVIEW' THEN 1 ELSE 0 END) as pending_count,
        SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_count,
        SUM(CASE WHEN is_high_value = 1 THEN 1 ELSE 0 END) as high_value_count,
        SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as duplicate_count
    FROM invoices
    """)
    stats_row = cursor.fetchone()
    
    # Top vendors by spend
    cursor.execute("""
    SELECT vendor_name, COUNT(*) as invoice_count, SUM(total_amount) as total_vendor_spend
    FROM invoices
    WHERE vendor_name IS NOT NULL AND vendor_name != ''
    GROUP BY vendor_name
    ORDER BY total_vendor_spend DESC
    LIMIT 6
    """)
    vendor_rows = cursor.fetchall()
    top_vendors = [
        {
            "vendor": r["vendor_name"],
            "count": r["invoice_count"],
            "total_spend": round(r["total_vendor_spend"], 2)
        } for r in vendor_rows
    ]
    
    # Recent alerts
    cursor.execute("""
    SELECT a.*, i.original_filename, i.vendor_name 
    FROM alerts a
    LEFT JOIN invoices i ON a.invoice_id = i.id
    ORDER BY a.created_at DESC
    LIMIT 10
    """)
    alerts_rows = cursor.fetchall()
    recent_alerts = [dict(r) for r in alerts_rows]
    
    conn.close()
    
    return {
        "total_invoices": stats_row["total_count"],
        "total_spend": round(stats_row["total_spend"], 2),
        "avg_confidence": round(stats_row["avg_confidence"] * 100, 1),
        "approved_count": stats_row["approved_count"] or 0,
        "flagged_count": stats_row["flagged_count"] or 0,
        "pending_count": stats_row["pending_count"] or 0,
        "rejected_count": stats_row["rejected_count"] or 0,
        "high_value_count": stats_row["high_value_count"] or 0,
        "duplicate_count": stats_row["duplicate_count"] or 0,
        "top_vendors": top_vendors,
        "recent_alerts": recent_alerts
    }

def export_invoices_csv() -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Invoice ID", "Original Filename", "Status", "Vendor Name", "Invoice Number",
        "PO Number", "Invoice Date", "Due Date", "Currency", "Subtotal", "Tax Amount",
        "Shipping Amount", "Discount Amount", "Total Amount", "High Value", "Duplicate",
        "Confidence (%)", "Extraction Method", "Manual Reviewed", "Reviewer Notes", "Created At"
    ])
    
    for r in rows:
        writer.writerow([
            r["id"], r["original_filename"], r["status"], r["vendor_name"], r["invoice_number"],
            "", r["invoice_date"], r["due_date"], r["currency"], r["subtotal"], r["tax_amount"],
            r["shipping_amount"], r["discount_amount"], r["total_amount"],
            "Yes" if r["is_high_value"] else "No", "Yes" if r["is_duplicate"] else "No",
            round(r["confidence_score"] * 100, 1), r["extraction_method"],
            "Yes" if r["manual_reviewed"] else "No", r["reviewer_notes"] or "", r["created_at"]
        ])
        
    return output.getvalue()

def export_line_items_csv() -> str:
    invoices = get_all_invoices()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Invoice ID", "Invoice Number", "Vendor Name", "Item Description",
        "Quantity", "Unit Price", "Tax Rate (%)", "Line Total Amount", "Math Match"
    ])
    
    for inv in invoices:
        for item in inv.data.line_items:
            writer.writerow([
                inv.id, inv.data.invoice_number, inv.data.vendor_name,
                item.description, item.quantity, item.unit_price,
                item.tax_rate, item.amount, "Yes" if item.math_match else "Mismatch"
            ])
            
    return output.getvalue()

# Auto-initialize database tables on module import
init_db()
