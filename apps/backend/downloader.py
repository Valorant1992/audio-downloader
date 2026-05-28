import yt_dlp
import os
import re
import requests
import urllib.parse
from urllib.parse import unquote
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TCON, TDRC, error

# Determine the base directory of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# BASE_DIR is /app/apps/backend, so we need to go up two directories to reach /app root
ROOT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
DEFAULT_DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
COOKIES_FILE = os.path.join(ROOT_DIR, 'cookies.txt')

# FFmpeg paths specific to this setup
FFMPEG_DIR = r'C:\Users\giris\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin'

import logging
logger = logging.getLogger("audio_downloader.downloader")

# Ensure logging outputs to stdout for Docker/HuggingFace container visibility
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s"))
    logger.addHandler(sh)

# Dynamically write cookies.txt from environment variable if provided (e.g. on Hugging Face)
cookies_env = os.environ.get("COOKIES_CONTENT")
if cookies_env:
    logger.info("COOKIES_CONTENT environment variable detected. Attempting to write to cookies file...")
    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(cookies_env.strip())
        logger.info("Successfully wrote COOKIES_CONTENT to file at: %s", COOKIES_FILE)
    except Exception as e:
        logger.error("Failed to write COOKIES_CONTENT to file: %s", e)
else:
    logger.warning("No COOKIES_CONTENT environment variable detected in system env.")

def apply_id3_tags(filepath: str, query: str):
    """Searches iTunes API for the song and embeds perfect ID3 tags."""
    logger.info("Searching iTunes API for perfect metadata: %s", query)
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data['resultCount'] == 0:
            logger.warning("No iTunes metadata found. Falling back to default YouTube tags.")
            return
            
        track = data['results'][0]
        
        # Download high-res album art (replace 100x100 with 1000x1000)
        art_url = track.get('artworkUrl100', '').replace('100x100bb', '1000x1000bb')
        art_data = None
        if art_url:
            art_data = requests.get(art_url, timeout=10).content
            
        audio = MP3(filepath, ID3=ID3)
        
        # Add ID3 tag container if it doesn't exist
        try:
            audio.add_tags()
        except error:
            pass # Tags already exist

        # Embed tags (Track Name, Artist, Album, Genre, Year)
        if 'trackName' in track:
            audio.tags.add(TIT2(encoding=3, text=track['trackName']))
        if 'artistName' in track:
            audio.tags.add(TPE1(encoding=3, text=track['artistName']))
        if 'collectionName' in track: # Album / Soundtrack
            audio.tags.add(TALB(encoding=3, text=track['collectionName']))
        if 'primaryGenreName' in track:
            audio.tags.add(TCON(encoding=3, text=track['primaryGenreName']))
        if 'releaseDate' in track:
            year = track['releaseDate'][:4]
            audio.tags.add(TDRC(encoding=3, text=year))
            
        # Embed High-Res Album Art
        if art_data:
            audio.tags.add(
                APIC(
                    encoding=3, # utf-8
                    mime='image/jpeg',
                    type=3, # cover front
                    desc='Cover',
                    data=art_data
                )
            )
            
        audio.save(v2_version=3)
        logger.info("Perfect ID3 tags applied successfully!")
        
    except Exception as e:
        logger.exception("Failed to apply custom ID3 tags: %s", e)

def extract_spotify_title(url: str):
    """Scrapes the Spotify track title and artist from the page title."""
    try:
        html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
        match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if match:
            title = match.group(1)
            title = title.replace(" - song and lyrics by ", " ")
            title = title.replace(" | Spotify", "")
            title = title.replace(" - song by ", " ")
            return title.strip()
    except Exception as e:
        pass
    return None

def extract_applemusic_title(url: str):
    """Fallback simple extraction for Apple Music using the URL path."""
    try:
        match = re.search(r'/album/([^/]+)', url)
        if match:
            title = unquote(match.group(1)).replace('-', ' ')
            return title.strip()
    except Exception as e:
        pass
    return None

def duration_filter(info, *, incomplete):
    """Filters out videos longer than 10 minutes (600 seconds)."""
    duration = info.get('duration')
    if duration and duration > 600:
        return 'The video is too long (over 10 minutes).'
    return None

