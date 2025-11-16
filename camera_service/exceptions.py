"""
Custom exceptions for the Pi Camera Service.

This module defines all custom exceptions used throughout the application
for better error handling and categorization.
"""

from __future__ import annotations


class CameraError(Exception):
    """
    Base exception for all camera-related errors.

    This is the parent class for all camera service exceptions,
    allowing for broad exception handling when needed.
    """
    pass


class CameraNotAvailableError(CameraError):
    """
    Raised when the camera hardware is not available or cannot be initialized.

    This typically occurs when:
    - No camera is physically connected
    - Camera is already in use by another process
    - Camera drivers are not properly installed
    """
    pass


class InvalidParameterError(CameraError):
    """
    Raised when invalid parameters are provided to camera operations.

    This includes:
    - Out of range values (exposure time, gain, resolution, etc.)
    - Invalid combinations of parameters
    - Type mismatches that pass Pydantic validation but fail hardware validation
    """
    pass


class StreamingError(CameraError):
    """
    Raised when streaming operations fail.

    This can occur during:
    - Starting/stopping the H.264 encoder
    - Connection issues with MediaMTX
    - RTSP transport failures
    """
    pass


class ConfigurationError(CameraError):
    """
    Raised when camera configuration fails.

    This typically occurs when:
    - Invalid video configuration is requested
    - Hardware doesn't support requested settings
    - Configuration conflicts arise
    """
    pass
