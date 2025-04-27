import requests

# Pixabay Music API (Free)
def search_pixabay_music(api_key, query, per_page=10):
    url = f"https://pixabay.com/api/audio/?key={api_key}&q={query}&per_page={per_page}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                'title': hit['tags'],
                'url': hit['audio'],
                'duration': hit['duration'],
                'user': hit['user']
            }
            for hit in data.get('hits', [])
        ]
    except Exception as e:
        print(f"[DIAG] Pixabay music fetch failed: {e}")
        return []

# YouTube Audio Library Trending (Scraping, since no public API)
def fetch_youtube_audio_library_trending():
    # NOTE: No official public API. For demo, return a static list or instruct user to download from YT Audio Library
    # https://www.youtube.com/audiolibrary/music
    return [
        {'title': 'Dreams', 'url': 'https://www.youtube.com/audiolibrary_download?vid=12345'},
        {'title': 'Epic Journey', 'url': 'https://www.youtube.com/audiolibrary_download?vid=67890'}
    ]

# Epidemic Sound (Paid, requires user to download manually)
def epidemic_sound_note():
    return "Epidemic Sound is paid and requires login. Please download manually from https://www.epidemicsound.com/music/ and upload."
