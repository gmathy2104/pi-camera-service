# Changelog

All notable changes to Pi Camera Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
