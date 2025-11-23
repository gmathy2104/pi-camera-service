# Changelog

All notable changes to Pi Camera Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.8.1] - 2025-11-23

### Added

#### System Logs API with Real-Time Streaming
- **NEW FEATURE**: Remote access to service logs via HTTP API without requiring SSH access
  - **Problem Solved**: Debugging and monitoring required SSH access to Raspberry Pi, limiting remote troubleshooting capabilities
  - **Solution**: HTTP API endpoints for log retrieval with filtering and real-time streaming via Server-Sent Events (SSE)
  - **Impact**: Full remote debugging and monitoring capabilities for production deployments

#### New System Logs Endpoints

**1. `GET /v1/system/logs` - Log Retrieval with Filtering**
- Query recent logs (1-10,000 lines, default: 100)
- Filter by log level: INFO, WARNING, ERROR
- Search by keyword/pattern
- Returns JSON with log lines, count, and service name
- Examples:
  - `?lines=50` - Get last 50 lines
  - `?level=ERROR&lines=100` - Filter ERROR logs
  - `?search=resolution&lines=200` - Search for pattern
  - `?lines=500&level=ERROR&search=camera` - Combined filters

**2. `GET /v1/system/logs/stream` - Real-Time Log Streaming (SSE)**
- Server-Sent Events for continuous log monitoring
- Same filtering capabilities as retrieval endpoint (level, search)
- Auto-cleanup on client disconnect (no orphaned processes)
- Perfect for live debugging dashboards
- Examples:
  - Stream all logs in real-time
  - Stream only ERROR logs: `?level=ERROR`
  - Stream logs matching pattern: `?search=camera`

#### Implementation Details
- Uses `journalctl` to read systemd service logs
- No `sudo` required (service can read its own logs)
- Async subprocess management using `asyncio.create_subprocess_exec`
- Proper cleanup to prevent orphaned `journalctl` processes
- Added `LogsResponse` Pydantic model for structured responses
- Fixed `StreamingResponse` import conflict (renamed to `FastAPIStreamingResponse`)

### Changed
- API version bumped from 2.8.0 to 2.8.1
- `camera_service/api.py`:
  - Added `asyncio`, `subprocess` imports
  - Added `Query` parameter support
  - Renamed `StreamingResponse` import to avoid conflict with Pydantic model
  - Added `LogsResponse` model
  - Added two new system endpoints for logs

### Benefits
- **Remote Debugging**: Access logs from anywhere without SSH
- **Real-Time Monitoring**: Build live monitoring dashboards
- **Error Detection**: Filter and alert on ERROR logs instantly
- **Audit Trail**: Track camera operations and configuration changes
- **Client Integration**: Embed log viewers in web/mobile apps

### Use Cases

**1. Remote Debugging**:
```bash
# Get last 100 ERROR logs
curl -H "X-API-Key: your-key" \
  "http://<PI_IP>:8000/v1/system/logs?level=ERROR&lines=100"
```

**2. Live Log Monitoring (JavaScript)**:
```javascript
const eventSource = new EventSource('http://<PI_IP>:8000/v1/system/logs/stream?level=ERROR');
eventSource.onmessage = (event) => {
  console.log('New error:', event.data);
  // Send alert, update UI, etc.
};
```

**3. Search Configuration Changes**:
```bash
# Find all resolution changes
curl -H "X-API-Key: your-key" \
  "http://<PI_IP>:8000/v1/system/logs?search=resolution&lines=500"
```

**4. Monitor Service Health**:
```python
# Python script to monitor and alert on errors
import requests

url = "http://<PI_IP>:8000/v1/system/logs/stream"
params = {"level": "ERROR"}
headers = {"X-API-Key": "your-key"}

with requests.get(url, headers=headers, params=params, stream=True) as response:
    for line in response.iter_lines():
        if line and line.startswith(b'data: '):
            log_line = line[6:].decode('utf-8')
            send_alert(log_line)  # Your alert function
```

### Documentation
- Updated README.md with v2.8.1 feature announcement
- Enhanced `docs/api-reference.md` with comprehensive logs endpoint documentation
- Created `docs/examples.md` with practical use cases and integration examples
- Created `pi-camera-api-collection.json` (Postman/Insomnia collection)

