"""
Podcast RSS feed parser and episode downloader.
"""

import feedparser
import requests
import os
from datetime import datetime
from typing import List, Dict, Optional


class PodcastEpisode:
    """Represents a podcast episode."""
    
    def __init__(self, title: str, link: str, published: datetime, media_url: str):
        self.title = title
        self.link = link
        self.published = published
        self.media_url = media_url
    
    def __repr__(self):
        return f"PodcastEpisode(title='{self.title}', published={self.published})"


class PodcastFetcher:
    """Fetches and manages podcast episodes from RSS feeds."""
    
    def __init__(self, download_directory: str = "./downloads"):
        """
        Initialize podcast fetcher.
        
        Args:
            download_directory: Directory to save downloaded episodes
        """
        self.download_directory = download_directory
        os.makedirs(download_directory, exist_ok=True)
    
    def get_latest_episode(self, rss_url: str) -> Optional[PodcastEpisode]:
        """
        Get the latest episode from an RSS feed.
        
        Args:
            rss_url: URL of the RSS feed
            
        Returns:
            PodcastEpisode object or None if no episode found
        """
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                print(f"Warning: RSS feed parsing issue: {feed.bozo_exception}")
            
            if not feed.entries:
                print(f"No entries found in RSS feed: {rss_url}")
                return None
            
            # Get the first (latest) entry
            entry = feed.entries[0]
            
            # Extract title
            title = entry.get('title', 'Untitled')
            
            # Extract link
            link = entry.get('link', '')
            
            # Extract published date
            published = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])
            
            # Extract media URL (MP3)
            media_url = None
            
            # Try different ways to get the media URL
            if hasattr(entry, 'links'):
                for link_obj in entry.links:
                    if link_obj.get('type', '').startswith('audio/'):
                        media_url = link_obj.get('href', '')
                        break
                    elif link_obj.get('rel') == 'enclosure':
                        media_url = link_obj.get('href', '')
                        break
            
            # Fallback: check for enclosures
            if not media_url and hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        media_url = enclosure.get('href', '')
                        break
            
            # Fallback: check for media_content
            if not media_url and hasattr(entry, 'media_content'):
                for media in entry.media_content:
                    if media.get('type', '').startswith('audio/'):
                        media_url = media.get('url', '')
                        break
            
            if not media_url:
                print(f"No media URL found for episode: {title}")
                return None
            
            return PodcastEpisode(title, link, published, media_url)
            
        except Exception as e:
            print(f"Error fetching RSS feed {rss_url}: {e}")
            return None
    
    def download_episode(self, episode: PodcastEpisode, podcast_name: str) -> Optional[str]:
        """
        Download a podcast episode to the download directory.
        
        Args:
            episode: PodcastEpisode to download
            podcast_name: Name of the podcast (used for directory structure)
            
        Returns:
            Path to downloaded file or None if download failed
        """
        try:
            # Create podcast-specific directory
            podcast_dir = os.path.join(self.download_directory, podcast_name)
            os.makedirs(podcast_dir, exist_ok=True)
            
            # Generate filename from episode title and date
            safe_title = "".join(c for c in episode.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:100]  # Limit length
            date_str = episode.published.strftime('%Y-%m-%d')
            filename = f"{date_str}_{safe_title}.mp3"
            
            # Clean filename
            filename = filename.replace(' ', '_')
            filepath = os.path.join(podcast_dir, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                print(f"Episode already downloaded: {filepath}")
                return filepath
            
            # Download the file
            print(f"Downloading: {episode.title}")
            print(f"URL: {episode.media_url}")
            
            response = requests.get(episode.media_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get file size for progress
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}%", end='', flush=True)
            
            print(f"\nDownloaded: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error downloading episode: {e}")
            return None
    
    def get_and_download_latest(self, podcast_name: str, rss_url: str) -> Optional[str]:
        """
        Get the latest episode and download it.
        
        Args:
            podcast_name: Name of the podcast
            rss_url: URL of the RSS feed
            
        Returns:
            Path to downloaded file or None if failed
        """
        episode = self.get_latest_episode(rss_url)
        if episode:
            print(f"\nLatest episode: {episode.title}")
            print(f"Published: {episode.published}")
            return self.download_episode(episode, podcast_name)
        return None


if __name__ == "__main__":
    # Test the podcast fetcher
    fetcher = PodcastFetcher()
    
    # Test with This Week in Tech
    rss_url = "https://feeds.twit.tv/twit.xml"
    print(f"Fetching latest episode from: {rss_url}")
    
    filepath = fetcher.get_and_download_latest("This Week in Tech", rss_url)
    if filepath:
        print(f"Successfully downloaded to: {filepath}")
    else:
        print("Failed to download episode")

