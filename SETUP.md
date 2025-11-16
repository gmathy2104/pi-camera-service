# Pi Camera Service - Complete Setup Guide

This guide will walk you through setting up the Pi Camera Service from scratch.

## Step 1: Install System Dependencies

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

**What these packages do:**
- `python3-picamera2` - Python interface for Raspberry Pi camera
- `python3-libcamera` - Camera library for Raspberry Pi
- `libcamera-apps` - Camera testing utilities (e.g., `rpicam-hello`)
- `ffmpeg` - Video processing tool (required for RTSP streaming)
- `python3-venv` - Python virtual environment support
- `git` - Version control

## Step 2: Clone or Navigate to Project

```bash
cd ~/pi-camera-service
```

If you haven't cloned it yet:
```bash
cd ~
git clone <your-repo-url> pi-camera-service
cd pi-camera-service
```

## Step 3: Create Virtual Environment

**Important:** You MUST use the `--system-site-packages` flag!

```bash
# Create virtual environment with access to system packages
python3 -m venv --system-site-packages venv
```

**Why `--system-site-packages`?**
The `picamera2` library is installed via APT (system package manager), not pip. The `--system-site-packages` flag allows your virtual environment to access these system-installed packages.

## Step 4: Install Python Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt
```

**Verify picamera2 is accessible:**
```bash
python -c "from picamera2 import Picamera2; print('✓ Success')"
```

You should see: `✓ Success`

## Step 5: Configure MediaMTX

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

**Important:** Use `source: publisher`, NOT `source: rpiCamera` (would conflict with our service).

**Restart MediaMTX:**
```bash
sudo systemctl restart mediamtx
sudo systemctl status mediamtx
```

## Step 6: Configure the Camera Service (Optional)

The service works with defaults, but you can customize settings:

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Common settings:**
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
```

## Step 7: Test Manual Start

Before setting up the service, test that everything works:

```bash
# Make sure you're in the project directory
cd ~/pi-camera-service

# Activate virtual environment
source venv/bin/activate

# Start the service manually
python main.py
```

**You should see:**
```
INFO:camera_service.api:=== Pi Camera Service Starting ===
INFO:camera_service.api:Configuration: 1920x1080@30fps
INFO:camera_service.camera_controller:Configuring camera...
INFO:camera_service.camera_controller:Camera configured: 1920x1080@30fps
INFO:camera_service.streaming_manager:Starting RTSP streaming to rtsp://127.0.0.1:8554/cam
INFO:camera_service.streaming_manager:Streaming started successfully
INFO:camera_service.api:=== Pi Camera Service Started Successfully ===
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

## Step 8: Install as System Service

Install the service to start automatically on boot:

```bash
# Run the installation script
./install-service.sh
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

## Step 9: Test the Video Stream

### Using VLC (from another computer)

1. Open VLC
2. Media → Open Network Stream
3. Enter: `rtsp://<YOUR_PI_IP>:8554/cam`
4. Click Play

### Using Command Line

```bash
# Using ffplay
ffplay rtsp://<YOUR_PI_IP>:8554/cam

# Using VLC command line
vlc rtsp://<YOUR_PI_IP>:8554/cam
```

### Get Raspberry Pi IP Address

```bash
hostname -I
```

## Step 10: Test Auto-Start (Optional but Recommended)

```bash
# Reboot the Pi
sudo reboot
```

After reboot:
```bash
# Check service is running
sudo systemctl status pi-camera-service

# Test API
curl http://localhost:8000/health
```

---

## ✅ Setup Complete!

Your Pi Camera Service is now:
- ✅ Installed and configured
- ✅ Running as a system service
- ✅ Starting automatically on boot
- ✅ Streaming to MediaMTX
- ✅ Accessible via HTTP API

---

## Next Steps

### View Logs

```bash
# Live log viewing
sudo journalctl -u pi-camera-service -f

# Last 50 lines
sudo journalctl -u pi-camera-service -n 50
```

### Control the Service

```bash
# Start
sudo systemctl start pi-camera-service

# Stop
sudo systemctl stop pi-camera-service

# Restart
sudo systemctl restart pi-camera-service

# Status
sudo systemctl status pi-camera-service
```

### Update Configuration

```bash
# Edit .env file
nano .env

# Restart service to apply changes
sudo systemctl restart pi-camera-service
```

### Test API Endpoints

```bash
# Get camera status
curl http://localhost:8000/v1/camera/status

# Set manual exposure (10ms, gain 2.0)
curl -X POST http://localhost:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -d '{"exposure_us": 10000, "gain": 2.0}'

# Enable auto exposure
curl -X POST http://localhost:8000/v1/camera/auto_exposure \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

---

## Troubleshooting

See `SERVICE-SETUP.md` for detailed troubleshooting, including:
- Common errors and solutions
- How to fix virtual environment issues
- PATH and ffmpeg problems
- Permission issues

---

## Documentation

- **`CLAUDE.md`** - Development guide for working with the code
- **`SERVICE-SETUP.md`** - Detailed systemd service documentation
- **`MIGRATION.md`** - Guide for migrating from older versions
- **`README.md`** - Original project documentation (in French)

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u pi-camera-service -n 50`
2. Verify camera: `rpicam-hello --list-cameras`
3. Check MediaMTX: `sudo systemctl status mediamtx`
4. Review `SERVICE-SETUP.md` troubleshooting section