### Technical Details
- Zero breaking changes - all new endpoints are additions
- Logs endpoint uses journalctl (standard on systemd systems)
- SSE streaming uses async I/O for efficient resource usage
- Proper subprocess cleanup on client disconnect
- Works with or without API key authentication
- Fully backwards compatible with existing clients

---

## [2.8.0] - 2025-11-23

### Added

#### Advanced Camera Controls Status Tracking
- **NEW FEATURE**: Camera status endpoint now includes current advanced control settings
  - **Problem Solved**: Clients couldn't verify which camera settings were active, leading to configuration confusion
  - **Solution**: Track and expose all advanced control values in real-time via `/v1/camera/status`
  - **Impact**: Full transparency of camera configuration for debugging and monitoring

#### New Status API Fields
**Enhanced `GET /v1/camera/status` Response** with 4 new fields:
- `exposure_value`: Current EV compensation value (-8.0 to +8.0, default: 0.0)
- `noise_reduction_mode`: Current noise reduction mode (off/fast/high_quality/minimal/zsl, default: off)
- `ae_constraint_mode`: Current auto-exposure constraint mode (normal/highlight/shadows/custom, default: normal)
- `ae_exposure_mode`: Current auto-exposure mode (normal/short/long/custom, default: normal)

All fields include default values and are updated in real-time when camera settings are changed.

### Changed
- `CameraController.__init__()`: Added instance variables to track advanced control values
- `CameraController.set_exposure_value()`: Now stores value in `_exposure_value`
- `CameraController.set_noise_reduction_mode()`: Now stores value in `_noise_reduction_mode`
- `CameraController.set_ae_constraint_mode()`: Now stores value in `_ae_constraint_mode`
- `CameraController.set_ae_exposure_mode()`: Now stores value in `_ae_exposure_mode`
- `CameraController.get_status()`: Returns advanced control values in status dict
- `CameraStatusResponse` model: Added 4 new optional fields for advanced controls
- Status endpoint handler: Now populates advanced control fields from camera status

### Benefits
- **Debugging**: Instantly verify which low-light/motion mode is active
- **Client UIs**: Display current camera configuration to users
- **Monitoring**: Track camera settings over time for diagnostics
- **Integration**: Clients can adapt behavior based on current camera mode

### Use Cases

**Verify Low-Light Mode is Active**:
```bash
curl http://localhost:8000/v1/camera/status | jq '{
  exposure_value,
  noise_reduction_mode,
  ae_constraint_mode,
  ae_exposure_mode
}'
```

**Expected output after `./scripts/set-low-light-mode.sh`**:
```json
{
  "exposure_value": 1.5,
  "noise_reduction_mode": "high_quality",
  "ae_constraint_mode": "shadows",
  "ae_exposure_mode": "long"
}
```

### Technical Details
- Zero breaking changes - all new fields are optional
- Default values set in `__init__`: EV=0.0, Noise=off, AE_constraint=normal, AE_exposure=normal
- Values persist for lifetime of `CameraController` instance
- Fully backwards compatible with existing clients

## [2.7.0] - 2025-11-23

### Added

#### Wide-Angle Camera Detection and Intelligent Sensor Mode Selection
- **NEW FEATURE**: Automatic wide-angle camera detection (Camera Module 3 Wide - 120° FOV)
  - **Problem Solved**: Wide-angle cameras were using cropped sensor modes (Mode 2), losing the wide 120° field of view advantage
  - **Solution**: Auto-detect wide vs standard cameras and intelligently select sensor mode to preserve FOV
  - **Impact**: Wide cameras now preserve full 120° FOV at all resolutions up to 1080p

#### Camera Type-Aware Sensor Mode Selection
The system now adapts sensor mode selection based on camera type:

**For Wide-Angle Cameras (120° FOV)**:
- **Always use full sensor** (Mode 0 or Mode 1) to preserve wide field of view
- Mode 2 (cropped) would lose the wide-angle advantage
- Recommended resolutions:
  - 720p-1080p: Mode 1 (2304x1296 @ 56fps) - Full sensor with binning
  - 4K: Mode 0 (4608x2592 @ 14fps) - Full sensor, no binning
  - All preserve full 120° FOV

