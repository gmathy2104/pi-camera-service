"""
System monitoring module for Raspberry Pi.

Collects system metrics including temperature, CPU, memory, network, and disk usage.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system health metrics on Raspberry Pi."""

    def __init__(self):
        """Initialize system monitor."""
        self._start_time = time.time()
        self._boot_time = psutil.boot_time() if HAS_PSUTIL else None

        # Check if psutil is available
        if not HAS_PSUTIL:
            logger.warning("psutil not available - some system metrics will be unavailable")

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.

        Returns:
            Dictionary with system metrics
        """
        status = {
            "temperature": self._get_temperature(),
            "cpu": self._get_cpu_stats(),
            "memory": self._get_memory_stats(),
            "network": self._get_network_stats(),
            "disk": self._get_disk_stats(),
            "uptime": self._get_uptime(),
            "throttled": self._get_throttle_status(),
        }

        return status

    def _get_temperature(self) -> Optional[Dict[str, Any]]:
        """Get CPU/GPU temperature in Celsius."""
        try:
            # Try thermal zone (most reliable on Pi)
            thermal_file = Path("/sys/class/thermal/thermal_zone0/temp")
            if thermal_file.exists():
                temp_millidegrees = int(thermal_file.read_text().strip())
                temp_c = temp_millidegrees / 1000.0
                return {
                    "cpu_c": round(temp_c, 1),
                    "status": self._get_temp_status(temp_c)
                }
        except Exception as e:
            logger.debug(f"Failed to read temperature from thermal zone: {e}")

        # Fallback: try vcgencmd (Pi-specific)
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                # Output format: temp=52.4'C
                temp_str = result.stdout.strip().split("=")[1].split("'")[0]
                temp_c = float(temp_str)
                return {
                    "cpu_c": round(temp_c, 1),
                    "status": self._get_temp_status(temp_c)
                }
        except Exception as e:
            logger.debug(f"Failed to read temperature from vcgencmd: {e}")

        return None

    def _get_temp_status(self, temp_c: float) -> str:
        """Get temperature status classification."""
        if temp_c < 60:
            return "normal"
        elif temp_c < 70:
            return "warm"
        elif temp_c < 80:
            return "hot"
        else:
            return "critical"

    def _get_cpu_stats(self) -> Optional[Dict[str, Any]]:
        """Get CPU usage and load average."""
        if not HAS_PSUTIL:
            return None

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            load_avg = psutil.getloadavg()
            cpu_count = psutil.cpu_count()

            return {
                "usage_percent": round(cpu_percent, 1),
                "load_average": {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2)
                },
                "cores": cpu_count
            }
        except Exception as e:
            logger.debug(f"Failed to get CPU stats: {e}")
            return None

    def _get_memory_stats(self) -> Optional[Dict[str, Any]]:
        """Get memory usage statistics."""
        if not HAS_PSUTIL:
            return None

        try:
            mem = psutil.virtual_memory()
            return {
                "total_mb": round(mem.total / (1024 * 1024), 1),
                "used_mb": round(mem.used / (1024 * 1024), 1),
                "available_mb": round(mem.available / (1024 * 1024), 1),
                "percent": round(mem.percent, 1)
            }
        except Exception as e:
            logger.debug(f"Failed to get memory stats: {e}")
            return None

    def _get_network_stats(self) -> Optional[Dict[str, Any]]:
        """Get network statistics including WiFi signal if available."""
        if not HAS_PSUTIL:
            return None

        try:
            net_io = psutil.net_io_counters()
            stats = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_received": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_received": net_io.packets_recv,
            }

            # Try to get WiFi signal strength
            wifi_info = self._get_wifi_signal()
            if wifi_info:
                stats["wifi"] = wifi_info

            # Get active interface
            active_interface = self._get_active_interface()
            if active_interface:
                stats["interface"] = active_interface

            return stats
        except Exception as e:
            logger.debug(f"Failed to get network stats: {e}")
            return None

    def _get_wifi_signal(self) -> Optional[Dict[str, Any]]:
        """Get WiFi signal strength and quality."""
        try:
            # Try iwconfig for wlan0
            result = subprocess.run(
                ["iwconfig", "wlan0"],
                capture_output=True,
                text=True,
                timeout=1
            )

            if result.returncode == 0:
                output = result.stdout

                # Parse signal level (e.g., "Signal level=-45 dBm")
                signal_dbm = None
                quality_percent = None

                for line in output.split('\n'):
                    if 'Signal level' in line:
                        try:
                            # Extract dBm value
                            dbm_str = line.split('Signal level=')[1].split(' ')[0]
                            signal_dbm = int(dbm_str)

                            # Convert dBm to quality percentage (approximation)
                            # -30 dBm = 100%, -90 dBm = 0%
                            quality_percent = max(0, min(100, 2 * (signal_dbm + 100)))
                        except (IndexError, ValueError):
                            pass

                if signal_dbm is not None:
                    return {
                        "signal_dbm": signal_dbm,
                        "quality_percent": round(quality_percent, 1),
                        "status": self._get_wifi_status(signal_dbm)
                    }
        except Exception as e:
            logger.debug(f"Failed to get WiFi signal: {e}")

        return None

    def _get_wifi_status(self, signal_dbm: int) -> str:
        """Get WiFi signal status classification."""
        if signal_dbm >= -50:
            return "excellent"
        elif signal_dbm >= -60:
            return "good"
        elif signal_dbm >= -70:
            return "fair"
        else:
            return "weak"

    def _get_active_interface(self) -> Optional[str]:
        """Get the active network interface name."""
        if not HAS_PSUTIL:
            return None

        try:
            # Get default gateway interface
            gateways = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            # Find first interface that is up and has an address
            for interface, addrs in gateways.items():
                if interface in stats and stats[interface].isup:
                    # Skip loopback
                    if interface != 'lo':
                        return interface
        except Exception as e:
            logger.debug(f"Failed to get active interface: {e}")

        return None

    def _get_disk_stats(self) -> Optional[Dict[str, Any]]:
        """Get disk usage statistics for root partition."""
        if not HAS_PSUTIL:
            return None

        try:
            disk = psutil.disk_usage('/')
            return {
                "total_gb": round(disk.total / (1024 ** 3), 1),
                "used_gb": round(disk.used / (1024 ** 3), 1),
                "free_gb": round(disk.free / (1024 ** 3), 1),
                "percent": round(disk.percent, 1)
            }
        except Exception as e:
            logger.debug(f"Failed to get disk stats: {e}")
            return None

    def _get_uptime(self) -> Dict[str, Any]:
        """Get system and service uptime."""
        uptime_data = {
            "service_seconds": round(time.time() - self._start_time, 1)
        }

        if self._boot_time:
            system_uptime = time.time() - self._boot_time
            uptime_data["system_seconds"] = round(system_uptime, 1)
            uptime_data["system_days"] = round(system_uptime / 86400, 1)

        return uptime_data

    def _get_throttle_status(self) -> Optional[Dict[str, Any]]:
        """Get throttling status (Pi-specific)."""
        try:
            result = subprocess.run(
                ["vcgencmd", "get_throttled"],
                capture_output=True,
                text=True,
                timeout=1
            )

            if result.returncode == 0:
                # Output format: throttled=0x0
                throttled_hex = result.stdout.strip().split("=")[1]
                throttled_value = int(throttled_hex, 16)

                return {
                    "currently_throttled": bool(throttled_value & 0x1),
                    "under_voltage_detected": bool(throttled_value & 0x1),
                    "frequency_capped": bool(throttled_value & 0x2),
                    "currently_throttled_temperature": bool(throttled_value & 0x4),
                    "has_occurred": throttled_value != 0,
                    "raw_value": throttled_hex
                }
        except Exception as e:
            logger.debug(f"Failed to get throttle status: {e}")

        return None
