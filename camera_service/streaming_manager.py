from __future__ import annotations

from threading import Lock
from typing import Optional

from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

from camera_service.config import CONFIG
from camera_service.camera_controller import CameraController


class StreamingManager:
    """
    Démarrage/arrêt du streaming H.264 vers MediaMTX (RTSP).
    """

    def __init__(self, camera: CameraController) -> None:
        self._camera = camera
        self._encoder: Optional[H264Encoder] = None
        self._output: Optional[FfmpegOutput] = None
        self._streaming: bool = False
        self._lock = Lock()

    def start(self) -> None:
        with self._lock:
            if self._streaming:
                return

            picam2 = self._camera.picam2

            self._encoder = H264Encoder(bitrate=CONFIG.bitrate)
            self._output = FfmpegOutput(
                f"-f rtsp -rtsp_transport tcp {CONFIG.rtsp_url}",
                audio=False,
            )

            picam2.start_recording(self._encoder, self._output)
            self._streaming = True

    def stop(self) -> None:
        with self._lock:
            if not self._streaming:
                return

            picam2 = self._camera.picam2
            picam2.stop_recording()

            self._encoder = None
            self._output = None
            self._streaming = False

    def is_streaming(self) -> bool:
        return self._streaming