**For Standard Cameras (66° FOV)**:
- Can use Mode 2 (cropped) for higher framerates at lower resolutions
- Mode 2 acceptable since cropping doesn't lose wide-angle advantage
- Optimized for framerate vs resolution tradeoffs

#### New API Fields - Camera Type Information

**Enhanced `GET /v1/camera/status` Response**:
- `is_wide_camera`: Boolean flag indicating wide-angle camera (120° FOV)
- `sensor_mode_width`: Sensor mode width being used (e.g., 2304 for Mode 1)
- `sensor_mode_height`: Sensor mode height being used (e.g., 1296 for Mode 1)

**Enhanced `GET /v1/camera/capabilities` Response**:
- `is_wide_camera`: Camera type detection result
- `field_of_view_degrees`: Field of view in degrees (120° for wide, 66° for standard)
- `sensor_modes`: Complete specifications for all 3 IMX708 sensor modes
  - Mode 0: 4608x2592 @ 14.35fps (full sensor, no binning)
  - Mode 1: 2304x1296 @ 56.03fps (full sensor with 2x2 binning)
  - Mode 2: 1536x864 @ 120.13fps (cropped sensor with 2x2 binning)
- `recommended_resolutions`: Array of recommended resolutions for this camera type
  - Includes resolution, label, max FPS, sensor mode, and FOV preservation info
  - Different recommendations for wide vs standard cameras

#### Wide-Angle Camera Detection Logic
- Detects Camera Module 3 Wide via model name: `imx708_wide_noir`, `imx708_wide`
- Logs camera type at startup for visibility
- Graceful fallback to standard camera if detection fails

### Changed
- Updated `CameraController._get_optimal_sensor_mode()` to consider camera type
- Wide cameras now default to Mode 1 for all resolutions ≤ 1080p (preserves 120° FOV)
- Standard cameras continue to use Mode 2 for ≤ 720p (optimizes framerate)
- Enhanced logging to show FOV preservation rationale in sensor mode selection

### Fixed
- **CRITICAL FIX**: Wide-angle cameras no longer lose field of view at lower resolutions
  - Root cause: Mode 2 crops the sensor, eliminating the wide-angle advantage
  - Impact: Users with Camera Module 3 Wide now get full 120° FOV at 720p and 1080p
  - Verified: `sensor_mode_width/height` shows 2304x1296 (Mode 1) instead of 1536x864 (Mode 2)

### Technical Details
- New method: `CameraController._detect_wide_camera() -> bool`
- New method: `CameraController._get_recommended_resolutions() -> list`
- Updated method: `_get_optimal_sensor_mode()` now accepts camera type parameter
- New instance variable: `self._is_wide_camera`
- API models updated: `CameraStatusResponse`, `CameraCapabilitiesResponse`
- Zero breaking changes - fully backwards compatible

### Use Cases
- **Surveillance with wide FOV**: Preserve 120° coverage at all resolutions
- **Dynamic preset selection**: Client can query recommended resolutions for camera type
- **Intelligent client UIs**: Display appropriate resolution options based on camera capabilities
- **FOV-aware applications**: Adjust counting lines, detection zones based on actual FOV

### Client Integration Example

```javascript
// Query camera capabilities
const capabilities = await fetch('/v1/camera/capabilities').then(r => r.json());

if (capabilities.is_wide_camera) {
  console.log(`Wide-angle camera detected: ${capabilities.field_of_view_degrees}° FOV`);

  // Use recommended resolutions that preserve full FOV
  const presets = capabilities.recommended_resolutions.map(res => ({
    label: res.label,
    width: res.width,
    height: res.height,
    maxFps: res.max_fps,
    fov: res.fov
  }));
}
```

### Upgrade Notes
- Existing deployments with Camera Module 3 Wide will automatically benefit from FOV preservation
- No configuration changes required - detection is automatic
- Check `/v1/camera/capabilities` to verify camera type detection
- Recommended to update client UIs to use `recommended_resolutions` endpoint for dynamic presets

## [2.6.1] - 2025-11-22

### Added

