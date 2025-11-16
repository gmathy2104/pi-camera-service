"""
Tests for StreamingManager.

Tests streaming lifecycle, error handling, and resource management
with mocked Picamera2 encoder and output.
"""

import pytest
from unittest.mock import Mock, patch

from camera_service.streaming_manager import StreamingManager
from camera_service.exceptions import StreamingError


class TestStreamingManagerInit:
    """Test streaming manager initialization."""

    def test_init(self, camera_controller):
        """Test that manager initializes correctly."""
        manager = StreamingManager(camera_controller)

        assert manager._camera is camera_controller
        assert manager._encoder is None
        assert manager._output is None
        assert manager._streaming is False
        assert manager._lock is not None


class TestStreamingManagerStart:
    """Test streaming start functionality."""

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_start_success(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test successful streaming start."""
        streaming_manager.start()

        assert streaming_manager._streaming is True
        assert streaming_manager._encoder is not None
        assert streaming_manager._output is not None

        # Verify encoder and output were created
        mock_encoder.assert_called_once()
        mock_ffmpeg.assert_called_once()

        # Verify recording was started
        mock_picamera2.start_recording.assert_called_once()

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_start_idempotent(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test that starting when already streaming is a no-op."""
        streaming_manager.start()
        initial_encoder = streaming_manager._encoder
        initial_output = streaming_manager._output

        # Start again
        streaming_manager.start()

        assert streaming_manager._streaming is True
        # Should be the same instances (not recreated)
        assert streaming_manager._encoder is initial_encoder
        assert streaming_manager._output is initial_output

        # Should only be called once total
        assert mock_picamera2.start_recording.call_count == 1

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_start_failure(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test streaming start failure handling."""
        mock_picamera2.start_recording.side_effect = Exception("Encoding failed")

        with pytest.raises(StreamingError):
            streaming_manager.start()

        # Should have cleaned up on failure
        assert streaming_manager._streaming is False
        assert streaming_manager._encoder is None
        assert streaming_manager._output is None


class TestStreamingManagerStop:
    """Test streaming stop functionality."""

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_stop_success(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test successful streaming stop."""
        # Start streaming first
        streaming_manager.start()
        assert streaming_manager._streaming is True

        # Stop streaming
        streaming_manager.stop()

        assert streaming_manager._streaming is False
        assert streaming_manager._encoder is None
        assert streaming_manager._output is None

        # Verify recording was stopped
        mock_picamera2.stop_recording.assert_called_once()

    def test_stop_when_not_streaming(self, streaming_manager):
        """Test that stopping when not streaming is a no-op."""
        # Should not raise exception
        streaming_manager.stop()

        assert streaming_manager._streaming is False

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_stop_with_error(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test that stop handles errors gracefully."""
        # Start streaming first
        streaming_manager.start()

        # Make stop_recording raise an error
        mock_picamera2.stop_recording.side_effect = Exception("Stop failed")

        # Should not raise exception
        streaming_manager.stop()

        # Should still cleanup resources
        assert streaming_manager._streaming is False
        assert streaming_manager._encoder is None
        assert streaming_manager._output is None


class TestStreamingManagerIsStreaming:
    """Test is_streaming method."""

    def test_is_streaming_false_initially(self, streaming_manager):
        """Test that is_streaming returns False initially."""
        assert streaming_manager.is_streaming() is False

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_is_streaming_true_when_streaming(self, mock_ffmpeg, mock_encoder, streaming_manager):
        """Test that is_streaming returns True when streaming."""
        streaming_manager.start()

        assert streaming_manager.is_streaming() is True

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_is_streaming_false_after_stop(self, mock_ffmpeg, mock_encoder, streaming_manager):
        """Test that is_streaming returns False after stopping."""
        streaming_manager.start()
        streaming_manager.stop()

        assert streaming_manager.is_streaming() is False


class TestStreamingManagerLifecycle:
    """Test complete streaming lifecycle."""

    @patch("camera_service.streaming_manager.H264Encoder")
    @patch("camera_service.streaming_manager.FfmpegOutput")
    def test_start_stop_cycle(self, mock_ffmpeg, mock_encoder, streaming_manager, mock_picamera2):
        """Test multiple start/stop cycles."""
        # First cycle
        streaming_manager.start()
        assert streaming_manager.is_streaming() is True
        streaming_manager.stop()
        assert streaming_manager.is_streaming() is False

        # Second cycle
        streaming_manager.start()
        assert streaming_manager.is_streaming() is True
        streaming_manager.stop()
        assert streaming_manager.is_streaming() is False

        # Verify calls
        assert mock_picamera2.start_recording.call_count == 2
        assert mock_picamera2.stop_recording.call_count == 2
