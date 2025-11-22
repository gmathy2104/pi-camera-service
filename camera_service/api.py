"""
FastAPI application for Pi Camera Service.

Provides HTTP API for controlling Raspberry Pi camera including exposure,
white balance, and RTSP streaming to MediaMTX.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from threading import RLock
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from camera_service.camera_controller import CameraController, MAX_EXPOSURE_US, MAX_GAIN
from camera_service.config import CONFIG
from camera_service.exceptions import (
    CameraError,
    CameraNotAvailableError,
    ConfigurationError,
    InvalidParameterError,
    StreamingError,
)
from camera_service.streaming_manager import StreamingManager
from camera_service.system_monitor import SystemMonitor

# Configure logging
logging.basicConfig(
    level=CONFIG.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
camera_controller: CameraController | None = None
streaming_manager: StreamingManager | None = None
system_monitor: SystemMonitor | None = None

# Global lock for camera reconfiguration operations
# Protects sequences that require stopping/reconfiguring/restarting streaming
_reconfiguration_lock = RLock()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """
    Verify API key for authentication.

    Args:
        api_key: API key from X-API-Key header

    Raises:
        HTTPException: If authentication is required and key is invalid
    """
    # If no API key is configured, skip authentication
    if CONFIG.api_key is None:
        logger.debug("API authentication disabled (no API key configured)")
        return

    # If API key is configured, require it
    if api_key is None or api_key != CONFIG.api_key:
        logger.warning("Authentication failed: invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


# Dependency injection functions
def get_camera_controller() -> CameraController:
    """
    Dependency injection for camera controller.

    Returns:
        CameraController: The global camera controller instance

    Raises:
        HTTPException: If camera is not initialized
    """
    if camera_controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Camera not initialized",
        )
    return camera_controller


def get_streaming_manager() -> StreamingManager:
    """
    Dependency injection for streaming manager.

    Returns:
        StreamingManager: The global streaming manager instance

    Raises:
        HTTPException: If streaming manager is not initialized
    """
    if streaming_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Streaming manager not initialized",
        )
    return streaming_manager


def get_system_monitor() -> SystemMonitor:
    """
    Dependency injection for system monitor.

    Returns:
        SystemMonitor: The global system monitor instance

    Raises:
        HTTPException: If system monitor is not initialized
    """
    if system_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System monitor not initialized",
        )
    return system_monitor


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle: startup and shutdown events.

    Initializes camera and streaming on startup, cleans up on shutdown.
    """
    global camera_controller, streaming_manager, system_monitor

    logger.info("=== Pi Camera Service Starting ===")
    logger.info(f"Configuration: {CONFIG.width}x{CONFIG.height}@{CONFIG.framerate}fps")
    logger.info(f"RTSP URL: {CONFIG.rtsp_url}")
    logger.info(f"API Key Auth: {'Enabled' if CONFIG.api_key else 'Disabled'}")

    try:
        # Initialize camera controller
        camera_controller = CameraController()
        camera_controller.configure()

        # Initialize streaming manager
        streaming_manager = StreamingManager(camera_controller)

        # Initialize system monitor
        system_monitor = SystemMonitor()
        logger.info("System monitor initialized")
        streaming_manager.start()

        logger.info("=== Pi Camera Service Started Successfully ===")

    except CameraNotAvailableError as e:
        logger.error(f"Camera not available: {e}")
        raise
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to start camera service: {e}")
        raise

    yield

    # Shutdown
    logger.info("=== Pi Camera Service Shutting Down ===")

    if streaming_manager is not None:
        try:
            streaming_manager.stop()
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")

    if camera_controller is not None:
        try:
            camera_controller.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up camera: {e}")

    logger.info("=== Pi Camera Service Shutdown Complete ===")


# Create FastAPI app
app = FastAPI(
    title="Pi Camera Service",
    description="API for controlling Raspberry Pi camera and streaming to MediaMTX via RTSP",
    version="2.5.0",
    lifespan=lifespan,
)


# ========== Pydantic Models ==========

class StatusResponse(BaseModel):
    """Base response model with status."""
    status: str = "ok"


class ManualExposureRequest(BaseModel):
    """Request model for manual exposure settings."""
    exposure_us: int = Field(
        ...,
        gt=0,
        le=MAX_EXPOSURE_US,
        description=f"Exposure time in microseconds (100-{MAX_EXPOSURE_US})",
    )
    gain: float = Field(
        1.0,
        gt=0.0,
        le=MAX_GAIN,
        description=f"Analogue gain (1.0-{MAX_GAIN})",
    )


class AutoExposureRequest(BaseModel):
    """Request model for auto exposure toggle."""
    enabled: bool = Field(..., description="Enable or disable auto exposure")


class AwbRequest(BaseModel):
    """Request model for AWB toggle."""
    enabled: bool = Field(..., description="Enable or disable auto white balance")


