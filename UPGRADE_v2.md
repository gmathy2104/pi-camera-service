# Pi Camera Service v2.0 - Upgrade Guide

## Overview

Version 2.0 is a major feature release that adds comprehensive control over the Camera Module 3's advanced capabilities, with special optimizations for NoIR (No IR filter) cameras and wide-angle lenses.

### What's New in v2.0

- **Autofocus Control**: Full control over Camera Module 3's hardware autofocus
- **Snapshot Capture**: Capture still images without stopping streaming
- **Advanced White Balance**: Manual AWB gains + NoIR-optimized presets
- **Image Processing**: Brightness, contrast, saturation, sharpness controls
- **HDR Support**: Hardware HDR from Camera Module 3 sensor
- **ROI/Digital Zoom**: Crop and stream specific regions
- **Exposure Limits**: Constrain auto-exposure behavior
- **Lens Correction**: Distortion correction for wide-angle cameras
- **Day/Night Detection**: Automatic scene mode detection
- **Enhanced Metadata**: Comprehensive camera status information
- **NoIR Optimization**: Auto-detection of tuning files for NoIR cameras

## Breaking Changes

### ⚠️ None! v2.0 is fully backward compatible with v1.0

All existing v1.0 endpoints continue to work unchanged. New v2.0 features are additive only.

## New Configuration Variables

Add these to your `.env` file (optional - auto-detected if not specified):

```bash
# Camera sensor model (for tuning file detection)
CAMERA_CAMERA_MODEL=imx708

# Is this a NoIR camera?
CAMERA_IS_NOIR=true

# Override tuning file path (optional)
# CAMERA_TUNING_FILE=/usr/share/libcamera/ipa/rpi/vc4/imx708_noir.json
```

For **Camera Module 3 Wide NoIR** users (like you!), set:
```bash
CAMERA_CAMERA_MODEL=imx708
CAMERA_IS_NOIR=true
```

The service will automatically detect and use the correct NoIR tuning file.

## New Dependencies

v2.0 adds one new dependency:

```bash
# Install Pillow (for snapshot capture)
pip install Pillow>=10.0.0
```

Or simply:
```bash
pip install -r requirements.txt
```

## New API Endpoints

### 🎯 Autofocus Controls

#### Set Autofocus Mode
```bash
POST /v1/camera/autofocus_mode
Content-Type: application/json

{
  "mode": "continuous"  # Options: "default", "manual", "auto", "continuous"
}
```

- **default/manual**: No autofocus, use lens_position for manual control
- **auto**: One-shot autofocus
- **continuous**: Continuous autofocus (best for streaming)

#### Set Manual Lens Position
```bash
POST /v1/camera/lens_position
Content-Type: application/json

{
  "position": 5.0  # 0.0=infinity, 1-5=normal range, 10+=macro
}
```

#### Set Autofocus Range
```bash
POST /v1/camera/autofocus_range
Content-Type: application/json

{
  "range_mode": "normal"  # Options: "normal", "macro", "full"
}
```

### 📸 Snapshot Capture

Capture a JPEG image without stopping streaming:

```bash
POST /v1/camera/snapshot
Content-Type: application/json

{
  "width": 1920,             # Optional, default: 1920
  "height": 1080,            # Optional, default: 1080
  "autofocus_trigger": true  # Optional, default: true
}
```

Returns:
```json
{
  "status": "ok",
  "image_base64": "base64_encoded_jpeg_data_here...",
  "width": 1920,
  "height": 1080
}
```

**Usage example:**
```bash
# Capture and save to file
curl -X POST http://localhost:8000/v1/camera/snapshot \
  -H "Content-Type: application/json" \
  -d '{"width": 1920, "height": 1080}' \
  | jq -r '.image_base64' | base64 -d > snapshot.jpg
```

### 🎨 Advanced White Balance

#### Manual White Balance Gains
```bash
POST /v1/camera/manual_awb
Content-Type: application/json

{
  "red_gain": 1.5,   # 0.5-5.0
  "blue_gain": 1.8   # 0.5-5.0
}
```

