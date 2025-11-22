# Pi Camera Service - API Reference

This document provides a complete reference for the Pi Camera Service HTTP API, including all available features, endpoints, and connection instructions.

> **Note**: This document primarily covers v1.0 API endpoints. For comprehensive documentation of v2.0+ features (autofocus, snapshot, HDR, exposure value, noise reduction, capabilities, framerate control, FOV mode, etc.), see the main [README.md](../README.md).
>
> **New in v2.4**: Field of View (FOV) mode selection - documented below.

## Overview

The Pi Camera Service is a REST API that controls a Raspberry Pi camera and streams H.264 video to MediaMTX via RTSP. It provides real-time control over camera settings including exposure, gain, white balance, and streaming.

**Base URL:** `http://<RASPBERRY_PI_IP>:8000`

**API Version:** v2.4.0 (this document covers v1.0 core features + v2.4 FOV mode)

**Protocol:** HTTP/REST

**Response Format:** JSON

---

## Connection Information

### Network Access

The API listens on all network interfaces by default:
- **Host:** `0.0.0.0` (all interfaces)
- **Port:** `8000` (configurable via `CAMERA_PORT`)
- **Protocol:** HTTP (HTTPS not configured by default)

### Finding the Raspberry Pi IP Address

On the Raspberry Pi:
```bash
hostname -I
```

### Testing Connectivity

```bash
# From any computer on the same network
curl http://<RASPBERRY_PI_IP>:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "camera_configured": true,
  "streaming_active": true,
  "version": "1.0.0"
}
```

---

## Authentication

### API Key Authentication (Optional)

If the service is configured with an API key, all `/v1/*` endpoints require authentication.

**Configuration:**
```bash
# On Raspberry Pi, set environment variable
export CAMERA_API_KEY="your-secret-key"

# Or in .env file
CAMERA_API_KEY=your-secret-key
```

**Authentication Header:**
```
X-API-Key: your-secret-key
```

**Example:**
```bash
curl -H "X-API-Key: your-secret-key" http://<PI_IP>:8000/v1/camera/status
```

**Note:** The `/health` endpoint does NOT require authentication.

### No Authentication

If `CAMERA_API_KEY` is not set, authentication is disabled and all endpoints are publicly accessible.

---

## API Features

The API provides the following capabilities:

1. **Camera Control**
   - Get real-time camera status (lux, exposure, gain, temperature)
   - Enable/disable auto exposure
   - Set manual exposure time and gain
   - Enable/disable auto white balance (AWB)

2. **Streaming Control**
   - Start/stop H.264 RTSP streaming to MediaMTX
   - Check streaming status

3. **System Monitoring**
   - Health check endpoint
   - Service version information

---

## Endpoints Reference

### System Endpoints

#### GET /health

Health check endpoint for monitoring service availability.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "camera_configured": true,
  "streaming_active": true,
  "version": "1.0.0"
}
```

**Example:**
```bash
curl http://<PI_IP>:8000/health
```

---

### Camera Control Endpoints

All camera endpoints require the `/v1` prefix and authentication (if configured).

#### GET /v1/camera/status

Get current camera status including exposure settings, gain, brightness, and streaming state.

**Authentication:** Required (if configured)

**Response:**
```json
{
  "lux": 100.5,
  "exposure_us": 10000,
  "analogue_gain": 2.5,
  "colour_temperature": 4500.0,
  "auto_exposure": true,
  "streaming": true
}
```

**Response Fields:**
- `lux` (float|null): Estimated scene brightness in lux
- `exposure_us` (int|null): Current exposure time in microseconds
- `analogue_gain` (float|null): Current analogue gain (1.0-16.0)
- `colour_temperature` (float|null): Estimated color temperature in Kelvin
- `auto_exposure` (bool): Whether auto exposure is enabled
- `streaming` (bool): Whether RTSP streaming is active

**Example:**
```bash
curl -H "X-API-Key: your-key" http://<PI_IP>:8000/v1/camera/status
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://<PI_IP>:8000/v1/camera/status",
    headers={"X-API-Key": "your-key"}
)
status = response.json()
print(f"Lux: {status['lux']}")
print(f"Exposure: {status['exposure_us']}µs")
```

---

#### POST /v1/camera/auto_exposure

Enable or disable automatic exposure control.

**Authentication:** Required (if configured)

**Request Body:**
```json
{
  "enabled": true
}
```

**Request Fields:**
- `enabled` (bool, required): `true` to enable auto exposure, `false` to disable

**Response:**
```json
{
  "status": "ok",
  "auto_exposure": true
}
```

**Example - Enable:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/auto_exposure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"enabled": true}'
```

