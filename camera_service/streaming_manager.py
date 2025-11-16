"""
Streaming manager module for Pi Camera Service.

Manages H.264 encoding and RTSP streaming to MediaMTX with proper
error handling and resource cleanup.
"""

from __future__ import annotations

import logging
from threading import RLock
from typing import Optional

from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

from camera_service.camera_controller import CameraController
from camera_service.config import CONFIG
from camera_service.exceptions import StreamingError

logger = logging.getLogger(__name__)


class StreamingManager:
    """
    Thread-safe manager for H.264 streaming to MediaMTX via RTSP.

    Handles encoder initialization, streaming lifecycle, and proper
    resource cleanup on shutdown.
    """

    def __init__(self, camera: CameraController) -> None:
        """
        Initialize the streaming manager.

        Args:
            camera: CameraController instance to stream from
        """
        self._camera = camera
        self._encoder: Optional[H264Encoder] = None
        self._output: Optional[FfmpegOutput] = None
        self._streaming: bool = False
        self._lock = RLock()  # Reentrant lock

        logger.debug("StreamingManager initialized")

    def start(self) -> None:
        """
        Start H.264 streaming to MediaMTX.

        Raises:
            StreamingError: If streaming fails to start
        """
        with self._lock:
            if self._streaming:
                logger.debug("Streaming already active, skipping start")
                return

            try:
                logger.info(f"Starting RTSP streaming to {CONFIG.rtsp_url}")

                picam2 = self._camera.picam2

                # Ensure camera is started before recording
                if not picam2.started:
                    logger.debug("Camera not started, starting it now...")
                    picam2.start()

                # Create H.264 encoder
                self._encoder = H264Encoder(bitrate=CONFIG.bitrate)

                # Create RTSP output via ffmpeg
                self._output = FfmpegOutput(
                    f"-f rtsp -rtsp_transport tcp {CONFIG.rtsp_url}",
                    audio=False,
                )

                # Start recording
                picam2.start_recording(self._encoder, self._output)
                self._streaming = True

                logger.info(
                    f"Streaming started successfully to {CONFIG.rtsp_url} "
                    f"(bitrate={CONFIG.bitrate}bps)"
                )

            except Exception as e:
                logger.error(f"Failed to start streaming: {e}")
                # Cleanup on failure
                self._encoder = None
                self._output = None
                self._streaming = False
                raise StreamingError(f"Failed to start streaming: {e}") from e

    def stop(self) -> None:
        """
        Stop H.264 streaming.

        Performs cleanup of encoder and output resources.
        """
        with self._lock:
            if not self._streaming:
                logger.debug("Streaming not active, skipping stop")
                return

            try:
                logger.info("Stopping RTSP streaming...")

                picam2 = self._camera.picam2
                picam2.stop_recording()

                logger.info("Streaming stopped successfully")

            except Exception as e:
                logger.error(f"Error stopping recording: {e}")
                # Continue with cleanup even if stop fails

            finally:
                # Always cleanup resources
                if self._output is not None:
                    try:
                        # FfmpegOutput may have cleanup methods
                        # For now, just clear the reference
                        self._output = None
                    except Exception as e:
                        logger.warning(f"Error cleaning up output: {e}")

                self._encoder = None
                self._streaming = False
                logger.debug("Streaming resources cleaned up")

    def is_streaming(self) -> bool:
        """
        Check if streaming is currently active.

        Returns:
            bool: True if streaming, False otherwise
        """
        with self._lock:
            return self._streaming
