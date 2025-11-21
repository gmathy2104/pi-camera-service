# Pi Camera Service

Production-ready **FastAPI** microservice for controlling Raspberry Pi Camera (libcamera/Picamera2) with **H.264 streaming** to **MediaMTX** via RTSP.

**Version 2.0** - Advanced Camera Module 3 control with NoIR optimization, autofocus, HDR, image capture, and more!

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/gmathy2104/pi-camera-service/releases)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

> 🆕 **New in v2.0**: Autofocus control, snapshot capture, manual AWB with NoIR presets, image processing (brightness/contrast/saturation/sharpness), HDR support, ROI/digital zoom, day/night detection, and enhanced metadata! See [UPGRADE_v2.md](UPGRADE_v2.md) for details.

---

## 🚀 Quick Start

```bash
# Complete installation (see SETUP.md for details)
./install-service.sh

# Test everything works
./test-api-v2.sh

# Access RTSP stream
# VLC: rtsp://<PI_IP>:8554/cam
```

📖 **Complete Documentation**: See [SETUP.md](SETUP.md) for step-by-step installation.

---

## ✨ Features

This service runs **on the Raspberry Pi**, controls the camera (e.g., Raspberry Pi Camera Module 3 Wide NoIR), and exposes an **HTTP REST API** to:

### Core Features (v1.0)
- ✅ Start/stop RTSP streaming to MediaMTX
- ✅ Enable/disable auto-exposure
- ✅ Set manual exposure (time + gain)
- ✅ Enable/disable auto white balance (AWB)
- ✅ Get current camera status (lux, exposure, gain, color temperature, etc.)
- ✅ API key authentication (optional)
- ✅ Auto-start at boot (systemd)
- ✅ Comprehensive test suite

### Advanced Features (v2.0) 🆕

#### 🎯 Autofocus Control (Camera Module 3)
- **Autofocus modes**: manual, auto, continuous
- **Manual lens position**: 0.0 (infinity) to 15.0 (macro ~10cm)
- **Autofocus range**: normal, macro, full
- **Endpoints**: `POST /v1/camera/{autofocus_mode,lens_position,autofocus_range}`

#### 📸 Image Capture
- **Snapshot without stopping stream**: Capture JPEG images on-demand
- **Configurable resolution**: Up to 4608×2592 (12MP)
- **Auto-focus trigger**: Optional autofocus before capture
- **Base64 encoded output**: Easy integration with web apps
- **Endpoint**: `POST /v1/camera/snapshot`

#### 🎨 Advanced White Balance
- **Manual AWB gains**: Precise red/blue channel control
- **NoIR-optimized presets**:
  - `daylight_noir` - Outdoor/daylight with NoIR camera
  - `ir_850nm` - IR illumination at 850nm wavelength
  - `ir_940nm` - IR illumination at 940nm wavelength
  - `indoor_noir` - Indoor lighting with NoIR camera
- **Endpoints**: `POST /v1/camera/{manual_awb,awb_preset}`

#### 🖼️ Image Processing
- **Brightness**: -1.0 to 1.0 adjustment
- **Contrast**: 0.0 to 2.0 (1.0 = no change)
- **Saturation**: 0.0 to 2.0 (1.0 = no change)
- **Sharpness**: 0.0 to 16.0 (higher = sharper)
- **Endpoint**: `POST /v1/camera/image_processing`

#### ✨ HDR Support
- **Hardware HDR**: From Camera Module 3 sensor
- **Modes**: off, auto, sensor, single-exp
- **Endpoint**: `POST /v1/camera/hdr`

#### 🔍 ROI / Digital Zoom
- **Region of Interest**: Crop and stream specific areas
- **Normalized coordinates**: 0.0-1.0 for resolution-independent control
- **Hardware-accelerated**: No performance impact
- **Endpoint**: `POST /v1/camera/roi`

#### ⚙️ Exposure Control
- **Exposure limits**: Constrain auto-exposure min/max values
- **Prevent flicker**: Useful for artificial lighting
- **Maintain framerate**: Limit max exposure time
- **Endpoint**: `POST /v1/camera/exposure_limits`

#### 🔧 Lens & Transform
- **Lens correction**: Distortion correction for wide-angle cameras (120° FOV)
- **Image transform**: Horizontal/vertical flip, rotation
- **Endpoints**: `POST /v1/camera/{lens_correction,transform}`

#### 🌓 Day/Night Detection
- **Automatic scene detection**: day, low_light, night
- **Configurable threshold**: Lux-based switching
- **Endpoint**: `POST /v1/camera/day_night_mode`

