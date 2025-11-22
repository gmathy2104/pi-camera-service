"""
Integration tests for the Pi Camera Service API.

These tests run against a live API instance (not mocked).
The service must be running on http://localhost:8000 before running these tests.

Usage:
    # Start the service first
    python main.py

    # In another terminal, run the tests
    pytest tests/test_api_integration.py -v

    # Or use the convenience script
    ./test-api.sh
"""

import time
from typing import Any, Dict

import requests

# pytest is optional - only needed when running with pytest
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    # Create dummy pytest for standalone mode
    class pytest:  # type: ignore
        @staticmethod
        def fixture(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

        @staticmethod
        def fail(msg: str) -> None:
            raise AssertionError(msg)

# API base URL - change if running on a different host/port
BASE_URL = "http://localhost:8000"
TIMEOUT = 5  # seconds


class TestAPIIntegration:
    """Integration tests for Pi Camera Service API."""

    @pytest.fixture(autouse=True)
    def wait_between_tests(self) -> None:
        """Wait a bit between tests to avoid overwhelming the API."""
        yield
        time.sleep(0.5)

    def test_health_endpoint(self) -> None:
        """Test GET /health endpoint."""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "camera_configured" in data
        assert "streaming_active" in data
        assert data["version"] == "2.3.1"

        print("✓ Health endpoint working")

    def test_camera_status_endpoint(self) -> None:
        """Test GET /v1/camera/status endpoint."""
        response = requests.get(f"{BASE_URL}/v1/camera/status", timeout=TIMEOUT)

        assert response.status_code == 200
        data = response.json()

        # Check all required fields are present
        assert "lux" in data
        assert "exposure_us" in data
        assert "analogue_gain" in data
        assert "colour_temperature" in data
        assert "auto_exposure" in data
        assert "streaming" in data

        # Check types
        assert isinstance(data["lux"], (int, float)) or data["lux"] is None
        assert isinstance(data["exposure_us"], (int, float)) or data["exposure_us"] is None
        assert isinstance(data["analogue_gain"], (int, float)) or data["analogue_gain"] is None
        assert isinstance(data["auto_exposure"], bool)
        assert isinstance(data["streaming"], bool)

        print("✓ Camera status endpoint working")

    def test_auto_exposure_disable_enable(self) -> None:
        """Test POST /v1/camera/auto_exposure endpoint."""
        # Disable auto exposure
        response = requests.post(
            f"{BASE_URL}/v1/camera/auto_exposure",
            json={"enabled": False},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["auto_exposure"] is False

        # Verify via status endpoint
        status = requests.get(f"{BASE_URL}/v1/camera/status", timeout=TIMEOUT).json()
        assert status["auto_exposure"] is False

        # Re-enable auto exposure
        response = requests.post(
            f"{BASE_URL}/v1/camera/auto_exposure",
            json={"enabled": True},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["auto_exposure"] is True

        # Verify via status endpoint
        status = requests.get(f"{BASE_URL}/v1/camera/status", timeout=TIMEOUT).json()
        assert status["auto_exposure"] is True

        print("✓ Auto exposure toggle working")

    def test_manual_exposure_valid_params(self) -> None:
        """Test POST /v1/camera/manual_exposure with valid parameters."""
        # Set manual exposure
        response = requests.post(
            f"{BASE_URL}/v1/camera/manual_exposure",
            json={"exposure_us": 10000, "gain": 2.0},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["exposure_us"] == 10000
        assert data["gain"] == 2.0

        # Verify via status endpoint
        time.sleep(0.5)  # Give camera time to apply settings
        status = requests.get(f"{BASE_URL}/v1/camera/status", timeout=TIMEOUT).json()
        assert status["auto_exposure"] is False  # Manual mode
        # Note: actual exposure might be slightly different due to hardware constraints
        assert 9000 <= status["exposure_us"] <= 11000  # Allow 10% tolerance
        assert 1.8 <= status["analogue_gain"] <= 2.2  # Allow small tolerance

        print("✓ Manual exposure working")

    def test_manual_exposure_invalid_exposure(self) -> None:
        """Test POST /v1/camera/manual_exposure with invalid exposure (too low)."""
        response = requests.post(
            f"{BASE_URL}/v1/camera/manual_exposure",
            json={"exposure_us": 50, "gain": 2.0},  # Min is 100
            timeout=TIMEOUT,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert "exposure_us must be >= 100" in data["detail"]

        print("✓ Manual exposure validation (exposure too low) working")

    def test_manual_exposure_invalid_gain(self) -> None:
        """Test POST /v1/camera/manual_exposure with invalid gain (too high)."""
        response = requests.post(
            f"{BASE_URL}/v1/camera/manual_exposure",
            json={"exposure_us": 10000, "gain": 20.0},  # Max is 16.0
            timeout=TIMEOUT,
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        print("✓ Manual exposure validation (gain too high) working")

    def test_awb_disable_enable(self) -> None:
        """Test POST /v1/camera/awb endpoint."""
        # Disable AWB
        response = requests.post(
            f"{BASE_URL}/v1/camera/awb",
            json={"enabled": False},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["awb_enabled"] is False

        # Re-enable AWB
        response = requests.post(
            f"{BASE_URL}/v1/camera/awb",
            json={"enabled": True},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["awb_enabled"] is True

        print("✓ Auto white balance toggle working")

    def test_streaming_stop_start_cycle(self) -> None:
        """Test POST /v1/streaming/stop and /v1/streaming/start endpoints."""
        # Check initial state
        health = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT).json()
        initial_streaming = health["streaming_active"]

        # Stop streaming
        response = requests.post(
            f"{BASE_URL}/v1/streaming/stop",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["streaming"] is False

        # Verify streaming is stopped
        time.sleep(1)
        health = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT).json()
        assert health["streaming_active"] is False

        print("✓ Streaming stop working")

        # Start streaming
        response = requests.post(
            f"{BASE_URL}/v1/streaming/start",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["streaming"] is True

        # Verify streaming is started
        time.sleep(2)  # Give streaming time to start
        health = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT).json()
        assert health["streaming_active"] is True

        print("✓ Streaming start working")
        print("✓ Complete stop/start cycle working")


def test_service_is_running() -> None:
    """
    Pre-flight check: ensure the service is running before running tests.

    This test runs first and will fail fast if the service is not available.
    """
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        assert response.status_code == 200
        print(f"✓ Service is running at {BASE_URL}")
    except requests.ConnectionError:
        pytest.fail(
            f"Cannot connect to API at {BASE_URL}. "
            "Make sure the service is running (python main.py)"
        )
    except requests.Timeout:
        pytest.fail(
            f"Connection to {BASE_URL} timed out. "
            "Service may be unresponsive."
        )


if __name__ == "__main__":
    """
    Run tests directly without pytest for quick checks.

    Usage: python tests/test_api_integration.py
    """
    print("=" * 60)
    print("Pi Camera Service - API Integration Tests")
    print("=" * 60)
    print()

    # Pre-flight check
    print("[1/9] Checking if service is running...")
    test_service_is_running()
    print()

    # Create test instance
    tester = TestAPIIntegration()

    # Run all tests
    tests = [
        ("[2/9] Testing health endpoint...", tester.test_health_endpoint),
        ("[3/9] Testing camera status endpoint...", tester.test_camera_status_endpoint),
        ("[4/9] Testing auto exposure toggle...", tester.test_auto_exposure_disable_enable),
        ("[5/9] Testing manual exposure (valid)...", tester.test_manual_exposure_valid_params),
        ("[6/9] Testing manual exposure validation (exposure)...", tester.test_manual_exposure_invalid_exposure),
        ("[7/9] Testing manual exposure validation (gain)...", tester.test_manual_exposure_invalid_gain),
        ("[8/9] Testing auto white balance toggle...", tester.test_awb_disable_enable),
        ("[9/9] Testing streaming stop/start cycle...", tester.test_streaming_stop_start_cycle),
    ]

    passed = 0
    failed = 0

    for description, test_func in tests:
        print(description)
        try:
            tester.wait_between_tests()
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        exit(1)
    else:
        print("\n✓ All tests passed! Your Pi Camera Service is working correctly.")
        exit(0)
