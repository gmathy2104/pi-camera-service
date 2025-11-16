"""
Tests for CameraController.

Tests camera initialization, configuration, exposure controls,
white balance, and error handling with mocked Picamera2.
"""

import pytest
from unittest.mock import MagicMock

from camera_service.camera_controller import CameraController, MAX_EXPOSURE_US, MIN_EXPOSURE_US, MAX_GAIN, MIN_GAIN
from camera_service.exceptions import (
    CameraNotAvailableError,
    ConfigurationError,
    InvalidParameterError,
)


class TestCameraControllerInit:
    """Test camera controller initialization."""

    def test_init(self, mock_picamera2_class):
        """Test that controller initializes correctly."""
        controller = CameraController()

        assert controller._picam2 is None
        assert controller._configured is False
        assert controller._lock is not None

    def test_configure_success(self, mock_picamera2_class, mock_picamera2):
        """Test successful camera configuration."""
        controller = CameraController()
        controller.configure()

        assert controller._configured is True
        mock_picamera2.configure.assert_called_once()
        mock_picamera2.create_video_configuration.assert_called_once()

    def test_configure_idempotent(self, mock_picamera2_class, mock_picamera2):
        """Test that configure can be called multiple times safely."""
        controller = CameraController()
        controller.configure()
        controller.configure()  # Should not configure again

        assert controller._configured is True
        # Should only be called once
        assert mock_picamera2.configure.call_count == 1

    def test_configure_no_camera(self, mock_picamera2_class, mock_picamera2):
        """Test configuration failure when no camera is available."""
        # Simulate no camera available
        mock_picamera2.global_camera_info.return_value = []

        controller = CameraController()

        with pytest.raises(CameraNotAvailableError):
            controller.configure()

    def test_configure_failure(self, mock_picamera2_class, mock_picamera2):
        """Test configuration failure handling."""
        mock_picamera2.configure.side_effect = Exception("Hardware error")

        controller = CameraController()

        with pytest.raises(ConfigurationError):
            controller.configure()


class TestCameraControllerExposure:
    """Test exposure control methods."""

    def test_set_auto_exposure_enable(self, camera_controller, mock_picamera2):
        """Test enabling auto exposure."""
        camera_controller.set_auto_exposure(True)

        mock_picamera2.set_controls.assert_called_with({
            "AeEnable": True,
            "ExposureTime": 0,
        })
        assert camera_controller._auto_exposure is True

    def test_set_auto_exposure_disable(self, camera_controller, mock_picamera2):
        """Test disabling auto exposure."""
        camera_controller.set_auto_exposure(False)

        mock_picamera2.set_controls.assert_called_with({
            "AeEnable": False,
        })
        assert camera_controller._auto_exposure is False

    def test_set_manual_exposure_valid(self, camera_controller, mock_picamera2):
        """Test setting valid manual exposure parameters."""
        camera_controller.set_manual_exposure(exposure_us=10000, gain=2.0)

        mock_picamera2.set_controls.assert_called_with({
            "AeEnable": False,
            "ExposureTime": 10000,
            "AnalogueGain": 2.0,
        })
        assert camera_controller._auto_exposure is False

    def test_set_manual_exposure_exposure_too_low(self, camera_controller):
        """Test that exposure below minimum is rejected."""
        with pytest.raises(InvalidParameterError) as exc_info:
            camera_controller.set_manual_exposure(exposure_us=50, gain=1.0)

        assert "exposure_us must be >=" in str(exc_info.value)

    def test_set_manual_exposure_exposure_too_high(self, camera_controller):
        """Test that exposure above maximum is rejected."""
        with pytest.raises(InvalidParameterError) as exc_info:
            camera_controller.set_manual_exposure(exposure_us=2_000_000, gain=1.0)

        assert "exposure_us must be <=" in str(exc_info.value)

    def test_set_manual_exposure_gain_too_low(self, camera_controller):
        """Test that gain below minimum is rejected."""
        with pytest.raises(InvalidParameterError) as exc_info:
            camera_controller.set_manual_exposure(exposure_us=10000, gain=0.5)

        assert "gain must be >=" in str(exc_info.value)

    def test_set_manual_exposure_gain_too_high(self, camera_controller):
        """Test that gain above maximum is rejected."""
        with pytest.raises(InvalidParameterError) as exc_info:
            camera_controller.set_manual_exposure(exposure_us=10000, gain=20.0)

        assert "gain must be <=" in str(exc_info.value)

    def test_set_manual_exposure_boundary_values(self, camera_controller, mock_picamera2):
        """Test manual exposure with boundary values."""
        # Minimum values
        camera_controller.set_manual_exposure(exposure_us=MIN_EXPOSURE_US, gain=MIN_GAIN)
        mock_picamera2.set_controls.assert_called()

        # Maximum values
        camera_controller.set_manual_exposure(exposure_us=MAX_EXPOSURE_US, gain=MAX_GAIN)
        mock_picamera2.set_controls.assert_called()


