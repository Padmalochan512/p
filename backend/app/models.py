from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ReviewStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"

class IssueSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="Demo User")
    role = Column(String(50), default="accountant")
    default_currency = Column(String(10), default="INR")
    alert_threshold = Column(Float, default=50000.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'PDF', 'PNG', 'JPG', 'JPEG', 'WEBP'
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), default="application/octet-stream")
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    page_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="documents")
    invoice = relationship("Invoice", back_populates="document", uselist=False, cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(64), primary_key=True, index=True)
    document_id = Column(String(64), ForeignKey("documents.id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    vendor_name = Column(String(255), index=True, default="Unknown Vendor")
    vendor_address = Column(Text, nullable=True)
    vendor_tax_id = Column(String(100), nullable=True)  # GSTIN, VAT, EIN
    vendor_email = Column(String(150), nullable=True)
    vendor_phone = Column(String(100), nullable=True)

    customer_name = Column(String(255), nullable=True)
    customer_address = Column(Text, nullable=True)

    invoice_number = Column(String(150), index=True, default="INV-UNKNOWN")
    po_number = Column(String(100), nullable=True)
    invoice_date = Column(String(50), nullable=True, index=True)
    due_date = Column(String(50), nullable=True)
    payment_terms = Column(String(100), nullable=True)
    currency = Column(String(10), default="INR")

    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tax_rate = Column(Float, nullable=True)
    shipping_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0, index=True)

    review_status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.NEEDS_REVIEW, index=True)
    is_high_value = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False, index=True)
    confidence_score = Column(Float, default=0.95)
    extraction_method = Column(String(100), default="Hybrid Rule-based OCR")
    reviewer_notes = Column(Text, nullable=True)
    raw_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="invoices")
    document = relationship("Document", back_populates="invoice")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="invoice", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(64), ForeignKey("invoices.id"), nullable=False, index=True)
    item_number = Column(Integer, default=1)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)
    calculated_total = Column(Float, default=0.0)
    is_math_match = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="line_items")

class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(64), ForeignKey("invoices.id"), nullable=False, index=True)
    issue_code = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=True)
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    severity = Column(SQLEnum(IssueSeverity), default=IssueSeverity.WARNING)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="validation_issues")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invoice_id = Column(String(64), ForeignKey("invoices.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="SYSTEM")
    severity = Column(String(20), default="INFO")
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="notifications")
    invoice = relationship("Invoice", back_populates="notifications")

class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False, index=True)
    stage = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), default="INFO")
    timestamp = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="logs")

class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
