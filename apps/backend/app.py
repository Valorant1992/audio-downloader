from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from .downloader import download_audio_to_mp3
import logging

# Configure standard logging for backend and frontend
LOGS_DIR = os.environ.get("LOG_DIR", "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Format for logger outputs
log_formatter = logging.Formatter("[%(asctime)s] %(levelname)-8s [%(name)s:%(filename)s:%(lineno)d] %(message)s")

# Backend Logger: logs to console and logs/backend.log
backend_handler = logging.FileHandler(os.path.join(LOGS_DIR, "backend.log"), encoding="utf-8")
backend_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("audio_downloader.app")
logger.setLevel(logging.DEBUG)
logger.addHandler(backend_handler)
logger.addHandler(console_handler)

# Configure root/downloader logger to use same backend logging files
downloader_logger = logging.getLogger("audio_downloader.downloader")
downloader_logger.setLevel(logging.DEBUG)
downloader_logger.addHandler(backend_handler)
downloader_logger.addHandler(console_handler)

# Frontend Logger: logs to logs/frontend.log
frontend_handler = logging.FileHandler(os.path.join(LOGS_DIR, "frontend.log"), encoding="utf-8")
frontend_handler.setFormatter(log_formatter)

frontend_logger = logging.getLogger("audio_downloader.frontend")
frontend_logger.setLevel(logging.DEBUG)
frontend_logger.addHandler(frontend_handler)
# Also print frontend logs to console for development visibility
frontend_logger.addHandler(console_handler)

logger.info("Initializing Audio Downloader FastAPI backend...")

app = FastAPI(title="Audio Downloader API")

# Serve static assets (frontend) from the apps/frontend directory
app.mount("/static", StaticFiles(directory="apps/frontend"), name="static")

# Root endpoint returns the frontend HTML page
@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    logger.info("Serving frontend homepage index.html to %s", request.client.host)
    with open("apps/frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

class DownloadRequest(BaseModel):
    url: str
    start_time: int | None = None  # optional start in seconds
    end_time: int | None = None    # optional end in seconds

class ClientLogRequest(BaseModel):
    level: str
    message: str
    timestamp: str
    metadata: dict | None = None

@app.post("/api/log")
async def log_client_message(request: ClientLogRequest):
    # Route the client-side logs to logs/frontend.log using the dedicated frontend_logger
    level_upper = request.level.upper()
    log_msg = f"[CLIENT] {request.message} (Client Time: {request.timestamp}) | Metadata: {request.metadata}"
    
    if level_upper == "DEBUG":
        frontend_logger.debug(log_msg)
    elif level_upper == "INFO":
        frontend_logger.info(log_msg)
    elif level_upper == "WARN" or level_upper == "WARNING":
        frontend_logger.warning(log_msg)
    elif level_upper == "ERROR":
        frontend_logger.error(log_msg)
    else:
        frontend_logger.info(log_msg)
        
    return {"status": "success"}

@app.post("/api/download")
async def download_audio(request: DownloadRequest):
    logger.info("Received download request for URL: %s", request.url)
    logger.debug("Request details - start_time: %s, end_time: %s", request.start_time, request.end_time)
    
    if not request.url:
        logger.warning("Empty URL provided in request payload.")
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        logger.debug("Invoking downloader module...")
        filepath = download_audio_to_mp3(
            request.url,
            start_time=request.start_time,
            end_time=request.end_time,
        )
        
        if not filepath or not os.path.exists(filepath):
            logger.error("Download failed or file not found on disk at: %s", filepath)
            raise HTTPException(status_code=500, detail="File download failed or file not found.")

        filename = os.path.basename(filepath)
        logger.info("Successfully processed audio download: %s -> %s", request.url, filename)
        logger.debug("File stored locally at: %s", filepath)
        
        # Return the file as a downloadable attachment
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='audio/mpeg'
        )

    except Exception as e:
        logger.exception("An error occurred during audio download processing:")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok", "message": "Audio Downloader API is running."}

if __name__ == "__main__":
    import uvicorn
    # When run directly, start uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
