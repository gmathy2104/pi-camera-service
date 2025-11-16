#!/bin/bash
# Pi Camera Service - API Integration Test Runner
#
# This script runs integration tests against the live API.
# The service must be running before executing this script.
#
# Usage:
#   ./test-api.sh           # Run with python directly (no pytest needed)
#   ./test-api.sh pytest    # Run with pytest (more detailed output)

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if service is running
echo -e "${YELLOW}Checking if Pi Camera Service is running...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to API at http://localhost:8000${NC}"
    echo ""
    echo "Please start the service first:"
    echo "  python main.py"
    echo ""
    echo "Or if running as a service:"
    echo "  sudo systemctl start pi-camera-service"
    exit 1
fi

echo -e "${GREEN}✓ Service is running${NC}"
echo ""

# Run tests based on argument
if [ "$1" == "pytest" ]; then
    echo -e "${YELLOW}Running tests with pytest...${NC}"
    echo ""

    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}ERROR: pytest is not installed${NC}"
        echo "Install it with: pip install pytest pytest-timeout"
        exit 1
    fi

    # Run with pytest
    pytest tests/test_api_integration.py -v --timeout=30
else
    echo -e "${YELLOW}Running tests with python...${NC}"
    echo ""

    # Run directly with python
    python tests/test_api_integration.py
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