#### Intelligent Bitrate Auto-Selection
- **NEW FEATURE**: Automatic bitrate calculation based on resolution × framerate
  - **Formula**: ~6.5 Mbps per megapixel at 30fps, scaled with framerate
  - **Dynamic adjustment**: Bitrate automatically recalculates when resolution or framerate changes
  - **Safety limits**: Clamped between 2-25 Mbps for stability
  - **Fallback chain**: Calculation → .env value → 6 Mbps safe default

#### Enhanced Status Endpoint
- Added `bitrate_bps` field to `GET /v1/camera/status`
  - Shows current bitrate in bits per second
- Added `bitrate_mbps` field to `GET /v1/camera/status`
  - Shows current bitrate in megabits per second (rounded to 2 decimals)

### Changed
- Streaming now uses calculated bitrate instead of fixed .env value
- Bitrate automatically adjusts for optimal quality at each resolution/framerate
- Logging enhanced to show calculated bitrate for each configuration

### Fixed
- **CRITICAL FIX**: Resolved corrupted macroblock errors at 60fps
  - Root cause: 6 Mbps bitrate was too low for 720p@60fps
  - Now uses 12 Mbps for 720p@60fps (auto-calculated)
  - Prevents H.264 encoder quality degradation

### Bitrate Examples (Auto-Calculated)

| Resolution | Framerate | Calculated Bitrate | Quality         |
|------------|-----------|-------------------|------------------|
| 640x480    | 30fps     | 2.0 Mbps         | Min limit        |
| 1280x720   | 30fps     | 6.0 Mbps         | Good             |
| 1280x720   | 60fps     | 12.0 Mbps        | Excellent        |
| 1920x1080  | 30fps     | 13.3 Mbps        | High quality     |
| 1920x1080  | 60fps     | 25.0 Mbps        | Max limit        |
| 3840x2160  | 30fps     | 25.0 Mbps        | Max limit        |

### Technical Details
- New function: `calculate_optimal_bitrate(width, height, framerate) -> int`
- New method: `CameraController._get_optimal_bitrate() -> int`
- New method: `CameraController.get_current_bitrate() -> int`
- Bitrate recalculation integrated into `set_resolution()` and `set_framerate()`
- StreamingManager uses `camera.get_current_bitrate()` instead of `CONFIG.bitrate`
- Zero breaking changes - fully backwards compatible

## [2.6.0] - 2025-11-22

### Added

#### Intelligent IMX708 Sensor Mode Auto-Selection
- **NEW FEATURE**: Automatic optimal sensor mode selection for Camera Module 3 (IMX708)
  - **Problem Solved**: Previous versions used full 4K sensor readout (14fps max) even for lower resolutions, causing severe framerate limitations
  - **Solution**: Auto-select optimal native sensor mode based on target resolution
  - **Performance Improvement**: 720p streaming now achieves 60fps (was 14fps) - **4.2x faster!**

#### Sensor Mode Selection Logic
The system now intelligently chooses from 3 native IMX708 sensor modes:

- **Mode 2 (1536x864 @ 120fps)**: Auto-selected for resolutions ≤ 720p
  - Uses: 2x2 binning + crop for maximum framerate
  - Best for: High-speed capture, smooth video, sports/action
  - Example: 640x480, 1280x720

- **Mode 1 (2304x1296 @ 56fps)**: Auto-selected for resolutions ≤ 1440p
  - Uses: 2x2 binning of full sensor
  - Best for: Balanced quality and performance
  - Example: 1920x1080, 2560x1440

- **Mode 0 (4608x2592 @ 14fps)**: Auto-selected for 4K resolutions
  - Uses: Full sensor readout
  - Best for: Maximum resolution, still images
  - Example: 3840x2160

### Changed
- Enhanced `CameraController._get_sensor_config()` to use intelligent mode selection
- Added new method `CameraController._get_optimal_sensor_mode()` for mode selection logic
- Updated default configuration to 720p@60fps in `.env`
- FOV mode "crop" preserved for backwards compatibility (bypasses auto-selection)

### Fixed
- **CRITICAL PERFORMANCE FIX**: 720p streaming now achieves 60fps instead of 14fps
  - Root cause: Previous "scale" FOV mode always used full 4K sensor (14fps max)
  - Impact: All resolutions below 4K now achieve their optimal framerate
  - Verified with ffprobe: `r_frame_rate=60/1` (was `43/3` = 14.33fps)

