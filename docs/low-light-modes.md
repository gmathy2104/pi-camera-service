# Low-Light Configuration Modes

This guide explains how to configure your Pi Camera for optimal performance in low-light conditions **without IR illumination**.

## 🌙 Available Modes

### 1. **Low-Light Mode** (Static Scenes)
**Best for:** Static or slow-moving subjects in very low light

```bash
./scripts/set-low-light-mode.sh [EV_compensation]
```

**How it works:**
- Maximizes exposure time (up to 1 second)
- Uses high gain when needed
- High-quality noise reduction
- Preserves shadow details

**Settings:**
- AE Exposure Mode: `long` (prioritize long exposure)
- AE Constraint Mode: `shadows` (preserve dark areas)
- EV Compensation: `+1.5` (default, adjustable)
- Noise Reduction: `high_quality`
- Exposure Limits: `100µs - 1,000,000µs` (up to 1 second)

**Trade-offs:**
- ✅ Maximum brightness in low light
- ✅ Lower noise (prefers exposure over gain)
- ❌ Motion blur on moving subjects
- ❌ Lower framerate (can drop to ~1fps in very low light)

**Example:**
```bash
# Default (EV +1.5)
./scripts/set-low-light-mode.sh

# More aggressive (EV +2.0)
./scripts/set-low-light-mode.sh 2.0
```

---

### 2. **Low-Light Motion Mode** (Moving Subjects)
**Best for:** Moving subjects in low light (people, vehicles, etc.)

```bash
./scripts/set-low-light-motion-mode.sh [exposure_us] [gain]
```

**How it works:**
- Short, fixed exposure time (reduces motion blur)
- High gain to compensate (more noise)
- High-quality noise reduction to clean up
- Consistent framerate

**Settings:**
- Manual Exposure: `33,333µs` (~30fps, default)
- Analogue Gain: `12.0` (default, range 1.0-16.0)
- Noise Reduction: `high_quality`
- AE Constraint Mode: `shadows`
- EV Compensation: `+1.0`

**Trade-offs:**
- ✅ Reduced motion blur
- ✅ Maintains framerate
- ❌ More noise (high gain)
- ❌ Darker image overall

**Examples:**
```bash
# Default: 33ms exposure, gain 12.0 (~30fps)
./scripts/set-low-light-motion-mode.sh

# Faster: 16ms exposure, gain 14.0 (~60fps, more noise)
./scripts/set-low-light-motion-mode.sh 16666 14.0

# Slower: 50ms exposure, gain 10.0 (~20fps, less noise)
./scripts/set-low-light-motion-mode.sh 50000 10.0
```

---

### 3. **Normal Mode** (Balanced)
**Best for:** Well-lit scenes, general purpose

```bash
./scripts/set-normal-mode.sh
```

**Settings:**
- AE Exposure Mode: `normal`
- AE Constraint Mode: `normal`
- EV Compensation: `0.0`
- Noise Reduction: `fast`
- Exposure Limits: `100µs - 33,333µs` (30fps)

---

## 📊 Comparison Table

| Mode | Brightness | Motion Blur | Noise | Framerate | Best For |
|------|-----------|-------------|-------|-----------|----------|
| **Low-Light** | ⭐⭐⭐⭐⭐ | ❌ High | ⭐⭐⭐⭐ | Variable (1-30fps) | Static scenes, surveillance |
| **Low-Light Motion** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | Fixed (30fps) | Moving subjects, action |
| **Normal** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Fixed (30fps) | General, well-lit |

---

## 🎯 Quick Decision Guide

**Choose your mode based on your scenario:**

```
Do you have moving subjects?
│
├─ NO → Use Low-Light Mode
│        ./scripts/set-low-light-mode.sh
│
└─ YES → Use Low-Light Motion Mode
         ./scripts/set-low-light-motion-mode.sh
```

---

## 🔧 Manual Fine-Tuning

If the scripts don't fit your exact needs, you can manually adjust individual parameters:

