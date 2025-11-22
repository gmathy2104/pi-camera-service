"""
Integration tests for the Pi Camera Service API v2.1.

These tests cover new v2.1 endpoints including:
- Exposure value (EV) compensation
- Noise reduction modes
- Advanced AE controls
- AWB modes
- Autofocus trigger
- Dynamic resolution change

Usage:
    # Start the service first
    python main.py

    # In another terminal, run the tests
    pytest tests/test_api_v2_1.py -v

    # Or run standalone
    python tests/test_api_v2_1.py
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


class TestAPIv21Integration:
    """Integration tests for Pi Camera Service API v2.1 features."""

    @pytest.fixture(autouse=True)
    def wait_between_tests(self) -> None:
        """Wait a bit between tests to avoid overwhelming the API."""
        yield
        time.sleep(0.5)

    def test_exposure_value_compensation(self) -> None:
        """Test POST /v1/camera/exposure_value endpoint."""
        # Set positive EV compensation
        response = requests.post(
            f"{BASE_URL}/v1/camera/exposure_value",
            json={"ev": 1.0},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Set negative EV compensation
        response = requests.post(
            f"{BASE_URL}/v1/camera/exposure_value",
            json={"ev": -0.5},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200

        # Reset to no compensation
        response = requests.post(
            f"{BASE_URL}/v1/camera/exposure_value",
            json={"ev": 0.0},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        print("✓ Exposure value compensation working")

    def test_exposure_value_out_of_range(self) -> None:
        """Test POST /v1/camera/exposure_value with invalid value."""
        response = requests.post(
            f"{BASE_URL}/v1/camera/exposure_value",
            json={"ev": 10.0},  # Out of range
            timeout=TIMEOUT,
        )

        assert response.status_code == 422
        print("✓ Exposure value validation working")

    def test_noise_reduction_modes(self) -> None:
        """Test POST /v1/camera/noise_reduction endpoint."""
        modes = ["off", "fast", "high_quality", "minimal"]

        for mode in modes:
            response = requests.post(
                f"{BASE_URL}/v1/camera/noise_reduction",
                json={"mode": mode},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

        print("✓ Noise reduction modes working")

    def test_ae_constraint_mode(self) -> None:
        """Test POST /v1/camera/ae_constraint_mode endpoint."""
        modes = ["normal", "highlight", "shadows"]

        for mode in modes:
            response = requests.post(
                f"{BASE_URL}/v1/camera/ae_constraint_mode",
                json={"mode": mode},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

        print("✓ AE constraint modes working")

    def test_ae_exposure_mode(self) -> None:
        """Test POST /v1/camera/ae_exposure_mode endpoint."""
        modes = ["normal", "short", "long"]

        for mode in modes:
            response = requests.post(
                f"{BASE_URL}/v1/camera/ae_exposure_mode",
                json={"mode": mode},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

        print("✓ AE exposure modes working")

    def test_awb_mode(self) -> None:
        """Test POST /v1/camera/awb_mode endpoint."""
        modes = ["auto", "tungsten", "daylight", "cloudy"]

        for mode in modes:
            response = requests.post(
                f"{BASE_URL}/v1/camera/awb_mode",
                json={"mode": mode},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

        print("✓ AWB modes working")

    def test_autofocus_trigger(self) -> None:
        """Test POST /v1/camera/autofocus_trigger endpoint."""
        response = requests.post(
            f"{BASE_URL}/v1/camera/autofocus_trigger",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        print("✓ Autofocus trigger working")

    def test_resolution_change(self) -> None:
        """Test POST /v1/camera/resolution endpoint."""
        # Change to 720p
        response = requests.post(
            f"{BASE_URL}/v1/camera/resolution",
            json={"width": 1280, "height": 720, "restart_streaming": True},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Wait for resolution change to apply
        time.sleep(2)

        # Change back to 1080p
        response = requests.post(
            f"{BASE_URL}/v1/camera/resolution",
            json={"width": 1920, "height": 1080, "restart_streaming": True},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200

        # Wait for resolution change to apply
        time.sleep(2)

        print("✓ Dynamic resolution change working")

    def test_resolution_invalid(self) -> None:
        """Test POST /v1/camera/resolution with invalid resolution."""
        response = requests.post(
            f"{BASE_URL}/v1/camera/resolution",
            json={"width": 50, "height": 50},  # Too small
            timeout=TIMEOUT,
        )

        assert response.status_code == 422
        print("✓ Resolution validation working")

    def test_exposure_limits_fixed(self) -> None:
        """Test POST /v1/camera/exposure_limits with corrected implementation."""
        # Set exposure limits using FrameDurationLimits
        response = requests.post(
            f"{BASE_URL}/v1/camera/exposure_limits",
            json={
                "min_exposure_us": 1000,
                "max_exposure_us": 50000,
            },
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        # Reset to default
        response = requests.post(
            f"{BASE_URL}/v1/camera/auto_exposure",
            json={"enabled": True},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200

        print("✓ Exposure limits (FrameDurationLimits) working")

    def test_camera_capabilities(self) -> None:
        """Test GET /v1/camera/capabilities endpoint (v2.2)."""
        response = requests.get(
            f"{BASE_URL}/v1/camera/capabilities",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "sensor_model" in data
        assert "sensor_resolution" in data
        assert "supported_resolutions" in data
        assert "exposure_limits_us" in data
        assert "gain_limits" in data
        assert "features" in data

        # Validate exposure limits
        assert "min" in data["exposure_limits_us"]
        assert "max" in data["exposure_limits_us"]
        assert data["exposure_limits_us"]["min"] == 100
        assert data["exposure_limits_us"]["max"] == 1000000

        # Validate gain limits
        assert data["gain_limits"]["min"] == 1.0
        assert data["gain_limits"]["max"] == 16.0

        # Check that supported_resolutions is a non-empty list
        assert isinstance(data["supported_resolutions"], list)
        assert len(data["supported_resolutions"]) > 0

        # Check that features is a non-empty list
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0

        print("✓ Camera capabilities endpoint working")

    def test_status_with_current_limits(self) -> None:
        """Test GET /v1/camera/status includes current_limits (v2.2)."""
        response = requests.get(
            f"{BASE_URL}/v1/camera/status",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        # Check current_limits field exists
        assert "current_limits" in data
        assert data["current_limits"] is not None

        # Validate current_limits structure
        assert "frame_duration_us" in data["current_limits"]
        assert "effective_exposure_limit_us" in data["current_limits"]

        # Validate effective_exposure_limit_us has min/max
        assert "min" in data["current_limits"]["effective_exposure_limit_us"]
        assert "max" in data["current_limits"]["effective_exposure_limit_us"]

        print("✓ Status endpoint includes current_limits")

    def test_capabilities_with_framerate_limits(self) -> None:
        """Test GET /v1/camera/capabilities includes framerate limits (v2.3)."""
        response = requests.get(
            f"{BASE_URL}/v1/camera/capabilities",
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        # Check framerate fields exist
        assert "current_framerate" in data
        assert "framerate_limits_by_resolution" in data
        assert "max_framerate_for_current_resolution" in data

        # Validate framerate_limits_by_resolution structure
        assert isinstance(data["framerate_limits_by_resolution"], list)
        assert len(data["framerate_limits_by_resolution"]) > 0

        # Check first entry has required fields
        first_limit = data["framerate_limits_by_resolution"][0]
        assert "width" in first_limit
        assert "height" in first_limit
        assert "label" in first_limit
        assert "max_fps" in first_limit

        # Validate values are reasonable
        assert data["current_framerate"] > 0
        assert data["max_framerate_for_current_resolution"] > 0

        print("✓ Capabilities include framerate limits")

    def test_framerate_change_normal(self) -> None:
        """Test POST /v1/camera/framerate with valid framerate (v2.3)."""
        # Set a reasonable framerate (30fps works for all resolutions)
        response = requests.post(
            f"{BASE_URL}/v1/camera/framerate",
            json={"framerate": 30},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["requested_framerate"] == 30.0
        assert data["applied_framerate"] == 30.0
        assert "max_framerate_for_resolution" in data
        assert "resolution" in data
        assert "clamped" in data
        assert data["clamped"] is False  # 30fps should not be clamped

        print("✓ Framerate change (normal) working")

    def test_framerate_change_with_clamping(self) -> None:
        """Test POST /v1/camera/framerate with intelligent clamping (v2.3)."""
        # First, ensure we're at a resolution with known limits (1080p -> max 50fps)
        requests.post(
            f"{BASE_URL}/v1/camera/resolution",
            json={"width": 1920, "height": 1080},
            timeout=TIMEOUT,
        )
        time.sleep(2)

        # Request an impossibly high framerate
        response = requests.post(
            f"{BASE_URL}/v1/camera/framerate",
            json={"framerate": 500},
            timeout=TIMEOUT,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert data["requested_framerate"] == 500.0
        assert data["applied_framerate"] == 50.0  # Should be clamped to 1080p max
        assert data["max_framerate_for_resolution"] == 50.0
        assert data["resolution"] == "1920x1080"
        assert data["clamped"] is True  # Should indicate clamping occurred

        print("✓ Framerate clamping (intelligent limit) working")


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

    Usage: python tests/test_api_v2_1.py
    """
    print("=" * 60)
    print("Pi Camera Service - API v2.1 Integration Tests")
    print("=" * 60)
    print()

    # Pre-flight check
    print("[1/16] Checking if service is running...")
    test_service_is_running()
    print()

    # Create test instance
    tester = TestAPIv21Integration()

    # Run all tests
    tests = [
        ("[2/16] Testing exposure value compensation...", tester.test_exposure_value_compensation),
        ("[3/16] Testing exposure value validation...", tester.test_exposure_value_out_of_range),
        ("[4/16] Testing noise reduction modes...", tester.test_noise_reduction_modes),
        ("[5/16] Testing AE constraint modes...", tester.test_ae_constraint_mode),
        ("[6/16] Testing AE exposure modes...", tester.test_ae_exposure_mode),
        ("[7/16] Testing AWB modes...", tester.test_awb_mode),
        ("[8/16] Testing autofocus trigger...", tester.test_autofocus_trigger),
        ("[9/16] Testing resolution change...", tester.test_resolution_change),
        ("[10/16] Testing resolution validation...", tester.test_resolution_invalid),
        ("[11/16] Testing corrected exposure limits...", tester.test_exposure_limits_fixed),
        ("[12/16] Testing camera capabilities endpoint...", tester.test_camera_capabilities),
        ("[13/16] Testing status with current limits...", tester.test_status_with_current_limits),
        ("[14/16] Testing capabilities with framerate limits...", tester.test_capabilities_with_framerate_limits),
        ("[15/16] Testing framerate change (normal)...", tester.test_framerate_change_normal),
        ("[16/16] Testing framerate clamping...", tester.test_framerate_change_with_clamping),
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
        print("\n✓ All v2.1 tests passed! Your Pi Camera Service is working correctly.")
        exit(0)