### Technical Details
- New method: `_get_optimal_sensor_mode(target_width, target_height) -> tuple`
- Sensor mode selection based on resolution thresholds
- Logging added to track selected sensor mode for debugging
- Zero breaking changes - fully backwards compatible
- FOV mode API still available for manual control

### Performance Comparison

| Resolution | Before (fps) | After (fps) | Improvement |
|-----------|-------------|------------|-------------|
| 640x480   | 14          | 120        | 8.6x faster |
| 1280x720  | 14          | 60-120     | 4.3-8.6x    |
| 1920x1080 | 14          | 50-56      | 3.6-4.0x    |
| 2560x1440 | 14          | 40-56      | 2.9-4.0x    |
| 3840x2160 | 14          | 30         | 2.1x        |

### Upgrade Notes
- Existing deployments automatically benefit from this fix upon restart
- No configuration changes required
- Default `.env` now uses 720p@60fps for optimal performance
- FOV mode can still be set to "crop" to use legacy behavior if needed

## [2.5.0] - 2025-11-22

### Added

#### System Monitoring Endpoint
- **NEW FEATURE**: Comprehensive system health monitoring for Raspberry Pi
  - `GET /v1/system/status` - Query system metrics in real-time
  - Monitor CPU temperature and thermal status (normal/warm/hot/critical)
  - Track CPU usage percentage and load average (1min, 5min, 15min)
  - Monitor memory (RAM) usage and availability
  - WiFi signal strength and quality (dBm, percentage, status)
  - Network statistics (bytes/packets sent/received, active interface)
  - Disk usage statistics (total, used, free space)
  - System and service uptime tracking
  - Raspberry Pi throttling detection (under-voltage, frequency capping, thermal throttling)

#### System Monitoring Features
- **Temperature Monitoring**: CPU temperature with status classification
  - Normal: < 60°C
  - Warm: 60-70°C
  - Hot: 70-80°C
  - Critical: > 80°C

- **WiFi Quality Monitoring**: Signal strength classification
  - Excellent: ≥ -50 dBm
  - Good: -50 to -60 dBm
  - Fair: -60 to -70 dBm
  - Weak: < -70 dBm

- **Throttling Detection**: Detect Raspberry Pi performance issues
  - Under-voltage detection
  - Frequency capping
  - Temperature-based throttling
  - Historical throttling events

### Changed
- Added `psutil>=5.9.0` dependency for system monitoring
- Created new `SystemMonitor` class in `camera_service/system_monitor.py`
- Enhanced API with system health visibility

### Technical Details
- New module: `camera_service/system_monitor.py`
- New endpoint: `GET /v1/system/status` (requires authentication)
- Graceful fallback when system tools are not available
- Thread-safe implementation
- Zero breaking changes - fully backwards compatible

### Use Cases
- Monitor Pi temperature during video encoding
- Detect WiFi connectivity issues affecting streaming
- Track resource usage for optimization
- Alert on thermal throttling or under-voltage
- Verify system stability for long-running deployments

## [2.4.0] - 2025-11-22

### Added

#### Field of View (FOV) Mode Selection
- **NEW FEATURE**: Choose between two FOV modes for different use cases
  - **"scale" mode** (default): Constant field of view at all resolutions
    - Reads full sensor area (4608x2592 for IMX708)
    - Hardware ISP downscales to target resolution
    - Better image quality (downsampling vs cropping)
    - Ideal for monitoring, surveillance, and consistent framing
  - **"crop" mode**: Digital zoom effect with sensor crop
    - Reads only required sensor area for target resolution
    - FOV reduces at lower resolutions (telephoto effect)
    - Lower processing load, faster sensor readout
    - Useful for zoom/telephoto applications

#### New API Endpoints
- `GET /v1/camera/fov_mode` - Query current FOV mode
  - Returns: `{"mode": "scale", "description": "..."}`
- `POST /v1/camera/fov_mode` - Change FOV mode
  - Request: `{"mode": "scale"}` or `{"mode": "crop"}`
  - Takes effect on next resolution/framerate change

