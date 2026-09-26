import json
import os
import base64
import requests
from typing import Optional, Dict, Any
from app.config import settings
from app.models import ExtractedInvoiceData, LineItem, DocumentType

PROMPT_SYSTEM = """
You are an expert financial and document processing AI.
Your task is to analyze the provided invoice/receipt image or document text and extract structured key-value data with 100% precision.

Return ONLY a valid JSON object matching this schema exactly:
{
  "doc_type": "INVOICE",
  "vendor_name": "string",
  "vendor_address": "string or null",
  "vendor_tax_id": "string or null",
  "vendor_email": "string or null",
  "customer_name": "string or null",
  "invoice_number": "string",
  "po_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "payment_terms": "string or null",
  "currency": "USD",
  "subtotal": 0.0,
  "tax_amount": 0.0,
  "tax_rate": 0.0,
  "shipping_amount": 0.0,
  "discount_amount": 0.0,
  "total_amount": 0.0,
  "line_items": [
    {
      "description": "Item name/description",
      "quantity": 1.0,
      "unit_price": 0.0,
      "amount": 0.0
    }
  ],
  "confidence_score": 0.98
}
"""

def extract_with_gemini(raw_text: str, image_bytes: Optional[bytes] = None, api_key: Optional[str] = None) -> Optional[ExtractedInvoiceData]:
    key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    parts = [{"text": PROMPT_SYSTEM}]
    
    if raw_text:
        parts.append({"text": f"Document Text:\n{raw_text}"})
        
    if image_bytes:
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": b64_data
            }
        })
        
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }
    
    try:
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            result = res.json()
            text_resp = result["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_resp)
            return build_model_from_json(parsed, method="Gemini 1.5 Vision LLM")
    except Exception as e:
        print(f"Gemini Vision extraction error: {e}")
    return None

def extract_with_openai(raw_text: str, image_bytes: Optional[bytes] = None, api_key: Optional[str] = None) -> Optional[ExtractedInvoiceData]:
    key = api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
        
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    messages_content = [{"type": "text", "text": PROMPT_SYSTEM + (f"\n\nDocument Text:\n{raw_text}" if raw_text else "")}]
    if image_bytes:
        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        messages_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_data}"}
        })
        
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": messages_content}],
        "temperature": 0.1
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return build_model_from_json(parsed, method="OpenAI GPT-4o Vision")
    except Exception as e:
        print(f"OpenAI extraction error: {e}")
    return None

def extract_with_ollama(raw_text: str, image_bytes: Optional[bytes] = None, endpoint: Optional[str] = None, model: Optional[str] = None) -> Optional[ExtractedInvoiceData]:
    ep = endpoint or settings.ollama_endpoint
    mdl = model or settings.ollama_model
    url = f"{ep.rstrip('/')}/api/generate"
    
    prompt = PROMPT_SYSTEM + f"\nDocument Text:\n{raw_text}"
    payload: Dict[str, Any] = {
        "model": mdl,
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    if image_bytes:
        payload["images"] = [base64.b64encode(image_bytes).decode("utf-8")]
        
    try:
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            content = res.json().get("response", "{}")
            parsed = json.loads(content)
            return build_model_from_json(parsed, method=f"Ollama ({mdl})")
    except Exception as e:
        print(f"Ollama extraction error: {e}")
    return None

def build_model_from_json(parsed: Dict[str, Any], method: str) -> ExtractedInvoiceData:
    raw_items = parsed.get("line_items", [])
    line_items = []
    for item in raw_items:
        qty = float(item.get("quantity", 1.0) or 1.0)
        price = float(item.get("unit_price", 0.0) or 0.0)
        amt = float(item.get("amount", 0.0) or 0.0)
        if amt == 0.0 and price > 0:
            amt = round(qty * price, 2)
        line_items.append(LineItem(
            description=item.get("description", "Item"),
            quantity=qty,
            unit_price=price,
            amount=amt,
            calculated_amount=round(qty * price, 2),
            math_match=abs((qty * price) - amt) < 0.05
        ))
        
    return ExtractedInvoiceData(
        doc_type=DocumentType(parsed.get("doc_type", "INVOICE")),
        vendor_name=parsed.get("vendor_name", "Unknown Vendor"),
        vendor_address=parsed.get("vendor_address"),
        vendor_tax_id=parsed.get("vendor_tax_id"),
        vendor_email=parsed.get("vendor_email"),
        customer_name=parsed.get("customer_name"),
        invoice_number=parsed.get("invoice_number", "INV-UNKNOWN"),
        po_number=parsed.get("po_number"),
        invoice_date=parsed.get("invoice_date"),
        due_date=parsed.get("due_date"),
        payment_terms=parsed.get("payment_terms"),
        currency=parsed.get("currency", "USD"),
        subtotal=float(parsed.get("subtotal", 0.0) or 0.0),
        tax_amount=float(parsed.get("tax_amount", 0.0) or 0.0),
        tax_rate=float(parsed.get("tax_rate", 0.0)) if parsed.get("tax_rate") is not None else None,
        shipping_amount=float(parsed.get("shipping_amount", 0.0) or 0.0),
        discount_amount=float(parsed.get("discount_amount", 0.0) or 0.0),
        total_amount=float(parsed.get("total_amount", 0.0) or 0.0),
        line_items=line_items,
        confidence_score=float(parsed.get("confidence_score", 0.96)),
        extraction_method=method
    )
