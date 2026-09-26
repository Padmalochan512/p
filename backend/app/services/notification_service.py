import requests
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import Notification, Invoice
from app.config import settings

def create_system_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    invoice_id: Optional[str] = None,
    notification_type: str = "SYSTEM",
    severity: str = "INFO"
) -> Notification:
    notif = Notification(
        user_id=user_id,
        invoice_id=invoice_id,
        title=title,
        message=message,
        notification_type=notification_type,
        severity=severity
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Optional Webhook Dispatch
    if settings.WEBHOOK_ALERT_URL:
        try:
            payload = {
                "title": title,
                "message": message,
                "invoice_id": invoice_id,
                "severity": severity,
                "type": notification_type
            }
            requests.post(settings.WEBHOOK_ALERT_URL, json=payload, timeout=4)
        except Exception:
            pass

    return notif
