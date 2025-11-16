from dataclasses import dataclass


@dataclass
class CameraConfig:
    width: int = 1920
    height: int = 1080
    framerate: int = 30
    bitrate: int = 8_000_000  # bits/s pour H.264
    # URL RTSP servie par MediaMTX sur le PI
    rtsp_url: str = "rtsp://127.0.0.1:8554/cam"
    enable_awb: bool = True
    default_auto_exposure: bool = True


CONFIG = CameraConfig()