#### Enhanced Resolution Endpoint
- Added optional `fov_mode` parameter to `POST /v1/camera/resolution`
  - Can change FOV mode and resolution in single request
  - Example: `{"width": 1280, "height": 720, "fov_mode": "crop"}`

#### Enhanced Status Response
- Added `fov_mode` field to `GET /v1/camera/status`
  - Shows current FOV mode ("scale" or "crop")

### Changed
- Default FOV mode is now "scale" for constant field of view across all resolutions
- All resolution/framerate changes now maintain configurable FOV behavior
- Camera configuration uses conditional sensor parameters based on FOV mode

### Technical Details
- New `CameraController` methods: `set_fov_mode()`, `get_fov_mode()`, `_get_sensor_config()`
- FOV mode persists across camera reconfigurations
- Thread-safe implementation with existing RLock protection
- Zero breaking changes - fully backwards compatible

## [2.3.1] - 2025-11-22

### Fixed

#### Critical Race Condition in Camera Reconfiguration
- **CRITICAL BUG FIX**: Added global lock to prevent race conditions in concurrent camera reconfiguration
  - **Problem**: Multiple simultaneous requests to change resolution or framerate could cause:
    - Service crashes with "Failed to set framerate" errors
    - Internal server errors and deadlocks
    - Streaming interruptions and inconsistent camera state
  - **Root cause**: While `StreamingManager` and `CameraController` had internal locks, there was no global lock protecting the complete stop→reconfigure→start sequence at the API level
  - **Solution**: Added `_reconfiguration_lock` (RLock) in `api.py` to serialize all reconfiguration operations
  - **Impact**: Concurrent requests to `/v1/camera/resolution` and `/v1/camera/framerate` now execute sequentially and safely
  - **Testing**: Verified with multiple concurrent requests - all now succeed without errors or crashes

This was an intermittent, timing-dependent bug that could occur when:
- UI sends multiple rapid configuration changes
- Automation scripts make concurrent API calls
- Multiple clients access the API simultaneously

## [2.3.0] - 2025-11-22

### Added

#### Dynamic Framerate Control with Intelligent Clamping
- `POST /v1/camera/framerate` - Change framerate dynamically with smart limit enforcement
  - Automatically clamps requested framerate to hardware maximum for current resolution
  - Returns detailed information about requested vs applied framerate
  - Indicates with `clamped` flag when value was adjusted
  - Example: Requesting 500fps at 4K automatically applies 30fps (the maximum for 4K)

#### Framerate Limits in Capabilities
- Enhanced `GET /v1/camera/capabilities` with framerate information:
  - `current_framerate`: Currently configured framerate
  - `max_framerate_for_current_resolution`: Maximum framerate for active resolution
  - `framerate_limits_by_resolution`: Complete table of max fps per resolution
    - 4K (3840x2160): 30fps max
    - 1440p (2560x1440): 40fps max
    - 1080p (1920x1080): 50fps max
    - 720p (1280x720): 120fps max
    - VGA (640x480): 120fps max

### Changed
- Resolution tracking now persists across camera reconfigurations
- Updated test suite with 3 new comprehensive tests (now 16 tests total for v2.1+)

### Documentation
- Updated README.md with v2.3 framerate endpoint documentation
- Added comprehensive CHANGELOG entry for v2.3

## [2.2.0] - 2025-11-22

### Added

#### Camera Capabilities Discovery
- `GET /v1/camera/capabilities` - New endpoint to query camera hardware capabilities
  - Returns sensor model, supported resolutions, exposure/gain limits
  - Lists all supported features (autofocus, noise reduction modes, etc.)
  - Provides exposure value ranges and available control modes
  - Essential for clients to discover what the camera supports

#### Enhanced Status Information
- `GET /v1/camera/status` now includes `current_limits` field
  - Shows currently active frame duration and exposure limits
  - Displays effective exposure limits based on hardware and configured constraints
  - Helps understand why certain exposure values may not be achievable

### Changed
- Updated test suite with 2 new comprehensive tests (now 13 tests total for v2.1)

### Documentation
- Updated README.md with v2.2 capabilities endpoint
- Added comprehensive CHANGELOG entry for v2.2

## [2.1.0] - 2025-11-22

### Added