#### 📊 Enhanced Metadata
- **10 new status fields**: autofocus_mode, lens_position, focus_fom, hdr_mode, scene_mode, and more
- **Real-time monitoring**: All metadata available via `GET /v1/camera/status`

#### 🌙 NoIR Camera Support
- **Auto-detection**: Tuning files for NoIR cameras
- **Configuration variables**: `CAMERA_CAMERA_MODEL`, `CAMERA_IS_NOIR`, `CAMERA_TUNING_FILE`
- **Optimized presets**: AWB presets specifically for NoIR imaging

The video stream is published to MediaMTX, which then serves it via **RTSP / WebRTC / HLS**.

---

## 📐 Architecture

```
Pi Camera v3  ──>  Picamera2/libcamera  ──>  H.264 encoder  ──>  MediaMTX (RTSP, WebRTC, HLS)
                         ▲                         ▲
                         │                         │
                  Pi Camera Service API (FastAPI)  │
                         ▲                         │
                   External App (backend, UI)  ────┘
```

**Components**:
- **Pi Camera Service**: This project, running on the Pi
- **Picamera2**: Python library for controlling libcamera
- **MediaMTX**: Multi-protocol streaming server
- **External Application**: Consumes stream via MediaMTX and controls camera via HTTP

**Technologies**:
- FastAPI with modern lifespan context manager
- Pydantic BaseSettings for type-safe configuration
- Threading with RLock for thread-safety
- Structured logging
- pytest tests + integration tests

---

## 📋 Prerequisites

### Hardware
- Raspberry Pi (Pi 4 or Pi 5 recommended for H.264 encoding)
- libcamera-compatible camera (e.g., Raspberry Pi Camera Module 3)

### Software
- Raspberry Pi OS (Bookworm or later)
- Python 3.9+
- MediaMTX installed and configured

---

## 📦 Installation

### Quick Installation

Follow the complete guide in [SETUP.md](SETUP.md):

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install -y python3-venv python3-picamera2 python3-libcamera libcamera-apps ffmpeg git

# 2. Clone the project
git clone https://github.com/gmathy2104/pi-camera-service.git ~/pi-camera-service
cd ~/pi-camera-service

# 3. Create virtual environment (IMPORTANT: with --system-site-packages)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Install systemd service
./install-service.sh
```

> **⚠️ Important**: The virtual environment MUST be created with `--system-site-packages`
> to access picamera2 which is installed via APT.

---

## ⚙️ Configuration

### Environment Variables

The service uses environment variables with the `CAMERA_` prefix.

Create a `.env` file (optional):

```bash
cp .env.example .env
nano .env
```

**Main variables**:

```bash
# Video resolution and quality
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
CAMERA_BITRATE=8000000

# API server
CAMERA_HOST=0.0.0.0
CAMERA_PORT=8000

# Authentication (optional)
CAMERA_API_KEY=your-secret-key

# MediaMTX RTSP URL
CAMERA_RTSP_URL=rtsp://127.0.0.1:8554/cam

# Camera hardware (v2.0)
CAMERA_CAMERA_MODEL=imx708         # Camera sensor model
CAMERA_IS_NOIR=false               # True for NoIR cameras

# Logging
CAMERA_LOG_LEVEL=INFO
```

### MediaMTX Configuration

In `mediamtx.yml`, declare the `cam` path as **publisher**:

```yaml
paths:
  cam:
    source: publisher
```

> ⚠️ **DO NOT use** `source: rpiCamera` (conflicts with this service)

---

## 🚀 Usage

### Manual Start

```bash
cd ~/pi-camera-service
source venv/bin/activate
python main.py
```

The API will be available at `http://0.0.0.0:8000`

### Systemd Service (Production)

```bash
# Start
sudo systemctl start pi-camera-service

# Stop
sudo systemctl stop pi-camera-service

# Restart
sudo systemctl restart pi-camera-service

# View logs
sudo journalctl -u pi-camera-service -f
```

📖 See [SERVICE-SETUP.md](SERVICE-SETUP.md) for complete service documentation.

---

## 📡 HTTP API - Endpoints

**Base URL**: `http://<PI_IP>:8000`

### Service Health

**GET** `/health`
```json
{
  "status": "healthy",
  "camera_configured": true,
  "streaming_active": true,
  "version": "2.0.0"
}
```

### Camera Status (Enhanced in v2.0)

