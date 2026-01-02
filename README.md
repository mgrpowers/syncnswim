# SyncNSwim

Automatically download and transfer the latest podcast episodes to your Shokz OpenSwim headphones when their storage is mounted on your Raspberry Pi.

## Overview

SyncNSwim monitors for when your Shokz OpenSwim headphones are mounted as a storage device (disk drive). When detected, it automatically fetches the latest episodes from your favorite podcasts and transfers them directly to the headphone's built-in storage.

## Features

- 💾 Automatic storage device detection (monitors for disk drive mount)
- 📻 RSS feed parsing for podcast episodes
- ⬇️ Automatic download and transfer of latest episodes to headphone storage
- 🔄 Smart transfer (skips already transferred episodes)
- ⚙️ Easy configuration management via CLI
- 📝 JSON-based configuration

## Requirements

- Raspberry Pi (or Linux system)
- Python 3.7+
- Internet connection
- USB connection (Shokz OpenSwim headphones connect via USB to appear as storage device)

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment (recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   Note: If `python3 -m venv` fails, install python3-venv first:

   ```bash
   sudo apt-get install python3-venv
   ```

3. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   Note: If you prefer not to use a virtual environment, you can use system packages or install with `--break-system-packages` (not recommended):

   ```bash
   pip3 install -r requirements.txt --break-system-packages
   ```

4. **Connect your Shokz OpenSwim headphones:**
   - Connect the headphones via USB cable to your Raspberry Pi
   - The headphones should appear as a disk drive when connected
   - The device should automatically mount (typically in `/media`, `/mnt`, or `/run/media`)

## Configuration

### Initial Setup

The app comes with "This Week in Tech" pre-configured. The configuration is stored in `config.json`:

```json
{
  "shokz_device_name": "SWIM",
  "download_directory": "./downloads",
  "device_music_directory": "MUSIC",
  "storage_wait_timeout": 30,
  "podcasts": [
    {
      "name": "This Week in Tech",
      "rss_url": "https://feeds.twit.tv/twit.xml",
      "enabled": true
    }
  ]
}
```

Configuration options:

- `shokz_device_name`: Name or partial name to match your device (default: "SWIM", matches "SWIM PRO" mount point)
- `download_directory`: Local directory for temporary downloads (default: "./downloads")
- `device_music_directory`: Directory name on device where music is stored (default: "MUSIC")
- `storage_wait_timeout`: Seconds to wait for storage to mount (default: 30, not used in current monitoring mode)
- `podcasts`: Array of podcast configurations

### Managing Podcasts via CLI

Use the CLI tool to manage your podcast list:

**List all podcasts:**

```bash
python3 cli.py list
```

**Add a new podcast:**

```bash
python3 cli.py add "Podcast Name" "https://example.com/rss.xml"
```

**Test an RSS feed:**

```bash
python3 cli.py test "https://feeds.twit.tv/twit.xml"
```

**Remove a podcast:**

```bash
python3 cli.py remove "https://example.com/rss.xml"
```

**Enable/disable a podcast:**

```bash
python3 cli.py enable "https://example.com/rss.xml"
python3 cli.py disable "https://example.com/rss.xml"
```

### Manual Configuration

You can also edit `config.json` directly (see configuration section above for details).

## Usage

### Running the Application

Start the monitoring service:

If using a virtual environment (recommended):

```bash
source venv/bin/activate
python main.py
```

Or if installed system-wide:

```bash
python3 main.py
```

The app will:

1. Monitor for Shokz OpenSwim headphones storage device mount
2. When storage device is detected, fetch latest episodes from enabled podcasts (downloads to local directory first)
3. Transfer MP3 files to the headphone's storage device
4. Continue monitoring for unmount/remount events

Press `Ctrl+C` to stop.

### Running as a Service (Optional)

To run SyncNSwim automatically on boot, you can create a systemd service:

1. Create a service file:

   ```bash
   sudo nano /etc/systemd/system/syncnswim.service
   ```

2. Add the following (adjust paths as needed):

   ```ini
   [Unit]
   Description=SyncNSwim - Podcast Sync for Shokz
   After=network.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/syncnswim
   ExecStart=/usr/bin/python3 /home/pi/syncnswim/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl enable syncnswim.service
   sudo systemctl start syncnswim.service
   ```

4. Check status:
   ```bash
   sudo systemctl status syncnswim.service
   ```

## How It Works

1. **Storage Monitoring**: Continuously monitors for when the Shokz OpenSwim storage device is mounted as a disk drive (typically in `/media`, `/mnt`, or `/run/media`)
2. **Storage Detection**: Detects the mount point by looking for devices matching the configured device name
3. **RSS Parsing**: When storage is detected, parses RSS feeds to find the latest episode for each enabled podcast
4. **Download**: Downloads MP3 files to local directory first (organized by podcast name)
5. **Transfer**: Copies MP3 files to the headphone's storage device (in the MUSIC directory)
6. **Smart Updates**: Only downloads/transfers new episodes (checks if file already exists on device)

## Default Podcast

The app comes pre-configured with "This Week in Tech" (TWiT):

- RSS Feed: `https://feeds.twit.tv/twit.xml`
- Latest episodes are automatically fetched when storage device is mounted

## Troubleshooting

**Storage device not detected:**

- Make sure headphones are in storage/USB mode (they should appear as a disk drive)
- Check if device is mounted as a disk drive: `lsblk` or `df -h`
- Look for device in `/media`, `/mnt`, or `/run/media` directories
- The device should show up like `/dev/sda1` or similar when connected
- Try connecting via USB cable - Shokz OpenSwim typically needs USB connection for storage mode
- Check the mount point name matches (or contains) the device name from config (`shokz_device_name`)
- Increase `storage_wait_timeout` in config.json if device takes longer to mount
- Run `python3 storage_detector.py` to see all mounted disk drives and debug detection

**Download fails:**

- Check internet connection
- Verify RSS feed URL is correct: `python3 cli.py test [RSS_URL]`
- Check available disk space (both local and device)
- Ensure download directory is writable

**Transfer fails / Permission denied:**

- Check if device is mounted read-only: `mount | grep SWIM` (look for 'ro' in output)
- Verify you have write permissions: Try manually creating a file: `touch /media/raspberry/SWIM\ PRO/test.txt`
- If mounted read-only, you may need to remount with write permissions (check device settings first)
- Ensure the user running the script has permission to write to the mount point
- Some devices require being mounted with specific options - check device documentation
- If using systemd service, ensure the service user has write permissions to the mount point

## License

MIT License - see LICENSE file for details
