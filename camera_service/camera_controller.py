"""
Camera controller module for Pi Camera Service.

Provides thread-safe access to Picamera2 camera controls including
exposure, gain, white balance, and status retrieval.
"""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Dict, Optional

from picamera2 import Picamera2

from camera_service.config import CONFIG
from camera_service.exceptions import (
    CameraNotAvailableError,
    ConfigurationError,
    InvalidParameterError,
)

logger = logging.getLogger(__name__)

# Hardware limits for Pi Camera Module v3
# These can be adjusted based on your specific camera model
MAX_EXPOSURE_US = 1_000_000  # 1 second
MIN_EXPOSURE_US = 100  # 100 microseconds
MAX_GAIN = 16.0
MIN_GAIN = 1.0


class CameraController:
    """
    Thread-safe controller for Raspberry Pi camera operations.

    Manages camera configuration, exposure control, white balance,
    and metadata retrieval. Uses RLock for reentrant thread safety.
    """

    def __init__(self) -> None:
        """
        Initialize the camera controller.

        Raises:
            CameraNotAvailableError: If camera hardware is not available
        """
        self._picam2: Optional[Picamera2] = None
        self._lock = RLock()  # Reentrant lock for nested lock acquisition
        self._configured = False
        self._auto_exposure = CONFIG.default_auto_exposure

        logger.debug("CameraController initialized")

    def _check_camera_available(self) -> bool:
        """
        Check if a camera is available.

        Returns:
            bool: True if at least one camera is detected
        """
        try:
            cameras = Picamera2.global_camera_info()
            return len(cameras) > 0
        except Exception as e:
            logger.error(f"Error checking camera availability: {e}")
            return False

    def configure(self) -> None:
        """
        Configure the camera with settings from CONFIG.

        Raises:
            CameraNotAvailableError: If no camera is detected
            ConfigurationError: If configuration fails
        """
        with self._lock:
            if self._configured:
                logger.debug("Camera already configured, skipping")
                return

            logger.info("Configuring camera...")

            # Check camera availability
            if not self._check_camera_available():
                raise CameraNotAvailableError(
                    "No camera detected. Check hardware connection."
                )

            try:
                # Initialize Picamera2
                self._picam2 = Picamera2()

                # Create video configuration
                video_config = self._picam2.create_video_configuration(
                    main={
                        "size": (CONFIG.width, CONFIG.height),
                        "format": "YUV420",
                    },
                    controls={
                        "FrameRate": CONFIG.framerate,
                    },
                )
                self._picam2.configure(video_config)

                logger.info(
                    f"Camera configured: {CONFIG.width}x{CONFIG.height} "
                    f"@ {CONFIG.framerate}fps, bitrate={CONFIG.bitrate}bps"
                )

                # Apply initial settings
                self.set_auto_exposure(CONFIG.default_auto_exposure)
                if CONFIG.enable_awb:
                    self._picam2.set_controls({"AwbEnable": True})
                    logger.debug("Auto white balance enabled")

                self._configured = True

            except Exception as e:
                logger.error(f"Failed to configure camera: {e}")
                raise ConfigurationError(f"Camera configuration failed: {e}") from e

    @property
    def picam2(self) -> Picamera2:
        """
        Get the Picamera2 instance, configuring it if necessary.

        Returns:
            Picamera2: The configured camera instance

        Raises:
            CameraNotAvailableError: If camera is not available
            ConfigurationError: If configuration fails
        """
        with self._lock:
            if not self._configured:
                self.configure()
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")
            return self._picam2

    def cleanup(self) -> None:
        """
        Release camera resources and cleanup.

        Should be called during application shutdown.
        """
        with self._lock:
            if self._picam2 is not None:
                try:
                    logger.info("Cleaning up camera resources...")
                    self._picam2.close()
                    logger.info("Camera closed successfully")
                except Exception as e:
                    logger.error(f"Error closing camera: {e}")
                finally:
                    self._picam2 = None
                    self._configured = False

    # ---------- Exposure & Gain Controls ----------

    def set_auto_exposure(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic exposure control.

        Args:
            enabled: True to enable auto exposure, False to disable

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            controls: Dict[str, Any] = {
                "AeEnable": enabled,
            }
            if enabled:
                controls["ExposureTime"] = 0  # Let auto-exposure decide

            self._picam2.set_controls(controls)
            self._auto_exposure = enabled

            logger.info(f"Auto exposure {'enabled' if enabled else 'disabled'}")

    def set_manual_exposure(self, exposure_us: int, gain: float = 1.0) -> None:
        """
        Set manual exposure parameters.

        Args:
            exposure_us: Exposure time in microseconds (100 - 1,000,000)
            gain: Analogue gain (1.0 - 16.0)

        Raises:
            InvalidParameterError: If parameters are out of valid range
            CameraNotAvailableError: If camera is not configured
        """
        # Validate parameters
        if exposure_us < MIN_EXPOSURE_US:
            raise InvalidParameterError(
                f"exposure_us must be >= {MIN_EXPOSURE_US} (got {exposure_us})"
            )
        if exposure_us > MAX_EXPOSURE_US:
            raise InvalidParameterError(
                f"exposure_us must be <= {MAX_EXPOSURE_US} (got {exposure_us})"
            )
        if gain < MIN_GAIN:
            raise InvalidParameterError(
                f"gain must be >= {MIN_GAIN} (got {gain})"
            )
        if gain > MAX_GAIN:
            raise InvalidParameterError(
                f"gain must be <= {MAX_GAIN} (got {gain})"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({
                "AeEnable": False,
                "ExposureTime": exposure_us,
                "AnalogueGain": gain,
            })
            self._auto_exposure = False

            logger.info(f"Manual exposure set: {exposure_us}µs, gain={gain}")

    def set_awb(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic white balance.

        Args:
            enabled: True to enable AWB, False to disable

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({
                "AwbEnable": enabled,
            })

            logger.info(f"Auto white balance {'enabled' if enabled else 'disabled'}")

    # ---------- Status & Metadata ----------

    def get_status(self) -> Dict[str, Optional[float] | bool]:
        """
        Get current camera status and metadata.

        Returns:
            dict: Camera status including lux, exposure, gain, color temperature

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            try:
                meta = self._picam2.capture_metadata()
                status = {
                    "lux": meta.get("Lux"),
                    "exposure_us": meta.get("ExposureTime"),
                    "analogue_gain": meta.get("AnalogueGain"),
                    "colour_temperature": meta.get("ColourTemperature"),
                    "auto_exposure": self._auto_exposure,
                }
                logger.debug(f"Camera status: {status}")
                return status
            except Exception as e:
                logger.error(f"Error retrieving camera metadata: {e}")
                raise