class CameraStatusResponse(BaseModel):
    """Camera status response model with comprehensive metadata."""
    # Existing fields
    lux: float | None = Field(None, description="Estimated scene brightness (lux)")
    exposure_us: int | None = Field(None, description="Current exposure time (µs)")
    analogue_gain: float | None = Field(None, description="Current analogue gain")
    colour_temperature: float | None = Field(None, description="Color temperature (K)")
    auto_exposure: bool = Field(..., description="Auto exposure enabled")
    streaming: bool = Field(..., description="Streaming active")

    # New fields
    autofocus_mode: str | None = Field(None, description="Current autofocus mode")
    lens_position: float | None = Field(None, description="Current lens position")
    focus_fom: int | None = Field(None, description="Focus Figure of Merit")
    hdr_mode: str | None = Field(None, description="HDR mode")
    lens_correction_enabled: bool | None = Field(None, description="Lens correction enabled")
    scene_mode: str | None = Field(None, description="Scene mode (day/night/low_light)")
    day_night_mode: str | None = Field(None, description="Day/night detection mode")
    day_night_threshold_lux: float | None = Field(None, description="Lux threshold for day/night")
    frame_duration_us: int | None = Field(None, description="Frame duration in microseconds")
    sensor_black_levels: list[int] | None = Field(None, description="Sensor black levels")
    fov_mode: str | None = Field(None, description="Field of view mode (scale/crop)")

    # Current limits (v2.2)
    current_limits: dict | None = Field(None, description="Currently applied exposure/frame duration limits")


class CameraCapabilitiesResponse(BaseModel):
    """Camera capabilities response model with hardware limits and features."""
    sensor_model: str = Field(..., description="Camera sensor model name")
    sensor_resolution: dict = Field(..., description="Native sensor resolution")
    supported_resolutions: list[dict] = Field(..., description="List of supported resolutions")
    exposure_limits_us: dict = Field(..., description="Hardware exposure time limits (microseconds)")
    gain_limits: dict = Field(..., description="Hardware gain limits")
    lens_position_limits: dict = Field(..., description="Lens position limits (for autofocus)")
    exposure_value_range: dict = Field(..., description="EV compensation range")
    supported_noise_reduction_modes: list[str] = Field(..., description="Supported noise reduction modes")
    supported_ae_constraint_modes: list[str] = Field(..., description="Supported AE constraint modes")
    supported_ae_exposure_modes: list[str] = Field(..., description="Supported AE exposure modes")
    supported_awb_modes: list[str] = Field(..., description="Supported AWB modes")
    features: list[str] = Field(..., description="List of supported features")
    current_framerate: float = Field(..., description="Current configured framerate")
    framerate_limits_by_resolution: list[dict] = Field(..., description="Maximum framerate for each resolution")
    max_framerate_for_current_resolution: float = Field(..., description="Maximum framerate for current resolution")


class AutoExposureResponse(StatusResponse):
    """Response model for auto exposure endpoint."""
    auto_exposure: bool = Field(..., description="Auto exposure state")


class ManualExposureResponse(StatusResponse):
    """Response model for manual exposure endpoint."""
    exposure_us: int = Field(..., description="Applied exposure time (µs)")
    gain: float = Field(..., description="Applied analogue gain")


class AwbResponse(StatusResponse):
    """Response model for AWB endpoint."""
    awb_enabled: bool = Field(..., description="AWB state")


class StreamingResponse(StatusResponse):
    """Response model for streaming endpoints."""
    streaming: bool = Field(..., description="Streaming state")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service health status")
    camera_configured: bool = Field(..., description="Camera is configured")
    streaming_active: bool = Field(..., description="Streaming is active")
    version: str = Field(..., description="API version")


# ========== New v2.0 Models ==========

class AutofocusModeRequest(BaseModel):
    """Request model for autofocus mode."""
    mode: str = Field(..., description="Autofocus mode: default, manual, auto, continuous")


class LensPositionRequest(BaseModel):
    """Request model for manual lens position."""
    position: float = Field(..., ge=0.0, le=15.0, description="Lens position (0.0=infinity, higher=closer)")


class AutofocusRangeRequest(BaseModel):
    """Request model for autofocus range."""
    range_mode: str = Field(..., description="Autofocus range: normal, macro, full")


class SnapshotRequest(BaseModel):
    """Request model for snapshot capture."""
    width: int = Field(1920, ge=320, le=4608, description="Image width in pixels")
    height: int = Field(1080, ge=240, le=2592, description="Image height in pixels")
    autofocus_trigger: bool = Field(True, description="Trigger autofocus before capture")


class SnapshotResponse(StatusResponse):
    """Response model for snapshot endpoint."""
    image_base64: str = Field(..., description="JPEG image encoded in base64")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")


class ManualAwbRequest(BaseModel):
    """Request model for manual white balance."""
    red_gain: float = Field(..., ge=0.5, le=5.0, description="Red channel gain")
    blue_gain: float = Field(..., ge=0.5, le=5.0, description="Blue channel gain")


class AwbPresetRequest(BaseModel):
    """Request model for AWB preset."""
    preset: str = Field(..., description="AWB preset: daylight_noir, ir_850nm, ir_940nm, indoor_noir")


class ImageProcessingRequest(BaseModel):
    """Request model for image processing parameters."""
    brightness: float | None = Field(None, ge=-1.0, le=1.0, description="Brightness (-1.0 to 1.0)")
    contrast: float | None = Field(None, ge=0.0, le=2.0, description="Contrast (0.0 to 2.0)")
    saturation: float | None = Field(None, ge=0.0, le=2.0, description="Saturation (0.0 to 2.0)")
    sharpness: float | None = Field(None, ge=0.0, le=16.0, description="Sharpness (0.0 to 16.0)")


class HdrModeRequest(BaseModel):
    """Request model for HDR mode."""
    mode: str = Field(..., description="HDR mode: off, auto, sensor, single-exp")