**GET** `/v1/camera/status`
```json
{
  "lux": 45.2,
  "exposure_us": 12000,
  "analogue_gain": 1.5,
  "colour_temperature": 4200.0,
  "auto_exposure": true,
  "streaming": true,

  // New v2.0 fields
  "autofocus_mode": "continuous",
  "lens_position": 2.5,
  "focus_fom": 12500,
  "hdr_mode": "off",
  "lens_correction_enabled": true,
  "scene_mode": "day",
  "day_night_mode": "auto",
  "day_night_threshold_lux": 10.0,
  "frame_duration_us": 33321,
  "sensor_black_levels": [4096, 4096, 4096, 4096]
}
```

### Exposure Control

**POST** `/v1/camera/auto_exposure`
```json
{"enabled": true}
```

**POST** `/v1/camera/manual_exposure`
```json
{
  "exposure_us": 20000,
  "gain": 2.0
}
```

### White Balance

**POST** `/v1/camera/awb`
```json
{"enabled": false}
```

**POST** `/v1/camera/manual_awb` (v2.0)
```json
{
  "red_gain": 1.5,
  "blue_gain": 1.8
}
```

**POST** `/v1/camera/awb_preset` (v2.0)
```json
{"preset": "daylight_noir"}
```

### Autofocus Control (v2.0)

**POST** `/v1/camera/autofocus_mode`
```json
{"mode": "continuous"}  // manual, auto, continuous
```

**POST** `/v1/camera/lens_position`
```json
{"position": 5.0}  // 0.0 = infinity, 10.0 = ~10cm
```

**POST** `/v1/camera/autofocus_range`
```json
{"range_mode": "normal"}  // normal, macro, full
```

### Image Capture (v2.0)

**POST** `/v1/camera/snapshot`
```json
{
  "width": 1920,
  "height": 1080,
  "autofocus_trigger": true
}
```

**Response**:
```json
{
  "status": "ok",
  "image_base64": "base64_encoded_jpeg_data...",
  "width": 1920,
  "height": 1080
}
```

### Image Processing (v2.0)

**POST** `/v1/camera/image_processing`
```json
{
  "brightness": 0.1,   // -1.0 to 1.0
  "contrast": 1.2,     // 0.0 to 2.0
  "saturation": 1.0,   // 0.0 to 2.0
  "sharpness": 8.0     // 0.0 to 16.0
}
```

### HDR Mode (v2.0)

**POST** `/v1/camera/hdr`
```json
{"mode": "sensor"}  // off, auto, sensor, single-exp
```

### ROI / Digital Zoom (v2.0)

**POST** `/v1/camera/roi`
```json
{
  "x": 0.25,      // X offset (0.0-1.0)
  "y": 0.25,      // Y offset (0.0-1.0)
  "width": 0.5,   // Width (0.0-1.0)
  "height": 0.5   // Height (0.0-1.0)
}
```

### Streaming Control

**POST** `/v1/streaming/start`

**POST** `/v1/streaming/stop`

📖 **Complete API Documentation**: See [API.md](API.md)

---

## 🧪 Testing

### v2.0 API Integration Tests

Test all v2.0 features:

```bash
# Service must be running
./test-api-v2.sh
```

**Expected output**:
```
========================================
✓ All v2.0 API tests passed!
========================================
```

### Legacy Tests

```bash
# Basic API test (v1.0 endpoints)
./test-api.sh

# Unit tests
pytest tests/ --ignore=tests/test_api_integration.py

# Integration tests (service must be running)
pytest tests/test_api_integration.py -v

# All tests
pytest tests/ -v
```

📖 See [TESTING.md](TESTING.md) for complete testing guide.

---

## 🔧 Usage Examples

### cURL

```bash
# Get status with v2.0 metadata
curl http://raspberrypi:8000/v1/camera/status

# Set autofocus to continuous mode
curl -X POST http://raspberrypi:8000/v1/camera/autofocus_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "continuous"}'

# Capture a snapshot
curl -X POST http://raspberrypi:8000/v1/camera/snapshot \
  -H "Content-Type: application/json" \
  -d '{"width": 1920, "height": 1080}' \
  | jq -r '.image_base64' | base64 -d > snapshot.jpg

# Set manual white balance (NoIR daylight preset)
curl -X POST http://raspberrypi:8000/v1/camera/awb_preset \
  -H "Content-Type: application/json" \
  -d '{"preset": "daylight_noir"}'

# Adjust image processing
curl -X POST http://raspberrypi:8000/v1/camera/image_processing \
  -H "Content-Type: application/json" \
  -d '{"brightness": 0.1, "contrast": 1.2, "sharpness": 10.0}'

# Set ROI (center crop)
curl -X POST http://raspberrypi:8000/v1/camera/roi \
  -H "Content-Type: application/json" \
  -d '{"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5}'

# With authentication (if CAMERA_API_KEY is set)
curl -H "X-API-Key: your-key" \
  http://raspberrypi:8000/v1/camera/status
```

