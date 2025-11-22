#!/bin/bash
#
# Reset camera to normal/default mode
#
# This script resets all camera settings to normal/balanced mode:
# - Normal AE exposure and constraint modes
# - EV compensation reset to 0
# - Noise reduction set to fast (good balance)
# - Standard exposure limits for 30fps
#
# Usage:
#   ./scripts/set-normal-mode.sh

API_URL="http://localhost:8000"

echo "======================================================================"
echo "Resetting Camera to Normal Mode"
echo "======================================================================"
echo ""

# Step 1: Set AE exposure mode to "normal"
echo "[1/6] Setting AE exposure mode to 'normal'..."
curl -s -X POST "${API_URL}/v1/camera/ae_exposure_mode" \
    -H "Content-Type: application/json" \
    -d '{"mode": "normal"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 2: Set AE constraint mode to "normal"
echo "[2/6] Setting AE constraint mode to 'normal'..."
curl -s -X POST "${API_URL}/v1/camera/ae_constraint_mode" \
    -H "Content-Type: application/json" \
    -d '{"mode": "normal"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 3: Reset EV compensation to 0
echo "[3/6] Resetting EV compensation to 0.0..."
curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d '{"ev": 0.0}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 4: Set noise reduction to fast (balanced)
echo "[4/6] Setting noise reduction to 'fast' (balanced)..."
curl -s -X POST "${API_URL}/v1/camera/noise_reduction" \
    -H "Content-Type: application/json" \
    -d '{"mode": "fast"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 5: Reset exposure limits to ~30fps
echo "[5/6] Resetting exposure limits to standard (30fps)..."
curl -s -X POST "${API_URL}/v1/camera/exposure_limits" \
    -H "Content-Type: application/json" \
    -d '{"min_exposure_us": 100, "max_exposure_us": 33333}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 6: Enable auto exposure
echo "[6/6] Enabling auto exposure..."
curl -s -X POST "${API_URL}/v1/camera/auto_exposure" \
    -H "Content-Type: application/json" \
    -d '{"enabled": true}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

echo ""
echo "======================================================================"
echo "✓ Normal Mode Configured Successfully!"
echo "======================================================================"
echo ""
echo "Settings applied:"
echo "  • AE Exposure Mode: normal (balanced exposure/gain)"
echo "  • AE Constraint Mode: normal (balanced)"
echo "  • EV Compensation: 0.0 (no adjustment)"
echo "  • Noise Reduction: fast (balanced quality/performance)"
echo "  • Exposure Limits: 100µs - 33,333µs (30fps)"
echo "  • Auto Exposure: enabled"
echo ""
