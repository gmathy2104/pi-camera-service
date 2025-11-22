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

# Framerate limits based on resolution (approximate for IMX708)
# These are based on pixel count and sensor readout limitations
def calculate_max_framerate(width: int, height: int) -> float:
    """
    Calculate maximum framerate based on resolution.

    Based on IMX708 sensor capabilities:
    - Higher resolutions require more readout time
    - Framerate is inversely proportional to pixel count

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        float: Maximum framerate for this resolution
    """
    total_pixels = width * height

    # Reference points based on IMX708 specs
    # 4K (3840x2160 = 8.3M pixels): 30fps
    # 1440p (2560x1440 = 3.7M pixels): 40fps
    # 1080p (1920x1080 = 2.1M pixels): 50fps
    # 720p (1280x720 = 0.9M pixels): 120fps

    if total_pixels >= 8_000_000:  # 4K and above
        return 30.0
    elif total_pixels >= 3_500_000:  # 1440p range
        return 40.0
    elif total_pixels >= 2_000_000:  # 1080p range
        return 50.0
    elif total_pixels >= 1_500_000:  # Between 1080p and 720p
        return 60.0
    elif total_pixels >= 900_000:  # 720p range
        return 120.0
    else:  # Very low resolutions
        return 120.0  # Cap at 120fps even for tiny resolutions

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

        # Track current resolution and framerate
        self._current_width = CONFIG.width
        self._current_height = CONFIG.height
        self._current_framerate = CONFIG.framerate

        logger.info("=== CameraController v2.0 initialized with autofocus support ===" )
        logger.debug(f"Initialized with: autofocus_mode={self._autofocus_mode}, hdr_mode={self._hdr_mode}")

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
                logger.debug(f"get_status: _autofocus_mode={self._autofocus_mode}, _hdr_mode={self._hdr_mode}")

                # Get scene mode
                try:
                    scene_mode = self.get_scene_mode()
                except Exception as scene_ex:
                    logger.warning(f"Failed to get scene mode: {scene_ex}")
                    scene_mode = "unknown"

                # Get frame duration limits if set
                frame_duration = meta.get("FrameDuration")
                frame_duration_limits = meta.get("FrameDurationLimits")

                # Extract current limits
                current_limits = {
                    "frame_duration_us": frame_duration,
                    "frame_duration_limits_us": None,
                    "effective_exposure_limit_us": None,
                }

                if frame_duration_limits:
                    min_dur, max_dur = frame_duration_limits
                    current_limits["frame_duration_limits_us"] = {
                        "min": min_dur,
                        "max": max_dur,
                    }
                    # Effective exposure limit is constrained by max frame duration
                    current_limits["effective_exposure_limit_us"] = {
                        "min": MIN_EXPOSURE_US,
                        "max": min(max_dur, MAX_EXPOSURE_US),
                    }
                else:
                    # No limits set, use hardware max
                    current_limits["effective_exposure_limit_us"] = {
                        "min": MIN_EXPOSURE_US,
                        "max": MAX_EXPOSURE_US,
                    }

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
                    "frame_duration_us": frame_duration,
                    "sensor_black_levels": meta.get("SensorBlackLevels"),

                    # Current limits (v2.2)
                    "current_limits": current_limits,
                }
                logger.debug(f"Camera status built: autofocus_mode={status['autofocus_mode']}, hdr_mode={status['hdr_mode']}")
                return status
            except Exception as e:
                logger.error(f"Error retrieving camera metadata: {e}", exc_info=True)
                raise

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get camera hardware capabilities and supported features.

        Returns comprehensive information about what the camera hardware supports,
        including resolution limits, exposure limits, gain limits, and available features.

        Returns:
            dict: Camera capabilities including:
                - sensor_model: Camera sensor model name
                - supported_resolutions: List of common supported resolutions
                - exposure_limits: Min/max exposure time in microseconds
                - gain_limits: Min/max analogue gain
                - lens_position_limits: Min/max lens position (for autofocus cameras)
                - features: List of supported features
                - sensor_resolution: Native sensor resolution

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            # Get sensor resolution - use safe access
            try:
                sensor_resolution = self._picam2.sensor_resolution
            except Exception:
                # If we can't get sensor resolution (e.g., camera is running),
                # use a reasonable default for IMX708 (Camera Module 3)
                sensor_resolution = (4608, 2592)  # IMX708 max resolution

            # Common supported resolutions (subset of what the sensor can do)
            supported_resolutions = [
                {"width": 640, "height": 480, "label": "VGA"},
                {"width": 1280, "height": 720, "label": "720p"},
                {"width": 1920, "height": 1080, "label": "1080p"},
                {"width": 2560, "height": 1440, "label": "1440p"},
                {"width": 3840, "height": 2160, "label": "4K"},
            ]

            # Filter resolutions to those supported by sensor
            if sensor_resolution:
                max_width, max_height = sensor_resolution
                supported_resolutions = [
                    res for res in supported_resolutions
                    if res["width"] <= max_width and res["height"] <= max_height
                ]

            # Determine supported features based on camera model
            features = [
                "auto_exposure",
                "manual_exposure",
                "auto_white_balance",
                "manual_white_balance",
                "exposure_value_compensation",
                "noise_reduction",
                "ae_constraint_modes",
                "ae_exposure_modes",
                "awb_modes",
                "image_processing",
                "roi_digital_zoom",
                "exposure_limits",
            ]

            # Check for autofocus support (Camera Module 3)
            try:
                if CONFIG.camera_model in ["imx708", "imx296"]:
                    features.extend([
                        "autofocus",
                        "lens_position_control",
                        "autofocus_trigger",
                    ])
            except Exception:
                pass

            capabilities = {
                "sensor_model": CONFIG.camera_model,
                "sensor_resolution": {
                    "width": sensor_resolution[0] if sensor_resolution else None,
                    "height": sensor_resolution[1] if sensor_resolution else None,
                },
                "supported_resolutions": supported_resolutions,
                "exposure_limits_us": {
                    "min": MIN_EXPOSURE_US,
                    "max": MAX_EXPOSURE_US,
                },
                "gain_limits": {
                    "min": MIN_GAIN,
                    "max": MAX_GAIN,
                },
                "lens_position_limits": {
                    "min": MIN_LENS_POSITION,
                    "max": MAX_LENS_POSITION,
                },
                "exposure_value_range": {
                    "min": -8.0,
                    "max": 8.0,
                },
                "supported_noise_reduction_modes": [
                    "off", "fast", "high_quality", "minimal", "zsl"
                ],
                "supported_ae_constraint_modes": [
                    "normal", "highlight", "shadows", "custom"
                ],
                "supported_ae_exposure_modes": [
                    "normal", "short", "long", "custom"
                ],
                "supported_awb_modes": [
                    "auto", "tungsten", "fluorescent", "indoor", "daylight", "cloudy", "custom"
                ],
                "features": features,
                "current_framerate": self._current_framerate,
                "framerate_limits_by_resolution": [
                    {"width": 3840, "height": 2160, "label": "4K", "max_fps": 30.0},
                    {"width": 2560, "height": 1440, "label": "1440p", "max_fps": 40.0},
                    {"width": 1920, "height": 1080, "label": "1080p", "max_fps": 50.0},
                    {"width": 1280, "height": 720, "label": "720p", "max_fps": 120.0},
                    {"width": 640, "height": 480, "label": "VGA", "max_fps": 120.0},
                ],
                "max_framerate_for_current_resolution": calculate_max_framerate(
                    self._current_width, self._current_height
                ),
            }

            logger.debug(f"Camera capabilities retrieved: {len(features)} features supported")
            return capabilities

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

        Uses FrameDurationLimits to constrain the frame duration, which indirectly
        limits the maximum exposure time that auto-exposure can use.

        Note: libcamera does not provide direct controls for min/max exposure time
        or gain limits. This method uses FrameDurationLimits as the closest alternative.
        For more precise control, use manual exposure mode.

        Args:
            min_exposure_us: Minimum frame duration in microseconds (default: based on framerate)
            max_exposure_us: Maximum frame duration in microseconds (limits max exposure)
            min_gain: Minimum analogue gain (not directly supported, logged as warning)
            max_gain: Maximum analogue gain (not directly supported, logged as warning)

        Raises:
            InvalidParameterError: If limits are invalid
            CameraNotAvailableError: If camera is not configured
        """
        controls = {}

        # Warn about gain limits not being directly supported
        if min_gain is not None or max_gain is not None:
            logger.warning(
                "Direct gain limits (min_gain/max_gain) are not supported by libcamera. "
                "Use FrameDurationLimits to indirectly constrain exposure, or use manual exposure mode."
            )

        # Use FrameDurationLimits to constrain exposure time
        # Frame duration directly limits how long the camera can expose
        if min_exposure_us is not None or max_exposure_us is not None:
            # Get current metadata to determine sensible defaults
            try:
                meta = self._picam2.capture_metadata()
                current_frame_duration = meta.get("FrameDuration", 33333)  # Default to ~30fps
            except Exception:
                current_frame_duration = 33333  # Default to ~30fps if metadata unavailable

            # Set frame duration limits
            min_duration = min_exposure_us if min_exposure_us is not None else 100
            max_duration = max_exposure_us if max_exposure_us is not None else current_frame_duration

            if min_duration < MIN_EXPOSURE_US:
                raise InvalidParameterError(
                    f"min_exposure_us must be >= {MIN_EXPOSURE_US}"
                )
            if max_duration > MAX_EXPOSURE_US:
                raise InvalidParameterError(
                    f"max_exposure_us must be <= {MAX_EXPOSURE_US}"
                )
            if min_duration >= max_duration:
                raise InvalidParameterError(
                    "min_exposure_us must be less than max_exposure_us"
                )

            controls["FrameDurationLimits"] = (min_duration, max_duration)
            logger.info(
                f"Setting FrameDurationLimits to constrain exposure: "
                f"min={min_duration}µs, max={max_duration}µs"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            if controls:
                self._picam2.set_controls(controls)
                logger.info(f"Exposure limits set via FrameDurationLimits: {controls}")
            else:
                logger.warning("No valid exposure limits provided")

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

    # ---------- New v2.1 Controls ----------

    def set_exposure_value(self, ev: float) -> None:
        """
        Set exposure value (EV) compensation.

        EV compensation adjusts the target brightness of the auto-exposure algorithm.
        Positive values make the image brighter, negative values make it darker.

        Args:
            ev: Exposure value compensation (-8.0 to +8.0, 0.0 = no adjustment)

        Raises:
            InvalidParameterError: If EV is out of range
            CameraNotAvailableError: If camera is not configured
        """
        if ev < -8.0 or ev > 8.0:
            raise InvalidParameterError(
                f"ExposureValue must be between -8.0 and 8.0 (got {ev})"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            self._picam2.set_controls({"ExposureValue": ev})
            logger.info(f"Exposure value compensation set to: {ev}")

    def set_noise_reduction_mode(self, mode: str) -> None:
        """
        Set noise reduction mode.

        Modes:
        - "off": No noise reduction
        - "fast": Fast noise reduction (lower quality, better performance)
        - "high_quality": High quality noise reduction (slower)
        - "minimal": Minimal noise reduction
        - "zsl": Zero shutter lag mode

        Args:
            mode: Noise reduction mode

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["off", "fast", "high_quality", "minimal", "zsl"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid noise reduction mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Map mode names to libcamera NoiseReductionMode enum values
            mode_map = {
                "off": 0,
                "fast": 1,
                "high_quality": 2,
                "minimal": 3,
                "zsl": 4,
            }

            self._picam2.set_controls({"NoiseReductionMode": mode_map[mode]})
            logger.info(f"Noise reduction mode set to: {mode}")

    def set_ae_constraint_mode(self, mode: str) -> None:
        """
        Set auto-exposure constraint mode.

        Constraint modes determine how the AE algorithm adjusts scene brightness
        to reach the target exposure.

        Modes:
        - "normal": Default constraint mode
        - "highlight": Preserve highlights (avoid overexposure)
        - "shadows": Preserve shadows (avoid underexposure)
        - "custom": Platform-specific custom mode

        Args:
            mode: Constraint mode

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["normal", "highlight", "shadows", "custom"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid AE constraint mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            mode_map = {
                "normal": 0,
                "highlight": 1,
                "shadows": 2,
                "custom": 3,
            }

            self._picam2.set_controls({"AeConstraintMode": mode_map[mode]})
            logger.info(f"AE constraint mode set to: {mode}")

    def set_ae_exposure_mode(self, mode: str) -> None:
        """
        Set auto-exposure mode.

        Exposure modes control how the AE algorithm selects exposure time and gain.

        Modes:
        - "normal": Normal exposure mode
        - "short": Prefer shorter exposure times (reduce motion blur)
        - "long": Prefer longer exposure times (reduce noise in low light)
        - "custom": Platform-specific custom mode

        Args:
            mode: Exposure mode

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["normal", "short", "long", "custom"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid AE exposure mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            mode_map = {
                "normal": 0,
                "short": 1,
                "long": 2,
                "custom": 3,
            }

            self._picam2.set_controls({"AeExposureMode": mode_map[mode]})
            logger.info(f"AE exposure mode set to: {mode}")

    def set_awb_mode(self, mode: str) -> None:
        """
        Set auto white balance mode (preset illuminants).

        AWB modes are optimized for different lighting conditions.

        Modes:
        - "auto": Automatic white balance for any scene
        - "tungsten": Incandescent/tungsten lighting (~2700K)
        - "fluorescent": Fluorescent lighting (~4000K)
        - "indoor": Indoor lighting
        - "daylight": Daylight (~5500K)
        - "cloudy": Cloudy daylight (~6500K)
        - "custom": Platform-specific custom mode

        Args:
            mode: AWB mode

        Raises:
            InvalidParameterError: If mode is not valid
            CameraNotAvailableError: If camera is not configured
        """
        valid_modes = ["auto", "tungsten", "fluorescent", "indoor", "daylight", "cloudy", "custom"]
        if mode not in valid_modes:
            raise InvalidParameterError(
                f"Invalid AWB mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            )

        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            mode_map = {
                "auto": 0,
                "tungsten": 1,
                "fluorescent": 2,
                "indoor": 3,
                "daylight": 4,
                "cloudy": 5,
                "custom": 7,
            }

            self._picam2.set_controls({
                "AwbEnable": True,
                "AwbMode": mode_map[mode]
            })
            logger.info(f"AWB mode set to: {mode}")

    def trigger_autofocus(self) -> None:
        """
        Trigger a one-shot autofocus cycle.

        Initiates an autofocus scan. Useful when in manual or auto focus mode.

        Raises:
            CameraNotAvailableError: If camera is not configured
        """
        with self._lock:
            if self._picam2 is None:
                raise CameraNotAvailableError("Camera not initialized")

            # Trigger autofocus cycle
            self._picam2.set_controls({"AfTrigger": 0})  # 0 = Start
            logger.info("Autofocus triggered")

    def set_resolution(self, width: int, height: int) -> None:
        """
        Change camera resolution by stopping and reconfiguring.

        This method stops the camera, reconfigures it with the new resolution,
        and leaves it in a stopped state. The caller (API/streaming_manager) is
        responsible for restarting the camera and streaming.

        Args:
            width: New video width in pixels (64-4096)
            height: New video height in pixels (64-4096)

        Raises:
            InvalidParameterError: If resolution is invalid
            CameraNotAvailableError: If camera is not configured
        """
        if width < 64 or width > 4096:
            raise InvalidParameterError(f"width must be between 64 and 4096 (got {width})")
        if height < 64 or height > 4096:
            raise InvalidParameterError(f"height must be between 64 and 4096 (got {height})")

        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            try:
                logger.info(f"Changing camera resolution to {width}x{height}")

                # Stop camera if running
                was_started = self._picam2.started
                if was_started:
                    logger.debug("Stopping camera for resolution change")
                    self._picam2.stop()

                # Create new video configuration with desired resolution
                new_config = self._picam2.create_video_configuration(
                    main={
                        "size": (width, height),
                        "format": "YUV420",
                    },
                    controls={
                        "FrameRate": self._current_framerate,
                        "AfMode": 2,  # Maintain continuous autofocus
                    },
                )

                # Apply new configuration
                self._picam2.configure(new_config)

                # Update tracked resolution
                self._current_width = width
                self._current_height = height

                # Restart camera if it was running
                if was_started:
                    logger.debug("Restarting camera with new resolution")
                    self._picam2.start()

                logger.info(f"Resolution changed to {width}x{height} successfully")

            except Exception as e:
                logger.error(f"Failed to change resolution: {e}")
                raise InvalidParameterError(f"Resolution change failed: {e}")

    def set_framerate(self, requested_framerate: float) -> Dict[str, Any]:
        """
        Change camera framerate with intelligent limit clamping.

        Automatically clamps the requested framerate to the maximum supported
        by the current resolution. This provides a user-friendly API that never
        rejects valid requests, instead applying the best possible framerate.

        Args:
            requested_framerate: Desired framerate in fps (e.g., 30.0, 60.0, 120.0)

        Returns:
            dict: Information about the applied framerate including:
                - requested_framerate: What the user asked for
                - applied_framerate: What was actually applied
                - max_framerate_for_resolution: Maximum possible for current resolution
                - resolution: Current resolution (width x height)

        Raises:
            InvalidParameterError: If framerate is invalid (≤ 0 or unreasonably high)
            CameraNotAvailableError: If camera is not configured
        """
        # Validate basic sanity
        if requested_framerate <= 0:
            raise InvalidParameterError(
                f"framerate must be > 0 (got {requested_framerate})"
            )
        if requested_framerate > 1000:
            raise InvalidParameterError(
                f"framerate must be <= 1000 (got {requested_framerate})"
            )

        with self._lock:
            if self._picam2 is None or not self._configured:
                raise CameraNotAvailableError("Camera not configured")

            # Calculate max framerate for current resolution
            max_fps = calculate_max_framerate(self._current_width, self._current_height)

            # Clamp to maximum (this is the intelligent part!)
            applied_framerate = min(requested_framerate, max_fps)

            try:
                logger.info(
                    f"Framerate change requested: {requested_framerate}fps "
                    f"(max for {self._current_width}x{self._current_height}: {max_fps}fps)"
                )

                # Stop camera if running
                was_started = self._picam2.started
                if was_started:
                    logger.debug("Stopping camera for framerate change")
                    self._picam2.stop()

                # Create new video configuration with new framerate
                new_config = self._picam2.create_video_configuration(
                    main={
                        "size": (self._current_width, self._current_height),
                        "format": "YUV420",
                    },
                    controls={
                        "FrameRate": applied_framerate,
                        "AfMode": 2,  # Maintain continuous autofocus
                    },
                )

                # Apply new configuration
                self._picam2.configure(new_config)

                # Update tracked framerate
                self._current_framerate = applied_framerate

                # Restart camera if it was running
                if was_started:
                    logger.debug("Restarting camera with new framerate")
                    self._picam2.start()

                logger.info(f"Framerate changed to {applied_framerate}fps successfully")

                return {
                    "requested_framerate": requested_framerate,
                    "applied_framerate": applied_framerate,
                    "max_framerate_for_resolution": max_fps,
                    "resolution": f"{self._current_width}x{self._current_height}",
                    "clamped": requested_framerate > max_fps,
                }

            except Exception as e:
                logger.error(f"Failed to change framerate: {e}")
                raise InvalidParameterError(f"Framerate change failed: {e}")
