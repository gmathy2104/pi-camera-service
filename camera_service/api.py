"""
FastAPI application for Pi Camera Service.

Provides HTTP API for controlling Raspberry Pi camera including exposure,
white balance, and RTSP streaming to MediaMTX.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

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

# Configure logging
logging.basicConfig(
    level=CONFIG.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
camera_controller: CameraController | None = None
streaming_manager: StreamingManager | None = None

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


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle: startup and shutdown events.

    Initializes camera and streaming on startup, cleans up on shutdown.
    """
    global camera_controller, streaming_manager

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
    version="1.0.0",
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
    """Camera status response model."""
    lux: float | None = Field(None, description="Estimated scene brightness (lux)")
    exposure_us: int | None = Field(None, description="Current exposure time (µs)")
    analogue_gain: float | None = Field(None, description="Current analogue gain")
    colour_temperature: float | None = Field(None, description="Color temperature (K)")
    auto_exposure: bool = Field(..., description="Auto exposure enabled")
    streaming: bool = Field(..., description="Streaming active")


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
        version="1.0.0",
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
            lux=status_data.get("lux"),
            exposure_us=status_data.get("exposure_us"),
            analogue_gain=status_data.get("analogue_gain"),
            colour_temperature=status_data.get("colour_temperature"),
            auto_exposure=status_data.get("auto_exposure", False),
            streaming=streaming.is_streaming(),
        )
    except CameraNotAvailableError:
        raise
    except Exception as e:
        logger.error(f"Error getting camera status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve camera status",
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
