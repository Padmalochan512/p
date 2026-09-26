from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    UTILITY_BILL = "UTILITY_BILL"
    UNKNOWN = "UNKNOWN"

class ValidationStatus(str, Enum):
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class LineItem(BaseModel):
    item_id: Optional[str] = None
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    tax_rate: float = 0.0
    amount: float = 0.0
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    calculated_amount: Optional[float] = None
    math_match: bool = True

class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: Severity
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None

class ExtractedInvoiceData(BaseModel):
    doc_type: DocumentType = DocumentType.INVOICE
    vendor_name: str = "Unknown Vendor"
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    invoice_number: str = "INV-UNKNOWN"
    po_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    tax_rate: Optional[float] = None
    shipping_amount: float = 0.0
    discount_amount: float = 0.0
    total_amount: float = 0.0
    line_items: List[LineItem] = []
    notes: Optional[str] = None
    raw_text: Optional[str] = None
    confidence_score: float = 0.95
    extraction_method: str = "Heuristic / Rule Engine"

class InvoiceRecord(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_path: str
    file_type: str
    file_size_bytes: int
    created_at: str
    updated_at: str
    status: ValidationStatus
    data: ExtractedInvoiceData
    validation_issues: List[ValidationIssue] = []
    is_high_value: bool = False
    is_duplicate: bool = False
    alerts_triggered: List[str] = []
    manual_reviewed: bool = False
    reviewer_notes: Optional[str] = None

class InvoiceUpdateRequest(BaseModel):
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
    line_items: Optional[List[LineItem]] = None
    status: Optional[ValidationStatus] = None
    reviewer_notes: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    high_value_threshold: Optional[float] = None
    duplicate_check_enabled: Optional[bool] = None
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_endpoint: Optional[str] = None
    ollama_model: Optional[str] = None
    webhook_alert_url: Optional[str] = None
