# Development Guide

Complete guide for developers contributing to Pi Camera Service.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Development Setup](#development-setup)
- [Code Structure](#code-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Contributing](#contributing)

---

## Project Overview

**Pi Camera Service** is a production-ready FastAPI-based microservice for Raspberry Pi that provides HTTP API control over Raspberry Pi cameras with RTSP streaming via MediaMTX.

### Key Features

- **FastAPI HTTP API** - Modern async web framework
- **RTSP Streaming** - H.264 video via MediaMTX
- **Camera Module 3 Support** - Autofocus, HDR, advanced controls
- **NoIR Optimization** - Auto-detection and presets for night vision
- **Type Safety** - Full Pydantic validation
- **Thread Safety** - RLock for concurrent operations
- **API Authentication** - Optional API key protection
- **Production Ready** - Systemd service, comprehensive logging, 80%+ test coverage

### Technology Stack

- **Python 3.9+** - Core language
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **Picamera2** - Camera interface
- **libcamera** - Low-level camera control
- **FFmpeg** - Video processing for RTSP
- **pytest** - Testing framework
- **MediaMTX** - RTSP/WebRTC/HLS server

---

## Architecture

### High-Level Flow

```
┌─────────────────┐
│   External App  │ (Backend, UI, Mobile...)
└────────┬────────┘
         │ HTTP API
         ▼
┌─────────────────────────────┐
│   Pi Camera Service (FastAPI) │
│   ┌─────────┬─────────┐    │
│   │ Camera  │Streaming│    │
│   │Controller│Manager  │    │
│   └─────────┴─────────┘    │
└─────────┬──────────┬────────┘
          │          │
          ▼          ▼
   ┌──────────┐ ┌─────────┐
   │Picamera2 │ │ FFmpeg  │
   │libcamera │ │ H.264   │
   └──────────┘ └────┬────┘
        │             │
        ▼             ▼
   ┌─────────────────────┐
   │   MediaMTX Server   │
   │  (RTSP/WebRTC/HLS)  │
   └─────────────────────┘
```

### Component Responsibilities

#### `camera_service/config.py`
- Pydantic `BaseSettings` for configuration management
- Environment variable support (prefix: `CAMERA_`)
- Validation with clear error messages
- Single `CONFIG` instance used throughout

#### `camera_service/exceptions.py`
- Custom exception hierarchy
- Types: `CameraError`, `CameraNotAvailableError`, `InvalidParameterError`, `StreamingError`, `ConfigurationError`
- Enables proper error handling with meaningful messages

#### `camera_service/camera_controller.py`
- **CameraController class** - Main camera control interface
- Thread-safe operations with `RLock` (reentrant lock)
- Camera initialization and configuration
- Exposure control (auto/manual) with hardware validation
- AWB (auto white balance) management
- Autofocus control (Camera Module 3)
- Image processing (brightness, contrast, saturation, sharpness)
- HDR, ROI, lens correction, transforms
- Snapshot capture (JPEG without stopping stream)
- Status/metadata retrieval
- Proper resource cleanup

#### `camera_service/streaming_manager.py`
- **StreamingManager class** - RTSP streaming lifecycle
- H.264 encoding with `H264Encoder`
- FFmpeg output to MediaMTX via RTSP
- Thread-safe with `RLock`
- Automatic cleanup on failure
- Comprehensive error handling

#### `camera_service/api.py`
- FastAPI application with v1/v2 API
- Modern patterns:
  - `@asynccontextmanager` lifespan (replaces deprecated `on_event`)
  - Dependency injection for controllers
  - API key authentication via `X-API-Key` header
- Pydantic models for all requests/responses
- Global exception handlers
- Health check endpoint (`/health`)
- API versioning (`/v1/...`)
- Proper HTTP status codes (200, 400, 401, 422, 500, 503)

#### `main.py`
- Application entry point
- Launches uvicorn server
- Configurable via `CONFIG`

### Design Patterns

1. **Modern Lifecycle Management** - `@asynccontextmanager` lifespan
2. **Dependency Injection** - FastAPI dependencies
3. **Reentrant Thread Safety** - `RLock` for nested lock acquisition
4. **Configuration as Code** - Pydantic BaseSettings
5. **Comprehensive Error Handling** - Custom exceptions with global handlers
6. **Resource Cleanup** - Proper cleanup in lifespan shutdown
7. **Separation of Concerns** - Clear layer boundaries
8. **Type Safety** - Full type hints with Pydantic
9. **Logging First** - All operations logged for observability

---

## Development Setup

### Prerequisites

- Raspberry Pi 4/5 or Zero 2W
- Raspberry Pi Camera (any model, Camera Module 3 recommended)
- Raspberry Pi OS Bullseye or newer
- Python 3.9+

### System Dependencies

```bash
sudo apt update
sudo apt install -y \
  python3-venv \
  python3-picamera2 \
  python3-libcamera \
  libcamera-apps \
  ffmpeg \
  git
```

### Clone Repository

```bash
git clone https://github.com/gmathy2104/pi-camera-service.git
cd pi-camera-service
```

### Virtual Environment

**CRITICAL:** Must use `--system-site-packages` to access picamera2!

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
```

### Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (testing, linting, type checking)
pip install -r requirements-dev.txt
```

**Verify installation:**
```bash
python -c "from picamera2 import Picamera2; print('✓ picamera2 OK')"
```

### Configure Environment

```bash
cp .env.example .env
nano .env
```

---

## Code Structure

```
pi-camera-service/
├── camera_service/           # Main application package
│   ├── __init__.py
│   ├── api.py                # FastAPI application
│   ├── camera_controller.py  # Camera control logic
│   ├── streaming_manager.py  # RTSP streaming
│   ├── config.py             # Configuration management
│   └── exceptions.py         # Custom exceptions
│
├── tests/                    # Test suite
│   ├── conftest.py           # pytest fixtures
│   ├── test_config.py        # Config tests
│   ├── test_camera_controller.py
│   ├── test_streaming_manager.py
│   ├── test_api.py           # Unit tests
│   └── test_api_integration.py
│
├── scripts/                  # Utility scripts
│   ├── install-service.sh
│   ├── uninstall-service.sh
│   ├── test-api.sh           # v1.0 API tests
│   └── test-api-v2.sh        # v2.0 API tests
│
├── docs/                     # Documentation
│   ├── installation.md
│   ├── configuration.md
│   ├── api-reference.md
│   ├── upgrade-v2.md
│   └── development.md        # This file
│
├── main.py                   # Application entry point
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
├── .env.example              # Configuration template
├── pi-camera-service.service # Systemd service file
├── VERSION                   # Semantic version
├── CHANGELOG.md              # Version history
├── LICENSE                   # MIT license
└── README.md                 # Project overview
```

---

## Development Workflow

### Running Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default configuration
python main.py

# Run with custom config
CAMERA_PORT=9000 CAMERA_LOG_LEVEL=DEBUG python main.py
```

### Making Changes

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**
   - Follow existing code style
   - Add type hints to all functions
   - Add docstrings to public methods
   - Update tests for new functionality

3. **Run tests**
   ```bash
   pytest
   ```

4. **Check code quality**
   ```bash
   black camera_service tests
   ruff check camera_service tests
   mypy camera_service
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

---

## Testing

### Test Types

#### 1. Unit Tests

Test individual components in isolation with mocked dependencies.

**Location:** `tests/test_*.py` (except `test_api_integration.py`)

**Run:**
```bash
# All unit tests
pytest tests/ --ignore=tests/test_api_integration.py

# Specific test file
pytest tests/test_camera_controller.py -v

# Specific test class
pytest tests/test_camera_controller.py::TestCameraControllerExposure -v

# Specific test
pytest tests/test_camera_controller.py::TestCameraControllerExposure::test_set_auto_exposure_enable -v
```

**No service required** - Unit tests mock all dependencies.

#### 2. Integration Tests

Test complete API against a running service.

**Location:** `tests/test_api_integration.py`

**Requirements:** Service MUST be running first!

**Run:**
```bash
# Start service in one terminal
python main.py

# Run integration tests in another terminal
./scripts/test-api.sh

# Or with pytest
pytest tests/test_api_integration.py -v
```

#### 3. API Test Scripts

Bash scripts that test all API endpoints.

**v1.0 API:**
```bash
./scripts/test-api.sh
```

**v2.0 API (Camera Module 3 features):**
```bash
./scripts/test-api-v2.sh
```

### Running All Tests

```bash
# All unit tests
pytest tests/ --ignore=tests/test_api_integration.py

# With coverage report
pytest --cov=camera_service --cov-report=html
# Open htmlcov/index.html

# Fast parallel execution
pytest -n auto

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=camera_service --cov-report=term-missing

# HTML coverage report
pytest --cov=camera_service --cov-report=html
open htmlcov/index.html
```

**Target:** >80% code coverage

### Writing Tests

**Example unit test:**
```python
def test_set_auto_exposure_enable(mock_camera_controller):
    """Test enabling auto-exposure."""
    controller = mock_camera_controller

    result = controller.set_auto_exposure(enabled=True)

    assert result is True
    assert controller._auto_exposure is True
```

**Example integration test:**
```python
def test_camera_status_endpoint():
    """Test GET /v1/camera/status returns valid data."""
    response = requests.get(f"{BASE_URL}/v1/camera/status")

    assert response.status_code == 200
    data = response.json()
    assert "lux" in data
    assert "exposure_us" in data
```

---

## Code Quality

### Formatting

**Black** - Automatic code formatting

```bash
# Format all code
black camera_service tests

# Check without changing
black camera_service tests --check

# Specific file
black camera_service/api.py
```

### Linting

**Ruff** - Fast Python linter

```bash
# Lint all code
ruff check camera_service tests

# Auto-fix issues
ruff check camera_service tests --fix

# Specific rules
ruff check camera_service --select E,F,I
```

### Type Checking

**mypy** - Static type checker

```bash
# Type check
mypy camera_service

# Strict mode
mypy camera_service --strict

# Specific file
mypy camera_service/api.py
```

### Pre-commit Checks

Before committing, run:

```bash
# Format
black camera_service tests

# Lint
ruff check camera_service tests --fix

# Type check
mypy camera_service

# Test
pytest
```

---

## Contributing

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Code style (formatting, no logic change)
- `refactor:` - Code refactoring
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

**Examples:**
```
feat(camera): add autofocus control for Camera Module 3
fix(api): handle null values in status endpoint
docs: update installation guide with NoIR camera setup
test: add integration tests for snapshot endpoint
```

### Pull Request Process

1. Fork the repository
2. Create feature branch from `master`
3. Make changes with tests
4. Ensure all tests pass
5. Run code quality checks
6. Update documentation if needed
7. Submit PR with clear description

### Code Review Checklist

- [ ] Code follows existing style
- [ ] All tests pass
- [ ] New code has tests (>80% coverage)
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Docstrings for public methods
- [ ] No hardcoded values (use config)
- [ ] Proper error handling
- [ ] Logging added for important operations
- [ ] No security vulnerabilities
- [ ] Backwards compatible (or documented breaking change)

---

## Debugging

### Enable Debug Logging

```bash
CAMERA_LOG_LEVEL=DEBUG python main.py
```

### View Service Logs

```bash
# Live tail
sudo journalctl -u pi-camera-service -f

# Last 100 lines
sudo journalctl -u pi-camera-service -n 100

# With timestamps
sudo journalctl -u pi-camera-service -o short-iso -n 50
```

### Test Camera Manually

```bash
# List cameras
rpicam-hello --list-cameras

# Test camera
rpicam-hello --timeout 5000

# Capture test image
rpicam-still -o test.jpg
```

### Debug Mode in IDE

Add breakpoints and run with debugger:

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "camera_service.api:app",
        host=CONFIG.host,
        port=CONFIG.port,
        log_level=CONFIG.log_level.lower(),
        reload=True  # Enable auto-reload for development
    )
```

---

## API Development

### Adding New Endpoints

1. **Define Pydantic models** in `api.py`:
   ```python
   class MyRequest(BaseModel):
       param: int = Field(..., ge=0, le=100)

   class MyResponse(BaseModel):
       status: str
       value: int
   ```

2. **Add controller method** in `camera_controller.py`:
   ```python
   def my_new_feature(self, param: int) -> int:
       with self._lock:
           # Implementation
           return result
   ```

3. **Add endpoint** in `api.py`:
   ```python
   @app.post("/v1/camera/my_feature", response_model=MyResponse)
   def my_feature(
       request: MyRequest,
       camera: CameraController = Depends(get_camera_controller)
   ):
       result = camera.my_new_feature(request.param)
       return MyResponse(status="ok", value=result)
   ```

4. **Add tests** in `tests/test_api.py`:
   ```python
   def test_my_feature_endpoint(client):
       response = client.post(
           "/v1/camera/my_feature",
           json={"param": 50}
       )
       assert response.status_code == 200
       assert response.json()["value"] == 50
   ```

5. **Update documentation** in `docs/api-reference.md`

### Thread Safety Guidelines

- Always acquire lock before camera operations:
  ```python
  with self._lock:
      # Camera operations here
  ```
- Use `RLock` (reentrant) not `Lock` (allows nested acquisition)
- Keep lock duration minimal
- Never do I/O while holding lock

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [libcamera Documentation](https://libcamera.org/getting-started.html)
- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## Support

- **Issues:** [GitHub Issues](https://github.com/gmathy2104/pi-camera-service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/gmathy2104/pi-camera-service/discussions)
- **Documentation:** [docs/](.)

---

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.