class RoiRequest(BaseModel):
    """Request model for Region of Interest."""
    x: float = Field(..., ge=0.0, le=1.0, description="X offset (normalized 0.0-1.0)")
    y: float = Field(..., ge=0.0, le=1.0, description="Y offset (normalized 0.0-1.0)")
    width: float = Field(..., gt=0.0, le=1.0, description="Width (normalized 0.0-1.0)")
    height: float = Field(..., gt=0.0, le=1.0, description="Height (normalized 0.0-1.0)")


class ExposureLimitsRequest(BaseModel):
    """Request model for exposure limits."""
    min_exposure_us: int | None = Field(None, ge=100, le=1_000_000, description="Min exposure (µs)")
    max_exposure_us: int | None = Field(None, ge=100, le=1_000_000, description="Max exposure (µs)")
    min_gain: float | None = Field(None, ge=1.0, le=16.0, description="Min gain")
    max_gain: float | None = Field(None, ge=1.0, le=16.0, description="Max gain")


class LensCorrectionRequest(BaseModel):
    """Request model for lens correction."""
    enabled: bool = Field(..., description="Enable lens shading correction")


class TransformRequest(BaseModel):
    """Request model for image transform."""
    hflip: bool = Field(False, description="Horizontal flip")
    vflip: bool = Field(False, description="Vertical flip")
    rotation: int = Field(0, description="Rotation in degrees (0 or 180)")


class DayNightModeRequest(BaseModel):
    """Request model for day/night mode."""
    mode: str = Field(..., description="Day/night mode: manual, auto")
    threshold_lux: float = Field(10.0, ge=0.0, description="Lux threshold for day/night detection")


# ========== New v2.1 Models ==========

class ExposureValueRequest(BaseModel):
    """Request model for exposure value (EV) compensation."""
    ev: float = Field(..., ge=-8.0, le=8.0, description="EV compensation (-8.0 to +8.0)")


class NoiseReductionRequest(BaseModel):
    """Request model for noise reduction mode."""
    mode: str = Field(..., description="Noise reduction mode: off, fast, high_quality, minimal, zsl")


class AeConstraintModeRequest(BaseModel):
    """Request model for AE constraint mode."""
    mode: str = Field(..., description="AE constraint mode: normal, highlight, shadows, custom")


class AeExposureModeRequest(BaseModel):
    """Request model for AE exposure mode."""
    mode: str = Field(..., description="AE exposure mode: normal, short, long, custom")


class AwbModeRequest(BaseModel):
    """Request model for AWB mode."""
    mode: str = Field(..., description="AWB mode: auto, tungsten, fluorescent, indoor, daylight, cloudy, custom")


class ResolutionRequest(BaseModel):
    """Request model for resolution change."""
    width: int = Field(..., ge=64, le=4096, description="Video width in pixels")
    height: int = Field(..., ge=64, le=4096, description="Video height in pixels")
    restart_streaming: bool = Field(True, description="Restart streaming after resolution change")
    fov_mode: Optional[str] = Field(None, description="FOV mode: 'scale' (constant FOV) or 'crop' (zoom)")


class FramerateRequest(BaseModel):
    """Request model for framerate change."""
    framerate: float = Field(..., gt=0, le=1000, description="Desired framerate in fps")
    restart_streaming: bool = Field(True, description="Restart streaming after framerate change")


class FovModeRequest(BaseModel):
    """Request model for FOV mode change."""
    mode: str = Field(..., description="FOV mode: 'scale' (constant FOV) or 'crop' (zoom)")


class FovModeResponse(BaseModel):
    """Response model for FOV mode."""
    mode: str = Field(..., description="Current FOV mode")
    description: str = Field(..., description="Description of the current mode")


class FramerateResponse(BaseModel):
    """Response model for framerate change."""
    status: str = "ok"
    requested_framerate: float = Field(..., description="Requested framerate")
    applied_framerate: float = Field(..., description="Actually applied framerate")
    max_framerate_for_resolution: float = Field(..., description="Maximum framerate for current resolution")
    resolution: str = Field(..., description="Current resolution (WxH)")
    clamped: bool = Field(..., description="Whether the framerate was clamped to maximum")


# ========== New v2.5 Models ==========

class SystemStatusResponse(BaseModel):
    """System status response model."""
    temperature: Optional[dict] = Field(None, description="CPU temperature info")
    cpu: Optional[dict] = Field(None, description="CPU usage and load average")
    memory: Optional[dict] = Field(None, description="Memory usage statistics")
    network: Optional[dict] = Field(None, description="Network statistics including WiFi")
    disk: Optional[dict] = Field(None, description="Disk usage statistics")
    uptime: dict = Field(..., description="System and service uptime")
    throttled: Optional[dict] = Field(None, description="Throttling status (Pi-specific)")


# ========== Exception Handlers ==========

@app.exception_handler(InvalidParameterError)
async def invalid_parameter_handler(request, exc: InvalidParameterError):
    """Handle invalid parameter errors."""
    logger.warning(f"Invalid parameter: {exc}")
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
    )


@app.exception_handler(CameraNotAvailableError)
async def camera_not_available_handler(request, exc: CameraNotAvailableError):
    """Handle camera not available errors."""
    logger.error(f"Camera not available: {exc}")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Camera is not available",
    )


@app.exception_handler(StreamingError)
async def streaming_error_handler(request, exc: StreamingError):
    """Handle streaming errors."""
    logger.error(f"Streaming error: {exc}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Streaming operation failed",
    )


@app.exception_handler(CameraError)
async def camera_error_handler(request, exc: CameraError):
    """Handle general camera errors."""
    logger.error(f"Camera error: {exc}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Camera operation failed",
    )


