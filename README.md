---
title: Audio Downloader
emoji: 🎧
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Audio Downloader

A **FastAPI** based service for downloading audio from various sources, with optional **Telegram bot** integration.

---

## ✨ Features
- Exposes a clean HTTP API for downloading audio files.
- Can be run as a standalone FastAPI server or together with a Telegram bot.
- Configurable via environment variables (`PORT`, `TELEGRAM_BOT_TOKEN`).
- Simple process manager in `run_all.py` that keeps the web app and bot alive.

---

## 📋 Prerequisites
- **Python 3.10+**
- `uvicorn` for serving the FastAPI app (installed via `requirements.txt`).
- Optional: a Telegram bot token if you want bot functionality.

---

## 🚀 Installation
```bash
# Clone the repo (skip if you already have the code)
# git clone https://github.com/yourusername/audio-downloader.git

# Navigate to the project directory
cd AudioDownloader

# Create a virtual environment
python -m venv venv

# Activate the environment
# Windows
tasks/venv/Scripts/activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## ⚙️ Configuration
Create a `.env` file (or set environment variables directly) with the following keys:
```
PORT=8000                # Port for the FastAPI server (default: 8000)
TELEGRAM_BOT_TOKEN=...   # Optional – token for the Telegram bot
```

---

## ▶️ Running the Application
```bash
# Start both FastAPI and the Telegram bot (if token is set)
python run_all.py
```
The script will:
1. Launch the FastAPI app on `0.0.0.0:<PORT>`.
2. Spin up the Telegram bot if `TELEGRAM_BOT_TOKEN` is defined.
3. Monitor the processes and restart/terminate them gracefully on exit.

You can also run the FastAPI server alone:
```bash
uvicorn apps.universal_audio_downloader.app:app --host 0.0.0.0 --port $PORT
```

---

## 📚 API Endpoints
The FastAPI app lives in `apps/universal_audio_downloader/app.py`. Typical endpoints:
- `POST /download` – Provide a URL and desired format; the service returns the audio file.
- `GET /health` – Simple health‑check.

Check the source code for more details and example request bodies.

---

## 🤝 Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/awesome-feature`).
3. Make your changes and ensure tests pass (`pytest`).
4. Open a Pull Request with a clear description of your changes.

---

## 📄 License
This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

*Happy coding! 🎧*
