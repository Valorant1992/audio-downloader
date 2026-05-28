import argparse
from downloader import download_audio_to_mp3

def main():
    parser = argparse.ArgumentParser(description="Download audio from a URL and save it as an MP3.")
    parser.add_argument(
        'url', 
        type=str, 
        nargs='?', # Make it optional so we can fallback to prompt
        help='The URL of the video or audio to download'
    )
    
    args = parser.parse_args()

    # If URL is not provided as an argument, prompt the user for it
    url = args.url
    if not url:
        try:
            url = input("Please enter the URL to download: ").strip()
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return

    if not url:
        print("No URL provided. Exiting.")
        return

    print("--- URL to MP3 Downloader ---")
    download_audio_to_mp3(url)

if __name__ == "__main__":
    main()