# ========== API Endpoints ==========

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """
    Health check endpoint for monitoring.

    Returns service health status, camera configuration state,
    and streaming status. Does not require authentication.

    Returns:
        HealthResponse: Service health information
    """
    return HealthResponse(
        status="healthy" if camera_controller is not None else "initializing",
        camera_configured=camera_controller._configured if camera_controller else False,
        streaming_active=streaming_manager.is_streaming() if streaming_manager else False,
        version="2.5.0",
    )


@app.get(
    "/v1/camera/status",
    response_model=CameraStatusResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def get_camera_status(
    camera: Annotated[CameraController, Depends(get_camera_controller)],
    streaming: Annotated[StreamingManager, Depends(get_streaming_manager)],
) -> CameraStatusResponse:
    """
    Get current camera status and metadata.

    Returns exposure settings, gain, color temperature, brightness (lux),
    auto exposure state, and streaming status.

    Returns:
        CameraStatusResponse: Current camera status

    Raises:
        HTTPException: If camera is not configured or operation fails
    """
    logger.debug("Getting camera status")

    try:
        status_data = camera.get_status()
        return CameraStatusResponse(
            # Existing v1.0 fields
            lux=status_data.get("lux"),
            exposure_us=status_data.get("exposure_us"),
            analogue_gain=status_data.get("analogue_gain"),
            colour_temperature=status_data.get("colour_temperature"),
            auto_exposure=status_data.get("auto_exposure", False),
            streaming=streaming.is_streaming(),

            # New v2.0 fields
            autofocus_mode=status_data.get("autofocus_mode"),
            lens_position=status_data.get("lens_position"),
            focus_fom=status_data.get("focus_fom"),
            hdr_mode=status_data.get("hdr_mode"),
            lens_correction_enabled=status_data.get("lens_correction_enabled"),
            scene_mode=status_data.get("scene_mode"),
            day_night_mode=status_data.get("day_night_mode"),
            day_night_threshold_lux=status_data.get("day_night_threshold_lux"),
            frame_duration_us=status_data.get("frame_duration_us"),
            sensor_black_levels=status_data.get("sensor_black_levels"),
            fov_mode=status_data.get("fov_mode"),

            # Current limits (v2.2)
            current_limits=status_data.get("current_limits"),
        )
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve camera status",
        )


