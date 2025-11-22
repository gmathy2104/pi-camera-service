#!/bin/bash
#
# Test script for Pi Camera Service API v2.1
#
# This script tests the new v2.1 endpoints including:
# - Exposure value (EV) compensation
# - Noise reduction modes
# - Advanced AE controls
# - AWB modes
# - Autofocus trigger
# - Dynamic resolution change
#
# Usage:
#   ./scripts/test-api-v2-1.sh

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000"
TIMEOUT=5

echo "======================================================================"
echo "Pi Camera Service - API v2.1 Integration Tests"
echo "======================================================================"
echo ""

# Check if service is running
echo "[1/11] Checking if service is running..."
if curl -s --max-time 2 "${API_URL}/health" > /dev/null; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ ERROR: Cannot connect to API at ${API_URL}${NC}"
    echo "Make sure the service is running (python main.py)"
    exit 1
fi
echo ""

# Test 2: Exposure value compensation
echo "[2/11] Testing exposure value compensation..."
if curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d '{"ev": 1.0}' \
    --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓ Exposure value compensation working${NC}"
else
    echo -e "${RED}✗ FAILED: Exposure value compensation${NC}"
fi
sleep 0.5

# Reset EV to 0
curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d '{"ev": 0.0}' \
    --max-time ${TIMEOUT} > /dev/null
echo ""

# Test 3: Exposure value validation
echo "[3/11] Testing exposure value validation..."
RESPONSE=$(curl -s -X POST "${API_URL}/v1/camera/exposure_value" \
    -H "Content-Type: application/json" \
    -d '{"ev": 10.0}' \
    --max-time ${TIMEOUT} -w "%{http_code}" -o /dev/null)
if [ "$RESPONSE" == "422" ]; then
    echo -e "${GREEN}✓ Exposure value validation working${NC}"
else
    echo -e "${RED}✗ FAILED: Exposure value validation${NC}"
fi
echo ""

# Test 4: Noise reduction modes
echo "[4/11] Testing noise reduction modes..."
NOISE_MODES=("off" "fast" "high_quality" "minimal")
SUCCESS=true
for mode in "${NOISE_MODES[@]}"; do
    if ! curl -s -X POST "${API_URL}/v1/camera/noise_reduction" \
        -H "Content-Type: application/json" \
        -d "{\"mode\": \"${mode}\"}" \
        --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
        SUCCESS=false
        break
    fi
    sleep 0.3
done
if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓ Noise reduction modes working${NC}"
else
    echo -e "${RED}✗ FAILED: Noise reduction modes${NC}"
fi
echo ""

# Test 5: AE constraint modes
echo "[5/11] Testing AE constraint modes..."
AE_CONSTRAINT_MODES=("normal" "highlight" "shadows")
SUCCESS=true
for mode in "${AE_CONSTRAINT_MODES[@]}"; do
    if ! curl -s -X POST "${API_URL}/v1/camera/ae_constraint_mode" \
        -H "Content-Type: application/json" \
        -d "{\"mode\": \"${mode}\"}" \
        --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
        SUCCESS=false
        break
    fi
    sleep 0.3
done
if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓ AE constraint modes working${NC}"
else
    echo -e "${RED}✗ FAILED: AE constraint modes${NC}"
fi
echo ""

# Test 6: AE exposure modes
echo "[6/11] Testing AE exposure modes..."
AE_EXPOSURE_MODES=("normal" "short" "long")
SUCCESS=true
for mode in "${AE_EXPOSURE_MODES[@]}"; do
    if ! curl -s -X POST "${API_URL}/v1/camera/ae_exposure_mode" \
        -H "Content-Type: application/json" \
        -d "{\"mode\": \"${mode}\"}" \
        --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
        SUCCESS=false
        break
    fi
    sleep 0.3
done
if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓ AE exposure modes working${NC}"
else
    echo -e "${RED}✗ FAILED: AE exposure modes${NC}"
fi
echo ""

