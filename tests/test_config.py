"""
Tests for configuration module.

Tests Pydantic BaseSettings configuration including validation,
environment variable support, and default values.
"""

import pytest
from pydantic import ValidationError

from camera_service.config import CameraConfig


class TestCameraConfig:
    """Test cases for CameraConfig."""

    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = CameraConfig()

        assert config.width == 1920
        assert config.height == 1080
        assert config.framerate == 30
        assert config.bitrate == 8_000_000
        assert config.rtsp_url == "rtsp://127.0.0.1:8554/cam"
        assert config.enable_awb is True
        assert config.default_auto_exposure is True
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.api_key is None
        assert config.log_level == "INFO"

    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("CAMERA_WIDTH", "1280")
        monkeypatch.setenv("CAMERA_HEIGHT", "720")
        monkeypatch.setenv("CAMERA_FRAMERATE", "60")
        monkeypatch.setenv("CAMERA_PORT", "9000")
        monkeypatch.setenv("CAMERA_API_KEY", "secret-key")

        config = CameraConfig()

        assert config.width == 1280
        assert config.height == 720
        assert config.framerate == 60
        assert config.port == 9000
        assert config.api_key == "secret-key"

    def test_resolution_validation_min(self):
        """Test that resolution below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(width=32)  # Below minimum of 64

        assert "width" in str(exc_info.value)

    def test_resolution_validation_max(self):
        """Test that resolution above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(width=5000)  # Above maximum of 4096

        assert "width" in str(exc_info.value)

    def test_framerate_validation_min(self):
        """Test that framerate below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(framerate=0)  # Below minimum of 1

        assert "framerate" in str(exc_info.value)

    def test_framerate_validation_max(self):
        """Test that framerate above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(framerate=200)  # Above maximum of 120

        assert "framerate" in str(exc_info.value)

    def test_bitrate_validation_min(self):
        """Test that bitrate below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(bitrate=50_000)  # Below minimum of 100_000

        assert "bitrate" in str(exc_info.value)

    def test_bitrate_validation_max(self):
        """Test that bitrate above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(bitrate=100_000_000)  # Above maximum of 50_000_000

        assert "bitrate" in str(exc_info.value)

    def test_port_validation_min(self):
        """Test that port below minimum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(port=0)  # Below minimum of 1

        assert "port" in str(exc_info.value)

    def test_port_validation_max(self):
        """Test that port above maximum is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(port=70000)  # Above maximum of 65535

        assert "port" in str(exc_info.value)

    def test_log_level_validation_valid(self):
        """Test that valid log levels are accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = CameraConfig(log_level=level)
            assert config.log_level == level

    def test_log_level_validation_case_insensitive(self):
        """Test that log level is case insensitive."""
        config = CameraConfig(log_level="debug")
        assert config.log_level == "DEBUG"

        config = CameraConfig(log_level="Info")
        assert config.log_level == "INFO"

    def test_log_level_validation_invalid(self):
        """Test that invalid log level is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(log_level="INVALID")

        assert "log_level" in str(exc_info.value)

    def test_rtsp_url_validation_valid(self):
        """Test that valid RTSP URL is accepted."""
        config = CameraConfig(rtsp_url="rtsp://192.168.1.100:8554/camera")
        assert config.rtsp_url == "rtsp://192.168.1.100:8554/camera"

    def test_rtsp_url_validation_invalid(self):
        """Test that non-RTSP URL is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CameraConfig(rtsp_url="http://localhost:8554/camera")

        assert "rtsp_url" in str(exc_info.value)
        assert "must start with rtsp://" in str(exc_info.value)

    def test_bool_fields(self):
        """Test boolean configuration fields."""
        config = CameraConfig(
            enable_awb=False,
            default_auto_exposure=False,
        )

        assert config.enable_awb is False
        assert config.default_auto_exposure is False

    def test_optional_api_key(self):
        """Test that API key can be None or a string."""
        # None (default)
        config1 = CameraConfig()
        assert config1.api_key is None

        # String value
        config2 = CameraConfig(api_key="my-secret-key")
        assert config2.api_key == "my-secret-key"

    def test_valid_configuration(self):
        """Test a complete valid configuration."""
        config = CameraConfig(
            width=1280,
            height=720,
            framerate=30,
            bitrate=4_000_000,
            rtsp_url="rtsp://127.0.0.1:8554/test",
            enable_awb=True,
            default_auto_exposure=False,
            host="127.0.0.1",
            port=9000,
            api_key="test-key",
            log_level="DEBUG",
        )

        assert config.width == 1280
        assert config.height == 720
        assert config.framerate == 30
        assert config.bitrate == 4_000_000
        assert config.rtsp_url == "rtsp://127.0.0.1:8554/test"
        assert config.enable_awb is True
        assert config.default_auto_exposure is False
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.api_key == "test-key"
        assert config.log_level == "DEBUG"