def download_with_ytdlp(query: str, output_dir: str, start_time: int = None, end_time: int = None) -> str:
    """Downloads a YouTube URL or a ytsearch query directly and returns the file path."""
    logger.info("Using yt-dlp to download: %s", query)
    if start_time is not None or end_time is not None:
        logger.debug("Download time range: start=%s, end=%s", start_time, end_time)
    
    # We use FFmpegMetadata as a fallback base layer and spoof clients to bypass bot detection.
    ydl_opts = {
        'format': 'bestaudio/best',
        'ignoreerrors': True,
        'writethumbnail': True,
        'match_filter': duration_filter,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            },
            {
                'key': 'EmbedThumbnail',
            }
        ],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': True,
    }

    # Use cookies if cookies.txt exists in the root directory
    if os.path.exists(COOKIES_FILE):
        logger.info("Using exported cookies from: %s", COOKIES_FILE)
        ydl_opts['cookiefile'] = COOKIES_FILE
    else:
        # If no cookies are provided, attempt to use client spoofing as a fallback
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': ['web', 'ios', 'android'],
            }
        }

    # Cloud/Linux compatibility: Only use the hardcoded Windows path if it exists.
    # Otherwise, yt-dlp will automatically find ffmpeg in the system PATH.
    win_ffmpeg = r'C:\Users\giris\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin'
    if os.name == 'nt' and os.path.exists(win_ffmpeg):
        ydl_opts['ffmpeg_location'] = win_ffmpeg

    if start_time is not None or end_time is not None:
        def time_range(info_dict, ydl):
            yield (start_time or 0, end_time or float('inf'))
        ydl_opts['download_ranges'] = time_range

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug("Calling extract_info on query...")
            info = ydl.extract_info(query, download=True)
            
            if info is None:
                logger.error("extract_info returned None. YouTube blocked the request or the query was invalid.")
                raise ValueError("No video information retrieved. YouTube block or invalid link.")

            if 'entries' in info:
                logger.debug("Unwrapping entries from playlist format response")
                info = info['entries'][0]
            
            # If the video was skipped by our filter, no file was downloaded
            if not info or (not info.get('requested_downloads') and not ydl.prepare_filename(info)):
                 raise ValueError("Download skipped. Ensure the video is not a livestream.")
                 
            # Find the output path
            if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                final_path = info['requested_downloads'][0]['filepath']
            else:
                original_path = ydl.prepare_filename(info)
                # Ensure the file actually exists, if it doesn't, it was skipped
                if not os.path.exists(original_path) and not os.path.exists(os.path.splitext(original_path)[0] + '.mp3'):
                     raise ValueError("The video is too long (over 10 minutes) and was skipped to save bandwidth.")
                
                base_name, _ = os.path.splitext(original_path)
                final_path = base_name + '.mp3'
                
            return final_path
            
    except Exception as e:
        logger.exception("An error occurred during yt-dlp download: %s", e)
        raise e

def clean_title_for_search(title: str) -> str:
    """Removes common video tags from titles to improve iTunes search."""
    clean = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    clean = re.sub(r'(?i)\b(official|video|lyrics|lyric|audio|visualizer|music|hd|4k|remaster|remastered)\b', '', clean)
    return clean.strip().replace(' - ', ' ')

def download_audio_to_mp3(url: str, output_dir: str = DEFAULT_DOWNLOAD_DIR, start_time: int = None, end_time: int = None) -> str:
    """
    Downloads audio from the given URL and converts it to an MP3 file.
    Routes Spotify/Apple Music to a YouTube search, and uses yt-dlp directly for others.
    Returns the absolute path to the downloaded MP3.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    search_query = None
    clean_title = None

    if 'spotify.com' in url or 'spotify.link' in url:
        clean_title = extract_spotify_title(url)
        if clean_title:
            search_query = clean_title
            
    elif 'apple.com' in url:
        clean_title = extract_applemusic_title(url)
        if clean_title:
            search_query = clean_title
            
    else:
        # Smart Match for YouTube/Generic URLs
        logger.info("Analyzing URL for smart matching...")
        try:
            ydl_opts_meta = {
                'quiet': True,
                'no_warnings': True,
            }
            if os.path.exists(COOKIES_FILE):
                ydl_opts_meta['cookiefile'] = COOKIES_FILE
            else:
                # If no cookies are provided, attempt to use client spoofing as a fallback
                ydl_opts_meta['extractor_args'] = {
                    'youtube': {
                        'player_client': ['web', 'ios', 'android'],
                    }
                }
            with yt_dlp.YoutubeDL(ydl_opts_meta) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    logger.warning("Smart match extract_info returned None. Skipping lookup.")
                    raise ValueError("No metadata retrieved during smart match lookup.")

                # 1. Try YouTube's official music metadata
                if info.get('track') and info.get('artist'):
                    clean_title = f"{info['artist']} {info['track']}"
                    logger.info("YouTube Content ID matched: %s", clean_title)
                    search_query = clean_title
                else:
                    # 2. Clean the video title and verify against iTunes API
                    title = info.get('title', '')
                    cleaned = clean_title_for_search(title)
                    logger.debug("Cleaned title for lookup: %s", cleaned)
                    
                    itunes_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(cleaned)}&entity=song&limit=1"
                    resp = requests.get(itunes_url, timeout=5).json()
                    
                    if resp['resultCount'] > 0:
                        track = resp['results'][0]
                        clean_title = f"{track['artistName']} {track['trackName']}"
                        logger.info("iTunes verified match: %s", clean_title)
                        search_query = clean_title
                    else:
                        logger.info("No iTunes match found. Proceeding with direct download.")
        except Exception as e:
            logger.warning("Smart match failed, falling back to direct download: %s", e)

    if search_query:
        # Download the OFFICIAL audio instead of a potentially bad lyrical/visualizer video
        yt_search = f"ytsearch1:{search_query} official audio"
        filepath = download_with_ytdlp(yt_search, output_dir, start_time, end_time)
        # Apply pristine iTunes tags to the file
        apply_id3_tags(filepath, clean_title)
        return filepath
    else:
        # Complete fallback (e.g., it's a vlog, a podcast, or unrecognized song)
        filepath = download_with_ytdlp(url, output_dir, start_time, end_time)
        return filepath
