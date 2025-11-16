from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from camera_service.camera_controller import CameraController
from camera_service.streaming_manager import StreamingManager

camera_controller = CameraController()
streaming_manager = StreamingManager(camera_controller)

app = FastAPI(
    title="Pi Camera Service",
    description="API pour contrôler la caméra Raspberry Pi et streamer vers MediaMTX.",
    version="0.1.0",
)


class ManualExposureRequest(BaseModel):
    exposure_us: int = Field(..., gt=0, description="Temps d'exposition en microsecondes")
    gain: float = Field(1.0, gt=0.0, description="Gain analogique")


class AutoExposureRequest(BaseModel):
    enabled: bool = True


class AwbRequest(BaseModel):
    enabled: bool = True


class CameraStatusResponse(BaseModel):
    lux: float | None
    exposure_us: int | None
    analogue_gain: float | None
    colour_temperature: float | None
    auto_exposure: bool
    streaming: bool


@app.on_event("startup")
def on_startup() -> None:
    camera_controller.configure()
    streaming_manager.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    streaming_manager.stop()


@app.get("/camera/status", response_model=CameraStatusResponse)
def get_camera_status() -> CameraStatusResponse:
    status = camera_controller.get_status()
    return CameraStatusResponse(
        lux=status.get("lux"),
        exposure_us=status.get("exposure_us"),
        analogue_gain=status.get("analogue_gain"),
        colour_temperature=status.get("colour_temperature"),
        auto_exposure=status.get("auto_exposure", False),
        streaming=streaming_manager.is_streaming(),
    )


@app.post("/camera/auto_exposure")
def set_auto_exposure(req: AutoExposureRequest) -> dict:
    camera_controller.set_auto_exposure(req.enabled)
    return {"status": "ok", "auto_exposure": req.enabled}


@app.post("/camera/manual_exposure")
def set_manual_exposure(req: ManualExposureRequest) -> dict:
    try:
        camera_controller.set_manual_exposure(
            exposure_us=req.exposure_us,
            gain=req.gain,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "status": "ok",
        "exposure_us": req.exposure_us,
        "gain": req.gain,
    }


@app.post("/camera/awb")
def set_awb(req: AwbRequest) -> dict:
    camera_controller.set_awb(req.enabled)
    return {"status": "ok", "awb_enabled": req.enabled}


@app.post("/streaming/start")
def start_streaming() -> dict:
    streaming_manager.start()
    return {"status": "ok", "streaming": streaming_manager.is_streaming()}


@app.post("/streaming/stop")
def stop_streaming() -> dict:
    streaming_manager.stop()
    return {"status": "ok", "streaming": streaming_manager.is_streaming()}
