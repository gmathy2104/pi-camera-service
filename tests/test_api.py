"""
Tests for FastAPI endpoints.

Tests all API endpoints including authentication, error handling,
and response models.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_no_auth_required(self, client_no_auth):
        """Test that health endpoint doesn't require authentication."""
        response = client_no_auth.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "camera_configured" in data
        assert "streaming_active" in data
        assert "version" in data


class TestCameraStatusEndpoint:
    """Test camera status endpoint."""

    def test_get_status_success(self, client_no_auth):
        """Test getting camera status successfully."""
        response = client_no_auth.get("/v1/camera/status")

        assert response.status_code == 200
        data = response.json()
        assert "lux" in data
        assert "exposure_us" in data
        assert "analogue_gain" in data
        assert "colour_temperature" in data
        assert "auto_exposure" in data
        assert "streaming" in data

    def test_get_status_with_auth(self, client_with_auth, auth_headers):
        """Test that status endpoint requires authentication when configured."""
        # Without auth header should fail
        response = client_with_auth.get("/v1/camera/status")
        assert response.status_code == 401

        # With auth header should succeed
        response = client_with_auth.get("/v1/camera/status", headers=auth_headers)
        assert response.status_code == 200


class TestAutoExposureEndpoint:
    """Test auto exposure endpoint."""

    def test_enable_auto_exposure(self, client_no_auth):
        """Test enabling auto exposure."""
        response = client_no_auth.post(
            "/v1/camera/auto_exposure",
            json={"enabled": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["auto_exposure"] is True

    def test_disable_auto_exposure(self, client_no_auth):
        """Test disabling auto exposure."""
        response = client_no_auth.post(
            "/v1/camera/auto_exposure",
            json={"enabled": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["auto_exposure"] is False

    def test_auto_exposure_invalid_request(self, client_no_auth):
        """Test auto exposure with invalid request body."""
        response = client_no_auth.post(
            "/v1/camera/auto_exposure",
            json={}  # Missing required field
        )

        assert response.status_code == 422  # Validation error


class TestManualExposureEndpoint:
    """Test manual exposure endpoint."""

    def test_set_manual_exposure_success(self, client_no_auth):
        """Test setting manual exposure successfully."""
        response = client_no_auth.post(
            "/v1/camera/manual_exposure",
            json={"exposure_us": 10000, "gain": 2.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["exposure_us"] == 10000
        assert data["gain"] == 2.0

    def test_manual_exposure_default_gain(self, client_no_auth):
        """Test manual exposure with default gain."""
        response = client_no_auth.post(
            "/v1/camera/manual_exposure",
            json={"exposure_us": 10000}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["gain"] == 1.0

    def test_manual_exposure_invalid_exposure_too_low(self, client_no_auth):
        """Test manual exposure with exposure below minimum."""
        response = client_no_auth.post(
            "/v1/camera/manual_exposure",
            json={"exposure_us": 50, "gain": 1.0}
        )

        assert response.status_code == 422

    def test_manual_exposure_invalid_gain_too_high(self, client_no_auth):
        """Test manual exposure with gain above maximum."""
        response = client_no_auth.post(
            "/v1/camera/manual_exposure",
            json={"exposure_us": 10000, "gain": 20.0}
        )

        assert response.status_code == 422


class TestAWBEndpoint:
    """Test auto white balance endpoint."""

    def test_enable_awb(self, client_no_auth):
        """Test enabling AWB."""
        response = client_no_auth.post(
            "/v1/camera/awb",
            json={"enabled": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["awb_enabled"] is True

    def test_disable_awb(self, client_no_auth):
        """Test disabling AWB."""
        response = client_no_auth.post(
            "/v1/camera/awb",
            json={"enabled": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["awb_enabled"] is False


class TestStreamingEndpoints:
    """Test streaming start/stop endpoints."""

    def test_start_streaming(self, client_no_auth):
        """Test starting streaming."""
        response = client_no_auth.post("/v1/streaming/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "streaming" in data

    def test_stop_streaming(self, client_no_auth):
        """Test stopping streaming."""
        response = client_no_auth.post("/v1/streaming/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "streaming" in data

    def test_streaming_lifecycle(self, client_no_auth):
        """Test complete streaming lifecycle."""
        # Start
        response = client_no_auth.post("/v1/streaming/start")
        assert response.status_code == 200

        # Check status
        response = client_no_auth.get("/v1/camera/status")
        # Streaming state depends on mock behavior

        # Stop
        response = client_no_auth.post("/v1/streaming/stop")
        assert response.status_code == 200


class TestAuthentication:
    """Test API authentication."""

    def test_no_auth_when_disabled(self, client_no_auth):
        """Test that endpoints work without auth when disabled."""
        response = client_no_auth.get("/v1/camera/status")
        assert response.status_code == 200

    def test_auth_required_when_enabled(self, client_with_auth):
        """Test that endpoints require auth when enabled."""
        response = client_with_auth.get("/v1/camera/status")
        assert response.status_code == 401

    def test_valid_auth_header(self, client_with_auth, auth_headers):
        """Test that valid API key allows access."""
        response = client_with_auth.get(
            "/v1/camera/status",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_invalid_auth_header(self, client_with_auth):
        """Test that invalid API key is rejected."""
        response = client_with_auth.get(
            "/v1/camera/status",
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_health_bypass_auth(self, client_with_auth):
        """Test that health endpoint bypasses authentication."""
        response = client_with_auth.get("/health")
        assert response.status_code == 200