### Exposure Value (EV) Compensation
Adjust overall brightness without changing exposure/gain balance:
```bash
# Brighter (+2.0 EV = 4x brighter)
curl -X POST http://localhost:8000/v1/camera/exposure_value \
  -H "Content-Type: application/json" \
  -d '{"ev": 2.0}'

# Darker (-1.0 EV = half as bright)
curl -X POST http://localhost:8000/v1/camera/exposure_value \
  -H "Content-Type: application/json" \
  -d '{"ev": -1.0}'
```

### Manual Exposure
Complete control over exposure time and gain:
```bash
# Example: 100ms exposure, gain 8.0
curl -X POST http://localhost:8000/v1/camera/manual_exposure \
  -H "Content-Type: application/json" \
  -d '{"exposure_us": 100000, "gain": 8.0}'
```

**Exposure time guidelines:**
- `1,000 - 10,000 µs` (1-10ms): Fast action, bright scenes
- `10,000 - 33,333 µs` (10-33ms): Normal scenes, 30fps
- `33,333 - 100,000 µs` (33-100ms): Low light, some blur
- `100,000 - 500,000 µs` (100-500ms): Very low light, static only
- `500,000 - 1,000,000 µs` (0.5-1s): Extreme low light, long exposure

**Gain guidelines:**
- `1.0 - 4.0`: Normal to bright scenes
- `4.0 - 8.0`: Low light, acceptable noise
- `8.0 - 12.0`: Very low light, noticeable noise
- `12.0 - 16.0`: Extreme low light, significant noise

### Noise Reduction
Balance between sharpness and noise:
```bash
# Maximum quality (slower)
curl -X POST http://localhost:8000/v1/camera/noise_reduction \
  -H "Content-Type: application/json" \
  -d '{"mode": "high_quality"}'

# Fast (real-time video)
curl -X POST http://localhost:8000/v1/camera/noise_reduction \
  -H "Content-Type: application/json" \
  -d '{"mode": "fast"}'

# No noise reduction (sharpest, noisiest)
curl -X POST http://localhost:8000/v1/camera/noise_reduction \
  -H "Content-Type: application/json" \
  -d '{"mode": "off"}'
```

---

## 📈 Monitoring Current Settings

Check current camera status:
```bash
curl http://localhost:8000/v1/camera/status | jq
```

Key fields to watch:
- `lux`: Scene brightness (0-100+)
- `exposure_us`: Current exposure time in microseconds
- `analogue_gain`: Current gain (1.0-16.0)
- `scene_mode`: Auto-detected scene ("day", "low_light", "night")

---

## 💡 Tips and Best Practices

1. **Start with presets**, then fine-tune if needed
2. **Monitor the stream** while adjusting settings
3. **Use EV compensation** (+/-) for quick brightness adjustments
4. **Check `scene_mode`** in status to see what the camera detects
5. **Higher gain = more noise**, but noise reduction helps
6. **Longer exposure = more light but more motion blur**
7. **For IR cameras (NoIR)**, also adjust white balance:
   ```bash
   ./scripts/set-awb-preset.sh ir_850nm  # For 850nm IR LEDs
   ```

---

## 🆘 Troubleshooting

### Image is too dark
1. Increase EV compensation: `./scripts/set-low-light-mode.sh 2.0`
2. Use manual exposure with higher gain
3. Check if you're in motion mode (limits exposure)

### Too much motion blur
1. Switch to motion mode: `./scripts/set-low-light-motion-mode.sh`
2. Reduce exposure time manually
3. Accept darker image or add lighting

### Too much noise
1. Reduce gain if possible
2. Enable high_quality noise reduction
3. Increase exposure time (if motion blur is acceptable)
4. Add more light to the scene

### Framerate drops
1. You're in low-light mode with very long exposures
2. This is normal - camera uses long exposure for brightness
3. Switch to motion mode if you need consistent framerate

---

## 📚 Related Documentation

- [API v2.1 Features](../README.md#v21-features)
- [Camera Controls Reference](../README.md#camera-controls)
- [Testing Guide](../scripts/test-api-v2-1.sh)

---

**Pro tip:** For the absolute best low-light performance, consider using a NoIR camera module with external IR illumination (850nm or 940nm LEDs).
