import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    print(f"================================================================")
    print(f"🚀 ApexInvoice AI - Intelligent Document Processing Agent")
    print(f"🌐 Server starting at: http://127.0.0.1:{port}")
    print(f"📁 Automated Inbox Watcher: ./inbox_folder")
    print(f"================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