#### NoIR-Optimized Presets
```bash
POST /v1/camera/awb_preset
Content-Type: application/json

{
  "preset": "daylight_noir"  # See presets below
}
```

**Available Presets:**
- `daylight_noir`: Outdoor/daylight with NoIR camera
- `ir_850nm`: IR illumination at 850nm wavelength
- `ir_940nm`: IR illumination at 940nm wavelength
- `indoor_noir`: Indoor lighting with NoIR camera

### 🖼️ Image Processing

```bash
POST /v1/camera/image_processing
Content-Type: application/json

{
  "brightness": 0.1,    # Optional, -1.0 to 1.0
  "contrast": 1.2,      # Optional, 0.0 to 2.0
  "saturation": 1.0,    # Optional, 0.0 to 2.0
  "sharpness": 8.0      # Optional, 0.0 to 16.0
}
```

All parameters are optional - only send the ones you want to change.

### ✨ HDR Mode

```bash
POST /v1/camera/hdr
Content-Type: application/json

{
  "mode": "sensor"  # Options: "off", "auto", "sensor", "single-exp"
}
```

- **off**: HDR disabled
- **auto**: Automatic HDR detection
- **sensor**: Hardware HDR from Camera Module 3 sensor
- **single-exp**: Software HDR (PiSP multi-frame)

⚠️ **Note:** May require camera restart to take full effect.

### 🔍 ROI (Region of Interest / Digital Zoom)

```bash
POST /v1/camera/roi
Content-Type: application/json

{
  "x": 0.25,      # X offset, 0.0-1.0 (normalized)
  "y": 0.25,      # Y offset, 0.0-1.0
  "width": 0.5,   # Width, 0.0-1.0
  "height": 0.5   # Height, 0.0-1.0
}
```

**Examples:**
```bash
# Center crop (50%)
{"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5}

# Left half
{"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0}

# Reset to full frame
{"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
```

### ⚙️ Exposure Limits

Constrain auto-exposure algorithm:

```bash
POST /v1/camera/exposure_limits
Content-Type: application/json

{
  "min_exposure_us": 1000,    # Optional, 100-1000000
  "max_exposure_us": 50000,   # Optional, 100-1000000
  "min_gain": 1.0,            # Optional, 1.0-16.0
  "max_gain": 8.0             # Optional, 1.0-16.0
}
```

Useful to:
- Prevent over/under-exposure in variable lighting
- Avoid flicker under artificial lighting (set max_exposure to 1/60s = 16666µs)
- Maintain minimum framerate (limit max exposure)

### 🔧 Lens Correction

Enable distortion correction for wide-angle cameras:

```bash
POST /v1/camera/lens_correction
Content-Type: application/json

{
  "enabled": true
}
```

**Important for Camera Module 3 Wide (120° FOV)** to reduce barrel distortion.

⚠️ **Note:** May require camera restart to take full effect.

### 🔄 Image Transform

```bash
POST /v1/camera/transform
Content-Type: application/json

{
  "hflip": false,     # Horizontal flip
  "vflip": false,     # Vertical flip
  "rotation": 0       # 0 or 180 degrees
}
```

Useful for mounting camera in different orientations.

⚠️ **Note:** Requires camera restart to take effect.

### 🌓 Day/Night Detection

```bash
POST /v1/camera/day_night_mode
Content-Type: application/json

{
  "mode": "auto",          # "manual" or "auto"
  "threshold_lux": 10.0    # Lux threshold for day/night (when mode="auto")
}
```

When `mode="auto"`, the camera will automatically detect scene brightness and report it in the status endpoint.

### 📊 Enhanced Camera Status

The `/v1/camera/status` endpoint now returns comprehensive metadata:

```json
{
  // Existing v1.0 fields
  "lux": 150.5,
  "exposure_us": 10000,
  "analogue_gain": 1.5,
  "colour_temperature": 5500,
  "auto_exposure": true,
  "streaming": true,

  // New v2.0 fields
  "autofocus_mode": "continuous",
  "lens_position": 5.2,
  "focus_fom": 12500,              // Focus Figure of Merit (higher = better focus)
  "hdr_mode": "off",
  "lens_correction_enabled": true,
  "scene_mode": "day",             // "day", "low_light", or "night"
  "day_night_mode": "auto",
  "day_night_threshold_lux": 10.0,
  "frame_duration_us": 33333,
  "sensor_black_levels": [256, 256, 256, 256]
}
```