**Example - Disable:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/auto_exposure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"enabled": false}'
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://<PI_IP>:8000/v1/camera/auto_exposure",
    headers={"X-API-Key": "your-key"},
    json={"enabled": True}
)
print(response.json())
```

**When to Use:**
- Enable when lighting conditions vary
- Disable before setting manual exposure

---

#### POST /v1/camera/manual_exposure

Set manual exposure parameters (time and gain).

**Authentication:** Required (if configured)

**Request Body:**
```json
{
  "exposure_us": 10000,
  "gain": 2.0
}
```

**Request Fields:**
- `exposure_us` (int, required): Exposure time in microseconds (100 - 1,000,000)
- `gain` (float, optional): Analogue gain (1.0 - 16.0), defaults to 1.0

**Response:**
```json
{
  "status": "ok",
  "exposure_us": 10000,
  "gain": 2.0
}
```

**Validation Rules:**
- Exposure time: 100µs (0.1ms) to 1,000,000µs (1 second)
- Gain: 1.0 (no gain) to 16.0 (maximum gain)
- Auto exposure is automatically disabled when setting manual exposure

**Error Response (422):**
```json
{
  "detail": "exposure_us must be >= 100 (got 50)"
}
```

**Example - Basic:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"exposure_us": 10000, "gain": 2.0}'
```

**Example - Long Exposure (Low Light):**
```bash
# 100ms exposure, high gain for very dark scenes
curl -X POST http://<PI_IP>:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"exposure_us": 100000, "gain": 8.0}'
```

**Example - Fast Exposure (Motion):**
```bash
# 1ms exposure, low gain for fast-moving subjects
curl -X POST http://<PI_IP>:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"exposure_us": 1000, "gain": 1.0}'
```

**Python Example:**
```python
import requests

# Set 20ms exposure with 2x gain
response = requests.post(
    "http://<PI_IP>:8000/v1/camera/manual_exposure",
    headers={"X-API-Key": "your-key"},
    json={"exposure_us": 20000, "gain": 2.0}
)
print(response.json())
```

**Exposure Guidelines:**
- **Bright scenes:** 100-5000µs, gain 1.0-2.0
- **Normal lighting:** 5000-20000µs, gain 1.0-4.0
- **Low light:** 20000-100000µs, gain 4.0-8.0
- **Very dark:** 100000-1000000µs, gain 8.0-16.0

---

#### POST /v1/camera/awb

Enable or disable automatic white balance.

**Authentication:** Required (if configured)

**Request Body:**
```json
{
  "enabled": true
}
```

**Request Fields:**
- `enabled` (bool, required): `true` to enable AWB, `false` to disable

**Response:**
```json
{
  "status": "ok",
  "awb_enabled": true
}
```

**Example - Enable:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/awb \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"enabled": true}'
```

**Example - Disable:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/awb \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"enabled": false}'
```

**When to Use:**
- Enable for automatic color correction
- Disable for consistent color temperature

---

#### POST /v1/camera/fov_mode (v2.4)

Set the Field of View (FOV) mode to control sensor readout behavior across different resolutions.

**Authentication:** Required (if configured)

**Request Body:**
```json
{
  "mode": "scale"
}
```

**Request Fields:**
- `mode` (string, required): FOV mode - either `"scale"` or `"crop"`

