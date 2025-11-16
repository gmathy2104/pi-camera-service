"""
Main entry point for Pi Camera Service.

Runs the FastAPI application using uvicorn with configuration from CONFIG.
"""

import uvicorn

from camera_service.api import app
from camera_service.config import CONFIG

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=CONFIG.host,
        port=CONFIG.port,
        reload=False,
        log_level=CONFIG.log_level.lower(),
    )