### Python

```python
import requests
import base64
from pathlib import Path

BASE_URL = "http://raspberrypi:8000"
HEADERS = {"X-API-Key": "your-key"}  # If auth enabled

# Get enhanced status with v2.0 metadata
response = requests.get(f"{BASE_URL}/v1/camera/status", headers=HEADERS)
status = response.json()
print(f"Autofocus: {status['autofocus_mode']}, Scene: {status['scene_mode']}")
print(f"Lux: {status['lux']}, Focus FoM: {status['focus_fom']}")

# Set autofocus mode
requests.post(
    f"{BASE_URL}/v1/camera/autofocus_mode",
    json={"mode": "continuous"},
    headers=HEADERS
)

# Capture snapshot and save to file
response = requests.post(
    f"{BASE_URL}/v1/camera/snapshot",
    json={"width": 1920, "height": 1080, "autofocus_trigger": True},
    headers=HEADERS
)
snapshot_data = response.json()
image_bytes = base64.b64decode(snapshot_data['image_base64'])
Path("snapshot.jpg").write_bytes(image_bytes)
print(f"Snapshot saved: {snapshot_data['width']}x{snapshot_data['height']}")

# Set manual AWB for NoIR camera
requests.post(
    f"{BASE_URL}/v1/camera/awb_preset",
    json={"preset": "daylight_noir"},
    headers=HEADERS
)

# Adjust image processing
requests.post(
    f"{BASE_URL}/v1/camera/image_processing",
    json={
        "brightness": 0.1,
        "contrast": 1.2,
        "saturation": 1.0,
        "sharpness": 8.0
    },
    headers=HEADERS
)
```

### JavaScript / TypeScript

```javascript
const BASE_URL = "http://raspberrypi:8000";
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": "your-key"  // If auth enabled
};

// Get enhanced status
const response = await fetch(`${BASE_URL}/v1/camera/status`, { headers });
const status = await response.json();
console.log(`Autofocus: ${status.autofocus_mode}, Scene: ${status.scene_mode}`);

// Set autofocus mode
await fetch(`${BASE_URL}/v1/camera/autofocus_mode`, {
  method: "POST",
  headers,
  body: JSON.stringify({ mode: "continuous" })
});

// Capture snapshot
const snapshotRes = await fetch(`${BASE_URL}/v1/camera/snapshot`, {
  method: "POST",
  headers,
  body: JSON.stringify({ width: 1920, height: 1080 })
});
const { image_base64 } = await snapshotRes.json();
// Convert base64 to blob for download or display
const blob = await fetch(`data:image/jpeg;base64,${image_base64}`).then(r => r.blob());

// Set manual AWB
await fetch(`${BASE_URL}/v1/camera/manual_awb`, {
  method: "POST",
  headers,
  body: JSON.stringify({ red_gain: 1.5, blue_gain: 1.8 })
});
```

---

## 🐛 Troubleshooting

### Camera not detected

```bash
rpicam-hello --list-cameras
```

If no camera appears, check cable and connection.

### Service won't start

```bash
# View error logs
sudo journalctl -u pi-camera-service -n 50

# Check status
sudo systemctl status pi-camera-service

# Test manually
cd ~/pi-camera-service
source venv/bin/activate
python main.py
```

### ModuleNotFoundError: picamera2

Recreate venv with `--system-site-packages`:

```bash
cd ~/pi-camera-service
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### No RTSP image

1. Check service is running: `curl http://localhost:8000/health`
2. Check MediaMTX: `sudo systemctl status mediamtx`
3. View logs: `sudo journalctl -u pi-camera-service -f`

### exposure_limits endpoint fails

Some libcamera versions don't support `ExposureTimeMin/Max` controls. This is a platform limitation, not a bug. The endpoint will fail gracefully with a clear error message.

