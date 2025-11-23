# Pi Camera Service - Examples & Use Cases

This document provides practical examples and real-world use cases for the Pi Camera Service API.

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [System Monitoring Examples](#system-monitoring-examples)
- [Camera Control Examples](#camera-control-examples)
- [Log Monitoring Examples](#log-monitoring-examples)
- [Complete Use Cases](#complete-use-cases)

---

## Quick Start Examples

### Test Connection

```bash
# Check if service is healthy
curl http://192.168.1.100:8000/health

# Expected response:
# {"status":"healthy","camera_configured":true,"streaming_active":true,"version":"2.8.1"}
```

### Get Camera Status

```bash
# Get current camera status
curl -H "X-API-Key: your-key" http://192.168.1.100:8000/v1/camera/status
```

### View Recent Logs

```bash
# Get last 20 logs
curl -H "X-API-Key: your-key" "http://192.168.1.100:8000/v1/system/logs?lines=20"
```

---

## System Monitoring Examples

### Monitor System Health

**Python Script - Monitor Temperature and WiFi**

```python
#!/usr/bin/env python3
"""
Monitor Raspberry Pi temperature and WiFi signal quality.
Alert if temperature is high or WiFi signal is weak.
"""

import requests
import time
from datetime import datetime

API_BASE = "http://192.168.1.100:8000"
API_KEY = "your-secret-key"
HEADERS = {"X-API-Key": API_KEY}

def check_system_health():
    """Check system health and return alerts."""
    try:
        response = requests.get(f"{API_BASE}/v1/system/status", headers=HEADERS)
        status = response.json()

        alerts = []

        # Check temperature
        if status['temperature']:
            temp = status['temperature']['cpu_c']
            temp_status = status['temperature']['status']

            if temp_status in ['hot', 'critical']:
                alerts.append(f"⚠️  High temperature: {temp}°C ({temp_status})")
            else:
                print(f"✅ Temperature OK: {temp}°C ({temp_status})")

        # Check WiFi signal
        if 'wifi' in status.get('network', {}):
            wifi = status['network']['wifi']
            signal_dbm = wifi['signal_dbm']
            wifi_status = wifi['status']

            if wifi_status in ['weak', 'fair']:
                alerts.append(f"⚠️  Weak WiFi signal: {signal_dbm} dBm ({wifi_status})")
            else:
                print(f"✅ WiFi signal OK: {signal_dbm} dBm ({wifi_status})")

        # Check throttling
        if status.get('throttled', {}).get('has_occurred'):
            alerts.append("⚠️  System throttling detected! Check power supply.")

        # Check disk space
        if status.get('disk'):
            disk_percent = status['disk']['percent']
            if disk_percent > 90:
                alerts.append(f"⚠️  Disk usage high: {disk_percent}%")

        return alerts

    except Exception as e:
        return [f"❌ Error checking system health: {e}"]

def main():
    """Main monitoring loop."""
    print("=== Pi Camera System Monitor ===")
    print("Checking every 30 seconds... (Ctrl+C to stop)\n")

    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Checking...")

        alerts = check_system_health()

        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
            print()

        time.sleep(30)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
```

---

## Camera Control Examples

### Night Mode Configuration

**Bash Script - Switch to Night Mode**

```bash
#!/bin/bash
# switch-to-night-mode.sh
# Configure camera for optimal night vision

API_BASE="http://192.168.1.100:8000"
API_KEY="your-secret-key"

echo "Configuring camera for night mode..."

# Disable auto exposure and set manual values
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$API_BASE/v1/camera/manual_exposure" \
  -d '{"exposure_us": 30000, "gain": 8.0}'

# Set exposure limits for low-light
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$API_BASE/v1/camera/exposure_limits" \
  -d '{"min_exposure_us": 10000, "max_exposure_us": 50000, "max_gain": 16.0}'

# Enable noise reduction
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$API_BASE/v1/camera/noise_reduction" \
  -d '{"mode": "high_quality"}'

# Set AWB preset for IR illumination (NoIR cameras)
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$API_BASE/v1/camera/awb_preset" \
  -d '{"preset": "ir_850nm"}'

echo "✅ Night mode configured!"
```

### Resolution Switcher

**Python Script - Dynamic Resolution Switching**

```python
#!/usr/bin/env python3
"""
Switch camera resolution based on time of day or bandwidth.
"""

import requests
import argparse

API_BASE = "http://192.168.1.100:8000"
API_KEY = "your-secret-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

RESOLUTIONS = {
    "4k": {"width": 3840, "height": 2160},
    "1080p": {"width": 1920, "height": 1080},
    "720p": {"width": 1280, "height": 720},
    "vga": {"width": 640, "height": 480},
}

def set_resolution(preset):
    """Set camera resolution by preset name."""
    if preset not in RESOLUTIONS:
        print(f"❌ Unknown preset: {preset}")
        print(f"Available presets: {', '.join(RESOLUTIONS.keys())}")
        return False

    res = RESOLUTIONS[preset]

    print(f"Setting resolution to {preset} ({res['width']}x{res['height']})...")

    response = requests.post(
        f"{API_BASE}/v1/camera/resolution",
        headers=HEADERS,
        json=res
    )

    if response.status_code == 200:
        print(f"✅ Resolution changed to {preset}")
        return True
    else:
        print(f"❌ Failed: {response.text}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Change camera resolution")
    parser.add_argument("preset", choices=RESOLUTIONS.keys(), help="Resolution preset")
    args = parser.parse_args()

    set_resolution(args.preset)

if __name__ == "__main__":
    main()

# Usage:
# ./set-resolution.py 720p
# ./set-resolution.py 4k
```

---

## Log Monitoring Examples

### Error Alert Script

**Python Script - Monitor Logs for Errors**

```python
#!/usr/bin/env python3
"""
Monitor service logs in real-time and send alerts on errors.
"""

import requests
import sys

API_BASE = "http://192.168.1.100:8000"
API_KEY = "your-secret-key"
HEADERS = {"X-API-Key": API_KEY}

def send_alert(log_line):
    """Send alert (email, Slack, Discord, etc.)."""
    print(f"🚨 ERROR DETECTED: {log_line}")
    # Add your alert logic here:
    # - Send email
    # - Post to Slack webhook
    # - Send push notification
    # - etc.

def monitor_logs():
    """Stream logs and alert on errors."""
    print("=== Log Monitor Started ===")
    print("Monitoring for ERROR logs... (Ctrl+C to stop)\n")

    url = f"{API_BASE}/v1/system/logs/stream"
    params = {"level": "ERROR"}

    try:
        with requests.get(url, headers=HEADERS, params=params, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    # Parse SSE format: "data: <log line>"
                    if line.startswith(b'data: '):
                        log_line = line[6:].decode('utf-8')
                        send_alert(log_line)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    monitor_logs()
```

### Web Dashboard (JavaScript)

**HTML + JavaScript - Live Log Viewer**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera Service - Live Logs</title>
    <style>
        body {
            font-family: monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
        }
        #controls {
            margin-bottom: 20px;
        }
        button {
            padding: 10px 20px;
            margin-right: 10px;
            cursor: pointer;
        }
        #logs {
            border: 1px solid #444;
            padding: 10px;
            height: 600px;
            overflow-y: scroll;
            background: #000;
        }
        .log-line {
            padding: 2px 0;
            border-bottom: 1px solid #222;
        }
        .error { color: #ff6b6b; }
        .warning { color: #feca57; }
        .info { color: #48dbfb; }
    </style>
</head>
<body>
    <h1>Pi Camera Service - Live Logs</h1>

    <div id="controls">
        <button onclick="connectAll()">All Logs</button>
        <button onclick="connectErrors()">Errors Only</button>
        <button onclick="disconnect()">Stop</button>
        <button onclick="clearLogs()">Clear</button>
    </div>

    <div id="logs"></div>

    <script>
        const API_BASE = 'http://192.168.1.100:8000';
        const API_KEY = 'your-secret-key';

        let eventSource = null;

        function connect(level = null) {
            disconnect();

            let url = `${API_BASE}/v1/system/logs/stream`;
            if (level) {
                url += `?level=${level}`;
            }

            // Note: EventSource doesn't support custom headers
            // For auth, you may need to use query params or fetch() with ReadableStream
            eventSource = new EventSource(url);

            eventSource.onmessage = (event) => {
                addLogLine(event.data);
            };

            eventSource.onerror = (error) => {
                console.error('Stream error:', error);
                addLogLine('❌ Connection error. Reconnecting...');
                setTimeout(() => connect(level), 5000);
            };

            addLogLine(`✅ Connected (${level || 'all logs'})`);
        }

        function disconnect() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
                addLogLine('⏸️  Disconnected');
            }
        }

        function addLogLine(text) {
            const logsDiv = document.getElementById('logs');
            const line = document.createElement('div');
            line.className = 'log-line';

            // Colorize by level
            if (text.includes('ERROR')) {
                line.className += ' error';
            } else if (text.includes('WARNING')) {
                line.className += ' warning';
            } else if (text.includes('INFO')) {
                line.className += ' info';
            }

            line.textContent = text;
            logsDiv.appendChild(line);

            // Auto-scroll to bottom
            logsDiv.scrollTop = logsDiv.scrollHeight;

            // Limit to 500 lines
            while (logsDiv.children.length > 500) {
                logsDiv.removeChild(logsDiv.firstChild);
            }
        }

        function clearLogs() {
            document.getElementById('logs').innerHTML = '';
        }

        function connectAll() {
            connect();
        }

        function connectErrors() {
            connect('ERROR');
        }

        // Auto-connect on load
        window.addEventListener('load', () => {
            connectAll();
        });

        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            disconnect();
        });
    </script>
</body>
</html>
```

---

## Complete Use Cases

### Use Case 1: 24/7 Security Camera with Health Monitoring

**Requirements:**
- Monitor system health (temperature, WiFi)
- Alert on errors or system issues
- Auto-adjust camera for day/night
- Log all camera configuration changes

**Solution:**

```python
#!/usr/bin/env python3
"""
24/7 Security Camera Monitoring Script
Combines system health monitoring with log error detection.
"""

import requests
import time
from datetime import datetime
import threading

API_BASE = "http://192.168.1.100:8000"
API_KEY = "your-secret-key"
HEADERS = {"X-API-Key": API_KEY}

class CameraMonitor:
    def __init__(self):
        self.running = True

    def check_health(self):
        """Check system health every minute."""
        while self.running:
            try:
                response = requests.get(f"{API_BASE}/v1/system/status", headers=HEADERS)
                status = response.json()

                # Check temperature
                temp = status['temperature']['cpu_c']
                if temp > 75:
                    self.alert(f"High temperature: {temp}°C")

                # Check WiFi
                if 'wifi' in status.get('network', {}):
                    signal = status['network']['wifi']['signal_dbm']
                    if signal < -75:
                        self.alert(f"Weak WiFi signal: {signal} dBm")

                # Check throttling
                if status.get('throttled', {}).get('currently_throttled'):
                    self.alert("System is throttling! Check power supply.")

            except Exception as e:
                self.alert(f"Health check failed: {e}")

            time.sleep(60)  # Check every minute

    def monitor_errors(self):
        """Stream error logs."""
        url = f"{API_BASE}/v1/system/logs/stream"
        params = {"level": "ERROR"}

        while self.running:
            try:
                with requests.get(url, headers=HEADERS, params=params, stream=True) as response:
                    for line in response.iter_lines():
                        if not self.running:
                            break
                        if line and line.startswith(b'data: '):
                            log_line = line[6:].decode('utf-8')
                            self.alert(f"ERROR in logs: {log_line}")
            except Exception as e:
                print(f"Log monitoring error: {e}")
                time.sleep(5)

    def alert(self, message):
        """Send alert (implement your preferred method)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 🚨 ALERT: {message}")

        # Add your alerting logic:
        # - Send email
        # - Post to Slack
        # - Send SMS
        # - etc.

    def start(self):
        """Start monitoring."""
        print("=== 24/7 Camera Monitor Started ===\n")

        # Start health monitoring thread
        health_thread = threading.Thread(target=self.check_health)
        health_thread.daemon = True
        health_thread.start()

        # Start error log monitoring thread
        error_thread = threading.Thread(target=self.monitor_errors)
        error_thread.daemon = True
        error_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nShutting down monitor...")
            self.running = False

if __name__ == "__main__":
    monitor = CameraMonitor()
    monitor.start()
```

---

### Use Case 2: Timelapse with Auto-Exposure

**Requirements:**
- Capture snapshots every 30 seconds
- Auto-adjust exposure for changing light
- Monitor for errors during capture
- Generate timelapse video from snapshots

**Solution:**

```python
#!/usr/bin/env python3
"""
Timelapse Capture Script
Captures snapshots at regular intervals with auto-exposure.
"""

import requests
import time
import base64
import os
from datetime import datetime
from pathlib import Path

API_BASE = "http://192.168.1.100:8000"
API_KEY = "your-secret-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

OUTPUT_DIR = Path("timelapse_images")
INTERVAL_SECONDS = 30
RESOLUTION = {"width": 1920, "height": 1080}

def capture_snapshot():
    """Capture a snapshot and save to disk."""
    try:
        # Enable auto-exposure for adaptive lighting
        requests.post(
            f"{API_BASE}/v1/camera/auto_exposure",
            headers=HEADERS,
            json={"enabled": True}
        )

        # Wait a moment for auto-exposure to settle
        time.sleep(1)

        # Capture snapshot
        response = requests.post(
            f"{API_BASE}/v1/camera/snapshot",
            headers=HEADERS,
            json={**RESOLUTION, "autofocus_trigger": True}
        )

        if response.status_code == 200:
            data = response.json()
            image_b64 = data['image_base64']

            # Decode and save
            image_data = base64.b64decode(image_b64)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = OUTPUT_DIR / f"frame_{timestamp}.jpg"

            filename.write_bytes(image_data)
            print(f"✅ Captured: {filename}")
            return True
        else:
            print(f"❌ Capture failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main timelapse loop."""
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("=== Timelapse Capture Started ===")
    print(f"Interval: {INTERVAL_SECONDS}s")
    print(f"Resolution: {RESOLUTION['width']}x{RESOLUTION['height']}")
    print(f"Output: {OUTPUT_DIR}")
    print("Press Ctrl+C to stop\n")

    frame_count = 0

    try:
        while True:
            if capture_snapshot():
                frame_count += 1
                print(f"Total frames: {frame_count}\n")

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print(f"\n\n✅ Timelapse complete! Captured {frame_count} frames.")
        print(f"\nCreate video with:")
        print(f"  ffmpeg -framerate 30 -pattern_type glob -i '{OUTPUT_DIR}/frame_*.jpg' -c:v libx264 timelapse.mp4")

if __name__ == "__main__":
    main()
```

---

## Best Practices

### 1. Error Handling

Always handle errors gracefully and implement retries:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    """Create session with automatic retries."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = create_session()
response = session.get(f"{API_BASE}/v1/camera/status", headers=HEADERS)
```

### 2. Resource Cleanup

Always clean up connections, especially for streaming:

```python
try:
    with requests.get(url, stream=True) as response:
        for line in response.iter_lines():
            # Process line
            pass
finally:
    # Cleanup happens automatically with context manager
    pass
```

### 3. Monitoring and Logging

Log all API interactions for debugging:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    response = requests.get(f"{API_BASE}/v1/camera/status", headers=HEADERS)
    logger.info(f"Status check: {response.status_code}")
except Exception as e:
    logger.error(f"API error: {e}", exc_info=True)
```

---

For more examples and use cases, see:
- [README.md](../README.md) - Complete feature documentation
- [API Reference](api-reference.md) - Detailed endpoint documentation
- [Installation Guide](installation.md) - Setup and configuration
