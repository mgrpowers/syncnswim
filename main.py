#!/usr/bin/env python3
"""
Main application for syncnswim - Sync podcasts when Shokz OpenSwim headphones storage is mounted.
"""

import sys
import time
import os
from config_manager import ConfigManager
from podcast_fetcher import PodcastFetcher
from storage_detector import StorageDetector
from file_transfer import FileTransfer
from music_selector import MusicSelector


class SyncNSwimApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.config_manager = ConfigManager()
        self.podcast_fetcher = PodcastFetcher(
            download_directory=self.config_manager.get_download_directory()
        )
        self.storage_detector = StorageDetector(
            device_name=self.config_manager.get_shokz_device_name()
        )
        self.last_storage_state = False
        self.file_transfer = None
    
    def sync_episodes(self):
        """Sync podcasts when storage device is mounted."""
        print(f"\n{'='*60}")
        print(f"Storage device detected: {self.config_manager.get_shokz_device_name()}")
        print(f"{'='*60}\n")
        
        mount_point = self.storage_detector.find_device_mount_point()
        
        if not mount_point:
            print("\n✗ Storage device not found")
            print(f"  Looking for device matching: '{self.config_manager.get_shokz_device_name()}'")
            print("  Make sure the headphones are connected via USB and mounted as a disk drive")
            print("  Run 'python3 storage_detector.py' to see all mounted devices for debugging")
            return
        
        print(f"✓ Storage device found at: {mount_point}\n")
        
        # Initialize file transfer
        self.file_transfer = FileTransfer(
            device_mount_point=mount_point,
            music_directory=self.config_manager.get_device_music_directory()
        )
        
        # Check mount status and permissions
        mount_info = self.file_transfer._get_mount_info()
        if mount_info:
            print(f"Mount info: {mount_info.get('device', 'unknown')} ({mount_info.get('fstype', 'unknown')})")
            if mount_info.get('read_only'):
                print("  WARNING: Device is mounted READ-ONLY")
            else:
                print("  Mount status: Read-Write")
        print()
        
        # Check free space
        free_space = self.file_transfer.get_device_free_space()
        if free_space:
            print(f"Device free space: {free_space / (1024*1024):.2f} MB\n")
        
        # Sync music files if configured
        music_source_dir = self.config_manager.get_music_source_directory()
        if music_source_dir:
            self.sync_random_music(mount_point)
        
        # Clean up old podcast files if configured (only if not using music sync)
        if not music_source_dir:
            cleanup_days = self.config_manager.get_cleanup_days()
            print(f"Cleaning up files older than {cleanup_days} days...")
            deleted_count = self.file_transfer.cleanup_old_files(days=cleanup_days)
            if deleted_count > 0:
                print(f"✓ Deleted {deleted_count} old file(s)\n")
            else:
                print("  No old files to delete\n")
        
        # Fetch and transfer latest podcast episodes
        self.fetch_and_transfer_episodes()
    
    def fetch_and_transfer_episodes(self):
        """Fetch and transfer latest episodes for all enabled podcasts."""
        if not self.file_transfer:
            print("Error: File transfer not initialized")
            return
        
        enabled_podcasts = self.config_manager.get_enabled_podcasts()
        
        if not enabled_podcasts:
            print("No enabled podcasts configured.")
            return
        
        print(f"Fetching and transferring latest episodes for {len(enabled_podcasts)} podcast(s)...\n")
        
        downloaded_files = []
        
        for podcast in enabled_podcasts:
            name = podcast.get("name", "Unknown")
            rss_url = podcast.get("rss_url")
            
            if not rss_url:
                print(f"Skipping {name}: No RSS URL configured")
                continue
            
            print(f"Processing: {name}")
            try:
                # Download to local directory first
                local_filepath = self.podcast_fetcher.get_and_download_latest(name, rss_url)
                
                if local_filepath and os.path.exists(local_filepath):
                    # Transfer to device
                    print(f"Transferring to device...")
                    device_filepath = self.file_transfer.copy_file(local_filepath)
                    
                    if device_filepath:
                        downloaded_files.append(device_filepath)
                        print(f"✓ Successfully transferred: {name}\n")
                    else:
                        print(f"✗ Failed to transfer: {name}\n")
                else:
                    print(f"✗ Failed to download: {name}\n")
                    
            except Exception as e:
                print(f"✗ Error processing {name}: {e}\n")
        
        if downloaded_files:
            print(f"\n{'='*60}")
            print(f"✓ Successfully transferred {len(downloaded_files)} episode(s) to device")
            print(f"{'='*60}\n")
    
    def sync_random_music(self, mount_point: str):
        """Sync random music files to the device."""
        music_source_dir = self.config_manager.get_music_source_directory()
        song_count = self.config_manager.get_random_songs_count()
        
        if not music_source_dir or not os.path.exists(music_source_dir):
            print(f"Music source directory not configured or doesn't exist: {music_source_dir}")
            return
        
        print(f"\n{'='*60}")
        print(f"Syncing {song_count} random songs from: {music_source_dir}")
        print(f"{'='*60}\n")
        
        # Initialize music selector
        selector = MusicSelector(music_source_dir, song_count)
        
        # Load list of previously added files
        previous_files = selector.load_selected_files_list(mount_point)
        
        # Delete previous batch
        if previous_files:
            print(f"Removing previous batch ({len(previous_files)} files)...")
            deleted_count = 0
            for filename in previous_files:
                file_path = os.path.join(mount_point, filename)
                try:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"  Error deleting {filename}: {e}")
            
            print(f"✓ Deleted {deleted_count} file(s) from previous batch\n")
        
        # Select random songs
        selected_files = selector.select_random_songs()
        
        if not selected_files:
            print("No music files to sync\n")
            return
        
        # Copy selected files to device
        print(f"Copying {len(selected_files)} files to device...\n")
        copied_files = []
        
        for source_file in selected_files:
            filename = os.path.basename(source_file)
            try:
                destination = self.file_transfer.copy_file(source_file, destination_filename=filename)
                if destination:
                    copied_files.append(source_file)
                    print(f"✓ {filename}\n")
                else:
                    print(f"✗ Failed to copy: {filename}\n")
            except Exception as e:
                print(f"✗ Error copying {filename}: {e}\n")
        
        # Save list of copied files for next sync
        if copied_files:
            selector.save_selected_files_list(mount_point, copied_files)
            print(f"\n{'='*60}")
            print(f"✓ Successfully synced {len(copied_files)} song(s) to device")
            print(f"{'='*60}\n")
    
    def run(self):
        """Run the application."""
        print("="*60)
        print("SyncNSwim - Podcast Sync for Shokz OpenSwim Headphones")
        print("="*60)
        print(f"\nMonitoring for storage device: {self.config_manager.get_shokz_device_name()}")
        print(f"Download directory: {self.config_manager.get_download_directory()}")
        music_dir = self.config_manager.get_device_music_directory()
        if music_dir:
            print(f"Device music directory: {music_dir}")
        else:
            print(f"Device music directory: root (files stored at device root)")
        
        # Show music sync configuration
        music_source = self.config_manager.get_music_source_directory()
        if music_source:
            song_count = self.config_manager.get_random_songs_count()
            print(f"\nMusic sync: {song_count} random songs from: {music_source}")
        
        enabled_podcasts = self.config_manager.get_enabled_podcasts()
        if enabled_podcasts:
            print(f"\nEnabled podcasts ({len(enabled_podcasts)}):")
            for podcast in enabled_podcasts:
                print(f"  • {podcast['name']}")
        
        print("\nPress Ctrl+C to stop\n")
        
        # Check initial state
        initial_state = self.storage_detector.is_device_mounted()
        self.last_storage_state = initial_state
        
        if initial_state:
            print(f"Storage device is already mounted.")
            print("Syncing latest episodes...\n")
            self.sync_episodes()
            print("\nMonitoring for unmount/remount...\n")
        
        # Start monitoring
        try:
            check_interval = 5.0
            check_count = 0
            while True:
                check_count += 1
                current_state = self.storage_detector.is_device_mounted()
                
                if current_state != self.last_storage_state:
                    if current_state:
                        # Device just mounted
                        print(f"\n[Monitor] Storage device mounted (check #{check_count})")
                        self.sync_episodes()
                    else:
                        # Device just unmounted
                        print(f"\n[Monitor] Storage device unmounted (check #{check_count})\n")
                        self.file_transfer = None
                    
                    self.last_storage_state = current_state
                elif check_count % 12 == 0:  # Every ~60 seconds (12 checks * 5s)
                    # Periodic status update when device is not mounted
                    if not current_state:
                        print(f"[Monitor] Still waiting for device... (check #{check_count}, ~{check_count * check_interval / 60:.0f} min elapsed)")
                
                time.sleep(check_interval)
        except KeyboardInterrupt:
            print("\n\nApplication stopped by user.")
            sys.exit(0)


def main():
    """Entry point."""
    app = SyncNSwimApp()
    app.run()


if __name__ == "__main__":
    main()
