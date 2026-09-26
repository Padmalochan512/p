import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
INBOX_DIR = BASE_DIR / "inbox_folder"
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "invoices.db"

# Create required directories
for directory in [UPLOAD_DIR, INBOX_DIR, DATA_DIR, EXPORTS_DIR, STATIC_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    app_name: str = "ApexInvoice AI - Intelligent Document Processing Agent"
    version: str = "2.0.0"
    db_path: str = str(DB_PATH)
    high_value_threshold: float = 5000.0  # Alert if total >= $5,000
    duplicate_check_enabled: bool = True
    llm_provider: str = "heuristic"  # 'heuristic', 'gemini', 'openai', 'ollama'
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ollama_endpoint: str = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
    ollama_model: str = "llava"
    webhook_alert_url: str = os.getenv("WEBHOOK_ALERT_URL", "")
    auto_watch_inbox: bool = True

settings = Settings()