📖 See [SERVICE-SETUP.md](SERVICE-SETUP.md#troubleshooting) for more solutions.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file - project overview |
| [UPGRADE_v2.md](UPGRADE_v2.md) | Complete v2.0 upgrade guide with examples |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [SETUP.md](SETUP.md) | Step-by-step installation guide |
| [API.md](API.md) | Complete REST API documentation |
| [SERVICE-SETUP.md](SERVICE-SETUP.md) | systemd service configuration |
| [TESTING.md](TESTING.md) | Testing and validation guide |
| [MIGRATION.md](MIGRATION.md) | Migration from previous versions |
| [CLAUDE.md](CLAUDE.md) | Development guide for contributors |

---

## 🏗️ Code Architecture

```
pi-camera-service/
├── camera_service/
│   ├── __init__.py
│   ├── api.py                 # FastAPI app with modern lifespan
│   ├── camera_controller.py   # Thread-safe camera control
│   ├── streaming_manager.py   # H.264 streaming management
│   ├── config.py              # Pydantic configuration
│   └── exceptions.py          # Custom exceptions
├── tests/
│   ├── test_api.py            # API tests (mocked)
│   ├── test_api_integration.py # Integration tests (live API)
│   ├── test_camera_controller.py
│   ├── test_config.py
│   └── test_streaming_manager.py
├── main.py                    # Entry point
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── .env.example              # Configuration template
├── test-api.sh               # v1.0 test script
├── test-api-v2.sh            # v2.0 test script (NEW)
├── install-service.sh        # Service installation
├── pi-camera-service.service # systemd file
├── CHANGELOG.md              # Version history (NEW)
├── VERSION                   # Version number (NEW)
└── UPGRADE_v2.md             # v2.0 upgrade guide (NEW)
```

---

## 🔄 Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Version 2.0.0 (2025-11-21)

**Major Features:**
- ✅ Autofocus control (modes, lens position, range)
- ✅ Snapshot capture (JPEG, base64 encoded)
- ✅ Manual white balance + NoIR presets
- ✅ Image processing (brightness, contrast, saturation, sharpness)
- ✅ HDR support (hardware + software modes)
- ✅ ROI / Digital zoom
- ✅ Exposure limits
- ✅ Lens correction for wide-angle cameras
- ✅ Image transform (flip/rotation)
- ✅ Day/night detection
- ✅ NoIR camera optimization
- ✅ Enhanced metadata (10 new status fields)

**14 new endpoints**, **1200+ lines of code**, **100% backward compatible** with v1.0

See [UPGRADE_v2.md](UPGRADE_v2.md) for complete upgrade guide.

### Version 1.0.0

**Initial production release:**
- FastAPI-based HTTP API
- RTSP streaming to MediaMTX
- Auto/manual exposure control
- Auto white balance control
- Camera status endpoint
- API key authentication
- systemd service support
- Comprehensive test suite

---

## 🌟 Use Cases

### Surveillance with NoIR Camera
```bash
# Set day/night auto-detection
curl -X POST http://raspberrypi:8000/v1/camera/day_night_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto", "threshold_lux": 10.0}'

# Apply NoIR IR preset
curl -X POST http://raspberrypi:8000/v1/camera/awb_preset \
  -H "Content-Type: application/json" \
  -d '{"preset": "ir_850nm"}'
```

### Time-lapse Photography
```python
import requests
import time

for i in range(100):
    response = requests.post(
        "http://raspberrypi:8000/v1/camera/snapshot",
        json={"width": 4608, "height": 2592, "autofocus_trigger": True}
    )
    # Save snapshot...
    time.sleep(60)  # Every minute
```

### Computer Vision / ML
```python
# Capture snapshot for processing
snapshot = requests.post(
    "http://raspberrypi:8000/v1/camera/snapshot",
    json={"width": 640, "height": 480}
).json()

# Decode and process with OpenCV/TensorFlow
image = base64.b64decode(snapshot['image_base64'])
# ... ML processing ...
```

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

See [CLAUDE.md](CLAUDE.md) for development guide.

To contribute:
1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

If you encounter issues:
1. Check [TESTING.md](TESTING.md) - Run `./test-api-v2.sh`
2. View logs: `sudo journalctl -u pi-camera-service -f`
3. Check [SERVICE-SETUP.md](SERVICE-SETUP.md) - Troubleshooting section
4. Open an issue on [GitHub](https://github.com/gmathy2104/pi-camera-service/issues)

---

## 🙏 Acknowledgments

- Raspberry Pi Foundation for Camera Module 3 and libcamera
- FastAPI team for the excellent framework
- MediaMTX for versatile streaming server
- Community contributors

---

**Built with ❤️ for Raspberry Pi**

🤖 Enhanced with [Claude Code](https://claude.com/claude-code)
