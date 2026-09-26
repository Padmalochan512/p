import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"=================================================================")
    print(f"🚀 AI Document & Invoice Processing Agent Backend Server")
    print(f"🌐 Running on: http://127.0.0.1:{port}")
    print(f"📖 API Docs:  http://127.0.0.1:{port}/docs")
    print(f"=================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
