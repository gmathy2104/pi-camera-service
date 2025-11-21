# Installation Guide

Complete guide for installing and configuring Pi Camera Service on Raspberry Pi.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Systemd Service Setup](#systemd-service-setup)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4/5 or Zero 2W
- Raspberry Pi Camera Module (v1/v2/v3, HQ, or NoIR variants)
- Stable power supply
- Network connection

### Software Requirements
- Raspberry Pi OS (Bullseye or newer)
- Python 3.9+
- MediaMTX server (for RTSP streaming)

---

## Quick Start

For experienced users:

```bash
# Install dependencies
sudo apt update && sudo apt install -y python3-venv python3-picamera2 python3-libcamera libcamera-apps ffmpeg git

# Clone repository
git clone https://github.com/gmathy2104/pi-camera-service.git
cd pi-camera-service

# Setup virtual environment
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configure (optional)
cp .env.example .env
nano .env

# Install as systemd service
./scripts/install-service.sh

# Check status
sudo systemctl status pi-camera-service
```

---

## Detailed Installation

### Step 1: Install System Dependencies

```bash
# Update package list
sudo apt update

# Install required system packages
sudo apt install -y \
  python3-venv \
  python3-picamera2 \
  python3-libcamera \
  libcamera-apps \
  ffmpeg \
  git
```

**Package descriptions:**
- `python3-picamera2` - Python interface for Raspberry Pi camera
- `python3-libcamera` - Camera library for Raspberry Pi
- `libcamera-apps` - Camera testing utilities (e.g., `rpicam-hello`)
- `ffmpeg` - Video processing tool (required for RTSP streaming)
- `python3-venv` - Python virtual environment support
- `git` - Version control

### Step 2: Clone Repository

```bash
cd ~
git clone https://github.com/gmathy2104/pi-camera-service.git
cd pi-camera-service
```

### Step 3: Create Virtual Environment

**IMPORTANT:** You MUST use the `--system-site-packages` flag!

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
```

**Why `--system-site-packages`?**
The `picamera2` library is installed via APT (system package manager), not pip. The `--system-site-packages` flag allows your virtual environment to access these system-installed packages.

### Step 4: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

**Verify picamera2 is accessible:**
```bash
python -c "from picamera2 import Picamera2; print('✓ picamera2 OK')"
```

You should see: `✓ picamera2 OK`

### Step 5: Configure MediaMTX

Ensure MediaMTX is installed and configured correctly.

**Edit MediaMTX configuration:**
```bash
sudo nano /etc/mediamtx.yml
```

**Add or verify the camera path:**
```yaml
paths:
  cam:
    source: publisher
```

**IMPORTANT:** Use `source: publisher`, NOT `source: rpiCamera` (would conflict with this service).

**Restart MediaMTX:**
```bash
sudo systemctl restart mediamtx
sudo systemctl status mediamtx
```

### Step 6: Configure Camera Service

The service works with defaults, but you can customize settings:

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Example configuration:**
```bash
# Video quality
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
CAMERA_BITRATE=8000000

# API server
CAMERA_PORT=8000

# Enable API authentication (optional)
CAMERA_API_KEY=your-secret-key-here

# Logging
CAMERA_LOG_LEVEL=INFO

# Camera Module 3 Wide NoIR example
CAMERA_CAMERA_MODEL=imx708
CAMERA_IS_NOIR=true
```

See [Configuration Guide](configuration.md) for all available options.

### Step 7: Test Manual Start

Before setting up the service, test that everything works:

```bash
# Ensure you're in the project directory
cd ~/pi-camera-service

# Activate virtual environment
source venv/bin/activate

# Start the service manually
python main.py
```

**Expected output:**
```
INFO:camera_service.api:=== Pi Camera Service Starting ===
INFO:camera_service.api:Configuration: 1920x1080@30fps
INFO:camera_service.camera_controller:Configuring camera...
INFO:camera_service.camera_controller:Camera configured: 1920x1080@30fps
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test the API (in another terminal):**
```bash
# Health check
curl http://localhost:8000/health

# Camera status
curl http://localhost:8000/v1/camera/status
```

**If it works, press Ctrl+C to stop and continue to the next step.**

---

## Systemd Service Setup

### Automatic Installation

```bash
# Run the installation script
./scripts/install-service.sh
```

The script will:
1. Copy the service file to systemd
2. Enable auto-start on boot
3. Ask if you want to start the service now

**Verify the service is running:**
```bash
sudo systemctl status pi-camera-service
```

You should see: `Active: active (running)`

### Manual Installation

If you prefer to install manually:

```bash
# Copy service file to systemd
sudo cp pi-camera-service.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable pi-camera-service

# Start service now
sudo systemctl start pi-camera-service

# Check status
sudo systemctl status pi-camera-service
```

### Service Management

**Start/Stop/Restart:**
```bash
sudo systemctl start pi-camera-service
sudo systemctl stop pi-camera-service
sudo systemctl restart pi-camera-service
```

**View logs:**
```bash
# Live tail
sudo journalctl -u pi-camera-service -f

# Last 100 lines
sudo journalctl -u pi-camera-service -n 100

# Since boot
sudo journalctl -u pi-camera-service -b
```

**Enable/Disable auto-start:**
```bash
# Enable (done automatically by install script)
sudo systemctl enable pi-camera-service

# Disable
sudo systemctl disable pi-camera-service

# Check status
sudo systemctl is-enabled pi-camera-service
```

---

## Configuration

### Environment Variables

**Option 1: `.env` file (Recommended)**

Edit the `.env` file in the project directory:

```bash
nano ~/pi-camera-service/.env
```

After editing, restart the service:

```bash
sudo systemctl restart pi-camera-service
```

**Option 2: Systemd service file**

Add environment variables directly to the service file:

```bash
sudo nano /etc/systemd/system/pi-camera-service.service
```

Add in the `[Service]` section:

```ini
[Service]
Environment="CAMERA_API_KEY=your-secret-key"
Environment="CAMERA_LOG_LEVEL=INFO"
Environment="CAMERA_PORT=8000"
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

### Testing the Stream

**Using VLC (from another computer):**

1. Open VLC
2. Media → Open Network Stream
3. Enter: `rtsp://<YOUR_PI_IP>:8554/cam`
4. Click Play

**Using command line:**
```bash
# Using ffplay
ffplay rtsp://<YOUR_PI_IP>:8554/cam

# Using VLC
vlc rtsp://<YOUR_PI_IP>:8554/cam
```

**Get your Raspberry Pi IP:**
```bash
hostname -I
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check detailed status
sudo systemctl status pi-camera-service

# Check logs for errors
sudo journalctl -u pi-camera-service -n 50
```

### Common Issues

#### 1. `ModuleNotFoundError: No module named 'picamera2'`

**Problem:** Virtual environment can't access system-installed picamera2.

**Solution:** Recreate venv with `--system-site-packages`:

```bash
# Backup old venv
mv venv venv.old

# Create new venv with system packages
python3 -m venv --system-site-packages venv

# Install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Restart service
sudo systemctl restart pi-camera-service
```

#### 2. `FileNotFoundError: ffmpeg not found`

**Problem:** systemd service can't find ffmpeg in PATH.

**Solution:** Verify PATH in service file:

```bash
grep "Environment.*PATH" /etc/systemd/system/pi-camera-service.service
```

Should show system paths including `/usr/bin`. If not:

```bash
sudo cp pi-camera-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

#### 3. Camera Permission Denied

**Problem:** User doesn't have permission to access camera.

**Solution:** Add user to video group:

```bash
sudo usermod -a -G video $USER
# Log out and back in for changes to take effect
```

#### 4. Service Crashes on Boot

**Problem:** Service starts before MediaMTX is ready.

**Solution:** Increase restart delay:

```bash
sudo nano /etc/systemd/system/pi-camera-service.service
# Change: RestartSec=5  (or higher, like 10)

sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

#### 5. Camera Not Detected

**Test camera manually:**
```bash
rpicam-hello --list-cameras
```

**Check MediaMTX status:**
```bash
sudo systemctl status mediamtx
```

**Check for other processes using the camera:**
```bash
sudo lsof /dev/video*
```

### Monitoring

**Check if service is running:**
```bash
# Quick check
sudo systemctl is-active pi-camera-service

# Test API
curl http://localhost:8000/health
```

**View restart history:**
```bash
sudo systemctl status pi-camera-service | grep -i restart
```

---

## Uninstallation

To remove the service:

```bash
# Using the uninstall script
./scripts/uninstall-service.sh

# Or manually:
sudo systemctl stop pi-camera-service
sudo systemctl disable pi-camera-service
sudo rm /etc/systemd/system/pi-camera-service.service
sudo systemctl daemon-reload
```

---

## Production Checklist

- [ ] Service installed: `./scripts/install-service.sh`
- [ ] Service enabled: `sudo systemctl is-enabled pi-camera-service`
- [ ] Service running: `sudo systemctl is-active pi-camera-service`
- [ ] MediaMTX running: `sudo systemctl is-active mediamtx`
- [ ] Camera accessible: `rpicam-hello --list-cameras`
- [ ] API responding: `curl http://localhost:8000/health`
- [ ] Video streaming: Test RTSP with VLC
- [ ] Logs clean: `sudo journalctl -u pi-camera-service -n 20`
- [ ] Configuration set: Review `.env` file
- [ ] Reboot test: `sudo reboot` and verify auto-start

---

## Next Steps

- [API Reference](api-reference.md) - Complete API documentation
- [Configuration Guide](configuration.md) - Detailed configuration options
- [Development Guide](development.md) - For contributors
- [Upgrade to v2.0](upgrade-v2.md) - Migration guide from v1.0

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u pi-camera-service -f`
2. Verify camera: `rpicam-hello --list-cameras`
3. Check MediaMTX: `sudo systemctl status mediamtx`
4. Review this troubleshooting section
5. Open an issue on [GitHub](https://github.com/gmathy2104/pi-camera-service/issues)
