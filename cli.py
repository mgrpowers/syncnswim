#!/usr/bin/env python3
"""
Command-line interface for managing podcasts configuration.
"""

import sys
import argparse
from config_manager import ConfigManager
from podcast_fetcher import PodcastFetcher


def list_podcasts(config_manager: ConfigManager):
    """List all configured podcasts."""
    podcasts = config_manager.get_podcasts()
    
    if not podcasts:
        print("No podcasts configured.")
        return
    
    print(f"\nConfigured Podcasts ({len(podcasts)}):\n")
    for i, podcast in enumerate(podcasts, 1):
        status = "✓ Enabled" if podcast.get("enabled", True) else "✗ Disabled"
        print(f"{i}. {podcast['name']}")
        print(f"   RSS: {podcast['rss_url']}")
        print(f"   Status: {status}\n")


def add_podcast(config_manager: ConfigManager, name: str, rss_url: str):
    """Add a new podcast."""
    try:
        config_manager.add_podcast(name, rss_url)
        print(f"✓ Added podcast: {name}")
        print(f"  RSS: {rss_url}")
    except Exception as e:
        print(f"✗ Error adding podcast: {e}")


def remove_podcast(config_manager: ConfigManager, rss_url: str):
    """Remove a podcast."""
    podcasts = config_manager.get_podcasts()
    podcast_name = None
    
    for podcast in podcasts:
        if podcast.get("rss_url") == rss_url:
            podcast_name = podcast.get("name")
            break
    
    if not podcast_name:
        print(f"✗ Podcast with RSS URL '{rss_url}' not found")
        return
    
    config_manager.remove_podcast(rss_url)
    print(f"✓ Removed podcast: {podcast_name}")


def toggle_podcast(config_manager: ConfigManager, rss_url: str, enabled: bool = None):
    """Toggle podcast enabled/disabled state."""
    podcasts = config_manager.get_podcasts()
    podcast_name = None
    
    for podcast in podcasts:
        if podcast.get("rss_url") == rss_url:
            podcast_name = podcast.get("name")
            break
    
    if not podcast_name:
        print(f"✗ Podcast with RSS URL '{rss_url}' not found")
        return
    
    config_manager.toggle_podcast(rss_url, enabled)
    new_state = "enabled" if enabled else ("disabled" if enabled is False else "toggled")
    print(f"✓ {podcast_name} {new_state}")


def test_podcast(rss_url: str):
    """Test fetching latest episode from a podcast RSS feed."""
    print(f"\nTesting RSS feed: {rss_url}\n")
    
    fetcher = PodcastFetcher(download_directory="./test_downloads")
    episode = fetcher.get_latest_episode(rss_url)
    
    if episode:
        print(f"✓ Latest episode found:")
        print(f"  Title: {episode.title}")
        print(f"  Published: {episode.published}")
        print(f"  Media URL: {episode.media_url}")
    else:
        print("✗ Failed to fetch episode from RSS feed")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage podcast configuration for SyncNSwim"
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List podcasts
    subparsers.add_parser('list', help='List all configured podcasts')
    
    # Add podcast
    add_parser = subparsers.add_parser('add', help='Add a new podcast')
    add_parser.add_argument('name', help='Podcast name')
    add_parser.add_argument('rss_url', help='RSS feed URL')
    
    # Remove podcast
    remove_parser = subparsers.add_parser('remove', help='Remove a podcast')
    remove_parser.add_argument('rss_url', help='RSS feed URL of podcast to remove')
    
    # Enable podcast
    enable_parser = subparsers.add_parser('enable', help='Enable a podcast')
    enable_parser.add_argument('rss_url', help='RSS feed URL')
    
    # Disable podcast
    disable_parser = subparsers.add_parser('disable', help='Disable a podcast')
    disable_parser.add_argument('rss_url', help='RSS feed URL')
    
    # Test podcast
    test_parser = subparsers.add_parser('test', help='Test an RSS feed')
    test_parser.add_argument('rss_url', help='RSS feed URL to test')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    config_manager = ConfigManager()
    
    if args.command == 'list':
        list_podcasts(config_manager)
    elif args.command == 'add':
        add_podcast(config_manager, args.name, args.rss_url)
    elif args.command == 'remove':
        remove_podcast(config_manager, args.rss_url)
    elif args.command == 'enable':
        toggle_podcast(config_manager, args.rss_url, enabled=True)
    elif args.command == 'disable':
        toggle_podcast(config_manager, args.rss_url, enabled=False)
    elif args.command == 'test':
        test_podcast(args.rss_url)


if __name__ == "__main__":
    main()

