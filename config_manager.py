"""
Configuration management for podcasts and settings.
"""

import json
import os
from typing import List, Dict


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._default_config()
        else:
            # Create default config file
            default = self._default_config()
            self.save_config(default)
            return default
    
    def _default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "shokz_device_name": "Shokz",
            "download_directory": "./downloads",
            "device_music_directory": "MUSIC",
            "storage_wait_timeout": 30,
            "podcasts": [
                {
                    "name": "This Week in Tech",
                    "rss_url": "https://feeds.twit.tv/twit.xml",
                    "enabled": True
                }
            ]
        }
    
    def save_config(self, config: Dict = None):
        """Save configuration to file."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get_podcasts(self) -> List[Dict]:
        """Get list of configured podcasts."""
        return self.config.get("podcasts", [])
    
    def get_enabled_podcasts(self) -> List[Dict]:
        """Get list of enabled podcasts."""
        return [p for p in self.get_podcasts() if p.get("enabled", True)]
    
    def add_podcast(self, name: str, rss_url: str, enabled: bool = True):
        """
        Add a new podcast to the configuration.
        
        Args:
            name: Podcast name
            rss_url: RSS feed URL
            enabled: Whether podcast is enabled
        """
        podcasts = self.get_podcasts()
        
        # Check if podcast already exists
        for podcast in podcasts:
            if podcast.get("rss_url") == rss_url:
                print(f"Podcast with RSS URL {rss_url} already exists")
                return
        
        podcasts.append({
            "name": name,
            "rss_url": rss_url,
            "enabled": enabled
        })
        
        self.config["podcasts"] = podcasts
        self.save_config()
    
    def remove_podcast(self, rss_url: str):
        """
        Remove a podcast from configuration.
        
        Args:
            rss_url: RSS feed URL of podcast to remove
        """
        podcasts = self.get_podcasts()
        self.config["podcasts"] = [p for p in podcasts if p.get("rss_url") != rss_url]
        self.save_config()
    
    def toggle_podcast(self, rss_url: str, enabled: bool = None):
        """
        Toggle podcast enabled/disabled state.
        
        Args:
            rss_url: RSS feed URL
            enabled: New enabled state (None to toggle)
        """
        podcasts = self.get_podcasts()
        for podcast in podcasts:
            if podcast.get("rss_url") == rss_url:
                if enabled is None:
                    podcast["enabled"] = not podcast.get("enabled", True)
                else:
                    podcast["enabled"] = enabled
                self.config["podcasts"] = podcasts
                self.save_config()
                return
    
    def get_shokz_device_name(self) -> str:
        """Get the Shokz device name to monitor."""
        return self.config.get("shokz_device_name", "Shokz")
    
    def get_download_directory(self) -> str:
        """Get the download directory path."""
        return self.config.get("download_directory", "./downloads")
    
    def get_device_music_directory(self) -> str:
        """Get the music directory name on the device."""
        return self.config.get("device_music_directory", "MUSIC")
    
    def get_storage_wait_timeout(self) -> int:
        """Get the timeout in seconds to wait for storage device."""
        return self.config.get("storage_wait_timeout", 30)


if __name__ == "__main__":
    # Test the config manager
    config = ConfigManager()
    
    print("Current podcasts:")
    for podcast in config.get_podcasts():
        print(f"  - {podcast['name']}: {podcast['rss_url']} (enabled: {podcast['enabled']})")
    
    print(f"\nShokz device name: {config.get_shokz_device_name()}")
    print(f"Download directory: {config.get_download_directory()}")

