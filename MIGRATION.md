# Migration Guide to v1.0

This guide helps you migrate from the original version to the refactored v1.0 production-ready version.

## Breaking Changes

### 1. API Endpoints - New `/v1` Prefix

All camera and streaming endpoints now have a `/v1` prefix:

**Old:**
- `GET /camera/status`
- `POST /camera/auto_exposure`
- `POST /camera/manual_exposure`
- `POST /camera/awb`
- `POST /streaming/start`
- `POST /streaming/stop`

**New:**
- `GET /v1/camera/status`
- `POST /v1/camera/auto_exposure`
- `POST /v1/camera/manual_exposure`
- `POST /v1/camera/awb`
- `POST /v1/streaming/start`
- `POST /v1/streaming/stop`

**Added:**
- `GET /health` - Health check endpoint (no auth required)

### 2. API Authentication

The API now supports optional API key authentication via the `X-API-Key` header.

**To enable authentication:**
```bash
export CAMERA_API_KEY="your-secret-key-here"
# or in .env file:
CAMERA_API_KEY=your-secret-key-here
```

**Client requests must include the header:**
```bash
curl -H "X-API-Key: your-secret-key-here" http://pi:8000/v1/camera/status
```

```python
import requests

headers = {"X-API-Key": "your-secret-key-here"}
response = requests.get("http://pi:8000/v1/camera/status", headers=headers)
```

**To disable authentication** (default):
- Don't set `CAMERA_API_KEY` environment variable
- Or set it to empty string

### 3. Environment Variable Configuration

All settings can now be configured via environment variables with the `CAMERA_` prefix:

```bash
# Video settings
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
CAMERA_FRAMERATE=30
CAMERA_BITRATE=8000000

# Server settings
CAMERA_HOST=0.0.0.0
CAMERA_PORT=8000

# Security
CAMERA_API_KEY=your-secret-key

# Logging
CAMERA_LOG_LEVEL=INFO
```

See `.env.example` for all available options.

### 4. Error Messages

Error messages are now in English (previously French):

**Old:**
```
"exposure_us doit être > 0"
```

**New:**
```
"exposure_us must be >= 100 (got 50)"
```

### 5. Response Models

POST endpoints now return structured response models instead of generic dicts.

**Example - Auto Exposure Response:**
```json
{
  "status": "ok",
  "auto_exposure": true
}
```

All responses now have consistent structure with proper typing.

## New Features

### 1. Comprehensive Logging

The service now includes detailed logging at all levels:

```bash
# Set log level via environment variable
CAMERA_LOG_LEVEL=DEBUG python main.py
```

Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### 2. Health Check Endpoint

New `/health` endpoint for monitoring (doesn't require authentication):

```bash
curl http://pi:8000/health
```

Response:
```json
{
  "status": "healthy",
  "camera_configured": true,
  "streaming_active": true,
  "version": "1.0.0"
}
```

### 3. Better Error Handling

- Custom exception types for different error scenarios
- Proper HTTP status codes (401, 422, 500, 503)
- Global exception handlers
- Graceful degradation on errors

### 4. Resource Cleanup

- Proper camera resource cleanup on shutdown
- Streaming resources properly released
- No resource leaks

### 5. Input Validation

Enhanced validation with clear error messages:

- Exposure time: 100 - 1,000,000 µs
- Gain: 1.0 - 16.0
- Resolution: 64 - 4096 pixels
- Framerate: 1 - 120 fps
- Port: 1 - 65535

## Testing

The project now includes comprehensive tests:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=camera_service --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v
```

## Development Improvements

### New Files

- `camera_service/exceptions.py` - Custom exception types
- `.env.example` - Environment variable template
- `requirements-dev.txt` - Development dependencies
- `tests/` - Comprehensive test suite
- `MIGRATION.md` - This file

### Code Quality

- Full type hints throughout
- Comprehensive docstrings
- Thread-safe with RLock
- Modern async/await patterns (lifespan)
- Dependency injection

## Migration Checklist

- [ ] Update client code to use `/v1/` prefix for all endpoints
- [ ] Add `X-API-Key` header if authentication is enabled
- [ ] Update error handling for new error messages (English)
- [ ] Test with new response models
- [ ] Configure environment variables in `.env` file
- [ ] Update monitoring to use `/health` endpoint
- [ ] Review and adjust log levels
- [ ] Update systemd service file if needed
- [ ] Test streaming lifecycle
- [ ] Verify camera cleanup on shutdown

## Backwards Compatibility

**Not Provided:**
- Old endpoint URLs (without `/v1` prefix) are not supported
- You must update client applications

**Maintained:**
- Core functionality remains the same
- RTSP streaming protocol unchanged
- MediaMTX configuration unchanged
- Camera control logic unchanged

## Support

For issues or questions, please check:
1. This migration guide
2. Updated README.md
3. CLAUDE.md for development details
4. Test files for usage examples
