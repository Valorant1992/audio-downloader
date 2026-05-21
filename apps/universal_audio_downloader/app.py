from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from downloader import download_audio_to_mp3

app = FastAPI(title="Audio Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DownloadRequest(BaseModel):
    url: str

@app.post("/api/download")
async def download_audio(request: DownloadRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        # This will block the event loop, but for a simple local app it's perfectly fine.
        # For production, this should run in a ThreadPoolExecutor.
        filepath = download_audio_to_mp3(request.url)
        
        if not filepath or not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="File download failed or file not found.")

        filename = os.path.basename(filepath)
        
        # Return the file as a downloadable attachment
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='audio/mpeg'
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Audio Downloader API is running. Send a POST request to /api/download with {'url': 'your_link_here'}"}

if __name__ == "__main__":
    import uvicorn
    # When run directly, start uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
