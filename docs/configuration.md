# Configuration Guide

Complete reference for all configuration options in Pi Camera Service.

## Table of Contents

- [Configuration Methods](#configuration-methods)
- [Video Configuration](#video-configuration)
- [Streaming Configuration](#streaming-configuration)
- [Camera Control Defaults](#camera-control-defaults)
- [Camera Hardware Configuration (v2.0)](#camera-hardware-configuration-v20)
- [API Server Configuration](#api-server-configuration)
- [Authentication](#authentication)
- [Logging](#logging)
- [Advanced Configuration](#advanced-configuration)

---

## Configuration Methods

Pi Camera Service can be configured in three ways (in order of precedence):

1. **Environment variables** - Direct environment variable export
2. **`.env` file** - Recommended for most use cases
3. **Default values** - Built-in defaults in `config.py`

### Using `.env` File (Recommended)

Create or edit `.env` in the project root:

```bash
cp .env.example .env
nano .env
```

After changes:
```bash
sudo systemctl restart pi-camera-service
```

### Using Environment Variables

For temporary testing or systemd configuration:

```bash
# Temporary (current session only)
export CAMERA_WIDTH=1280
export CAMERA_HEIGHT=720
python main.py

# Or inline
CAMERA_WIDTH=1280 CAMERA_HEIGHT=720 python main.py
```

### Using Systemd Service File

Edit `/etc/systemd/system/pi-camera-service.service`:

```ini
[Service]
Environment="CAMERA_WIDTH=1920"
Environment="CAMERA_HEIGHT=1080"
Environment="CAMERA_API_KEY=secret123"
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

---

## Video Configuration

### Resolution

```bash
CAMERA_WIDTH=1920          # Video width in pixels
CAMERA_HEIGHT=1080         # Video height in pixels
```

**Supported resolutions (Camera Module 3):**
- `1920x1080` - Full HD (default)
- `2304x1296` - Wide (16:9)
- `4608x2592` - Maximum resolution
- `1280x720` - HD (lower bandwidth)
- `640x480` - VGA (testing)

**Note:** Higher resolutions require more bandwidth and processing power.

### Frame Rate

```bash
CAMERA_FRAMERATE=30        # Frames per second (FPS)
```

**Common values:**
- `30` - Standard (default)
- `60` - Smooth motion (requires good lighting)
- `24` - Cinematic
- `15` - Low bandwidth
- `10` - Very low bandwidth

**Note:** Higher frame rates require better lighting and more bandwidth.

### Bitrate

```bash
CAMERA_BITRATE=8000000     # H.264 bitrate in bits/second
```

**Recommended values:**
- `8000000` (8 Mbps) - High quality 1080p (default)
- `4000000` (4 Mbps) - Medium quality 1080p
- `2000000` (2 Mbps) - Low bandwidth 1080p
- `10000000` (10 Mbps) - Maximum quality
- `1000000` (1 Mbps) - Very low bandwidth

**Formula:** Bitrate should be ~8-12 bits per pixel for good quality.

---

## Streaming Configuration

### RTSP URL

```bash
CAMERA_RTSP_URL=rtsp://127.0.0.1:8554/cam
```

**Format:** `rtsp://[host]:[port]/[path]`

**Examples:**
- `rtsp://127.0.0.1:8554/cam` - Local MediaMTX (default)
- `rtsp://192.168.1.100:8554/camera1` - Remote RTSP server
- `rtsp://localhost:8554/front_door` - Custom path name

**Note:** Ensure MediaMTX (or your RTSP server) is configured to accept publishers on this path.

---

## Camera Control Defaults

### Auto White Balance (AWB)

```bash
CAMERA_ENABLE_AWB=true     # Enable AWB on startup
```

**Values:**
- `true` - Auto white balance enabled (default)
- `false` - AWB disabled (manual control)

### Auto Exposure

```bash
CAMERA_DEFAULT_AUTO_EXPOSURE=true  # Enable auto-exposure on startup
```

**Values:**
- `true` - Auto-exposure enabled (default)
- `false` - Manual exposure control

---

## Camera Hardware Configuration (v2.0)

### Camera Model

```bash
CAMERA_CAMERA_MODEL=imx708
```

**Supported models:**
- `imx708` - Camera Module 3 / 3 Wide (default)
- `imx477` - HQ Camera
- `imx296` - Global Shutter Camera
- `imx219` - Camera Module v2
- `ov5647` - Camera Module v1

**Use case:** Required for correct tuning file auto-detection.

### NoIR Camera

```bash
CAMERA_IS_NOIR=false       # Set to true for NoIR cameras
```

**Values:**
- `true` - NoIR camera (no infrared filter)
- `false` - Standard camera (default)

**Effect:** Automatically selects `*_noir.json` tuning file when `true`.

### Tuning File Override

```bash
CAMERA_TUNING_FILE=/usr/share/libcamera/ipa/rpi/pisp/imx708_noir.json
```

**Purpose:** Override auto-detection for custom tuning files.

**When to use:**
- Custom tuning file modifications
- Non-standard camera configurations
- Debugging tuning issues

**Default behavior:** Auto-detects based on `CAMERA_CAMERA_MODEL` and `CAMERA_IS_NOIR`.

**Auto-detection search paths:**
1. `/usr/share/libcamera/ipa/rpi/pisp/{model}{_noir}.json` (Pi 5)
2. `/usr/share/libcamera/ipa/rpi/vc4/{model}{_noir}.json` (Pi 4/Zero 2W)

---

## API Server Configuration

### Host and Port

```bash
CAMERA_HOST=0.0.0.0        # Listen address
CAMERA_PORT=8000           # HTTP port
```

**Host values:**
- `0.0.0.0` - Listen on all interfaces (default, recommended)
- `127.0.0.1` - Localhost only (more secure, local access only)
- `192.168.1.10` - Specific IP address

**Port values:**
- `8000` - Default HTTP port
- `80` - Standard HTTP (requires root/sudo)
- `8080` - Alternative HTTP port

---

## Authentication

### API Key

```bash
CAMERA_API_KEY=your-secret-key-here
```

**When set:**
- All `/v1/*` endpoints require `X-API-Key` header
- `/health` endpoint remains public

**When not set:**
- All endpoints are public (no authentication)

**Security recommendations:**
- Use strong, random keys (min 32 characters)
- Use secrets manager in production
- Rotate keys periodically
- Never commit `.env` to version control

**Example usage:**
```bash
curl -H "X-API-Key: your-secret-key-here" \
  http://localhost:8000/v1/camera/status
```

---

## Logging

### Log Level

```bash
CAMERA_LOG_LEVEL=INFO      # Logging verbosity
```

**Values (least to most verbose):**
- `CRITICAL` - Only critical errors
- `ERROR` - Errors only
- `WARNING` - Warnings and errors
- `INFO` - General information (default, recommended)
- `DEBUG` - Detailed debug information

**Use cases:**
- `INFO` - Production (default)
- `DEBUG` - Development/troubleshooting
- `WARNING` - Quiet production
- `ERROR` - Minimal logging

**View logs:**
```bash
# Systemd service
sudo journalctl -u pi-camera-service -f

# Manual run
python main.py  # Logs to console
```

---

## Advanced Configuration

### Complete `.env` Example

```bash
# ========== Video Configuration ==========
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
CAMERA_BITRATE=8000000

# ========== Streaming Configuration ==========
CAMERA_RTSP_URL=rtsp://127.0.0.1:8554/cam

# ========== Camera Control Defaults ==========
CAMERA_ENABLE_AWB=true
CAMERA_DEFAULT_AUTO_EXPOSURE=true

# ========== Camera Hardware Configuration (v2.0) ==========
# Camera Module 3 Wide NoIR example
CAMERA_CAMERA_MODEL=imx708
CAMERA_IS_NOIR=true
# CAMERA_TUNING_FILE=/custom/path/tuning.json  # Optional override

# ========== API Server Configuration ==========
CAMERA_HOST=0.0.0.0
CAMERA_PORT=8000

# ========== Authentication ==========
# CAMERA_API_KEY=your-secret-key-here  # Uncomment to enable

# ========== Logging ==========
CAMERA_LOG_LEVEL=INFO
```

### Camera Module 3 Standard

```bash
CAMERA_CAMERA_MODEL=imx708
CAMERA_IS_NOIR=false
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
```

### Camera Module 3 Wide NoIR (Night Vision)

```bash
CAMERA_CAMERA_MODEL=imx708
CAMERA_IS_NOIR=true
CAMERA_WIDTH=2304
CAMERA_HEIGHT=1296
CAMERA_FRAMERATE=30
CAMERA_ENABLE_AWB=true
```

### HQ Camera (imx477)

```bash
CAMERA_CAMERA_MODEL=imx477
CAMERA_IS_NOIR=false
CAMERA_WIDTH=2028
CAMERA_HEIGHT=1520
CAMERA_FRAMERATE=30
CAMERA_BITRATE=10000000
```

### Low Bandwidth Configuration

```bash
CAMERA_WIDTH=1280
CAMERA_HEIGHT=720
CAMERA_FRAMERATE=15
CAMERA_BITRATE=2000000
```

### High Quality Configuration

```bash
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=60
CAMERA_BITRATE=12000000
```

---

## Configuration Validation

The service validates all configuration on startup. Check logs for errors:

```bash
sudo journalctl -u pi-camera-service -n 50
```

**Common validation errors:**
- Invalid resolution (not supported by camera)
- Invalid frame rate (too high for resolution)
- Invalid bitrate (too low/high)
- Invalid tuning file path
- Port already in use

---

## Runtime Configuration

Some settings can be changed at runtime via the API (without restart):

**Can be changed via API:**
- Auto exposure (on/off)
- Manual exposure (time, gain)
- Auto white balance (on/off)
- Manual AWB gains
- Autofocus mode/position
- Image processing (brightness, contrast, etc.)
- HDR mode
- ROI/zoom
- Transform (flip, rotate)

**Requires restart:**
- Video resolution
- Frame rate
- Bitrate
- RTSP URL
- API port
- Camera model
- Tuning file

---

## Environment Variable Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CAMERA_WIDTH` | int | 1920 | Video width in pixels |
| `CAMERA_HEIGHT` | int | 1080 | Video height in pixels |
| `CAMERA_FRAMERATE` | int | 30 | Frames per second |
| `CAMERA_BITRATE` | int | 8000000 | H.264 bitrate (bits/s) |
| `CAMERA_RTSP_URL` | str | rtsp://127.0.0.1:8554/cam | RTSP stream destination |
| `CAMERA_ENABLE_AWB` | bool | true | Auto white balance on startup |
| `CAMERA_DEFAULT_AUTO_EXPOSURE` | bool | true | Auto exposure on startup |
| `CAMERA_CAMERA_MODEL` | str | imx708 | Camera sensor model |
| `CAMERA_IS_NOIR` | bool | false | NoIR camera flag |
| `CAMERA_TUNING_FILE` | str | None | Tuning file override path |
| `CAMERA_HOST` | str | 0.0.0.0 | API server bind address |
| `CAMERA_PORT` | int | 8000 | API server port |
| `CAMERA_API_KEY` | str | None | API authentication key |
| `CAMERA_LOG_LEVEL` | str | INFO | Logging level |

---

## Next Steps

- [API Reference](api-reference.md) - Use the API to control camera settings
- [Installation Guide](installation.md) - Setup and installation
- [Development Guide](development.md) - Contributing to the project