**Response:**
```json
{
  "status": "ok",
  "mode": "scale",
  "description": "Full sensor readout with downscaling → Constant field of view"
}
```

**FOV Modes:**

- **`scale`** (default): Constant field of view at all resolutions
  - Reads full sensor area (4608x2592 for IMX708)
  - Hardware ISP downscales to target resolution
  - Better image quality from downsampling vs cropping
  - Perfect for surveillance, monitoring, consistent framing
  - Use when you want the same field of view regardless of resolution

- **`crop`**: Digital zoom effect (sensor crop)
  - Reads only required sensor area for target resolution
  - FOV reduces at lower resolutions (telephoto effect)
  - Lower processing load, faster sensor readout
  - Useful for zoom/telephoto applications
  - Use when you want a "zoomed in" view at lower resolutions

**Example - Set to scale mode:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/fov_mode \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"mode": "scale"}'
```

**Example - Set to crop mode:**
```bash
curl -X POST http://<PI_IP>:8000/v1/camera/fov_mode \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"mode": "crop"}'
```

**Python Example:**
```python
import requests

# Set to scale mode for constant FOV
response = requests.post(
    "http://<PI_IP>:8000/v1/camera/fov_mode",
    headers={"X-API-Key": "your-key"},
    json={"mode": "scale"}
)
print(response.json())

# Set to crop mode for digital zoom effect
response = requests.post(
    "http://<PI_IP>:8000/v1/camera/fov_mode",
    headers={"X-API-Key": "your-key"},
    json={"mode": "crop"}
)
print(response.json())
```

**Combined with Resolution Change:**

You can also set FOV mode when changing resolution:

```bash
curl -X POST http://<PI_IP>:8000/v1/camera/resolution \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "width": 1280,
    "height": 720,
    "fov_mode": "crop",
    "restart_streaming": true
  }'
```

**When to Use:**
- Use `scale` for surveillance cameras where consistent framing is essential
- Use `crop` when you want different zoom levels at different resolutions
- Change to `crop` before lowering resolution if you want a telephoto effect
- Change to `scale` if lower resolutions appear too zoomed in

**Note:** Changes take effect on the next camera reconfiguration (resolution/framerate change).

---

#### GET /v1/camera/fov_mode (v2.4)

Query the current FOV mode.

**Authentication:** Required (if configured)

**Response:**
```json
{
  "mode": "scale",
  "description": "Full sensor readout with downscaling → Constant field of view"
}
```

**Example:**
```bash
curl -H "X-API-Key: your-key" http://<PI_IP>:8000/v1/camera/fov_mode
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://<PI_IP>:8000/v1/camera/fov_mode",
    headers={"X-API-Key": "your-key"}
)
mode_info = response.json()
print(f"Current FOV mode: {mode_info['mode']}")
print(f"Description: {mode_info['description']}")
```

---

### Streaming Control Endpoints

#### POST /v1/streaming/start

Start H.264 streaming to MediaMTX via RTSP.

**Authentication:** Required (if configured)

**Request Body:** None

**Response:**
```json
{
  "status": "ok",
  "streaming": true
}
```

**Example:**
```bash
curl -X POST http://<PI_IP>:8000/v1/streaming/start \
  -H "X-API-Key: your-key"
```

**Python Example:**
```python
import requests

response = requests.post(
    "http://<PI_IP>:8000/v1/streaming/start",
    headers={"X-API-Key": "your-key"}
)
print(response.json())
```

**Note:** Streaming starts automatically when the service starts. This endpoint is useful if you manually stopped streaming and want to restart it.

---

#### POST /v1/streaming/stop

Stop H.264 streaming.

**Authentication:** Required (if configured)

**Request Body:** None

**Response:**
```json
{
  "status": "ok",
  "streaming": false
}
```

**Example:**
```bash
curl -X POST http://<PI_IP>:8000/v1/streaming/stop \
  -H "X-API-Key: your-key"
