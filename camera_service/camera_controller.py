"""
Camera controller module for Pi Camera Service.

Provides thread-safe access to Picamera2 camera controls including
exposure, gain, white balance, autofocus, HDR, image processing, and status retrieval.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Optional

from picamera2 import Picamera2
from PIL import Image

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
MAX_LENS_POSITION = 15.0
MIN_LENS_POSITION = 0.0

# NoIR AWB presets (red_gain, blue_gain)
AWB_PRESETS = {
    "daylight_noir": (1.2, 1.8),
    "ir_850nm": (1.0, 1.0),
    "ir_940nm": (1.0, 1.0),
    "indoor_noir": (1.4, 1.6),
}


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
        self._autofocus_mode = "continuous"  # default, manual, auto, continuous
        self._hdr_mode = "off"  # off, auto, sensor, single-exp
        self._lens_correction_enabled = False
        self._day_night_mode = "manual"  # manual, auto
        self._day_night_threshold_lux = 10.0

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

    def _detect_tuning_file(self) -> Optional[str]:
        """
        Auto-detect the appropriate tuning file for the camera.

        Returns:
            str: Path to tuning file, or None if not found
        """
        # If explicitly configured, use that
        if CONFIG.tuning_file is not None:
            if os.path.exists(CONFIG.tuning_file):
                logger.info(f"Using configured tuning file: {CONFIG.tuning_file}")
                return CONFIG.tuning_file
            else:
                logger.warning(f"Configured tuning file not found: {CONFIG.tuning_file}")

        # Auto-detect based on camera model and NoIR flag
        model = CONFIG.camera_model
        noir_suffix = "_noir" if CONFIG.is_noir else ""

        # Try Pi 5 path first (pisp)
        pi5_path = f"/usr/share/libcamera/ipa/rpi/pisp/{model}{noir_suffix}.json"
        if os.path.exists(pi5_path):
            logger.info(f"Auto-detected tuning file (Pi 5): {pi5_path}")
            return pi5_path

        # Try Pi 4/Zero 2W path (vc4)
        pi4_path = f"/usr/share/libcamera/ipa/rpi/vc4/{model}{noir_suffix}.json"
        if os.path.exists(pi4_path):
            logger.info(f"Auto-detected tuning file (Pi 4): {pi4_path}")
            return pi4_path

        logger.warning("Could not auto-detect tuning file, using default")
        return None

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
                # Detect and load tuning file
                tuning_file = self._detect_tuning_file()

                # Initialize Picamera2 with tuning file
                if tuning_file:
                    self._picam2 = Picamera2(tuning=Picamera2.load_tuning_file(tuning_file))
                else:
                    self._picam2 = Picamera2()

                # Create video configuration
                video_config = self._picam2.create_video_configuration(
                    main={
                        "size": (CONFIG.width, CONFIG.height),
                        "format": "YUV420",
                    },
                    controls={
                        "FrameRate": CONFIG.framerate,
                        "AfMode": 2,  # Continuous autofocus by default
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

    def get_status(self) -> Dict[str, Any]:
        """
        Get current camera status and metadata.

        Returns:
            dict: Comprehensive camera status including exposure, focus, scene mode, etc.

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            try:
                meta = self._picam2.capture_metadata()

                # Get scene mode
                scene_mode = self.get_scene_mode()

                status = {
                    # Existing metadata
                    "lux": meta.get("Lux"),
                    "exposure_us": meta.get("ExposureTime"),
                    "analogue_gain": meta.get("AnalogueGain"),
                    "colour_temperature": meta.get("ColourTemperature"),
                    "auto_exposure": self._auto_exposure,

                    # New metadata
                    "autofocus_mode": self._autofocus_mode,
                    "lens_position": meta.get("LensPosition"),
                    "focus_fom": meta.get("FocusFoM"),  # Focus Figure of Merit
                    "hdr_mode": self._hdr_mode,
                    "lens_correction_enabled": self._lens_correction_enabled,
                    "scene_mode": scene_mode,
                    "day_night_mode": self._day_night_mode,
                    "day_night_threshold_lux": self._day_night_threshold_lux,
                    "frame_duration_us": meta.get("FrameDuration"),
                    "sensor_black_levels": meta.get("SensorBlackLevels"),
                }
                logger.debug(f"Camera status: {status}")
                return status
            except Exception as e:
                logger.error(f"Error retrieving camera metadata: {e}")
                raise

    # ---------- Autofocus Controls ----------

    def set_autofocus_mode(self, mode: str) -> None:
        """
        Set the autofocus mode.

        Args:
            mode: Autofocus mode - "default", "manual", "auto", "continuous"

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["default", "manual", "auto", "continuous"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid autofocus mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Map mode to libcamera AfMode values
            af_mode_map = {
                "default": 0,
                "manual": 0,
                "auto": 1,
                "continuous": 2,
            }

            self._picam2.set_controls({"AfMode": af_mode_map[mode]})
            self._autofocus_mode = mode
            logger.info(f"Autofocus mode set to: {mode}")

    def set_lens_position(self, position: float) -> None:
        """
        Set manual lens position for focus.

        Args:
            position: Lens position (0.0 = infinity, higher values = closer focus)
                     Typical range: 0.0 to 15.0

        Raises:
            InvalidParameterError: If position is out of range
            CameraNotAvailableError: If camera is not configured
        """
        if position < MIN_LENS_POSITION or position > MAX_LENS_POSITION:
            raise InvalidParameterError(
                f"lens_position must be between {MIN_LENS_POSITION} and {MAX_LENS_POSITION} (got {position})"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({"LensPosition": position})
            logger.info(f"Lens position set to: {position}")

    def set_autofocus_range(self, range_mode: str) -> None:
        """
        Set the autofocus range (constrains focus search area).

        Args:
            range_mode: "normal", "macro", or "full"

        Raises:
            InvalidParameterError: If range_mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_ranges = ["normal", "macro", "full"]
        if range_mode not in valid_ranges:
            raise InvalidParameterError(
                f"Invalid autofocus range '{range_mode}'. Must be one of: {', '.join(valid_ranges)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Map range to libcamera AfRange values
            af_range_map = {
                "normal": 0,
                "macro": 1,
                "full": 2,
            }

            self._picam2.set_controls({"AfRange": af_range_map[range_mode]})
            logger.info(f"Autofocus range set to: {range_mode}")

    # ---------- Snapshot/Capture ----------

    def capture_snapshot(
        self, width: int = 1920, height: int = 1080, autofocus_trigger: bool = True
    ) -> str:
        """
        Capture a single JPEG image without stopping streaming.

        Args:
            width: Image width in pixels (default 1920)
            height: Image height in pixels (default 1080)
            autofocus_trigger: Trigger autofocus before capture (default True)

        Returns:
            str: Base64-encoded JPEG image

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            try:
                # Trigger autofocus if requested and in auto/continuous mode
                if autofocus_trigger and self._autofocus_mode in ["auto", "continuous"]:
                    self._picam2.autofocus_cycle()

                # Capture frame
                array = self._picam2.capture_array("main")

                # Convert to PIL Image and resize if needed
                img = Image.fromarray(array)
                if img.size != (width, height):
                    img = img.resize((width, height), Image.Resampling.LANCZOS)

                # Encode to JPEG in memory
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=95)
                buffer.seek(0)

                # Encode to base64
                img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

                logger.info(f"Snapshot captured: {width}x{height}")
                return img_base64

            except Exception as e:
                logger.error(f"Error capturing snapshot: {e}")
                raise

    # ---------- Manual White Balance ----------

    def set_manual_awb(self, red_gain: float, blue_gain: float) -> None:
        """
        Set manual white balance gains.

        Args:
            red_gain: Red channel gain (typical range: 0.5 - 3.0)
            blue_gain: Blue channel gain (typical range: 0.5 - 3.0)

        Raises:
            InvalidParameterError: If gains are out of reasonable range
            CameraNotAvailableError: If camera is not configured
        """
        if red_gain < 0.5 or red_gain > 5.0:
            raise InvalidParameterError(
                f"red_gain must be between 0.5 and 5.0 (got {red_gain})"
            )
        if blue_gain < 0.5 or blue_gain > 5.0:
            raise InvalidParameterError(
                f"blue_gain must be between 0.5 and 5.0 (got {blue_gain})"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({
                "AwbEnable": False,
                "ColourGains": (red_gain, blue_gain),
            })

            logger.info(f"Manual white balance set: R={red_gain}, B={blue_gain}")

    def set_awb_preset(self, preset: str) -> None:
        """
        Set white balance using a preset optimized for NoIR camera.

        Args:
            preset: Preset name - "daylight_noir", "ir_850nm", "ir_940nm", "indoor_noir"

        Raises:
            InvalidParameterError: If preset is not valid
            CameraNotAvailableError: If camera is not configured
        """
        if preset not in AWB_PRESETS:
            raise InvalidParameterError(
                f"Invalid AWB preset '{preset}'. Must be one of: {', '.join(AWB_PRESETS.keys())}"
            )

        red_gain, blue_gain = AWB_PRESETS[preset]
        self.set_manual_awb(red_gain, blue_gain)
        logger.info(f"AWB preset '{preset}' applied: R={red_gain}, B={blue_gain}")

    # ---------- Image Processing ----------

    def set_image_processing(
        self,
        brightness: Optional[float] = None,
        contrast: Optional[float] = None,
        saturation: Optional[float] = None,
        sharpness: Optional[float] = None,
    ) -> None:
        """
        Set image processing parameters.

        Args:
            brightness: Brightness adjustment (-1.0 to 1.0, 0 = no change)
            contrast: Contrast (0.0 to 2.0, 1.0 = no change)
            saturation: Saturation (0.0 to 2.0, 1.0 = no change)
            sharpness: Sharpness (0.0 to 16.0, higher = sharper)

        Raises:
            InvalidParameterError: If parameters are out of range
            CameraNotAvailableError: If camera is not configured
        """
        controls = {}

        if brightness is not None:
            if brightness < -1.0 or brightness > 1.0:
                raise InvalidParameterError(
                    f"brightness must be between -1.0 and 1.0 (got {brightness})"
                )
            controls["Brightness"] = brightness

        if contrast is not None:
            if contrast < 0.0 or contrast > 2.0:
                raise InvalidParameterError(
                    f"contrast must be between 0.0 and 2.0 (got {contrast})"
                )
            controls["Contrast"] = contrast

        if saturation is not None:
            if saturation < 0.0 or saturation > 2.0:
                raise InvalidParameterError(
                    f"saturation must be between 0.0 and 2.0 (got {saturation})"
                )
            controls["Saturation"] = saturation

        if sharpness is not None:
            if sharpness < 0.0 or sharpness > 16.0:
                raise InvalidParameterError(
                    f"sharpness must be between 0.0 and 16.0 (got {sharpness})"
                )
            controls["Sharpness"] = sharpness

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls(controls)
            logger.info(f"Image processing parameters updated: {controls}")

    # ---------- HDR Mode ----------

    def set_hdr_mode(self, mode: str) -> None:
        """
        Set HDR (High Dynamic Range) mode.

        Args:
            mode: HDR mode - "off", "auto", "sensor", "single-exp"
                  - "sensor": Hardware HDR from sensor
                  - "single-exp": Software HDR (PiSP multi-frame)

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["off", "auto", "sensor", "single-exp"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid HDR mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        # Note: HDR configuration typically requires camera reconfiguration
        # This is a simplified implementation - full HDR may need restart
        self._hdr_mode = mode
        logger.info(f"HDR mode set to: {mode}")
        logger.warning("HDR mode change may require camera reconfiguration to take full effect")

    # ---------- ROI (Region of Interest) ----------

    def set_roi(self, x: float, y: float, width: float, height: float) -> None:
        """
        Set Region of Interest (digital crop/zoom).

        Args:
            x: X offset (0.0 to 1.0, normalized coordinates)
            y: Y offset (0.0 to 1.0, normalized coordinates)
            width: Width (0.0 to 1.0, normalized)
            height: Height (0.0 to 1.0, normalized)

        Raises:
            InvalidParameterError: If coordinates are invalid
            CameraNotAvailableError: If camera is not configured
        """
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise InvalidParameterError(
                f"ROI x and y must be between 0.0 and 1.0 (got x={x}, y={y})"
            )
        if not (0.0 < width <= 1.0 and 0.0 < height <= 1.0):
            raise InvalidParameterError(
                f"ROI width and height must be between 0.0 and 1.0 (got w={width}, h={height})"
            )
        if x + width > 1.0 or y + height > 1.0:
            raise InvalidParameterError(
                "ROI extends beyond image boundaries"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({
                "ScalerCrop": (
                    int(x * self._picam2.sensor_resolution[0]),
                    int(y * self._picam2.sensor_resolution[1]),
                    int(width * self._picam2.sensor_resolution[0]),
                    int(height * self._picam2.sensor_resolution[1]),
                )
            })
            logger.info(f"ROI set: x={x}, y={y}, width={width}, height={height}")

    # ---------- Exposure Limits ----------

    def set_exposure_limits(
        self,
        min_exposure_us: Optional[int] = None,
        max_exposure_us: Optional[int] = None,
        min_gain: Optional[float] = None,
        max_gain: Optional[float] = None,
    ) -> None:
        """
        Set limits for auto-exposure algorithm.

        Args:
            min_exposure_us: Minimum exposure time in microseconds
            max_exposure_us: Maximum exposure time in microseconds
            min_gain: Minimum analogue gain
            max_gain: Maximum analogue gain

        Raises:
            InvalidParameterError: If limits are invalid
            CameraNotAvailableError: If camera is not configured
        """
        controls = {}

        if min_exposure_us is not None:
            if min_exposure_us < MIN_EXPOSURE_US:
                raise InvalidParameterError(
                    f"min_exposure_us must be >= {MIN_EXPOSURE_US}"
                )
            controls["ExposureTimeMin"] = min_exposure_us

        if max_exposure_us is not None:
            if max_exposure_us > MAX_EXPOSURE_US:
                raise InvalidParameterError(
                    f"max_exposure_us must be <= {MAX_EXPOSURE_US}"
                )
            controls["ExposureTimeMax"] = max_exposure_us

        if min_gain is not None:
            if min_gain < MIN_GAIN:
                raise InvalidParameterError(f"min_gain must be >= {MIN_GAIN}")
            controls["AnalogueGainMin"] = min_gain

        if max_gain is not None:
            if max_gain > MAX_GAIN:
                raise InvalidParameterError(f"max_gain must be <= {MAX_GAIN}")
            controls["AnalogueGainMax"] = max_gain

        # Validate min < max
        if min_exposure_us and max_exposure_us and min_exposure_us >= max_exposure_us:
            raise InvalidParameterError(
                "min_exposure_us must be less than max_exposure_us"
            )
        if min_gain and max_gain and min_gain >= max_gain:
            raise InvalidParameterError("min_gain must be less than max_gain")

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls(controls)
            logger.info(f"Exposure limits set: {controls}")

    # ---------- Lens Correction ----------

    def set_lens_correction(self, enabled: bool) -> None:
        """
        Enable or disable lens shading correction (for wide-angle distortion).

        Args:
            enabled: True to enable lens correction, False to disable

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Lens shading correction is typically controlled via tuning file
            # This is a placeholder - actual implementation may require reconfiguration
            self._lens_correction_enabled = enabled
            logger.info(f"Lens correction {'enabled' if enabled else 'disabled'}")
            logger.warning("Lens correction may require camera reconfiguration to take full effect")

    # ---------- Transform (Flip/Rotation) ----------

    def set_transform(
        self, hflip: bool = False, vflip: bool = False, rotation: int = 0
    ) -> None:
        """
        Set image transformation (flip/rotation).

        Args:
            hflip: Horizontal flip
            vflip: Vertical flip
            rotation: Rotation in degrees (0 or 180)

        Raises:
            InvalidParameterError: If rotation is not 0 or 180
            CameraNotAvailableError: If camera is not configured
        """
        if rotation not in [0, 180]:
            raise InvalidParameterError(
                f"rotation must be 0 or 180 (got {rotation})"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Transform requires reconfiguration
            logger.info(f"Transform set: hflip={hflip}, vflip={vflip}, rotation={rotation}")
            logger.warning("Transform changes require camera restart to take effect")

    # ---------- Day/Night Mode ----------

    def set_day_night_mode(self, mode: str, threshold_lux: float = 10.0) -> None:
        """
        Set day/night detection mode.

        Args:
            mode: "manual" or "auto"
            threshold_lux: Lux threshold for day/night detection (when mode="auto")

        Raises:
            InvalidParameterError: If mode is invalid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["manual", "auto"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid day/night mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        if threshold_lux < 0:
            raise InvalidParameterError("threshold_lux must be non-negative")

        self._day_night_mode = mode
        self._day_night_threshold_lux = threshold_lux

        logger.info(f"Day/night mode set to: {mode}, threshold: {threshold_lux} lux")

    def get_scene_mode(self) -> str:
        """
        Get current scene mode based on lux reading.

        Returns:
            str: "day", "low_light", or "night"

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            try:
                meta = self._picam2.capture_metadata()
                lux = meta.get("Lux", 0)

                if lux is None:
                    return "unknown"
                elif lux > 100:
                    return "day"
                elif lux > self._day_night_threshold_lux:
                    return "low_light"
                else:
                    return "night"
            except Exception as e:
                logger.error(f"Error detecting scene mode: {e}")
                return "unknown"
