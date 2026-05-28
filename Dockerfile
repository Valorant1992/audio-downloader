FROM python:3.11-slim

# Install system dependencies (ffmpeg is required by yt-dlp to convert to MP3)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user (Hugging Face Spaces runs as user 1000)
RUN useradd -m -u 1000 user
WORKDIR /app

# Copy dependency files first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files and set ownership to the non-root user
COPY --chown=user:user . .

# Set up runtime directories with proper permissions
RUN mkdir -p logs apps/backend/downloads && chown -R user:user logs apps/backend/downloads

USER user

# Set Hugging Face port environment variable default (Hugging Face exposes port 7860)
ENV PORT=7860
ENV LOG_DIR=/app/logs

# Run the startup manager
CMD ["python", "run_all.py"]
