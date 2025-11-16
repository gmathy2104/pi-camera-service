from __future__ import annotations

from threading import Lock
from typing import Optional, Dict, Any

from picamera2 import Picamera2
from camera_service.config import CONFIG


class CameraController:
    """
    Encapsule l'accès à Picamera2 et les contrôles de base.
    """

    def __init__(self) -> None:
        self._picam2 = Picamera2()
        self._lock = Lock()
        self._configured = False
        self._auto_exposure = CONFIG.default_auto_exposure

    def configure(self) -> None:
        """
        Configure la caméra avec la configuration par défaut.
        """
        with self._lock:
            if self._configured:
                return

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

            # Réglages initiaux
            self.set_auto_exposure(CONFIG.default_auto_exposure)
            if CONFIG.enable_awb:
                self._picam2.set_controls({"AwbEnable": True})

            self._configured = True

    @property
    def picam2(self) -> Picamera2:
        if not self._configured:
            self.configure()
        return self._picam2

    # ---------- Contrôles d'exposition / gain ----------

    def set_auto_exposure(self, enabled: bool = True) -> None:
        with self._lock:
            controls: Dict[str, Any] = {
                "AeEnable": enabled,
            }
            if enabled:
                controls["ExposureTime"] = 0
            self._picam2.set_controls(controls)
            self._auto_exposure = enabled

    def set_manual_exposure(self, exposure_us: int, gain: float = 1.0) -> None:
        if exposure_us <= 0:
            raise ValueError("exposure_us doit être > 0")
        if gain <= 0:
            raise ValueError("gain doit être > 0")

        with self._lock:
            self._picam2.set_controls({
                "AeEnable": False,
                "ExposureTime": exposure_us,
                "AnalogueGain": gain,
            })
            self._auto_exposure = False

    def set_awb(self, enabled: bool = True) -> None:
        with self._lock:
            self._picam2.set_controls({
                "AwbEnable": enabled,
            })

    # ---------- Métadonnées ----------

    def get_status(self) -> Dict[str, Optional[float]]:
        meta = self._picam2.capture_metadata()
        return {
            "lux": meta.get("Lux"),
            "exposure_us": meta.get("ExposureTime"),
            "analogue_gain": meta.get("AnalogueGain"),
            "colour_temperature": meta.get("ColourTemperature"),
            "auto_exposure": self._auto_exposure,
        }
