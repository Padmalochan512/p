import requests
import json
from typing import Dict, Any, List
from app.config import settings

def dispatch_webhook_alert(invoice_data: Dict[str, Any], alerts: List[str]):
    """
    Dispatches alerts to configured Webhook URL (Slack, Discord, Teams, Custom API).
    """
    webhook_url = settings.webhook_alert_url
    if not webhook_url:
        # Webhook not configured; simulated dispatch
        print(f"[ALERT DISPATCH SIMULATION] Sent {len(alerts)} alerts for Invoice #{invoice_data.get('invoice_number', 'N/A')}")
        return True
        
    payload = {
        "text": f"🚨 *ApexInvoice Alert* for Invoice `{invoice_data.get('invoice_number', 'N/A')}`",
        "vendor": invoice_data.get("vendor_name"),
        "total": f"{invoice_data.get('currency', 'USD')} {invoice_data.get('total_amount', 0.0):,.2f}",
        "alerts": alerts,
        "status": invoice_data.get("status")
    }
    
    try:
        res = requests.post(webhook_url, json=payload, timeout=5)
        return res.status_code in [200, 201, 204]
    except Exception as e:
        print(f"Error dispatching webhook alert: {e}")
        return False