#### Advanced Exposure Controls
- `POST /v1/camera/exposure_value` - EV compensation (-8.0 to +8.0)
  - Fine-tune auto-exposure target brightness
  - Perfect for backlit scenes and high-contrast situations
- `POST /v1/camera/ae_constraint_mode` - AE constraint modes (normal/highlight/shadows/custom)
  - Control how auto-exposure handles over/underexposure
- `POST /v1/camera/ae_exposure_mode` - AE exposure modes (normal/short/long/custom)
  - Prioritize exposure time vs gain for different scenarios

#### Noise Reduction
- `POST /v1/camera/noise_reduction` - Noise reduction modes
  - 5 modes: off, fast, high_quality, minimal, zsl
  - Balance quality vs performance
  - Essential for low-light scenarios with high gain

#### White Balance Presets
- `POST /v1/camera/awb_mode` - AWB mode presets
  - 7 preset modes: auto, tungsten, fluorescent, indoor, daylight, cloudy, custom
  - Quick white balance adjustment for different lighting conditions

#### Autofocus Enhancement
- `POST /v1/camera/autofocus_trigger` - Manual autofocus trigger
  - Initiate one-shot autofocus on demand
  - Useful for manual or auto focus modes

#### Dynamic Resolution
- `POST /v1/camera/resolution` - Change resolution without service restart
  - Seamless stop/reconfigure/restart
  - Support for all standard resolutions (1920x1080, 1280x720, 640x480, 4K)

#### Low-Light Optimization
- `scripts/set-low-light-mode.sh` - One-command low-light configuration for static scenes
- `scripts/set-low-light-motion-mode.sh` - Low-light configuration for moving subjects
- `scripts/set-normal-mode.sh` - Reset to default settings
- `docs/low-light-modes.md` - Comprehensive low-light configuration guide

### Fixed
- **BREAKING FIX**: `POST /v1/camera/exposure_limits` now uses `FrameDurationLimits`
  - Previous implementation used non-existent libcamera controls (`ExposureTimeMin/Max`, `AnalogueGainMin/Max`)
  - Now correctly uses `FrameDurationLimits` to constrain frame duration
  - This indirectly limits maximum exposure time
  - **Note**: Direct gain limits are not supported by libcamera; use manual exposure mode for precise control

### Changed
- API version bumped to 2.1.0
- Health endpoint now returns version "2.0.0" (updated from "1.0.0")
- Enhanced test suite with 18 comprehensive tests (8 v2.0 + 10 v2.1)

### Documentation
- Updated README.md with v2.1 features
- Added comprehensive low-light modes documentation
- Added test script `scripts/test-api-v2-1.sh`
- Created `tests/test_api_v2_1.py` with 10 new integration tests

## [2.0.0] - 2025-11-21

### Added

#### Autofocus Control (Camera Module 3)
- `POST /v1/camera/autofocus_mode` - Set autofocus mode (manual/auto/continuous)
- `POST /v1/camera/lens_position` - Manual lens position control (0.0-15.0)
- `POST /v1/camera/autofocus_range` - Autofocus range selection (normal/macro/full)

#### Image Capture
- `POST /v1/camera/snapshot` - Capture JPEG images without stopping streaming
- Returns base64-encoded JPEG with configurable resolution
- Optional autofocus trigger before capture

#### Advanced White Balance
- `POST /v1/camera/manual_awb` - Manual AWB gains (red/blue channels)
- `POST /v1/camera/awb_preset` - NoIR-optimized presets:
  - `daylight_noir` - Outdoor/daylight with NoIR camera
  - `ir_850nm` - IR illumination at 850nm wavelength
  - `ir_940nm` - IR illumination at 940nm wavelength
  - `indoor_noir` - Indoor lighting with NoIR camera

#### Image Processing
- `POST /v1/camera/image_processing` - Control brightness, contrast, saturation, sharpness
- All parameters are optional (update only what you need)

#### HDR Support
- `POST /v1/camera/hdr` - Hardware HDR from Camera Module 3 sensor
- Modes: off, auto, sensor, single-exp

#### ROI/Digital Zoom
- `POST /v1/camera/roi` - Region of Interest with normalized coordinates
- Hardware-accelerated digital crop/zoom

