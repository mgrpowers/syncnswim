"""
Music file selection and management module.
Randomly selects music files from a source directory.
"""

import os
import random
import json
from pathlib import Path
from typing import List, Optional


class MusicSelector:
    """Handles random selection of music files from a source directory."""
    
    # Common audio file extensions
    AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.aac', '.flac', '.ogg', '.wav', '.wma', '.opus'}
    
    def __init__(self, source_directory: str, count: int = 20):
        """
        Initialize music selector.
        
        Args:
            source_directory: Directory to search for music files (searched recursively)
            count: Number of random songs to select (default: 20)
        """
        self.source_directory = source_directory
        self.count = count
    
    def find_all_music_files(self) -> List[str]:
        """
        Recursively find all music files in the source directory.
        
        Returns:
            List of full paths to music files
        """
        music_files = []
        
        if not self.source_directory or not os.path.exists(self.source_directory):
            return music_files
        
        try:
            for root, dirs, files in os.walk(self.source_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Check if it's an audio file
                    if Path(file).suffix.lower() in self.AUDIO_EXTENSIONS:
                        music_files.append(file_path)
        except Exception as e:
            print(f"Error scanning music directory: {e}")
        
        return music_files
    
    def select_random_songs(self) -> List[str]:
        """
        Randomly select the specified number of songs from the source directory.
        
        Returns:
            List of file paths to selected songs
        """
        all_files = self.find_all_music_files()
        
        if not all_files:
            print(f"No music files found in: {self.source_directory}")
            return []
        
        if len(all_files) <= self.count:
            print(f"Found {len(all_files)} music file(s), selecting all")
            return all_files
        
        selected = random.sample(all_files, self.count)
        print(f"Found {len(all_files)} music files, randomly selected {len(selected)}")
        return selected
    
    def save_selected_files_list(self, device_mount_point: str, file_paths: List[str]) -> bool:
        """
        Save list of selected files to a metadata file on the device.
        
        Args:
            device_mount_point: Mount point of the device
            file_paths: List of file paths that were copied
            
        Returns:
            True if saved successfully
        """
        metadata_file = os.path.join(device_mount_point, '.syncnswim_music.json')
        
        try:
            # Store just the filenames (not full paths) for deletion tracking
            filenames = [os.path.basename(path) for path in file_paths]
            
            data = {
                'files': filenames,
                'count': len(filenames)
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving music metadata: {e}")
            return False
    
    def load_selected_files_list(self, device_mount_point: str) -> List[str]:
        """
        Load list of previously selected files from metadata file.
        
        Args:
            device_mount_point: Mount point of the device
            
        Returns:
            List of filenames that were previously added
        """
        metadata_file = os.path.join(device_mount_point, '.syncnswim_music.json')
        
        if not os.path.exists(metadata_file):
            return []
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
            
            return data.get('files', [])
        except Exception as e:
            print(f"Error loading music metadata: {e}")
            return []


if __name__ == "__main__":
    # Test the music selector
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: music_selector.py <source_directory> [count]")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    
    selector = MusicSelector(source_dir, count)
    
    print(f"Scanning: {source_dir}")
    all_files = selector.find_all_music_files()
    print(f"Found {len(all_files)} music files\n")
    
    if all_files:
        selected = selector.select_random_songs()
        print(f"\nSelected {len(selected)} files:")
        for f in selected:
            print(f"  - {os.path.basename(f)}")

