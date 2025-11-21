"""
Configuration management for Pi Camera Service.

Uses Pydantic BaseSettings for type-safe configuration with environment variable support.
All settings can be overridden via environment variables with the CAMERA_ prefix.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CameraConfig(BaseSettings):
    """
    Camera and streaming configuration.

    All settings can be overridden via environment variables:
    - CAMERA_WIDTH: Video width in pixels (64-4096)
    - CAMERA_HEIGHT: Video height in pixels (64-4096)
    - CAMERA_FRAMERATE: Frames per second (1-120)
    - CAMERA_BITRATE: H.264 bitrate in bits/s
    - CAMERA_RTSP_URL: MediaMTX RTSP endpoint URL
    - CAMERA_ENABLE_AWB: Enable auto white balance (true/false)
    - CAMERA_DEFAULT_AUTO_EXPOSURE: Enable auto exposure on startup (true/false)
    - CAMERA_API_KEY: API key for authentication (optional, disables auth if not set)
    - CAMERA_HOST: API server host
    - CAMERA_PORT: API server port
    - CAMERA_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """

    model_config = SettingsConfigDict(
        env_prefix="CAMERA_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Video configuration
    width: int = Field(
        default=1920,
        description="Video width in pixels",
        ge=64,
        le=4096,
    )
    height: int = Field(
        default=1080,
        description="Video height in pixels",
        ge=64,
        le=4096,
    )
    framerate: int = Field(
        default=30,
        description="Frames per second",
        ge=1,
        le=120,
    )
    bitrate: int = Field(
        default=8_000_000,
        description="H.264 bitrate in bits/s",
        ge=100_000,
        le=50_000_000,
    )

    # Streaming configuration
    rtsp_url: str = Field(
        default="rtsp://127.0.0.1:8554/cam",
        description="MediaMTX RTSP endpoint URL",
    )

    # Camera control defaults
    enable_awb: bool = Field(
        default=True,
        description="Enable auto white balance on startup",
    )
    default_auto_exposure: bool = Field(
        default=True,
        description="Enable auto exposure on startup",
    )
    tuning_file: str | None = Field(
        default=None,
        description="Path to libcamera tuning file (auto-detected if None)",
    )
    camera_model: str = Field(
        default="imx708",
        description="Camera sensor model (imx708, imx477, etc.)",
    )
    is_noir: bool = Field(
        default=False,
        description="True if using NoIR (No IR filter) camera module",
    )

    # API server configuration
    host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    port: int = Field(
        default=8000,
        description="API server port",
        ge=1,
        le=65535,
    )

    # Security
    api_key: str | None = Field(
        default=None,
        description="API key for authentication (if not set, authentication is disabled)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard Python logging levels."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper

    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate RTSP URL format."""
        if not v.startswith("rtsp://"):
            raise ValueError("RTSP URL must start with rtsp://")
        return v


# Global configuration instance
CONFIG = CameraConfig()
