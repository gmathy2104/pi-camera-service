"""
Pytest configuration and fixtures for Pi Camera Service tests.

Provides mocks for Picamera2 and common test fixtures.
"""

import pytest
from unittest.mock import MagicMock, Mock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_picamera2():
    """
    Mock Picamera2 class for testing.

    Returns a mock object that simulates Picamera2 behavior without
    requiring actual camera hardware.
    """
    mock = MagicMock()

    # Mock camera info
    mock.global_camera_info.return_value = [
        {"Model": "imx708", "Location": 2, "Rotation": 0}
    ]

    # Mock configuration methods
    mock.create_video_configuration.return_value = {
        "main": {"size": (1920, 1080), "format": "YUV420"},
        "controls": {"FrameRate": 30},
    }

    # Mock metadata
    mock.capture_metadata.return_value = {
        "Lux": 100.0,
        "ExposureTime": 10000,
        "AnalogueGain": 1.5,
        "ColourTemperature": 4500.0,
    }

    # Mock control methods
    mock.set_controls = Mock()
    mock.configure = Mock()
    mock.start_recording = Mock()
    mock.stop_recording = Mock()
    mock.close = Mock()

    return mock


@pytest.fixture
def mock_picamera2_class(monkeypatch, mock_picamera2):
    """
    Patch the Picamera2 class to return our mock.

    This fixture patches the Picamera2 import so all tests use the mock.
    """
    def mock_init(*args, **kwargs):
        return mock_picamera2

    monkeypatch.setattr(
        "camera_service.camera_controller.Picamera2",
        lambda: mock_picamera2
    )

    # Also patch global_camera_info as a class method
    import camera_service.camera_controller
    original_picamera2 = camera_service.camera_controller.Picamera2
    original_picamera2.global_camera_info = mock_picamera2.global_camera_info

    return mock_picamera2


@pytest.fixture
def camera_controller(mock_picamera2_class):
    """
    Create a CameraController instance with mocked Picamera2.

    Returns:
        CameraController: Controller instance for testing
    """
    from camera_service.camera_controller import CameraController

    controller = CameraController()
    controller.configure()
    return controller


@pytest.fixture
def streaming_manager(camera_controller):
    """
    Create a StreamingManager instance with mocked camera.

    Returns:
        StreamingManager: Manager instance for testing
    """
    from camera_service.streaming_manager import StreamingManager

    return StreamingManager(camera_controller)


@pytest.fixture
def test_config():
    """
    Provide test configuration values.

    Returns:
        dict: Test configuration
    """
    return {
        "width": 1280,
        "height": 720,
        "framerate": 30,
        "bitrate": 4_000_000,
        "rtsp_url": "rtsp://127.0.0.1:8554/test",
        "api_key": "test-api-key-12345",
        "log_level": "DEBUG",
    }


@pytest.fixture
def client_no_auth(monkeypatch, mock_picamera2_class):
    """
    Create a FastAPI test client without authentication.

    Returns:
        TestClient: Test client with authentication disabled
    """
    # Disable authentication for this client
    monkeypatch.setenv("CAMERA_API_KEY", "")

    # Re-import to get fresh CONFIG
    import importlib
    import camera_service.config
    importlib.reload(camera_service.config)

    from camera_service.api import app
    return TestClient(app)


@pytest.fixture
def client_with_auth(monkeypatch, mock_picamera2_class, test_config):
    """
    Create a FastAPI test client with authentication enabled.

    Returns:
        TestClient: Test client with authentication enabled
    """
    # Enable authentication
    monkeypatch.setenv("CAMERA_API_KEY", test_config["api_key"])

    # Re-import to get fresh CONFIG
    import importlib
    import camera_service.config
    importlib.reload(camera_service.config)

    from camera_service.api import app
    return TestClient(app)


@pytest.fixture
def auth_headers(test_config):
    """
    Provide authentication headers for API requests.

    Returns:
        dict: Headers with API key
    """
    return {"X-API-Key": test_config["api_key"]}


@pytest.fixture(autouse=True)
def reset_logging():
    """
    Reset logging configuration between tests.

    This prevents log level changes from affecting other tests.
    """
    import logging

    # Store original level
    original_level = logging.root.level

    yield

    # Restore original level
    logging.root.setLevel(original_level)