```

**When to Use:**
- Temporarily stop streaming to save bandwidth
- Stop streaming before camera configuration changes
- Debugging streaming issues

---

## Video Stream Access

The API controls the camera, but video is streamed separately via MediaMTX.

**RTSP URL:** `rtsp://<RASPBERRY_PI_IP>:8554/cam`

### Accessing the Stream

**VLC (Desktop):**
1. Open VLC
2. Media → Open Network Stream
3. Enter: `rtsp://<PI_IP>:8554/cam`
4. Click Play

**ffplay (Command Line):**
```bash
ffplay rtsp://<PI_IP>:8554/cam
```

**Python (OpenCV):**
```python
import cv2

stream_url = "rtsp://<PI_IP>:8554/cam"
cap = cv2.VideoCapture(stream_url)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow('Camera Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

**JavaScript (Web Browser):**
```html
<!-- Using MediaMTX WebRTC -->
<video id="video" autoplay controls></video>
<script>
const pc = new RTCPeerConnection();
pc.addTransceiver('video', {direction: 'recvonly'});

pc.createOffer().then(offer => {
  pc.setLocalDescription(offer);
  return fetch('http://<PI_IP>:8889/cam/whep', {
    method: 'POST',
    body: offer.sdp
  });
}).then(res => res.text())
.then(answer => {
  pc.setRemoteDescription(new RTCSessionDescription({
    type: 'answer',
    sdp: answer
  }));
});

pc.ontrack = event => {
  document.getElementById('video').srcObject = event.streams[0];
};
</script>
```

---

## Error Handling

### HTTP Status Codes

- **200 OK**: Request successful
- **401 Unauthorized**: Missing or invalid API key
- **422 Unprocessable Entity**: Invalid request parameters
- **500 Internal Server Error**: Server error (camera failure, etc.)
- **503 Service Unavailable**: Camera not initialized

### Error Response Format

```json
{
  "detail": "Error description here"
}
```

### Common Errors

**401 - Invalid API Key:**
```json
{
  "detail": "Invalid or missing API key"
}
```

**422 - Invalid Parameters:**
```json
{
  "detail": "exposure_us must be >= 100 (got 50)"
}
```

**503 - Service Not Ready:**
```json
{
  "detail": "Camera not initialized"
}
```

---

## Complete Examples

### Python Client Class

```python
import requests
from typing import Optional, Dict, Any

