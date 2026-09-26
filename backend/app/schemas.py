from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.models import ProcessingStatus, ReviewStatus, IssueSeverity

# Auth & User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = "Demo User"
    default_currency: Optional[str] = "INR"
    alert_threshold: Optional[float] = 50000.0

class UserCreate(UserBase):
    password: str = Field(..., min_length=4)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# Line Item Schemas
class LineItemBase(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    tax_rate: Optional[float] = 0.0
    line_total: float = 0.0

class LineItemCreate(LineItemBase):
    pass

class LineItemUpdate(LineItemBase):
    id: Optional[int] = None
    calculated_total: Optional[float] = None
    is_math_match: Optional[bool] = True

class LineItemResponse(LineItemBase):
    id: int
    invoice_id: str
    item_number: int
    calculated_total: float
    is_math_match: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Validation Issue Schemas
class ValidationIssueResponse(BaseModel):
    id: int
    invoice_id: str
    issue_code: str
    field_name: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    message: str
    severity: IssueSeverity
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Invoice Schemas
class InvoiceBase(BaseModel):
    vendor_name: Optional[str] = "Unknown Vendor"
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    vendor_email: Optional[str] = None
    vendor_phone: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    invoice_number: Optional[str] = "INV-UNKNOWN"
    po_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = "INR"
    subtotal: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    tax_rate: Optional[float] = None
    shipping_amount: Optional[float] = 0.0
    discount_amount: Optional[float] = 0.0
    total_amount: Optional[float] = 0.0
    reviewer_notes: Optional[str] = None

class InvoiceUpdate(InvoiceBase):
    review_status: Optional[ReviewStatus] = None
    line_items: Optional[List[LineItemUpdate]] = None

class InvoiceResponse(InvoiceBase):
    id: str
    document_id: str
    user_id: int
    review_status: ReviewStatus
    is_high_value: bool
    is_duplicate: bool
    confidence_score: float
    extraction_method: str
    created_at: datetime
    updated_at: datetime
    line_items: List[LineItemResponse] = []
    validation_issues: List[ValidationIssueResponse] = []

    class Config:
        from_attributes = True

class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    page: int
    limit: int
    total_pages: int

# Document Schemas
class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    processing_status: ProcessingStatus
    page_count: int
    error_message: Optional[str] = None
    created_at: datetime
    invoice_id: Optional[str] = None
    invoice: Optional[InvoiceResponse] = None

    class Config:
        from_attributes = True

# Dashboard Schemas
class DashboardSummaryResponse(BaseModel):
    total_invoices: int
    validated_invoices: int
    needs_review_invoices: int
    flagged_invoices: int
    total_spend: float
    currency: str
    avg_confidence: float
    high_value_count: int
    duplicate_count: int

class ActivityItem(BaseModel):
    date: str
    processed_count: int
    total_amount: float

class StatusDistributionItem(BaseModel):
    name: str
    value: int
    color: str

class VendorSpendItem(BaseModel):
    vendor: str
    count: int
    total_spend: float

class DashboardActivityResponse(BaseModel):
    timeline: List[ActivityItem]
    status_distribution: List[StatusDistributionItem]
    top_vendors: List[VendorSpendItem]

# Notification Schemas
class NotificationResponse(BaseModel):
    id: int
    invoice_id: Optional[str] = None
    title: str
    message: str
    notification_type: str
    severity: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Settings Schemas
class SettingsResponse(BaseModel):
    user_profile: UserResponse
    default_currency: str
    alert_threshold: float
    ocr_status: str
    llm_status: str
    llm_provider: str
    database_status: str
    app_version: str
    upload_dir: str
    max_file_size_mb: int

class UserSettingsUpdate(BaseModel):
    full_name: Optional[str] = None
    default_currency: Optional[str] = None
    alert_threshold: Optional[float] = None
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    webhook_alert_url: Optional[str] = None