#### Exposure Control
- `POST /v1/camera/exposure_limits` - Constrain auto-exposure min/max values
  - **Note:** Not supported on all libcamera versions/platforms

#### Image Transform
- `POST /v1/camera/lens_correction` - Distortion correction for wide-angle cameras
- `POST /v1/camera/transform` - Horizontal/vertical flip, rotation

#### Scene Detection
- `POST /v1/camera/day_night_mode` - Automatic scene mode detection (day/low_light/night)
- Configurable lux threshold for day/night switching

#### NoIR Camera Support
- Auto-detection of tuning files for NoIR cameras
- Configuration variables:
  - `CAMERA_CAMERA_MODEL` - Camera sensor model (default: imx708)
  - `CAMERA_IS_NOIR` - Flag for NoIR camera (default: false)
  - `CAMERA_TUNING_FILE` - Override tuning file path (optional)

#### Enhanced Metadata
- Added 10 new fields to `GET /v1/camera/status`:
  - `autofocus_mode` - Current autofocus mode
  - `lens_position` - Current lens position
  - `focus_fom` - Focus Figure of Merit
  - `hdr_mode` - HDR mode
  - `lens_correction_enabled` - Lens correction status
  - `scene_mode` - Scene mode (day/low_light/night)
  - `day_night_mode` - Day/night detection mode
  - `day_night_threshold_lux` - Lux threshold for day/night
  - `frame_duration_us` - Frame duration in microseconds
  - `sensor_black_levels` - Sensor black levels

### Changed
- Updated API version to 2.0.0
- Enhanced `GET /v1/camera/status` response with comprehensive metadata
- Improved error handling and logging throughout

### Fixed
- Status endpoint now correctly returns all v2.0 metadata fields

### Dependencies
- Added `Pillow>=10.0.0` for snapshot capture functionality

### Documentation
- Added comprehensive [UPGRADE_v2.md](UPGRADE_v2.md) migration guide
- Added [test-api-v2.sh](test-api-v2.sh) test suite for all v2.0 endpoints
- Updated [README.md](README.md) with v2.0 feature list
- Updated `.env.example` with new configuration options

### Known Limitations
- `exposure_limits` endpoint: ExposureTimeMin/Max controls not available on all libcamera versions
  - This is a platform limitation, not a code bug
  - Feature gracefully fails with clear error message

---

## [1.0.0] - 2024-XX-XX

### Added
- Initial production-ready release
- FastAPI-based HTTP API for camera control
- RTSP streaming to MediaMTX via H.264
- Auto-exposure control
- Manual exposure control (time + gain)
- Auto white balance (AWB) control
- Camera status endpoint with metadata
- API key authentication (optional)
- Comprehensive test suite
- systemd service support
- Full documentation

### Features
- Thread-safe operations with RLock
- Proper resource cleanup
- Type safety with Pydantic
- Comprehensive logging
- Configuration via environment variables
- Health check endpoint

---

## Version History Summary

| Version | Date       | Endpoints | Key Features                                    |
|---------|------------|-----------|------------------------------------------------|
| 2.0.0   | 2025-11-21 | 18        | Autofocus, snapshot, HDR, NoIR support         |
| 1.0.0   | 2024-XX-XX | 4         | Basic camera control, streaming, exposure/AWB  |

---

## Future Roadmap

### Planned Features
- Local video recording
- Multi-resolution streaming
- GPIO control for IR illuminators
- Advanced tuning file customization
- Time-lapse capture
- Motion detection integration

### Under Consideration
- Support for multiple cameras
- WebRTC streaming (via MediaMTX)
- MQTT integration for IoT
- Web UI for configuration

---

## Contributing

Found a bug or have a feature request? Please open an issue on GitHub!

---

## Links

- [UPGRADE_v2.md](UPGRADE_v2.md) - Complete v2.0 upgrade guide
- [README.md](README.md) - Project overview
- [API.md](API.md) - API reference documentation
- [CLAUDE.md](CLAUDE.md) - Development guidelines

---

**Note:** This project uses [Semantic Versioning](https://semver.org/):
- MAJOR version: Incompatible API changes
- MINOR version: New functionality (backward compatible)
- PATCH version: Bug fixes (backward compatible)
