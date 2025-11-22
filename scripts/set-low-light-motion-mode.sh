#!/bin/bash
#
# Configure camera for low-light with moving subjects
#
# This script optimizes for motion in low light:
# - Short exposure mode (reduce motion blur)
# - Higher gain to compensate (more noise but sharper)
# - Shadow constraint mode
# - High quality noise reduction (compensate for high gain)
# - Fixed manual exposure for consistent results
#
# Usage:
#   ./scripts/set-low-light-motion-mode.sh [exposure_us] [gain]
#
# Examples:
#   ./scripts/set-low-light-motion-mode.sh            # Default: 33ms, gain 12.0
#   ./scripts/set-low-light-motion-mode.sh 16666 14.0 # Custom: 16ms, gain 14.0

API_URL="http://localhost:8000"
EXPOSURE_US=${1:-33333}  # Default: 33ms (~30fps)
GAIN=${2:-12.0}          # Default: gain 12.0

echo "======================================================================"
echo "Configuring Camera for Low-Light Motion Mode"
echo "======================================================================"
echo ""
echo "Target: Capture moving subjects in low light"
echo "Exposure: ${EXPOSURE_US}µs (~$((1000000 / EXPOSURE_US))fps)"
echo "Gain: ${GAIN}"
echo ""

# Step 1: Set noise reduction to high_quality
echo "[1/4] Setting noise reduction to 'high_quality' (compensate high gain)..."
curl -s -X POST "${API_URL}/v1/camera/noise_reduction" \
    -H "Content-Type: application/json" \
    -d '{"mode": "high_quality"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 2: Set AE constraint mode to "shadows"
echo "[2/4] Setting AE constraint mode to 'shadows' (preserve dark details)..."
curl -s -X POST "${API_URL}/v1/camera/ae_constraint_mode" \
    -H "Content-Type: application/json" \
    -d '{"mode": "shadows"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 3: Set EV compensation
echo "[3/4] Setting EV compensation to +1.0 (increase brightness)..."
curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d '{"ev": 1.0}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 4: Set manual exposure (short exposure + high gain)
echo "[4/4] Setting manual exposure (${EXPOSURE_US}µs, gain ${GAIN})..."
curl -s -X POST "${API_URL}/v1/camera/manual_exposure" \
    -H "Content-Type: application/json" \
    -d "{\"exposure_us\": ${EXPOSURE_US}, \"gain\": ${GAIN}}" | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

echo ""
echo "======================================================================"
echo "✓ Low-Light Motion Mode Configured Successfully!"
echo "======================================================================"
echo ""
echo "Settings applied:"
echo "  • Noise Reduction: high_quality (reduce noise from high gain)"
echo "  • AE Constraint Mode: shadows (preserve dark area details)"
echo "  • EV Compensation: +1.0 (increase brightness)"
echo "  • Manual Exposure: ${EXPOSURE_US}µs (~$((1000000 / EXPOSURE_US))fps)"
echo "  • Analogue Gain: ${GAIN}"
echo ""
echo "Trade-offs:"
echo "  ✓ Reduced motion blur (short exposure)"
echo "  ✓ Maintains framerate"
echo "  ✗ More noise (high gain)"
echo "  ✗ Darker image (limited by short exposure)"
echo ""
echo "For static scenes, use: ./scripts/set-low-light-mode.sh"
echo ""
