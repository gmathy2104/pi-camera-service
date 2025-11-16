# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pi Camera Service v1.0** is a production-ready FastAPI-based microservice running on Raspberry Pi that controls a Raspberry Pi Camera (libcamera/Picamera2) and streams H.264 video to MediaMTX via RTSP.

The service exposes an HTTP API (v1) for:
- Starting/stopping streaming to MediaMTX
- Toggling auto-exposure on/off
- Setting manual exposure (time + gain)
- Toggling auto white balance (AWB)
- Retrieving current camera status (lux, exposure, gain, color temperature, etc.)
- Health checks for monitoring

**Key Features:**
- API key authentication (optional)
- Environment variable configuration
- Comprehensive logging
- Full type safety with Pydantic
- Thread-safe operations with RLock
- Proper resource cleanup
- Extensive test coverage (>80%)
- Modern FastAPI patterns (lifespan, dependency injection)

## Architecture

### High-Level Flow
```
Pi Camera v3 → Picamera2/libcamera → H.264 encoder → MediaMTX (RTSP/WebRTC/HLS)
                     ↑                      ↑
                     └──────────────────────┘
                  Pi Camera Service API (FastAPI)
                             ↑
                  External App (backend, UI...)
```

### Component Responsibilities

**camera_service/config.py**
- Centralized configuration using Pydantic `BaseSettings`
- All settings configurable via environment variables (prefix: `CAMERA_`)
- Comprehensive validation with clear error messages
- Defines video resolution, framerate, bitrate, RTSP URL, API settings
- Reads from `.env` file automatically
- Single `CONFIG` instance used throughout the application

**camera_service/exceptions.py**
- Custom exception hierarchy for the application
- `CameraError` (base), `CameraNotAvailableError`, `InvalidParameterError`, `StreamingError`, `ConfigurationError`
- Enables proper error handling and meaningful error messages

**camera_service/camera_controller.py** (`CameraController`)
- Wraps Picamera2 interface with thread-safe controls using `RLock` (reentrant lock)
- Manages camera configuration, initialization, and cleanup
- Handles exposure controls (auto/manual) with hardware limits validation
- Manages AWB (auto white balance) settings
- Provides camera status via metadata retrieval
- Comprehensive logging at all operation points
- Proper resource cleanup via `cleanup()` method

**camera_service/streaming_manager.py** (`StreamingManager`)
- Manages H.264 encoding and RTSP streaming lifecycle
- Uses `H264Encoder` with `FfmpegOutput` for RTSP transport
- Thread-safe operations with `RLock`
- Comprehensive error handling with automatic cleanup on failure
- Detailed logging for all streaming operations
- Proper resource cleanup in `finally` blocks

**camera_service/api.py**
- FastAPI application with modern patterns (v1.0)
- **Lifespan context manager** (replaces deprecated on_event)
- **Dependency injection** for controllers
- **API key authentication** via `X-API-Key` header
- Comprehensive Pydantic models for all requests/responses
- Global exception handlers for all custom exceptions
- Health check endpoint (`/health`) for monitoring
- API versioning with `/v1` prefix
- Detailed docstrings on all endpoints
- Proper HTTP status codes (401, 422, 500, 503)

**main.py**
- Entry point that launches uvicorn server
- Configurable host/port via `CONFIG`
- Log level passed to uvicorn

### Critical Design Patterns

1. **Modern Lifecycle Management**: Uses `@asynccontextmanager` lifespan instead of deprecated `on_event()`
2. **Dependency Injection**: FastAPI dependencies for `CameraController` and `StreamingManager`
3. **Reentrant Thread Safety**: Both controllers use `RLock` for nested lock acquisition
4. **Configuration as Code**: Pydantic BaseSettings with validation and environment variable support
5. **Comprehensive Error Handling**: Custom exceptions with global handlers
6. **Resource Cleanup**: Proper cleanup in lifespan shutdown and controller `cleanup()` methods
7. **Separation of Concerns**: Clear boundaries between configuration, control, streaming, and API layers
8. **Type Safety**: Full type hints with Pydantic models throughout
9. **Logging First**: All operations logged for observability

## Development Commands

### Environment Setup
```bash
# Install system dependencies first
sudo apt install python3-picamera2 python3-libcamera libcamera-apps ffmpeg

# Create virtual environment with --system-site-packages flag
# This is REQUIRED to access picamera2 (installed via APT)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies (for testing, linting, etc.)
pip install -r requirements-dev.txt
```

**Critical**: The `--system-site-packages` flag is **required** because `picamera2` is installed via APT, not pip. Without this flag, the service will fail to start with `ModuleNotFoundError: No module named 'picamera2'`.

### Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration (optional - defaults work for most cases)
nano .env

# Common environment variables:
# CAMERA_WIDTH=1920
# CAMERA_HEIGHT=1080
# CAMERA_PORT=8000
# CAMERA_API_KEY=your-secret-key  # Enable authentication
# CAMERA_LOG_LEVEL=INFO
```

### Running the Service
```bash
# Start with default configuration
python main.py

# Start with custom environment variables
CAMERA_PORT=9000 CAMERA_LOG_LEVEL=DEBUG python main.py

# The API will be available at http://0.0.0.0:8000 (or configured port)
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=camera_service --cov-report=html
# Coverage report will be in htmlcov/index.html