@app.get(
    "/v1/camera/capabilities",
    response_model=CameraCapabilitiesResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def get_camera_capabilities(
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> CameraCapabilitiesResponse:
    """
    Get camera hardware capabilities and supported features.

    Returns comprehensive information about what the camera hardware supports,
    including resolution limits, exposure limits, gain limits, and available features.

    This endpoint provides static capabilities information (what the hardware can do),
    while /v1/camera/status provides dynamic runtime information (current state and limits).

    Returns:
        CameraCapabilitiesResponse: Camera capabilities

    Raises:
        HTTPException: If camera is not configured or operation fails
    """
    logger.debug("Getting camera capabilities")

    try:
        capabilities = camera.get_capabilities()
        return CameraCapabilitiesResponse(**capabilities)
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error getting camera capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve camera capabilities",
        )


@app.post(
    "/v1/camera/auto_exposure",
    response_model=AutoExposureResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def set_auto_exposure(
    req: AutoExposureRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> AutoExposureResponse:
    """
    Enable or disable automatic exposure control.

    When enabled, the camera automatically adjusts exposure time and gain
    based on scene brightness. When disabled, use manual exposure settings.

    Args:
        req: Auto exposure request parameters

    Returns:
        AutoExposureResponse: Confirmation with new state

    Raises:
        HTTPException: If camera is not configured or operation fails
    """
    logger.info(f"Setting auto exposure: {req.enabled}")

    try:
        camera.set_auto_exposure(req.enabled)
        return AutoExposureResponse(auto_exposure=req.enabled)
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error setting auto exposure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set auto exposure",
        )


@app.post(
    "/v1/camera/manual_exposure",
    response_model=ManualExposureResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def set_manual_exposure(
    req: ManualExposureRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> ManualExposureResponse:
    """
    Set manual exposure parameters.

    Disables auto exposure and sets specific exposure time and gain values.
    Use this for consistent lighting or when auto exposure doesn't work well.

    Args:
        req: Manual exposure parameters

    Returns:
        ManualExposureResponse: Confirmation with applied settings

    Raises:
        HTTPException: If parameters are invalid or operation fails
    """
    logger.info(f"Setting manual exposure: {req.exposure_us}µs, gain={req.gain}")

    try:
        camera.set_manual_exposure(
            exposure_us=req.exposure_us,
            gain=req.gain,
        )
        return ManualExposureResponse(
            exposure_us=req.exposure_us,
            gain=req.gain,
        )
    except InvalidParameterError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error setting manual exposure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set manual exposure",
        )


@app.post(
    "/v1/camera/awb",
    response_model=AwbResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def set_awb(
    req: AwbRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> AwbResponse:
    """
    Enable or disable automatic white balance (AWB).

    When enabled, the camera automatically adjusts color balance based on
    the scene. When disabled, white balance is fixed.

    Args:
        req: AWB request parameters

    Returns:
        AwbResponse: Confirmation with new state

    Raises:
        HTTPException: If camera is not configured or operation fails
    """
    logger.info(f"Setting AWB: {req.enabled}")

    try:
        camera.set_awb(req.enabled)
        return AwbResponse(awb_enabled=req.enabled)
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error setting AWB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set AWB",
        )


@app.post(
    "/v1/streaming/start",
    response_model=StreamingResponse,
    tags=["Streaming"],
    dependencies=[Depends(verify_api_key)],
)
def start_streaming(
    streaming: Annotated[StreamingManager, Depends(get_streaming_manager)],
) -> StreamingResponse:
    """
    Start H.264 streaming to MediaMTX.

    Begins encoding and streaming video to the configured RTSP URL.
    If streaming is already active, this is a no-op.

    Returns:
        StreamingResponse: Confirmation with streaming state

    Raises:
        HTTPException: If streaming fails to start
    """
    logger.info("Starting streaming (via API)")

    try:
        streaming.start()
        return StreamingResponse(streaming=streaming.is_streaming())
    except StreamingError:
        raise
    except Exception as e:
        logger.error(f"Error starting streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start streaming",
        )


@app.post(
    "/v1/streaming/stop",
    response_model=StreamingResponse,
    tags=["Streaming"],
    dependencies=[Depends(verify_api_key)],
)
def stop_streaming(
    streaming: Annotated[StreamingManager, Depends(get_streaming_manager)],
) -> StreamingResponse:
    """
    Stop H.264 streaming.

    Stops video encoding and streaming. If streaming is not active,
    this is a no-op.

    Returns:
        StreamingResponse: Confirmation with streaming state

    Raises:
        HTTPException: If stopping fails
    """
    logger.info("Stopping streaming (via API)")

    try:
        streaming.stop()
        return StreamingResponse(streaming=streaming.is_streaming())
    except Exception as e:
        logger.error(f"Error stopping streaming: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop streaming",
        )


# ========== New v2.0 Endpoints ==========


@app.post(
    "/v1/camera/autofocus_mode",
    response_model=StatusResponse,
    tags=["Camera - Autofocus"],
    dependencies=[Depends(verify_api_key)],
)
def set_autofocus_mode(
    req: AutofocusModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set autofocus mode.

    Modes:
    - default/manual: No autofocus, manual lens position control
    - auto: One-shot autofocus
    - continuous: Continuous autofocus during streaming

    Args:
        req: Autofocus mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting autofocus mode: {req.mode}")

    try:
        camera.set_autofocus_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting autofocus mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set autofocus mode",
        )


@app.post(
    "/v1/camera/lens_position",
    response_model=StatusResponse,
    tags=["Camera - Autofocus"],
    dependencies=[Depends(verify_api_key)],
)
def set_lens_position(
    req: LensPositionRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set manual lens position for focus.

    Position values:
    - 0.0: Focus at infinity
    - 1.0-5.0: Normal focus range
    - 10.0+: Macro/close-up focus

    Args:
        req: Lens position request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting lens position: {req.position}")

    try:
        camera.set_lens_position(req.position)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting lens position: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set lens position",
        )


@app.post(
    "/v1/camera/autofocus_range",
    response_model=StatusResponse,
    tags=["Camera - Autofocus"],
    dependencies=[Depends(verify_api_key)],
)
def set_autofocus_range(
    req: AutofocusRangeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set autofocus search range.

    Ranges:
    - normal: Standard focus range
    - macro: Close-up/macro focus only
    - full: Full range search (slower but more thorough)

    Args:
        req: Autofocus range request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting autofocus range: {req.range_mode}")

    try:
        camera.set_autofocus_range(req.range_mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting autofocus range: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set autofocus range",
        )


@app.post(
    "/v1/camera/snapshot",
    response_model=SnapshotResponse,
    tags=["Camera - Capture"],
    dependencies=[Depends(verify_api_key)],
)
def capture_snapshot(
    req: SnapshotRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> SnapshotResponse:
    """
    Capture a single JPEG image without stopping streaming.

    Optionally triggers autofocus before capture. Image is returned
    as base64-encoded JPEG data.

    Args:
        req: Snapshot request with resolution and autofocus settings

    Returns:
        SnapshotResponse: Base64-encoded JPEG image

    Raises:
        HTTPException: If capture fails
    """
    logger.info(f"Capturing snapshot: {req.width}x{req.height}")

    try:
        image_base64 = camera.capture_snapshot(
            width=req.width,
            height=req.height,
            autofocus_trigger=req.autofocus_trigger,
        )
        return SnapshotResponse(
            image_base64=image_base64,
            width=req.width,
            height=req.height,
        )
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error capturing snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture snapshot",
        )


@app.post(
    "/v1/camera/manual_awb",
    response_model=StatusResponse,
    tags=["Camera - White Balance"],
    dependencies=[Depends(verify_api_key)],
)
def set_manual_awb(
    req: ManualAwbRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set manual white balance gains.

    Allows precise control of color balance. Useful for NoIR cameras
    or fixed lighting conditions.

    Typical values:
    - Daylight: red_gain=1.2-1.5, blue_gain=1.5-2.0
    - Indoor: red_gain=1.3-1.6, blue_gain=1.4-1.8
    - IR lighting: red_gain=1.0, blue_gain=1.0

    Args:
        req: Manual AWB request with red and blue gains

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting manual AWB: R={req.red_gain}, B={req.blue_gain}")

    try:
        camera.set_manual_awb(req.red_gain, req.blue_gain)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting manual AWB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set manual AWB",
        )


@app.post(
    "/v1/camera/awb_preset",
    response_model=StatusResponse,
    tags=["Camera - White Balance"],
    dependencies=[Depends(verify_api_key)],
)
def set_awb_preset(
    req: AwbPresetRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set white balance using a NoIR-optimized preset.

    Presets:
    - daylight_noir: Outdoor/daylight with NoIR camera
    - ir_850nm: IR illumination at 850nm wavelength
    - ir_940nm: IR illumination at 940nm wavelength
    - indoor_noir: Indoor lighting with NoIR camera

    Args:
        req: AWB preset request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting AWB preset: {req.preset}")

    try:
        camera.set_awb_preset(req.preset)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting AWB preset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set AWB preset",
        )


@app.post(
    "/v1/camera/image_processing",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_image_processing(
    req: ImageProcessingRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set image processing parameters.

    Adjust brightness, contrast, saturation, and sharpness.
    All parameters are optional - only provided values will be updated.

    Args:
        req: Image processing request with optional parameters

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting image processing: {req}")

    try:
        camera.set_image_processing(
            brightness=req.brightness,
            contrast=req.contrast,
            saturation=req.saturation,
            sharpness=req.sharpness,
        )
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting image processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set image processing",
        )


@app.post(
    "/v1/camera/hdr",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_hdr_mode(
    req: HdrModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set HDR (High Dynamic Range) mode.

    Modes:
    - off: HDR disabled
    - auto: Automatic HDR detection
    - sensor: Hardware HDR from sensor (Camera Module 3)
    - single-exp: Software HDR via multi-frame processing

    Note: May require camera reconfiguration to take full effect.

    Args:
        req: HDR mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting HDR mode: {req.mode}")

    try:
        camera.set_hdr_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting HDR mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set HDR mode",
        )


@app.post(
    "/v1/camera/roi",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_roi(
    req: RoiRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set Region of Interest (digital crop/zoom).

    Defines a rectangular region to stream/process. Coordinates are
    normalized (0.0 to 1.0) relative to full sensor resolution.

    Example for center crop:
    - x=0.25, y=0.25, width=0.5, height=0.5

    Args:
        req: ROI request with normalized coordinates

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting ROI: x={req.x}, y={req.y}, w={req.width}, h={req.height}")

    try:
        camera.set_roi(req.x, req.y, req.width, req.height)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting ROI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set ROI",
        )


@app.post(
    "/v1/camera/exposure_limits",
    response_model=StatusResponse,
    tags=["Camera - Exposure"],
    dependencies=[Depends(verify_api_key)],
)
def set_exposure_limits(
    req: ExposureLimitsRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set limits for auto-exposure algorithm.

    Constrains the min/max values that auto-exposure can use.
    Useful to prevent over/under-exposure or avoid flicker under
    artificial lighting.

    All parameters are optional - only provided limits will be set.

    Args:
        req: Exposure limits request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting exposure limits: {req}")

    try:
        camera.set_exposure_limits(
            min_exposure_us=req.min_exposure_us,
            max_exposure_us=req.max_exposure_us,
            min_gain=req.min_gain,
            max_gain=req.max_gain,
        )
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting exposure limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set exposure limits",
        )


@app.post(
    "/v1/camera/lens_correction",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_lens_correction(
    req: LensCorrectionRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Enable or disable lens shading correction.

    Corrects lens distortion and vignetting, particularly important
    for wide-angle cameras (120° FOV).

    Note: May require camera reconfiguration to take full effect.

    Args:
        req: Lens correction request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting lens correction: {req.enabled}")

    try:
        camera.set_lens_correction(req.enabled)
        return StatusResponse()
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error setting lens correction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set lens correction",
        )


@app.post(
    "/v1/camera/transform",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_transform(
    req: TransformRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set image transformation (flip/rotation).

    Useful for mounting camera in different orientations.

    Note: Transform changes require camera restart to take effect.

    Args:
        req: Transform request with flip/rotation settings

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting transform: hflip={req.hflip}, vflip={req.vflip}, rotation={req.rotation}")

    try:
        camera.set_transform(req.hflip, req.vflip, req.rotation)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting transform: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set transform",
        )


@app.post(
    "/v1/camera/day_night_mode",
    response_model=StatusResponse,
    tags=["Camera - Scene Detection"],
    dependencies=[Depends(verify_api_key)],
)
def set_day_night_mode(
    req: DayNightModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set day/night detection mode.

    Modes:
    - manual: No automatic switching
    - auto: Automatic detection based on lux threshold

    When auto mode is enabled, the camera will detect scene brightness
    and report it in the status endpoint as "day", "low_light", or "night".

    Args:
        req: Day/night mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting day/night mode: {req.mode}, threshold={req.threshold_lux}")

    try:
        camera.set_day_night_mode(req.mode, req.threshold_lux)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting day/night mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set day/night mode",
        )


# ========== New v2.1 Endpoints ==========


@app.post(
    "/v1/camera/exposure_value",
    response_model=StatusResponse,
    tags=["Camera - Exposure"],
    dependencies=[Depends(verify_api_key)],
)
def set_exposure_value(
    req: ExposureValueRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set exposure value (EV) compensation.

    EV compensation adjusts the target brightness of auto-exposure.
    Positive values make the image brighter, negative values darker.

    Examples:
    - +1.0 EV: Double the brightness (useful in backlit scenes)
    - -1.0 EV: Half the brightness (useful in bright scenes)
    - 0.0 EV: No compensation

    Args:
        req: Exposure value request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting exposure value: {req.ev}")

    try:
        camera.set_exposure_value(req.ev)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting exposure value: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set exposure value",
        )


@app.post(
    "/v1/camera/noise_reduction",
    response_model=StatusResponse,
    tags=["Camera - Image Processing"],
    dependencies=[Depends(verify_api_key)],
)
def set_noise_reduction(
    req: NoiseReductionRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set noise reduction mode.

    Modes:
    - off: No noise reduction (sharpest but noisiest)
    - fast: Fast noise reduction (good for real-time video)
    - high_quality: High quality noise reduction (best quality, slower)
    - minimal: Minimal noise reduction
    - zsl: Zero shutter lag mode

    Args:
        req: Noise reduction request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting noise reduction mode: {req.mode}")

    try:
        camera.set_noise_reduction_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting noise reduction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set noise reduction mode",
        )


@app.post(
    "/v1/camera/ae_constraint_mode",
    response_model=StatusResponse,
    tags=["Camera - Exposure"],
    dependencies=[Depends(verify_api_key)],
)
def set_ae_constraint_mode(
    req: AeConstraintModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set auto-exposure constraint mode.

    Constraint modes determine how the AE algorithm handles exposure:
    - normal: Default balanced exposure
    - highlight: Preserve highlights (avoid overexposure/clipping)
    - shadows: Preserve shadows (avoid underexposure)
    - custom: Platform-specific custom mode

    Args:
        req: AE constraint mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting AE constraint mode: {req.mode}")

    try:
        camera.set_ae_constraint_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting AE constraint mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set AE constraint mode",
        )


@app.post(
    "/v1/camera/ae_exposure_mode",
    response_model=StatusResponse,
    tags=["Camera - Exposure"],
    dependencies=[Depends(verify_api_key)],
)
def set_ae_exposure_mode(
    req: AeExposureModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set auto-exposure mode.

    Exposure modes control how AE selects exposure time and gain:
    - normal: Balanced exposure time and gain
    - short: Prefer shorter exposure times (reduce motion blur, more noise)
    - long: Prefer longer exposure times (reduce noise, more blur in motion)
    - custom: Platform-specific custom mode

    Args:
        req: AE exposure mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting AE exposure mode: {req.mode}")

    try:
        camera.set_ae_exposure_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting AE exposure mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set AE exposure mode",
        )


@app.post(
    "/v1/camera/awb_mode",
    response_model=StatusResponse,
    tags=["Camera - White Balance"],
    dependencies=[Depends(verify_api_key)],
)
def set_awb_mode(
    req: AwbModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Set auto white balance mode (preset illuminants).

    AWB modes are optimized for different lighting conditions:
    - auto: Automatic white balance for any scene
    - tungsten: Incandescent/tungsten lighting (~2700K)
    - fluorescent: Fluorescent lighting (~4000K)
    - indoor: General indoor lighting
    - daylight: Outdoor daylight (~5500K)
    - cloudy: Cloudy/overcast daylight (~6500K)
    - custom: Platform-specific custom mode

    Args:
        req: AWB mode request

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting AWB mode: {req.mode}")

    try:
        camera.set_awb_mode(req.mode)
        return StatusResponse()
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting AWB mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set AWB mode",
        )


@app.post(
    "/v1/camera/autofocus_trigger",
    response_model=StatusResponse,
    tags=["Camera - Autofocus"],
    dependencies=[Depends(verify_api_key)],
)
def trigger_autofocus(
    camera: Annotated[CameraController, Depends(get_camera_controller)],
) -> StatusResponse:
    """
    Trigger a one-shot autofocus cycle.

    Initiates an autofocus scan. Useful when in manual or auto focus mode.

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info("Triggering autofocus")

    try:
        camera.trigger_autofocus()
        return StatusResponse()
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error triggering autofocus: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger autofocus",
        )


@app.post(
    "/v1/camera/resolution",
    response_model=StatusResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def set_resolution(
    req: ResolutionRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
    streaming: Annotated[StreamingManager, Depends(get_streaming_manager)],
) -> StatusResponse:
    """
    Change camera resolution dynamically.

    Changes the streaming resolution by stopping, reconfiguring, and restarting.
    The stream will be briefly interrupted during the resolution change.

    Common resolutions:
    - 1920x1080 (Full HD)
    - 1280x720 (HD)
    - 640x480 (VGA)
    - 3840x2160 (4K, if sensor supports)

    Args:
        req: Resolution request with width, height, and restart flag

    Returns:
        StatusResponse: Confirmation

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting resolution: {req.width}x{req.height}")

    # Use global lock to prevent concurrent reconfiguration operations
    with _reconfiguration_lock:
        try:
            # Set FOV mode if specified
            if req.fov_mode is not None:
                camera.set_fov_mode(req.fov_mode)
                logger.info(f"FOV mode set to: {req.fov_mode}")

            # Check if streaming is active
            was_streaming = streaming.is_streaming()

            # Stop streaming if active (must stop encoder first)
            if was_streaming:
                logger.info("Stopping streaming before resolution change")
                streaming.stop()

            # Change resolution (this will stop, reconfigure, and restart camera)
            camera.set_resolution(req.width, req.height)

            # Restart streaming if requested and was previously streaming
            if req.restart_streaming and was_streaming:
                logger.info("Restarting streaming after resolution change")
                streaming.start()

            return StatusResponse()
        except (CameraNotAvailableError, InvalidParameterError):
            raise
        except Exception as e:
            logger.error(f"Error setting resolution: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set resolution",
            )


@app.post(
    "/v1/camera/framerate",
    response_model=FramerateResponse,
    tags=["Camera"],
    dependencies=[Depends(verify_api_key)],
)
def set_framerate(
    req: FramerateRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
    streaming: Annotated[StreamingManager, Depends(get_streaming_manager)],
) -> FramerateResponse:
    """
    Change camera framerate with intelligent clamping.

    Automatically clamps the requested framerate to the maximum supported
    by the current resolution. For example, requesting 500fps at 4K will
    automatically apply 30fps (the maximum for 4K).

    **Framerate Limits by Resolution:**
    - 4K (3840x2160): Max 30fps
    - 1440p (2560x1440): Max 40fps
    - 1080p (1920x1080): Max 50fps
    - 720p (1280x720): Max 120fps

    The stream will be briefly interrupted during the framerate change.

    Args:
        req: Framerate request with desired fps and restart flag

    Returns:
        FramerateResponse: Details about requested vs applied framerate

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting framerate: {req.framerate}fps")

    # Use global lock to prevent concurrent reconfiguration operations
    with _reconfiguration_lock:
        try:
            # Check if streaming is active
            was_streaming = streaming.is_streaming()

            # Stop streaming if active (must stop encoder first)
            if was_streaming:
                logger.info("Stopping streaming before framerate change")
                streaming.stop()

            # Change framerate (this will stop, reconfigure, and restart camera)
            result = camera.set_framerate(req.framerate)

            # Restart streaming if requested and was previously streaming
            if req.restart_streaming and was_streaming:
                logger.info("Restarting streaming after framerate change")
                streaming.start()

            return FramerateResponse(**result)
        except (CameraNotAvailableError, InvalidParameterError):
            raise
        except Exception as e:
            logger.error(f"Error setting framerate: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set framerate",
            )


@app.get(
    "/v1/camera/fov_mode",
    response_model=FovModeResponse,
    summary="Get FOV mode",
    tags=["Camera"],
)
def get_fov_mode(
    camera: Annotated[CameraController, Depends(get_camera_controller)],
    _: Annotated[None, Depends(verify_api_key)],
) -> FovModeResponse:
    """
    Get current field of view mode.

    Returns information about the current FOV mode (scale or crop) and its
    description.

    Returns:
        FovModeResponse: Current FOV mode details

    Raises:
        HTTPException: If operation fails
    """
    try:
        mode = camera.get_fov_mode()
        description = (
            "Full sensor readout with downscaling → Constant field of view"
            if mode == "scale"
            else "Sensor crop → Digital zoom effect (FOV reduces at lower resolutions)"
        )
        return FovModeResponse(mode=mode, description=description)
    except Exception as e:
        logger.error(f"Error getting FOV mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get FOV mode",
        )


@app.post(
    "/v1/camera/fov_mode",
    response_model=FovModeResponse,
    summary="Set FOV mode",
    tags=["Camera"],
)
def set_fov_mode(
    req: FovModeRequest,
    camera: Annotated[CameraController, Depends(get_camera_controller)],
    _: Annotated[None, Depends(verify_api_key)],
) -> FovModeResponse:
    """
    Set field of view mode (scale or crop).

    Modes:
    - "scale": Read full sensor area, downscale to output resolution
      → Constant field of view at all resolutions
      → Better image quality (downsampling vs cropping)
      → Slightly higher processing load
      → Recommended for most use cases

    - "crop": Read only the required sensor area for target resolution
      → Digital zoom effect (FOV reduces at lower resolutions)
      → Lower processing load
      → Useful for telephoto/zoom applications

    Note: The new mode will take effect on the next resolution/framerate change
    or camera reconfiguration.

    Args:
        req: FOV mode request with mode ("scale" or "crop")

    Returns:
        FovModeResponse: New FOV mode and description

    Raises:
        HTTPException: If operation fails
    """
    logger.info(f"Setting FOV mode: {req.mode}")

    try:
        camera.set_fov_mode(req.mode)
        description = (
            "Full sensor readout with downscaling → Constant field of view"
            if req.mode == "scale"
            else "Sensor crop → Digital zoom effect (FOV reduces at lower resolutions)"
        )
        return FovModeResponse(mode=req.mode, description=description)
    except (CameraNotAvailableError, InvalidParameterError):
        raise
    except Exception as e:
        logger.error(f"Error setting FOV mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set FOV mode",
        )


# ========== System Status Endpoints (v2.5) ==========

@app.get(
    "/v1/system/status",
    response_model=SystemStatusResponse,
    summary="Get system status",
    description="Get comprehensive system metrics including temperature, CPU, memory, network, and disk usage",
    tags=["System"],
)
def get_system_status(
    monitor: Annotated[SystemMonitor, Depends(get_system_monitor)],
    _: Annotated[None, Depends(verify_api_key)],
) -> SystemStatusResponse:
    """
    Get comprehensive system status metrics.

    Returns hardware and system information including:
    - CPU temperature and thermal status
    - CPU usage percentage and load average
    - Memory (RAM) usage statistics
    - Network statistics (WiFi signal, bandwidth)
    - Disk usage statistics
    - System and service uptime
    - Throttling status (Raspberry Pi specific)

    This endpoint is useful for monitoring the health of the Raspberry Pi
    running the camera service, especially for:
    - Detecting thermal throttling issues
    - Monitoring network connectivity quality
    - Checking resource usage (CPU, memory, disk)
    - Verifying system stability

    Returns:
        SystemStatusResponse: Comprehensive system metrics

    Raises:
        HTTPException: If system monitor is not available
    """
    logger.debug("Getting system status")

    try:
        status_data = monitor.get_status()
        return SystemStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system status",
        )
