"""
Storage device detection module for Shokz OpenSwim headphones.
Detects when the headphones are mounted as a storage device.
"""

import subprocess
import os
import re
from typing import Optional, List
import time


class StorageDetector:
    """Detects and manages storage device mount points."""
    
    def __init__(self, device_name: str = "Shokz"):
        """
        Initialize storage detector.
        
        Args:
            device_name: Name or identifier for the device
        """
        self.device_name = device_name
    
    def get_mount_points(self) -> List[dict]:
        """
        Get all currently mounted filesystems.
        
        Returns:
            List of dicts with 'device', 'mountpoint', 'fstype', 'label' keys
        """
        mount_points = []
        
        try:
            # Use mount command
            result = subprocess.run(
                ['mount'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # Parse mount output (format varies)
                    # Typical format: device on mountpoint type fstype (options)
                    parts = line.split()
                    if len(parts) >= 3:
                        device = parts[0]
                        mountpoint = parts[2]
                        fstype = parts[4] if len(parts) > 4 else 'unknown'
                        
                        mount_points.append({
                            'device': device,
                            'mountpoint': mountpoint,
                            'fstype': fstype
                        })
        except Exception as e:
            print(f"Error getting mount points: {e}")
        
        return mount_points
    
    def find_device_mount_point(self, device_label: Optional[str] = None) -> Optional[str]:
        """
        Find the mount point for the Shokz device.
        
        Args:
            device_label: Optional specific label to search for
            
        Returns:
            Mount point path or None if not found
        """
        # Try multiple methods to find the device (disk drives)
        print(f"[Storage Detection] Looking for device matching: '{self.device_name}'")
        
        # Method 1: Use lsblk to find all mounted disk drives (most reliable)
        try:
            print("[Storage Detection] Method 1: Checking lsblk for mounted disk drives...")
            result = subprocess.run(
                ['lsblk', '-o', 'NAME,LABEL,MOUNTPOINT,FSTYPE', '-n', '-r'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                mounted_drives = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[0]
                        label = parts[1] if parts[1] != '-' else None
                        mountpoint = parts[2] if len(parts) > 2 and parts[2] != '-' else None
                        fstype = parts[3] if len(parts) > 3 and parts[3] != '-' else None
                        
                        # Check if it's a mounted disk drive (sd* or mmcblk*)
                        if mountpoint and (name.startswith('sd') or name.startswith('mmcblk')):
                            mounted_drives.append({'name': name, 'label': label, 'mountpoint': mountpoint})
                            
                            # Check label first (most specific)
                            if label and self.device_name.lower() in label.lower():
                                print(f"[Storage Detection] ✓ Found device via label match: {mountpoint} (label: {label})")
                                return mountpoint
                            
                            # Check mountpoint name (often contains device name)
                            if self.device_name.lower() in mountpoint.lower():
                                print(f"[Storage Detection] ✓ Found device via mountpoint match: {mountpoint} (label: {label or 'none'})")
                                return mountpoint
                
                if mounted_drives:
                    print(f"[Storage Detection] Found {len(mounted_drives)} mounted disk drive(s), but none match '{self.device_name}':")
                    for drive in mounted_drives:
                        print(f"  - {drive['name']}: {drive['mountpoint']} (label: {drive['label'] or 'none'})")
                else:
                    print("[Storage Detection] No mounted disk drives found via lsblk")
        except Exception as e:
            print(f"[Storage Detection] Error using lsblk: {e}")
        
        # Method 2: Check /proc/mounts for USB/removable disk drives
        try:
            print("[Storage Detection] Method 2: Checking /proc/mounts for removable drives...")
            removable_mounts = []
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device = parts[0]
                        mountpoint = parts[1]
                        fstype = parts[2] if len(parts) > 2 else ''
                        
                        # Check if it's a USB/removable disk drive (sd* devices)
                        if '/dev/sd' in device and not device.endswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                            # Skip if it's a partition number (we want the whole device)
                            continue
                        
                        if '/dev/sd' in device or '/dev/mmcblk' in device:
                            # Check if mountpoint is in typical removable storage locations
                            if '/media' in mountpoint or '/mnt' in mountpoint or '/run/media' in mountpoint:
                                # Normalize mountpoint (handle encoding from /proc/mounts)
                                normalized_mountpoint = mountpoint.replace('\\040', ' ').replace('\\x20', ' ')
                                removable_mounts.append({'device': device, 'mountpoint': normalized_mountpoint})
                                # Check label
                                label = self._get_device_label(device)
                                if label and self.device_name.lower() in label.lower():
                                    print(f"[Storage Detection] ✓ Found device via /proc/mounts label match: {normalized_mountpoint} (label: {label})")
                                    return normalized_mountpoint
                                
                                # Check mountpoint name
                                if self.device_name.lower() in normalized_mountpoint.lower():
                                    label_str = label if label else 'none'
                                    print(f"[Storage Detection] ✓ Found device via /proc/mounts mountpoint match: {normalized_mountpoint} (label: {label_str})")
                                    return normalized_mountpoint
            
            if removable_mounts:
                print(f"[Storage Detection] Found {len(removable_mounts)} removable mount(s) in /proc/mounts, but none match '{self.device_name}':")
                for mount in removable_mounts:
                    label = self._get_device_label(mount['device'])
                    print(f"  - {mount['device']}: {mount['mountpoint']} (label: {label or 'none'})")
        except Exception as e:
            print(f"[Storage Detection] Error reading /proc/mounts: {e}")
        
        # Method 3: Check /media, /mnt, and /run/media directories for mounted drives
        print("[Storage Detection] Method 3: Checking standard mount directories...")
        for base_dir in ['/run/media', '/media', '/mnt']:
            if os.path.exists(base_dir):
                try:
                    items = os.listdir(base_dir)
                    if items:
                        print(f"[Storage Detection] Checking {base_dir} ({len(items)} items)")
                        for item in items:
                            item_path = os.path.join(base_dir, item)
                            if os.path.isdir(item_path):
                                # Verify it's actually a mount point (disk drive)
                                if self._is_mount_point(item_path):
                                    print(f"  - Found mount point: {item_path}")
                                    # Check if name matches
                                    if self.device_name.lower() in item.lower():
                                        print(f"[Storage Detection] ✓ Found device via directory scan: {item_path}")
                                        return item_path
                                    else:
                                        print(f"    (Name '{item}' doesn't match '{self.device_name}')")
                    else:
                        print(f"[Storage Detection] {base_dir} exists but is empty")
                except PermissionError:
                    print(f"[Storage Detection] Permission denied accessing {base_dir}")
                    continue
                except Exception as e:
                    print(f"[Storage Detection] Error checking {base_dir}: {e}")
            else:
                print(f"[Storage Detection] {base_dir} does not exist")
        
        # Method 4: Use df to find all removable disk drives
        try:
            print("[Storage Detection] Method 4: Checking df output for removable drives...")
            result = subprocess.run(
                ['df', '-h', '-T'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                removable_dfs = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 7:
                        device = parts[0]
                        fstype = parts[1]
                        mountpoint = parts[6]
                        
                        # Check if it's a disk drive in removable storage locations
                        if ('/media' in mountpoint or '/mnt' in mountpoint or '/run/media' in mountpoint):
                            if os.path.isdir(mountpoint):
                                removable_dfs.append({'device': device, 'mountpoint': mountpoint})
                                # Check if name matches in mountpoint path
                                if self.device_name.lower() in mountpoint.lower():
                                    print(f"[Storage Detection] ✓ Found device via df: {mountpoint}")
                                    return mountpoint
                
                if removable_dfs:
                    print(f"[Storage Detection] Found {len(removable_dfs)} removable drive(s) via df, but none match '{self.device_name}':")
                    for df_mount in removable_dfs:
                        print(f"  - {df_mount['device']}: {df_mount['mountpoint']}")
        except Exception as e:
            print(f"[Storage Detection] Error using df: {e}")
        
        print(f"[Storage Detection] ✗ Device matching '{self.device_name}' not found after checking all methods")
        return None
    
    def _get_device_label(self, device: str) -> Optional[str]:
        """Get the label for a device."""
        try:
            # Use blkid to get label
            result = subprocess.run(
                ['blkid', device],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0:
                # Parse LABEL="value" from output
                match = re.search(r'LABEL="([^"]+)"', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass
        
        return None
    
    def _is_mount_point(self, path: str) -> bool:
        """Check if a path is actually a mount point."""
        try:
            result = subprocess.run(
                ['findmnt', path],
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.returncode == 0
        except FileNotFoundError:
            # findmnt might not be available, use alternative method
            try:
                result = subprocess.run(
                    ['mountpoint', path],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                return result.returncode == 0
            except FileNotFoundError:
                # Last resort: check if parent device is different
                try:
                    stat1 = os.stat(path)
                    stat2 = os.stat(os.path.dirname(path))
                    return stat1.st_dev != stat2.st_dev
                except Exception:
                    return False
        except Exception:
            return False
    
    def _looks_like_audio_device(self, mountpoint: str) -> bool:
        """Check if a mountpoint looks like an audio storage device."""
        # Audio devices often have specific directory structures
        # Check for common patterns
        try:
            contents = os.listdir(mountpoint)
            # Look for common audio file extensions or directories
            audio_extensions = ['.mp3', '.wav', '.flac', '.m4a']
            for item in contents:
                item_path = os.path.join(mountpoint, item)
                if os.path.isdir(item_path):
                    # Check subdirectories
                    try:
                        subcontents = os.listdir(item_path)
                        if any(item.endswith(ext) for item in subcontents for ext in audio_extensions):
                            return True
                    except PermissionError:
                        continue
                elif any(item.lower().endswith(ext) for ext in audio_extensions):
                    return True
        except PermissionError:
            pass
        except Exception as e:
            print(f"Error checking device structure: {e}")
        
        return False
    
    def wait_for_device(self, timeout: float = 30.0, check_interval: float = 2.0) -> Optional[str]:
        """
        Wait for the device to be mounted.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Seconds between checks
            
        Returns:
            Mount point path or None if timeout
        """
        start_time = time.time()
        check_count = 0
        
        print(f"[Storage Detection] Waiting up to {timeout} seconds for device to mount (checking every {check_interval}s)...")
        
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time
            print(f"\n[Storage Detection] Check #{check_count} (elapsed: {elapsed:.1f}s)")
            
            mount_point = self.find_device_mount_point()
            if mount_point:
                print(f"[Storage Detection] ✓ Device found after {elapsed:.1f} seconds")
                return mount_point
            
            remaining = timeout - elapsed
            if remaining > check_interval:
                print(f"[Storage Detection] Device not found, waiting {check_interval}s ({(remaining - check_interval):.1f}s remaining)...")
            time.sleep(check_interval)
        
        elapsed = time.time() - start_time
        print(f"\n[Storage Detection] ✗ Timeout after {elapsed:.1f} seconds - device not mounted")
        return None
    
    def is_device_mounted(self) -> bool:
        """Check if the device is currently mounted."""
        return self.find_device_mount_point() is not None


if __name__ == "__main__":
    # Test the storage detector
    detector = StorageDetector("Shokz")
    
    print("Checking for Shokz OpenSwim storage device (disk drive)...")
    
    # First, show all mounted disk drives for debugging
    print("\nAll mounted disk drives:")
    try:
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,LABEL,MOUNTPOINT,SIZE', '-n'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    mountpoint = parts[2] if len(parts) > 2 and parts[2] != '-' else None
                    if mountpoint:  # Only show mounted devices
                        print(f"  {line}")
    except Exception:
        pass
    
    print("\n" + "="*60)
    mount_point = detector.find_device_mount_point()
    
    if mount_point:
        print(f"\n✓ Device found at: {mount_point}")
        print(f"\nContents:")
        try:
            for item in os.listdir(mount_point):
                item_path = os.path.join(mount_point, item)
                item_type = "DIR" if os.path.isdir(item_path) else "FILE"
                size = os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
                print(f"  {item_type}: {item} ({size_str})")
        except PermissionError:
            print("  Permission denied")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("\n✗ Device not found. Make sure the headphones are connected and mounted as a disk drive.")
        print("\nTrying to wait for device (30 seconds)...")
        mount_point = detector.wait_for_device(timeout=30.0)
        if mount_point:
            print(f"✓ Device found at: {mount_point}")
        else:
            print("✗ Timeout: Device not mounted")