class PiCameraClient:
    """Client for Pi Camera Service API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['X-API-Key'] = api_key

    def health(self) -> Dict[str, Any]:
        """Check service health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Dict[str, Any]:
        """Get camera status."""
        response = requests.get(
            f"{self.base_url}/v1/camera/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def set_auto_exposure(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable auto exposure."""
        response = requests.post(
            f"{self.base_url}/v1/camera/auto_exposure",
            headers=self.headers,
            json={"enabled": enabled}
        )
        response.raise_for_status()
        return response.json()

    def set_manual_exposure(self, exposure_us: int, gain: float = 1.0) -> Dict[str, Any]:
        """Set manual exposure parameters."""
        response = requests.post(
            f"{self.base_url}/v1/camera/manual_exposure",
            headers=self.headers,
            json={"exposure_us": exposure_us, "gain": gain}
        )
        response.raise_for_status()
        return response.json()

    def set_awb(self, enabled: bool) -> Dict[str, Any]:
        """Enable or disable auto white balance."""
        response = requests.post(
            f"{self.base_url}/v1/camera/awb",
            headers=self.headers,
            json={"enabled": enabled}
        )
        response.raise_for_status()
        return response.json()

    def start_streaming(self) -> Dict[str, Any]:
        """Start video streaming."""
        response = requests.post(
            f"{self.base_url}/v1/streaming/start",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def stop_streaming(self) -> Dict[str, Any]:
        """Stop video streaming."""
        response = requests.post(
            f"{self.base_url}/v1/streaming/stop",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = PiCameraClient("http://192.168.1.100:8000", api_key="your-key")

# Check health
print(client.health())

# Get camera status
status = client.get_status()
print(f"Brightness: {status['lux']} lux")
print(f"Exposure: {status['exposure_us']}µs")

# Set manual exposure for low light
client.set_manual_exposure(exposure_us=50000, gain=4.0)

# Enable auto exposure
client.set_auto_exposure(enabled=True)
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

class PiCameraClient {
    constructor(baseUrl, apiKey = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = apiKey ? { 'X-API-Key': apiKey } : {};
    }

    async health() {
        const response = await axios.get(`${this.baseUrl}/health`);
        return response.data;
    }

    async getStatus() {
        const response = await axios.get(
            `${this.baseUrl}/v1/camera/status`,
            { headers: this.headers }
        );
        return response.data;
    }

    async setAutoExposure(enabled) {
        const response = await axios.post(
            `${this.baseUrl}/v1/camera/auto_exposure`,
            { enabled },
            { headers: this.headers }
        );
        return response.data;
    }

    async setManualExposure(exposureUs, gain = 1.0) {
        const response = await axios.post(
            `${this.baseUrl}/v1/camera/manual_exposure`,
            { exposure_us: exposureUs, gain },
            { headers: this.headers }
        );
        return response.data;
    }

    async setAwb(enabled) {
        const response = await axios.post(
            `${this.baseUrl}/v1/camera/awb`,
            { enabled },
            { headers: this.headers }
        );
        return response.data;
    }

    async startStreaming() {
        const response = await axios.post(
            `${this.baseUrl}/v1/streaming/start`,
            {},
            { headers: this.headers }
        );
        return response.data;
    }

    async stopStreaming() {
        const response = await axios.post(
            `${this.baseUrl}/v1/streaming/stop`,
            {},
            { headers: this.headers }
        );
        return response.data;
    }
}

// Usage
(async () => {
    const client = new PiCameraClient('http://192.168.1.100:8000', 'your-key');

    // Check health
    const health = await client.health();
    console.log('Service healthy:', health.status === 'healthy');

    // Get status
    const status = await client.getStatus();
    console.log(`Lux: ${status.lux}, Exposure: ${status.exposure_us}µs`);

    // Set manual exposure
    await client.setManualExposure(20000, 2.0);
    console.log('Manual exposure set');
})();
```

### curl Script

```bash
#!/bin/bash

# Configuration
PI_IP="192.168.1.100"
API_KEY="your-secret-key"
BASE_URL="http://${PI_IP}:8000"

# Helper function
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -H "X-API-Key: ${API_KEY}" \
            "${BASE_URL}${endpoint}"
    else
        curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -H "X-API-Key: ${API_KEY}" \
            -d "$data" \
            "${BASE_URL}${endpoint}"
    fi
}

# Check health
echo "Checking health..."
api_call GET /health

# Get status
echo -e "\nGetting camera status..."
api_call GET /v1/camera/status

# Set manual exposure
echo -e "\nSetting manual exposure..."
api_call POST /v1/camera/manual_exposure '{"exposure_us": 10000, "gain": 2.0}'

# Enable auto exposure
echo -e "\nEnabling auto exposure..."
api_call POST /v1/camera/auto_exposure '{"enabled": true}'
```

---

## Common Use Cases

### Use Case 1: Monitoring Bright Outdoor Scene

```python
# Enable auto exposure and AWB for changing light conditions
client.set_auto_exposure(enabled=True)
client.set_awb(enabled=True)

# Monitor status
status = client.get_status()
print(f"Scene brightness: {status['lux']} lux")
```

### Use Case 2: Low Light Photography

```python
# Disable auto exposure for manual control
client.set_auto_exposure(enabled=False)

# Set long exposure and high gain for low light
client.set_manual_exposure(exposure_us=100000, gain=8.0)  # 100ms, 8x gain

# Check result
status = client.get_status()
print(f"Exposure: {status['exposure_us']}µs, Gain: {status['analogue_gain']}")
```

### Use Case 3: Fast Motion Capture

```python
# Short exposure to freeze motion
client.set_manual_exposure(exposure_us=1000, gain=1.0)  # 1ms, no gain

# Requires bright lighting for good exposure
```

### Use Case 4: Timelapse Photography

```python
import time

# Disable auto exposure for consistent images
client.set_auto_exposure(enabled=False)
client.set_manual_exposure(exposure_us=10000, gain=2.0)

# Start streaming
client.start_streaming()

# Capture frames at intervals (handled by video client)
# ...

# Stop streaming when done
client.stop_streaming()
```

---

## Quick Reference

### Endpoint Summary

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| GET | `/health` | Health check | No |
| GET | `/v1/camera/status` | Get camera status | Yes* |
| POST | `/v1/camera/auto_exposure` | Toggle auto exposure | Yes* |
| POST | `/v1/camera/manual_exposure` | Set manual exposure | Yes* |
| POST | `/v1/camera/awb` | Toggle AWB | Yes* |
| POST | `/v1/streaming/start` | Start streaming | Yes* |
| POST | `/v1/streaming/stop` | Stop streaming | Yes* |

*Only if `CAMERA_API_KEY` is configured

### Parameter Ranges

| Parameter | Minimum | Maximum | Unit |
|-----------|---------|---------|------|
| exposure_us | 100 | 1,000,000 | microseconds |
| gain | 1.0 | 16.0 | multiplier |
| width | 64 | 4096 | pixels |
| height | 64 | 4096 | pixels |
| framerate | 1 | 120 | fps |

---

## For Claude Code / AI Assistants

When working with this API:

1. **Base URL**: Always use `http://<PI_IP>:8000` (replace `<PI_IP>` with actual IP)
2. **Authentication**: Include `X-API-Key` header if API key is configured
3. **API Version**: All camera/streaming endpoints use `/v1` prefix
4. **Content-Type**: Always use `application/json` for POST requests
5. **Error Handling**: Check HTTP status codes and parse `detail` field in error responses
6. **Streaming**: Video is via RTSP at `rtsp://<PI_IP>:8554/cam`, separate from HTTP API
7. **Common Pattern**:
   - Check health first: `GET /health`
   - Get current status: `GET /v1/camera/status`
   - Make changes: `POST /v1/camera/*`
   - Verify changes: `GET /v1/camera/status` again

**Example Workflow:**
```python
# 1. Check service is running
health = requests.get("http://<PI_IP>:8000/health").json()
assert health['status'] == 'healthy'

# 2. Get current state
status = requests.get(
    "http://<PI_IP>:8000/v1/camera/status",
    headers={"X-API-Key": "key"}
).json()

# 3. Make changes based on needs
if status['lux'] < 10:  # Low light
    requests.post(
        "http://<PI_IP>:8000/v1/camera/manual_exposure",
        headers={"X-API-Key": "key"},
        json={"exposure_us": 50000, "gain": 8.0}
    )
```

---

## System Monitoring Endpoints (v2.5)

### GET /v1/system/status

Get comprehensive Raspberry Pi system health metrics.

**Authentication:** Required (if configured)

**Response:**
```json
{
  "temperature": {
    "cpu_c": 50.7,
    "status": "normal"
  },
  "cpu": {
    "usage_percent": 32.5,
    "load_average": {
      "1min": 0.88,
      "5min": 0.62,
      "15min": 0.56
    },
    "cores": 4
  },
  "memory": {
    "total_mb": 16219.1,
    "used_mb": 1364.6,
    "available_mb": 14854.5,
    "percent": 8.4
  },
  "network": {
    "bytes_sent": 18863322109,
    "bytes_received": 11251936223,
    "packets_sent": 6849046,
    "packets_received": 2162715,
    "wifi": {
      "signal_dbm": -70,
      "quality_percent": 60,
      "status": "fair"
    },
    "interface": "wlan0"
  },
  "disk": {
    "total_gb": 234.6,
    "used_gb": 3.8,
    "free_gb": 218.9,
    "percent": 1.7
  },
  "uptime": {
    "service_seconds": 8.3,
    "system_seconds": 13949.0,
    "system_days": 0.2
  },
  "throttled": {
    "currently_throttled": false,
    "under_voltage_detected": false,
    "frequency_capped": false,
    "currently_throttled_temperature": false,
    "has_occurred": false,
    "raw_value": "0x0"
  }
}
```

**Response Fields:**

**temperature** (optional):
- `cpu_c` (float): CPU/GPU temperature in Celsius
- `status` (string): Temperature status - "normal" (< 60°C), "warm" (60-70°C), "hot" (70-80°C), "critical" (> 80°C)

**cpu** (optional):
- `usage_percent` (float): Current CPU usage percentage
- `load_average` (dict): System load average
  - `1min` (float): 1-minute load average
  - `5min` (float): 5-minute load average
  - `15min` (float): 15-minute load average
- `cores` (int): Number of CPU cores

**memory** (optional):
- `total_mb` (float): Total RAM in megabytes
- `used_mb` (float): Used RAM in megabytes
- `available_mb` (float): Available RAM in megabytes
- `percent` (float): Memory usage percentage

**network** (optional):
- `bytes_sent` (int): Total bytes sent since boot
- `bytes_received` (int): Total bytes received since boot
- `packets_sent` (int): Total packets sent
- `packets_received` (int): Total packets received
- `wifi` (optional): WiFi signal information
  - `signal_dbm` (int): Signal strength in dBm
  - `quality_percent` (float): Signal quality percentage (0-100)
  - `status` (string): Signal status - "excellent" (≥ -50 dBm), "good" (-50 to -60), "fair" (-60 to -70), "weak" (< -70)
- `interface` (string): Active network interface (e.g., "wlan0", "eth0")

**disk** (optional):
- `total_gb` (float): Total disk space in gigabytes
- `used_gb` (float): Used disk space in gigabytes
- `free_gb` (float): Free disk space in gigabytes
- `percent` (float): Disk usage percentage

**uptime**:
- `service_seconds` (float): Service uptime in seconds
- `system_seconds` (float, optional): System uptime in seconds
- `system_days` (float, optional): System uptime in days

**throttled** (optional, Raspberry Pi specific):
- `currently_throttled` (bool): Currently being throttled
- `under_voltage_detected` (bool): Under-voltage detected
- `frequency_capped` (bool): CPU frequency is capped
- `currently_throttled_temperature` (bool): Currently throttled due to temperature
- `has_occurred` (bool): Any throttling has occurred since boot
- `raw_value` (string): Raw hex value from vcgencmd

**Example:**
```bash
curl -H "X-API-Key: your-key" http://<PI_IP>:8000/v1/system/status
```

**Python Example:**
```python
import requests

response = requests.get(
    "http://<PI_IP>:8000/v1/system/status",
    headers={"X-API-Key": "your-key"}
)
status = response.json()

# Check temperature
temp = status['temperature']
print(f"CPU Temperature: {temp['cpu_c']}°C ({temp['status']})")

# Check WiFi signal
if 'wifi' in status['network']:
    wifi = status['network']['wifi']
    print(f"WiFi Signal: {wifi['signal_dbm']} dBm ({wifi['status']})")

# Check throttling
if status['throttled'] and status['throttled']['has_occurred']:
    print("⚠️ Throttling detected! Check power supply and cooling.")
```

**When to Use:**
- Monitor CPU temperature during intensive video encoding
- Detect WiFi signal degradation affecting stream quality
- Alert on thermal throttling or under-voltage (power supply issues)
- Track memory and disk usage for long-running deployments
- Verify system stability for 24/7 camera operations

**Note:** Some metrics require `psutil` Python package and may not be available on all systems. Fields that are unavailable will be `null`.

---

## Support

For issues or questions:
- Check service logs: `sudo journalctl -u pi-camera-service -f`
- Verify service status: `sudo systemctl status pi-camera-service`
- Test connectivity: `curl http://<PI_IP>:8000/health`
- See `SERVICE-SETUP.md` for troubleshooting
