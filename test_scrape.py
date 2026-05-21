import requests
import re

def test_scrape(url):
    html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
    
    # Try <title>
    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if title_match:
        print(f"Title: {title_match.group(1)}")
    
    # Try og:title
    og_match = re.search(r'og:title.*?content="(.*?)"', html, re.IGNORECASE)
    if og_match:
        print(f"OG Title: {og_match.group(1)}")

print("Spotify:")
test_scrape('https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT')
print("\nApple Music:")
test_scrape('https://music.apple.com/us/album/shape-of-you/1193701392?i=1193701399')
