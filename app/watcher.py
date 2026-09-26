import time
import shutil
import uuid
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.config import INBOX_DIR, UPLOAD_DIR
from app.extractor.orchestrator import orchestrate_extraction
from app.validator import validate_invoice_data
from app.database import save_invoice
from app.models import InvoiceRecord, ValidationStatus
from app.alerts import dispatch_webhook_alert
from datetime import datetime

class InvoiceFileHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback

    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        # Avoid temporary files
        if file_path.name.startswith(".") or file_path.suffix.lower() not in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]:
            return
            
        print(f"[WATCHER] New file detected in inbox: {file_path.name}")
        # Wait a moment for file to be completely written
        time.sleep(1.0)
        self.process_file(file_path)

    def process_file(self, file_path: Path):
        try:
            doc_id = f"doc_{uuid.uuid4().hex[:10]}"
            ext = file_path.suffix.lower()
            dest_filename = f"{doc_id}{ext}"
            dest_path = UPLOAD_DIR / dest_filename
            
            # Copy to uploads directory
            shutil.copy2(file_path, dest_path)
            
            # Extract data
            extracted_data = orchestrate_extraction(dest_path)
            
            # Validate
            status, issues, is_high_val, is_dup, alerts = validate_invoice_data(extracted_data, invoice_id=doc_id)
            
            now_iso = datetime.now().isoformat()
            record = InvoiceRecord(
                id=doc_id,
                filename=dest_filename,
                original_filename=file_path.name,
                file_path=str(dest_path),
                file_type=ext.replace(".", "").upper(),
                file_size_bytes=dest_path.stat().st_size,
                created_at=now_iso,
                updated_at=now_iso,
                status=status,
                data=extracted_data,
                validation_issues=issues,
                is_high_value=is_high_val,
                is_duplicate=is_dup,
                alerts_triggered=alerts
            )
            
            save_invoice(record)
            if alerts:
                dispatch_webhook_alert(record.model_dump(), alerts)
                
            print(f"[WATCHER] Successfully processed and indexed: {file_path.name} -> Status: {status}")
            if self.callback:
                self.callback(record)
        except Exception as e:
            print(f"[WATCHER ERROR] Failed to process {file_path}: {e}")

class InboxWatcherService:
    def __init__(self):
        self.observer = None
        self.is_running = False

    def start(self, callback=None):
        if self.is_running:
            return
        self.observer = Observer()
        handler = InvoiceFileHandler(callback)
        self.observer.schedule(handler, str(INBOX_DIR), recursive=False)
        self.observer.start()
        self.is_running = True
        print(f"[WATCHER SERVICE] Started monitoring directory: {INBOX_DIR}")

    def stop(self):
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            print("[WATCHER SERVICE] Stopped.")

watcher_service = InboxWatcherService()