## Testing v2.0 Features

Run the comprehensive v2.0 test suite:

```bash
./test-api-v2.sh
```

This will test all 16 new endpoints and verify functionality.

## Migration Checklist

1. ✅ **Update environment variables** (optional):
   ```bash
   # Add to .env
   CAMERA_CAMERA_MODEL=imx708
   CAMERA_IS_NOIR=true  # If you have a NoIR camera
   ```

2. ✅ **Install new dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. ✅ **Restart the service**:
   ```bash
   # If using systemd
   sudo systemctl restart pi-camera-service

   # Or manually
   python main.py
   ```

4. ✅ **Test new features**:
   ```bash
   ./test-api-v2.sh
   ```

5. ✅ **Update your client applications** to use new endpoints (optional)

## Use Cases

### NoIR Night Vision Setup

```bash
# 1. Enable day/night auto-detection
curl -X POST http://localhost:8000/v1/camera/day_night_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "auto", "threshold_lux": 10.0}'

# 2. Set AWB preset for IR mode
curl -X POST http://localhost:8000/v1/camera/awb_preset \
  -H "Content-Type: application/json" \
  -d '{"preset": "ir_850nm"}'

# 3. Increase sharpness for better detail in low light
curl -X POST http://localhost:8000/v1/camera/image_processing \
  -H "Content-Type: application/json" \
  -d '{"sharpness": 12.0}'
```

### Fixed Focus Surveillance

```bash
# 1. Switch to manual autofocus
curl -X POST http://localhost:8000/v1/camera/autofocus_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "manual"}'

# 2. Set focus distance (e.g., 3 meters)
curl -X POST http://localhost:8000/v1/camera/lens_position \
  -H "Content-Type: application/json" \
  -d '{"position": 2.5}'
```

### Wide-Angle Monitoring with Correction

```bash
# Enable lens correction for 120° wide camera
curl -X POST http://localhost:8000/v1/camera/lens_correction \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Event-Triggered Snapshots

```bash
# Capture high-res snapshot on motion detection
curl -X POST http://localhost:8000/v1/camera/snapshot \
  -H "Content-Type: application/json" \
  -d '{"width": 4608, "height": 2592, "autofocus_trigger": true}' \
  | jq -r '.image_base64' | base64 -d > motion_$(date +%s).jpg
```

### Zoom to Specific Area

```bash
# Digital zoom to top-right quadrant (e.g., monitoring a door)
curl -X POST http://localhost:8000/v1/camera/roi \
  -H "Content-Type: application/json" \
  -d '{"x": 0.5, "y": 0.0, "width": 0.5, "height": 0.5}'
```

## Performance Notes

- **Snapshot capture**: Takes ~100-300ms depending on autofocus
- **ROI/Digital zoom**: No performance impact (done in hardware)
- **HDR mode**: May reduce max framerate (check sensor specs)
- **Lens correction**: Minimal CPU impact (hardware-accelerated)

## Troubleshooting

### Tuning file not found

If you see warnings about tuning files:

```bash
# Check available tuning files
ls /usr/share/libcamera/ipa/rpi/vc4/
ls /usr/share/libcamera/ipa/rpi/pisp/

# Manually specify in .env if auto-detection fails
CAMERA_TUNING_FILE=/usr/share/libcamera/ipa/rpi/vc4/imx708_noir.json
```

### Autofocus not working

Camera Module 3 only! Older modules (v1, v2, HQ) don't have autofocus hardware.

```bash
# Check camera model
rpicam-hello --list-cameras
```

### HDR/Lens correction requires restart

Some features need camera reconfiguration:

```bash
sudo systemctl restart pi-camera-service
```

## What's Next?

Future v2.x releases may include:
- Local video recording
- Multi-resolution streaming
- GPIO control for IR illuminators
- Advanced tuning file customization

## Feedback

Found a bug or have a feature request? Open an issue on GitHub!

---

**Happy streaming! 🎥**
