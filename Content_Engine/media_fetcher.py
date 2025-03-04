import os
import requests
import json
import random
from PIL import Image
from io import BytesIO
import logging
from config_loader import load_config

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='./logs/media_fetcher.log')
logger = logging.getLogger('media_fetcher')


class MediaFetcher:
    def __init__(self, config=None):
        self.config = config if config else load_config()
        self.temp_dir = self.config['project']['temp_dir']
        self.setup_directories()

    def setup_directories(self):
        """Ensure all necessary directories exist."""
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.config['project']['output_dir'], exist_ok=True)

    def fetch_media_for_keywords(self, keywords, media_type="image"):
        """
        Fetch media based on keywords

        Args:
            keywords (list): List of keywords to search for
            media_type (str): Type of media to fetch ('image' or 'video')

        Returns:
            str: Path to downloaded media file
        """
        mode = self.config['media']['mode']

        if mode == "manual":
            # If in manual mode, return a random local file
            return self.get_random_local_media(media_type)

        # Try each enabled API in order
        if self.config['sources']['pixabay']['enabled']:
            media_path = self.fetch_from_pixabay(keywords, media_type)
            if media_path:
                return media_path

        if self.config['sources']['pexels']['enabled']:
            media_path = self.fetch_from_pexels(keywords, media_type)
            if media_path:
                return media_path

        if self.config['sources']['unsplash']['enabled']:
            media_path = self.fetch_from_unsplash(keywords, media_type)
            if media_path:
                return media_path

        # Fallback to local media if all APIs fail
        logger.warning(f"All API fetches failed for keywords: {keywords}. Using local media.")
        return self.get_random_local_media(media_type)

    def fetch_from_pixabay(self, keywords, media_type):
        """Fetch media from Pixabay API."""
        api_key = self.config['sources']['pixabay']['api_key']
        if not api_key or api_key == "YOUR_PIXABAY_API_KEY":
            logger.warning("Pixabay API key not set or invalid")
            return None

        # Prepare search query
        query = '+'.join(keywords)
        image_type = self.config['sources']['pixabay']['image_type']
        orientation = self.config['sources']['pixabay']['orientation']
        min_width = self.config['sources']['pixabay']['min_width']
        min_height = self.config['sources']['pixabay']['min_height']

        # Build URL
        url = f"https://pixabay.com/api/"
        if media_type == "video":
            url = f"https://pixabay.com/api/videos/"

        params = {
            'key': api_key,
            'q': query,
            'image_type': image_type,
            'orientation': orientation,
            'min_width': min_width,
            'min_height': min_height,
            'per_page': 10
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if 'hits' in data and len(data['hits']) > 0:
                # Get a random result from the top 10
                hit = random.choice(data['hits'][:10])

                if media_type == "image":
                    image_url = hit['largeImageURL']
                    return self.download_file(image_url, 'image')
                else:  # video
                    video_url = hit['videos']['large']['url']
                    return self.download_file(video_url, 'video')
            else:
                logger.warning(f"No results found in Pixabay for keywords: {keywords}")
                return None

        except Exception as e:
            logger.error(f"Error fetching from Pixabay: {str(e)}")
            return None

    def fetch_from_pexels(self, keywords, media_type):
        """Fetch media from Pexels API."""
        api_key = self.config['sources']['pexels']['api_key']
        if not api_key or api_key == "YOUR_PEXELS_API_KEY":
            logger.warning("Pexels API key not set or invalid")
            return None

        # Prepare search query
        query = ' '.join(keywords)
        orientation = self.config['sources']['pexels']['orientation']

        # Build header and URL
        headers = {
            'Authorization': api_key
        }

        if media_type == "image":
            url = f"https://api.pexels.com/v1/search?query={query}&orientation={orientation}&per_page=10"
        else:  # video
            url = f"https://api.pexels.com/videos/search?query={query}&orientation={orientation}&per_page=10"

        try:
            response = requests.get(url, headers=headers)
            data = response.json()

            if media_type == "image" and 'photos' in data and len(data['photos']) > 0:
                # Get a random result from the top 10
                photo = random.choice(data['photos'][:10])
                image_url = photo['src']['original']
                return self.download_file(image_url, 'image')

            elif media_type == "video" and 'videos' in data and len(data['videos']) > 0:
                # Get a random result from the top 10
                video = random.choice(data['videos'][:10])
                video_files = video['video_files']
                # Get the highest quality video
                video_file = max(video_files, key=lambda x: x.get('width', 0) if x.get('width', 0) <= 1920 else 0)
                video_url = video_file['link']
                return self.download_file(video_url, 'video')
            else:
                logger.warning(f"No results found in Pexels for keywords: {keywords}")
                return None

        except Exception as e:
            logger.error(f"Error fetching from Pexels: {str(e)}")
            return None

    def fetch_from_unsplash(self, keywords, media_type):
        """Fetch images from Unsplash API."""
        if media_type == "video":
            # Unsplash doesn't provide videos
            return None

        api_key = self.config['sources']['unsplash']['api_key']
        if not api_key or api_key == "YOUR_UNSPLASH_API_KEY":
            logger.warning("Unsplash API key not set or invalid")
            return None

        # Prepare search query
        query = ' '.join(keywords)
        orientation = self.config['sources']['unsplash']['orientation']

        # Build URL
        url = f"https://api.unsplash.com/search/photos?query={query}&orientation={orientation}&per_page=10"
        headers = {
            'Authorization': f"Client-ID {api_key}"
        }

        try:
            response = requests.get(url, headers=headers)
            data = response.json()

            if 'results' in data and len(data['results']) > 0:
                # Get a random result from the top 10
                photo = random.choice(data['results'][:10])
                image_url = photo['urls']['raw']
                return self.download_file(image_url, 'image')
            else:
                logger.warning(f"No results found in Unsplash for keywords: {keywords}")
                return None

        except Exception as e:
            logger.error(f"Error fetching from Unsplash: {str(e)}")
            return None

    def get_random_local_media(self, media_type):
        """Get a random media file from local assets."""
        if media_type == "image":
            path = self.config['sources']['local']['paths']['images']
        else:  # video
            path = self.config['sources']['local']['paths']['videos']

        try:
            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            if not files:
                logger.warning(f"No local {media_type} files found in {path}")
                return None

            random_file = random.choice(files)
            return os.path.join(path, random_file)
        except Exception as e:
            logger.error(f"Error getting local {media_type}: {str(e)}")
            return None

    def download_file(self, url, file_type):
        """Download a file from URL and save it to temp directory."""
        try:
            response = requests.get(url, stream=True)

            if response.status_code == 200:
                # Generate a random filename
                ext = 'jpg' if file_type == 'image' else 'mp4'
                filename = f"{file_type}_{random.randint(1000, 9999)}.{ext}"
                filepath = os.path.join(self.temp_dir, filename)

                # Save the file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                logger.info(f"Successfully downloaded {file_type} to {filepath}")
                return filepath
            else:
                logger.error(f"Failed to download from {url}, status code: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading {file_type}: {str(e)}")
            return None

    def extract_keywords_from_text(self, text):
        """Extract relevant keywords from text."""
        # This is a simple implementation - consider using NLP libraries for better results
        stop_words = {"a", "an", "the", "and", "or", "but", "is", "are", "was", "were",
                      "in", "on", "at", "to", "for", "with", "by", "about", "of"}

        words = text.lower().split()
        filtered_words = [word for word in words if word not in stop_words]

        # Count word frequency
        word_count = {}
        for word in filtered_words:
            if word in word_count:
                word_count[word] += 1
            else:
                word_count[word] = 1

        # Sort by frequency and return top keywords
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, count in sorted_words[:5]]

        return keywords