# Test 7: AWB modes
echo "[7/11] Testing AWB modes..."
AWB_MODES=("auto" "tungsten" "daylight" "cloudy")
SUCCESS=true
for mode in "${AWB_MODES[@]}"; do
    if ! curl -s -X POST "${API_URL}/v1/camera/awb_mode" \
        -H "Content-Type: application/json" \
        -d "{\"mode\": \"${mode}\"}" \
        --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
        SUCCESS=false
        break
    fi
    sleep 0.3
done
if [ "$SUCCESS" = true ]; then
    echo -e "${GREEN}✓ AWB modes working${NC}"
else
    echo -e "${RED}✗ FAILED: AWB modes${NC}"
fi
echo ""

# Test 8: Autofocus trigger
echo "[8/11] Testing autofocus trigger..."
if curl -s -X POST "${API_URL}/v1/camera/autofocus_trigger" \
    --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓ Autofocus trigger working${NC}"
else
    echo -e "${RED}✗ FAILED: Autofocus trigger${NC}"
fi
echo ""

# Test 9: Dynamic resolution change
echo "[9/11] Testing resolution change..."
if curl -s -X POST "${API_URL}/v1/camera/resolution" \
    -H "Content-Type: application/json" \
    -d '{"width": 1280, "height": 720, "restart_streaming": true}' \
    --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓ Resolution change to 720p working${NC}"
    sleep 2
    # Change back to 1080p
    curl -s -X POST "${API_URL}/v1/camera/resolution" \
        -H "Content-Type: application/json" \
        -d '{"width": 1920, "height": 1080, "restart_streaming": true}' \
        --max-time ${TIMEOUT} > /dev/null
    sleep 2
else
    echo -e "${RED}✗ FAILED: Resolution change${NC}"
fi
echo ""

# Test 10: Resolution validation
echo "[10/11] Testing resolution validation..."
RESPONSE=$(curl -s -X POST "${API_URL}/v1/camera/resolution" \
    -H "Content-Type: application/json" \
    -d '{"width": 50, "height": 50}' \
    --max-time ${TIMEOUT} -w "%{http_code}" -o /dev/null)
if [ "$RESPONSE" == "422" ]; then
    echo -e "${GREEN}✓ Resolution validation working${NC}"
else
    echo -e "${RED}✗ FAILED: Resolution validation${NC}"
fi
echo ""

# Test 11: Corrected exposure limits
echo "[11/11] Testing corrected exposure limits (FrameDurationLimits)..."
if curl -s -X POST "${API_URL}/v1/camera/exposure_limits" \
    -H "Content-Type: application/json" \
    -d '{"min_exposure_us": 1000, "max_exposure_us": 50000}' \
    --max-time ${TIMEOUT} | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓ Exposure limits (FrameDurationLimits) working${NC}"
    # Reset to auto exposure
    curl -s -X POST "${API_URL}/v1/camera/auto_exposure" \
        -H "Content-Type: application/json" \
        -d '{"enabled": true}' \
        --max-time ${TIMEOUT} > /dev/null
else
    echo -e "${RED}✗ FAILED: Exposure limits${NC}"
fi
echo ""

echo "======================================================================"
echo -e "${GREEN}✓ All v2.1 tests completed!${NC}"
echo "======================================================================"
echo ""
echo "New v2.1 endpoints tested:"
echo "  • POST /v1/camera/exposure_value (EV compensation)"
echo "  • POST /v1/camera/noise_reduction (denoise modes)"
echo "  • POST /v1/camera/ae_constraint_mode (AE constraints)"
echo "  • POST /v1/camera/ae_exposure_mode (AE exposure modes)"
echo "  • POST /v1/camera/awb_mode (AWB presets)"
echo "  • POST /v1/camera/autofocus_trigger (trigger AF)"
echo "  • POST /v1/camera/resolution (dynamic resolution)"
echo "  • POST /v1/camera/exposure_limits (FIXED with FrameDurationLimits)"
echo ""
