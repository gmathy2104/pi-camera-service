#!/bin/bash
#
# Configure camera for low-light conditions (without IR illumination)
#
# This script optimizes camera settings for maximum visibility in low light:
# - Long exposure mode (prioritizes exposure time over gain)
# - Shadow constraint mode (preserves details in dark areas)
# - Positive EV compensation (increases target brightness)
# - High quality noise reduction (compensates for high gain)
# - Extended exposure limits (up to 1 second)
#
# Usage:
#   ./scripts/set-low-light-mode.sh [EV_compensation]
#
# Examples:
#   ./scripts/set-low-light-mode.sh        # Default: EV +1.5
#   ./scripts/set-low-light-mode.sh 2.0    # Custom: EV +2.0

API_URL="http://localhost:8000"
EV_COMP=${1:-1.5}  # Default EV compensation: +1.5

echo "======================================================================"
echo "Configuring Camera for Low-Light Mode"
echo "======================================================================"
echo ""
echo "Target: Maximum visibility without IR illumination"
echo "EV Compensation: +${EV_COMP}"
echo ""

# Step 1: Set AE exposure mode to "long"
echo "[1/6] Setting AE exposure mode to 'long' (prioritize long exposure)..."
curl -s -X POST "${API_URL}/v1/camera/ae_exposure_mode" \
    -H "Content-Type: application/json" \
    -d '{"mode": "long"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 2: Set AE constraint mode to "shadows"
echo "[2/6] Setting AE constraint mode to 'shadows' (preserve dark details)..."
curl -s -X POST "${API_URL}/v1/camera/ae_constraint_mode" \
    -H "Content-Type: application/json" \
    -d '{"mode": "shadows"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 3: Set EV compensation
echo "[3/6] Setting EV compensation to +${EV_COMP} (increase brightness)..."
curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d "{\"ev\": ${EV_COMP}}" | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 4: Set noise reduction to high_quality
echo "[4/6] Setting noise reduction to 'high_quality'..."
curl -s -X POST "${API_URL}/v1/camera/noise_reduction" \
    -H "Content-Type: application/json" \
    -d '{"mode": "high_quality"}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 5: Extend exposure limits (up to 1 second)
echo "[5/6] Extending exposure limits (up to 1 second)..."
curl -s -X POST "${API_URL}/v1/camera/exposure_limits" \
    -H "Content-Type: application/json" \
    -d '{"min_exposure_us": 100, "max_exposure_us": 1000000}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

# Step 6: Enable auto exposure (to use all settings above)
echo "[6/6] Enabling auto exposure..."
curl -s -X POST "${API_URL}/v1/camera/auto_exposure" \
    -H "Content-Type: application/json" \
    -d '{"enabled": true}' | grep -q '"status":"ok"' && echo "✓ Done" || echo "✗ Failed"

echo ""
echo "======================================================================"
echo "✓ Low-Light Mode Configured Successfully!"
echo "======================================================================"
echo ""
echo "Settings applied:"
echo "  • AE Exposure Mode: long (prioritize long exposure over gain)"
echo "  • AE Constraint Mode: shadows (preserve dark area details)"
echo "  • EV Compensation: +${EV_COMP} (increase target brightness)"
echo "  • Noise Reduction: high_quality (reduce noise from high gain)"
echo "  • Exposure Limits: 100µs - 1,000,000µs (up to 1 second)"
echo "  • Auto Exposure: enabled"
echo ""
echo "Note: Long exposures may cause motion blur. For moving subjects,"
echo "      consider using manual exposure with higher gain instead:"
echo ""
echo "  curl -X POST ${API_URL}/v1/camera/manual_exposure \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"exposure_us\": 33333, \"gain\": 12.0}'"
echo ""
