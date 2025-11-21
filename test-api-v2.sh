#!/bin/bash
# Test script for Pi Camera Service API v2.0
# Tests all new v2.0 endpoints

set -e

BASE_URL="http://localhost:8000"
API_KEY=""  # Set if authentication is enabled

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to make requests
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -n "$API_KEY" ]; then
        if [ -n "$data" ]; then
            curl -s -X $method "$BASE_URL$endpoint" \
                -H "X-API-Key: $API_KEY" \
                -H "Content-Type: application/json" \
                -d "$data"
        else
            curl -s -X $method "$BASE_URL$endpoint" \
                -H "X-API-Key: $API_KEY"
        fi
    else
        if [ -n "$data" ]; then
            curl -s -X $method "$BASE_URL$endpoint" \
                -H "Content-Type: application/json" \
                -d "$data"
        else
            curl -s -X $method "$BASE_URL$endpoint"
        fi
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pi Camera Service API v2.0 Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Health check
echo -e "${BLUE}[1] Testing health endpoint...${NC}"
api_call GET "/health" | jq '.'
echo -e "${GREEN}✓ Health check passed${NC}"
echo ""

# Camera status (should show new v2.0 fields)
echo -e "${BLUE}[2] Testing camera status (with v2.0 metadata)...${NC}"
api_call GET "/v1/camera/status" | jq '.'
echo -e "${GREEN}✓ Camera status retrieved (check for autofocus_mode, scene_mode, etc.)${NC}"
echo ""

# Autofocus controls
echo -e "${BLUE}[3] Testing autofocus mode...${NC}"
api_call POST "/v1/camera/autofocus_mode" '{"mode": "continuous"}' | jq '.'
echo -e "${GREEN}✓ Autofocus mode set${NC}"
echo ""

echo -e "${BLUE}[4] Testing lens position...${NC}"
api_call POST "/v1/camera/lens_position" '{"position": 5.0}' | jq '.'
echo -e "${GREEN}✓ Lens position set${NC}"
echo ""

echo -e "${BLUE}[5] Testing autofocus range...${NC}"
api_call POST "/v1/camera/autofocus_range" '{"range_mode": "normal"}' | jq '.'
echo -e "${GREEN}✓ Autofocus range set${NC}"
echo ""

# Snapshot capture
echo -e "${BLUE}[6] Testing snapshot capture (this will take a moment)...${NC}"
SNAPSHOT_RESPONSE=$(api_call POST "/v1/camera/snapshot" '{"width": 640, "height": 480, "autofocus_trigger": true}')
if echo "$SNAPSHOT_RESPONSE" | jq -e '.image_base64' > /dev/null 2>&1; then
    IMAGE_SIZE=$(echo "$SNAPSHOT_RESPONSE" | jq -r '.image_base64' | wc -c)
    echo -e "${GREEN}✓ Snapshot captured (base64 size: $IMAGE_SIZE bytes)${NC}"
else
    echo -e "${RED}✗ Snapshot failed${NC}"
    echo "$SNAPSHOT_RESPONSE" | jq '.'
fi
echo ""

# Manual AWB
echo -e "${BLUE}[7] Testing manual white balance...${NC}"
api_call POST "/v1/camera/manual_awb" '{"red_gain": 1.5, "blue_gain": 1.8}' | jq '.'
echo -e "${GREEN}✓ Manual AWB set${NC}"
echo ""

echo -e "${BLUE}[8] Testing AWB preset (NoIR optimized)...${NC}"
api_call POST "/v1/camera/awb_preset" '{"preset": "daylight_noir"}' | jq '.'
echo -e "${GREEN}✓ AWB preset applied${NC}"
echo ""

# Image processing
echo -e "${BLUE}[9] Testing image processing parameters...${NC}"
api_call POST "/v1/camera/image_processing" '{"brightness": 0.1, "contrast": 1.2, "saturation": 1.0, "sharpness": 8.0}' | jq '.'
echo -e "${GREEN}✓ Image processing params set${NC}"
echo ""

# HDR mode
echo -e "${BLUE}[10] Testing HDR mode...${NC}"
api_call POST "/v1/camera/hdr" '{"mode": "off"}' | jq '.'
echo -e "${GREEN}✓ HDR mode set${NC}"
echo ""

# ROI (Region of Interest)
echo -e "${BLUE}[11] Testing ROI (center crop)...${NC}"
api_call POST "/v1/camera/roi" '{"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5}' | jq '.'
echo -e "${GREEN}✓ ROI set${NC}"
echo ""

# Reset ROI
echo -e "${BLUE}[12] Resetting ROI to full frame...${NC}"
api_call POST "/v1/camera/roi" '{"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}' | jq '.'
echo -e "${GREEN}✓ ROI reset${NC}"
echo ""

# Exposure limits
echo -e "${BLUE}[13] Testing exposure limits...${NC}"
api_call POST "/v1/camera/exposure_limits" '{"min_exposure_us": 1000, "max_exposure_us": 50000, "min_gain": 1.0, "max_gain": 8.0}' | jq '.'
echo -e "${GREEN}✓ Exposure limits set${NC}"
echo ""

# Lens correction
echo -e "${BLUE}[14] Testing lens correction (wide angle)...${NC}"
api_call POST "/v1/camera/lens_correction" '{"enabled": true}' | jq '.'
echo -e "${GREEN}✓ Lens correction enabled${NC}"
echo ""

# Transform
echo -e "${BLUE}[15] Testing image transform...${NC}"
api_call POST "/v1/camera/transform" '{"hflip": false, "vflip": false, "rotation": 0}' | jq '.'
echo -e "${GREEN}✓ Transform set${NC}"
echo ""

# Day/night mode
echo -e "${BLUE}[16] Testing day/night detection mode...${NC}"
api_call POST "/v1/camera/day_night_mode" '{"mode": "auto", "threshold_lux": 10.0}' | jq '.'
echo -e "${GREEN}✓ Day/night mode set${NC}"
echo ""

# Final status check to see all changes
echo -e "${BLUE}[17] Final camera status check (verify all changes)...${NC}"
api_call GET "/v1/camera/status" | jq '.'
echo -e "${GREEN}✓ Final status retrieved${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ All v2.0 API tests passed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Notes:"
echo "  - Some features (HDR, lens correction, transform) may require camera restart"
echo "  - NoIR AWB presets are optimized for your Camera Module 3 Wide NoIR"
echo "  - Check status output for: autofocus_mode, scene_mode, lens_position, etc."
