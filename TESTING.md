# Pi Camera Service - Testing Guide

This guide explains how to test the Pi Camera Service to verify it's working correctly.

## Types of Tests

### 1. Unit Tests

Unit tests test individual components in isolation (with mocked dependencies).

**Location**: `tests/test_*.py` (except `test_api_integration.py`)

**Run with**:
```bash
pytest tests/ -v --ignore=tests/test_api_integration.py
```

These tests DO NOT require the service to be running.

### 2. API Integration Tests

Integration tests test the complete API against a live running service.

**Location**: `tests/test_api_integration.py`

**Requirements**: The service MUST be running before executing these tests.

## Running API Integration Tests

### Method 1: Using the Test Script (Recommended)

The easiest way to test the API:

```bash
# Start the service first (if not already running as systemd service)
python main.py

# In another terminal, run the tests
./test-api.sh
```

**Output**:
```
✓ Service is running
============================================================
Pi Camera Service - API Integration Tests
============================================================

[1/9] Checking if service is running...
✓ Service is running at http://localhost:8000

[2/9] Testing health endpoint...
✓ Health endpoint working

... (all tests)

✓ All tests passed! Your Pi Camera Service is working correctly.
```

### Method 2: Using Python Directly

```bash
python tests/test_api_integration.py
```

This doesn't require pytest to be installed.

### Method 3: Using pytest (Most Detailed Output)

```bash
# Install pytest first (if not already installed)
pip install pytest pytest-timeout

# Run with pytest
./test-api.sh pytest

# Or directly
pytest tests/test_api_integration.py -v --timeout=30
```

## What the API Integration Tests Cover

The integration tests verify all API endpoints:

1. **GET /health** - Service health check
2. **GET /v1/camera/status** - Camera status and metadata
3. **POST /v1/camera/auto_exposure** - Enable/disable auto exposure
4. **POST /v1/camera/manual_exposure** - Set manual exposure parameters
   - Valid parameters
   - Invalid exposure (validation)
   - Invalid gain (validation)
5. **POST /v1/camera/awb** - Enable/disable auto white balance
6. **POST /v1/streaming/stop** - Stop RTSP streaming
7. **POST /v1/streaming/start** - Start RTSP streaming

## Testing Against a Remote Service

By default, tests run against `http://localhost:8000`. To test a remote instance:

```bash
# Edit the BASE_URL in tests/test_api_integration.py
# Change: BASE_URL = "http://localhost:8000"
# To:     BASE_URL = "http://192.168.1.100:8000"

# Then run tests normally
./test-api.sh
```

Or set it as an environment variable:

```python
# In tests/test_api_integration.py, change:
BASE_URL = "http://localhost:8000"

# To:
import os
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

Then run:
```bash
API_BASE_URL=http://192.168.1.100:8000 ./test-api.sh
```

## Continuous Integration

For CI/CD pipelines, use the exit code to determine success:

```bash
./test-api.sh
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Tests failed"
    exit 1
fi
```

## Troubleshooting

### "Cannot connect to API at http://localhost:8000"

**Solution**: Start the service first:

```bash
# If running manually:
python main.py

# If running as systemd service:
sudo systemctl start pi-camera-service

# Check service status:
sudo systemctl status pi-camera-service
```

### Tests timeout or hang

**Possible causes**:
1. Service is overloaded or unresponsive
2. Camera hardware issue
3. Streaming process stuck

**Solution**:
```bash
# Restart the service
sudo systemctl restart pi-camera-service

# Check logs for errors
sudo journalctl -u pi-camera-service -n 50
```

### Some tests fail but service works

**Possible causes**:
1. Camera in manual mode when tests expect auto mode
2. Previous test didn't cleanup properly

**Solution**: Restart the service to reset to default state:
```bash
sudo systemctl restart pi-camera-service
sleep 3
./test-api.sh
```

### Test streaming stop/start fails

This was a known issue that has been fixed. If you still encounter it:

1. Make sure you're on the latest version with the streaming restart fix
2. Check logs: `sudo journalctl -u pi-camera-service -n 20`
3. Verify ffmpeg is installed: `which ffmpeg`

## Quick Health Check

Just want to verify the service is responding?

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
    "status": "healthy",
    "camera_configured": true,
    "streaming_active": true,
    "version": "1.0.0"
}
```

## Complete Test Suite

To run ALL tests (unit + integration):

```bash
# 1. Start the service
python main.py &
SERVICE_PID=$!
sleep 5

# 2. Run unit tests
pytest tests/ -v --ignore=tests/test_api_integration.py

# 3. Run integration tests
./test-api.sh

# 4. Stop the service
kill $SERVICE_PID
```

Or use this one-liner:
```bash
python main.py & sleep 5 && pytest tests/ -v && ./test-api.sh && pkill -f "python main.py"
```

## Pre-Production Checklist

Before deploying to production, verify:

- [ ] All unit tests pass: `pytest tests/ --ignore=tests/test_api_integration.py`
- [ ] All integration tests pass: `./test-api.sh`
- [ ] Service starts automatically: `sudo systemctl status pi-camera-service`
- [ ] Streaming works: Test with VLC at `rtsp://<IP>:8554/cam`
- [ ] API is accessible: `curl http://<IP>:8000/health`
- [ ] Logs are clean: `sudo journalctl -u pi-camera-service -n 50`

---

## Adding New Tests

When adding new API endpoints, add corresponding tests to `tests/test_api_integration.py`:

```python
def test_new_endpoint(self) -> None:
    """Test POST /v1/new/endpoint."""
    response = requests.post(
        f"{BASE_URL}/v1/new/endpoint",
        json={"param": "value"},
        timeout=TIMEOUT,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    print("✓ New endpoint working")
```

Then add it to the main runner in the `if __name__ == "__main__"` section.

---

## Support

If tests fail and you can't figure out why:

1. Check service logs: `sudo journalctl -u pi-camera-service -f`
2. Verify camera: `rpicam-hello --list-cameras`
3. Check MediaMTX: `sudo systemctl status mediamtx`
4. Review [SERVICE-SETUP.md](SERVICE-SETUP.md) troubleshooting section