# Run specific test file
pytest tests/test_api.py

# Run specific test class
pytest tests/test_config.py::TestCameraConfig

# Run specific test
pytest tests/test_camera_controller.py::TestCameraControllerExposure::test_set_auto_exposure_enable

# Run tests in parallel (faster)
pytest -n auto
```

### Code Quality
```bash
# Format code with black
black camera_service tests

# Lint with ruff
ruff check camera_service tests

# Type check with mypy
mypy camera_service
```

### Testing the API

**Without authentication:**
```bash
# Health check
curl http://localhost:8000/health

# Get camera status (note /v1 prefix)
curl http://localhost:8000/v1/camera/status

# Enable auto-exposure
curl -X POST http://localhost:8000/v1/camera/auto_exposure \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Set manual exposure (20ms, gain 2.0)
curl -X POST http://localhost:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -d '{"exposure_us": 20000, "gain": 2.0}'

# Toggle AWB
curl -X POST http://localhost:8000/v1/camera/awb \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Start/stop streaming
curl -X POST http://localhost:8000/v1/streaming/start
curl -X POST http://localhost:8000/v1/streaming/stop
```

**With authentication:**
```bash
# Set API key (export or in .env)
export CAMERA_API_KEY="my-secret-key"

# All requests must include X-API-Key header
curl -H "X-API-Key: my-secret-key" http://localhost:8000/v1/camera/status

# Health check doesn't require authentication
curl http://localhost:8000/health
```

### Verifying the RTSP Stream
```bash
# Using VLC (from another machine)
vlc rtsp://<PI_IP>:8554/cam

# Or with ffplay
ffplay rtsp://<PI_IP>:8554/cam

# Or with ffmpeg
ffmpeg -i rtsp://<PI_IP>:8554/cam -f null -
```

## MediaMTX Configuration

The service publishes H.264 to `rtsp://127.0.0.1:8554/cam` by default.

**Critical**: In `mediamtx.yml`, the `cam` path must be configured as `source: publisher`:
```yaml
paths:
  cam:
    source: publisher
```

**Do NOT use** `source: rpiCamera` on this path, as it will conflict with the Pi Camera Service trying to access the camera.

## Key Configuration Points

**camera_service/config.py** - Modify these values to change defaults:
- `width`, `height`: Video resolution (default 1920x1080)
- `framerate`: FPS (default 30)
- `bitrate`: H.264 bitrate in bits/s (default 8Mbps)
- `rtsp_url`: MediaMTX RTSP endpoint (default `rtsp://127.0.0.1:8554/cam`)
- `enable_awb`: Auto white balance on startup (default True)
- `default_auto_exposure`: Auto-exposure on startup (default True)

## API Endpoints Reference

**System:**
- `GET /health` - Health check endpoint (no authentication required)
  - Returns: `{status, camera_configured, streaming_active, version}`

**Camera Control (all require authentication if `CAMERA_API_KEY` is set):**
- `GET /v1/camera/status` - Get camera status and metadata
  - Returns: `{lux, exposure_us, analogue_gain, colour_temperature, auto_exposure, streaming}`

- `POST /v1/camera/auto_exposure` - Enable/disable auto exposure
  - Request: `{"enabled": bool}`
  - Response: `{status: "ok", auto_exposure: bool}`

- `POST /v1/camera/manual_exposure` - Set manual exposure
  - Request: `{"exposure_us": int (100-1000000), "gain": float (1.0-16.0)}`
  - Response: `{status: "ok", exposure_us: int, gain: float}`
  - Validation: Exposure 100-1,000,000 µs, Gain 1.0-16.0

- `POST /v1/camera/awb` - Enable/disable auto white balance
  - Request: `{"enabled": bool}`
  - Response: `{status: "ok", awb_enabled: bool}`

**Streaming:**
- `POST /v1/streaming/start` - Start H.264 streaming to MediaMTX
  - Response: `{status: "ok", streaming: bool}`

- `POST /v1/streaming/stop` - Stop H.264 streaming
  - Response: `{status: "ok", streaming: bool}`

**Authentication:**
- All `/v1/*` endpoints require `X-API-Key` header if `CAMERA_API_KEY` is configured
- `/health` endpoint does not require authentication
- Returns 401 if authentication fails

**Error Responses:**
- `401` - Unauthorized (missing/invalid API key)
- `422` - Validation error (invalid parameters)
- `500` - Internal server error
- `503` - Service unavailable (camera not initialized)

## Production Deployment

Use systemd to run the service automatically:

```ini
# /etc/systemd/system/pi-camera-service.service
[Unit]
Description=Pi Camera Service (FastAPI + Picamera2)
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi-camera-service
ExecStart=/home/pi/pi-camera-service/venv/bin/python /home/pi/pi-camera-service/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-camera-service
sudo systemctl start pi-camera-service
```

## Troubleshooting

**Camera not detected:**
```bash
rpicam-hello --list-cameras
```

**Check if picamera2 is installed:**
```bash
dpkg -l | grep picamera2
```

**View service logs (if using systemd):**
```bash
sudo journalctl -u pi-camera-service -f
```

**MediaMTX logs:**
```bash
sudo journalctl -u mediamtx -f
```
