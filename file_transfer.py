"""
File transfer module for copying MP3 files to Shokz OpenSwim headphones.
"""

import os
import shutil
from typing import Optional, List
from pathlib import Path


class FileTransfer:
    """Handles file transfer to Shokz OpenSwim storage."""
    
    def __init__(self, device_mount_point: str, music_directory: str = "MUSIC"):
        """
        Initialize file transfer.
        
        Args:
            device_mount_point: Mount point of the Shokz device
            music_directory: Directory on device where music should be stored
        """
        self.device_mount_point = device_mount_point
        self.music_directory = music_directory
        self.device_music_path = os.path.join(device_mount_point, music_directory)
    
    def ensure_music_directory(self) -> bool:
        """
        Ensure the music directory exists on the device.
        
        Returns:
            True if directory exists or was created successfully
        """
        # Check mount status
        mount_info = self._get_mount_info()
        if mount_info:
            if mount_info.get('read_only'):
                print(f"Device is mounted READ-ONLY: {self.device_mount_point}")
                print(f"  Device: {mount_info.get('device', 'unknown')}")
                print(f"  Filesystem: {mount_info.get('fstype', 'unknown')}")
                print("  The device cannot be written to in its current state")
                print("  Check device documentation or try unmounting and remounting")
                return False
        
        # Check if we have write permissions
        # Try a test write first (more reliable than os.access for mounted filesystems)
        can_write = False
        test_file = os.path.join(self.device_mount_point, '.syncnswim_write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            can_write = True
        except (PermissionError, OSError) as e:
            can_write = False
            print(f"Cannot write to device mount point: {self.device_mount_point}")
            print(f"  Test write failed: {e}")
            print(f"  Current user: {os.getenv('USER', 'unknown')}")
            print(f"  Current UID: {os.getuid()}")
            
            # Check mount info for owner info
            if mount_info:
                print(f"  Device: {mount_info.get('device', 'unknown')}")
                print(f"  Filesystem: {mount_info.get('fstype', 'unknown')}")
                print(f"  Mount options: {mount_info.get('options', 'unknown')}")
                # Check if uid/gid are set in mount options
                options = mount_info.get('options', '')
                if 'uid=' in options or 'gid=' in options:
                    print(f"  Note: Mount has uid/gid specified in options")
            
            # Check if running as root would help
            if os.getuid() != 0:
                print("\n  Options:")
                print("    1. Check if mount point directory permissions allow write")
                print("    2. Verify with: ls -ld '/media/raspberry/SWIM PRO'")
                print("    3. Try: sudo chmod 755 '/media/raspberry/SWIM PRO'")
                print("    4. Check device documentation for write access requirements")
            return False
        
        if not can_write:
            return False
        
        try:
            if os.path.exists(self.device_music_path):
                if not os.access(self.device_music_path, os.W_OK):
                    print(f"No write permission on music directory: {self.device_music_path}")
                    return False
                return True
            
            os.makedirs(self.device_music_path, exist_ok=True)
            print(f"Created music directory: {self.device_music_path}")
            return True
        except PermissionError:
            print(f"Permission denied creating directory: {self.device_music_path}")
            print(f"  Mount point: {self.device_mount_point}")
            mount_info = self._get_mount_info()
            if mount_info and mount_info.get('read_only'):
                print("  Device is mounted read-only")
            else:
                print("  You may need to run with sudo, or check device/filesystem permissions")
            return False
        except Exception as e:
            print(f"Error creating music directory: {e}")
            return False
    
    def _get_mount_info(self) -> Optional[dict]:
        """Get mount information for the device."""
        try:
            # Check mount options from /proc/mounts
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        device = parts[0]
                        mountpoint = parts[1]
                        fstype = parts[2]
                        options = parts[3]
                        
                        # Normalize mountpoint (handle spaces/encoding)
                        normalized_mountpoint = mountpoint.replace('\\040', ' ').replace('\\x20', ' ')
                        normalized_our_mount = self.device_mount_point.replace('\\040', ' ').replace('\\x20', ' ')
                        
                        if normalized_mountpoint == normalized_our_mount or mountpoint == self.device_mount_point:
                            return {
                                'device': device,
                                'mountpoint': mountpoint,
                                'fstype': fstype,
                                'options': options,
                                'read_only': 'ro' in options.split(',')
                            }
        except Exception:
            pass
        
        return None
    
    def _is_mount_writable(self) -> bool:
        """Check if the mount point is writable (not read-only)."""
        mount_info = self._get_mount_info()
        if mount_info:
            return not mount_info.get('read_only', False)
        
        # If not found in /proc/mounts, assume writable
        return True
    
    def get_device_free_space(self) -> Optional[int]:
        """
        Get free space on device in bytes.
        
        Returns:
            Free space in bytes or None if error
        """
        try:
            stat = os.statvfs(self.device_mount_point)
            free_space = stat.f_bavail * stat.f_frsize
            return free_space
        except Exception as e:
            print(f"Error getting free space: {e}")
            return None
    
    def get_file_size(self, filepath: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(filepath)
        except Exception:
            return 0
    
    def file_exists_on_device(self, filename: str) -> bool:
        """
        Check if a file already exists on the device.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists
        """
        device_file_path = os.path.join(self.device_music_path, filename)
        return os.path.exists(device_file_path)
    
    def copy_file(self, source_file: str, destination_filename: Optional[str] = None) -> Optional[str]:
        """
        Copy a file to the device.
        
        Args:
            source_file: Path to source file
            destination_filename: Optional custom filename on device (defaults to source filename)
            
        Returns:
            Path to copied file on device or None if failed
        """
        if not os.path.exists(source_file):
            print(f"Source file does not exist: {source_file}")
            return None
        
        if not self.ensure_music_directory():
            return None
        
        # Use source filename if destination not specified
        if destination_filename is None:
            destination_filename = os.path.basename(source_file)
        
        # Sanitize filename for device compatibility
        destination_filename = self._sanitize_filename(destination_filename)
        
        destination_path = os.path.join(self.device_music_path, destination_filename)
        
        # Check if file already exists
        if os.path.exists(destination_path):
            print(f"File already exists on device: {destination_filename}")
            # Check if sizes match
            if os.path.getsize(source_file) == os.path.getsize(destination_path):
                print("Files are identical, skipping copy")
                return destination_path
            else:
                print("File exists but size differs, will overwrite")
        
        # Check free space
        free_space = self.get_device_free_space()
        file_size = self.get_file_size(source_file)
        
        if free_space is not None and file_size > free_space:
            print(f"Not enough free space on device: {file_size} bytes needed, {free_space} bytes available")
            return None
        
        try:
            print(f"Copying {os.path.basename(source_file)} to device...")
            shutil.copy2(source_file, destination_path)
            print(f"✓ Successfully copied to: {destination_path}")
            return destination_path
        except PermissionError:
            print(f"Permission denied copying to: {destination_path}")
            return None
        except Exception as e:
            print(f"Error copying file: {e}")
            return None
    
    def copy_files(self, source_files: List[str]) -> List[str]:
        """
        Copy multiple files to the device.
        
        Args:
            source_files: List of source file paths
            
        Returns:
            List of successfully copied file paths
        """
        copied_files = []
        
        for source_file in source_files:
            result = self.copy_file(source_file)
            if result:
                copied_files.append(result)
        
        return copied_files
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for device compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace characters that might cause issues on various filesystems
        # Keep alphanumeric, spaces, hyphens, underscores, dots
        sanitized = "".join(c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in filename)
        
        # Limit length (many filesystems have 255 char limit)
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:200 - len(ext)] + ext
        
        return sanitized
    
    def list_device_files(self) -> List[str]:
        """
        List all files currently on the device.
        
        Returns:
            List of filenames
        """
        files = []
        
        if not os.path.exists(self.device_music_path):
            return files
        
        try:
            for item in os.listdir(self.device_music_path):
                item_path = os.path.join(self.device_music_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
        except PermissionError:
            print("Permission denied listing device files")
        except Exception as e:
            print(f"Error listing device files: {e}")
        
        return files


if __name__ == "__main__":
    # Test the file transfer
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: file_transfer.py <device_mount_point> [source_file]")
        sys.exit(1)
    
    device_mount = sys.argv[1]
    
    transfer = FileTransfer(device_mount)
    
    print(f"Device mount point: {device_mount}")
    print(f"Music directory: {transfer.device_music_path}")
    
    free_space = transfer.get_device_free_space()
    if free_space:
        print(f"Free space: {free_space / (1024*1024):.2f} MB")
    
    existing_files = transfer.list_device_files()
    print(f"\nExisting files ({len(existing_files)}):")
    for f in existing_files[:10]:  # Show first 10
        print(f"  - {f}")
    if len(existing_files) > 10:
        print(f"  ... and {len(existing_files) - 10} more")
    
    if len(sys.argv) >= 3:
        source_file = sys.argv[2]
        result = transfer.copy_file(source_file)
        if result:
            print(f"\n✓ File copied successfully: {result}")
        else:
            print("\n✗ File copy failed")