class TestCameraControllerAWB:
    """Test auto white balance control."""

    def test_set_awb_enable(self, camera_controller, mock_picamera2):
        """Test enabling auto white balance."""
        camera_controller.set_awb(True)

        mock_picamera2.set_controls.assert_called_with({
            "AwbEnable": True,
        })

    def test_set_awb_disable(self, camera_controller, mock_picamera2):
        """Test disabling auto white balance."""
        camera_controller.set_awb(False)

        mock_picamera2.set_controls.assert_called_with({
            "AwbEnable": False,
        })


class TestCameraControllerStatus:
    """Test status retrieval."""

    def test_get_status(self, camera_controller, mock_picamera2):
        """Test getting camera status."""
        status = camera_controller.get_status()

        assert status["lux"] == 100.0
        assert status["exposure_us"] == 10000
        assert status["analogue_gain"] == 1.5
        assert status["colour_temperature"] == 4500.0
        assert "auto_exposure" in status

        mock_picamera2.capture_metadata.assert_called_once()

    def test_get_status_missing_metadata(self, camera_controller, mock_picamera2):
        """Test status when some metadata is missing."""
        mock_picamera2.capture_metadata.return_value = {
            "Lux": 50.0,
            # Missing other fields
        }

        status = camera_controller.get_status()

        assert status["lux"] == 50.0
        assert status["exposure_us"] is None
        assert status["analogue_gain"] is None
        assert status["colour_temperature"] is None


class TestCameraControllerCleanup:
    """Test resource cleanup."""

    def test_cleanup(self, camera_controller, mock_picamera2):
        """Test that cleanup properly releases resources."""
        camera_controller.cleanup()

        mock_picamera2.close.assert_called_once()
        assert camera_controller._picam2 is None
        assert camera_controller._configured is False

    def test_cleanup_error_handling(self, camera_controller, mock_picamera2):
        """Test that cleanup handles errors gracefully."""
        mock_picamera2.close.side_effect = Exception("Close failed")

        # Should not raise exception
        camera_controller.cleanup()

        assert camera_controller._picam2 is None
        assert camera_controller._configured is False

    def test_cleanup_when_not_initialized(self, mock_picamera2_class):
        """Test cleanup when camera was never initialized."""
        controller = CameraController()

        # Should not raise exception
        controller.cleanup()


class TestCameraControllerProperty:
    """Test picam2 property."""

    def test_picam2_property_configures_if_needed(self, mock_picamera2_class, mock_picamera2):
        """Test that accessing picam2 property triggers configuration."""
        controller = CameraController()

        assert controller._configured is False

        # Access property
        picam2 = controller.picam2

        assert controller._configured is True
        assert picam2 is mock_picamera2

    def test_picam2_property_returns_instance(self, camera_controller, mock_picamera2):
        """Test that picam2 property returns the Picamera2 instance."""
        picam2 = camera_controller.picam2

        assert picam2 is mock_picamera2
