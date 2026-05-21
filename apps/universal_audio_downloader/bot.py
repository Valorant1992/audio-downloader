import os
import re
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Import our download logic
from downloader import download_audio_to_mp3, DEFAULT_DOWNLOAD_DIR

# Load the .env file from the root directory
# The script is in apps/universal_audio_downloader/bot.py, so .env is two levels up
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def parse_time_str(time_str):
    """Converts a string like '3:00' or '03:00' or '1:05:00' to seconds."""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a greeting when the user starts the bot."""
    await update.message.reply_text(
        "Hello! I am your Universal Audio Downloader Bot 🎵\n\n"
        "Send me any link (YouTube, Spotify, Apple Music) and I will download the song and send you the MP3!\n\n"
        "**Bonus Tip**: You can add start and end times to trim the audio! \n"
        "Example: `https://youtu.be/dQw4w9WgXcQ 01:00 01:30` (This downloads from 1 min to 1 min 30 sec)."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes incoming messages, checks for URLs, and downloads audio."""
    text = update.message.text
    
    # Simple check if the message contains a URL
    if not re.search(r'http[s]?://', text):
        await update.message.reply_text("Please send me a valid URL (e.g., from YouTube, Spotify, or Apple Music).")
        return

    # Extract the first URL found in the message
    url = re.search(r'(http[s]?://\S+)', text).group(1)

    # Search for optional time stamps like MM:SS or HH:MM:SS
    time_matches = re.findall(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', text)
    start_time, end_time = None, None
    if len(time_matches) >= 1:
        start_time = parse_time_str(time_matches[0])
    if len(time_matches) >= 2:
        end_time = parse_time_str(time_matches[1])

    # Send a status message so the user knows it's working
    status_text = "⏳ Downloading... This might take a moment."
    if start_time is not None:
        status_text = f"⏳ Downloading specific section... This might take a moment."
    status_msg = await update.message.reply_text(status_text)

    try:
        # Run the synchronous download function in a separate thread to prevent blocking the bot
        filepath = await asyncio.to_thread(download_audio_to_mp3, url, DEFAULT_DOWNLOAD_DIR, start_time, end_time)
        
        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Failed to download the audio. The file was not found.")
            return

        await status_msg.edit_text("✅ Download complete! Uploading to Telegram...")

        # Send the audio file
        # Telegram allows up to 50MB for bots. Most songs are < 10MB.
        with open(filepath, 'rb') as audio_file:
            filename = os.path.basename(filepath)
            await context.bot.send_audio(
                chat_id=update.effective_chat.id, 
                audio=audio_file, 
                title=filename.replace('.mp3', '') # Clean title for Telegram UI
            )
        
        # Cleanup the status message
        await status_msg.delete()
        
        # Delete the file from the server to save space
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Failed to delete local file {filepath}: {e}")

    except Exception as e:
        print(f"Error during download/upload: {e}")
        await status_msg.edit_text(f"❌ An error occurred:\n{str(e)}")

if __name__ == '__main__':
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in the .env file.")
        exit(1)

    print("Starting Telegram Bot...")
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    app.run_polling()
