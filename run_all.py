import subprocess
import os
import sys
import time

processes = []

# Get Port from environment, default to 8000
port = os.environ.get("PORT", "8000")

# Start FastAPI web app (always run this)
print(f"Starting FastAPI web app on port {port}...")
fastapi_proc = subprocess.Popen([
    "uvicorn", "apps.universal_audio_downloader.app:app",
    "--host", "0.0.0.0",
    "--port", port
])
processes.append(fastapi_proc)

# Start Telegram Bot if token is provided in environment
token = os.environ.get("TELEGRAM_BOT_TOKEN")
if token:
    print("Starting Telegram Bot...")
    bot_proc = subprocess.Popen([
        "python", "apps/universal_audio_downloader/bot.py"
    ])
    processes.append(bot_proc)
else:
    print("TELEGRAM_BOT_TOKEN not set. Skipping Telegram Bot startup.")

try:
    while True:
        # Check if any process has exited
        for p in processes:
            poll_result = p.poll()
            if poll_result is not None:
                print(f"Process {p.args} exited with code {poll_result}")
                # Terminate other processes
                for other in processes:
                    if other != p:
                        other.terminate()
                sys.exit(poll_result)
        time.sleep(2)
except KeyboardInterrupt:
    print("Stopping all processes...")
    for p in processes:
        p.terminate()
