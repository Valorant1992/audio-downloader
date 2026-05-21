FROM python:3.11-slim

# Install ffmpeg (Required by yt-dlp to convert to MP3)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Run the startup manager by default
CMD ["python", "run_all.py"]
