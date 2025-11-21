#!/bin/bash
# Uninstall Pi Camera Service systemd service

set -e

echo "=== Uninstalling Pi Camera Service ==="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root or with sudo"
    echo "The script will ask for sudo password when needed"
    exit 1
fi

# Check if service exists
if [ ! -f /etc/systemd/system/pi-camera-service.service ]; then
    echo "Service is not installed"
    exit 0
fi

# Stop the service if running
echo "Stopping pi-camera-service..."
sudo systemctl stop pi-camera-service.service 2>/dev/null || true

# Disable the service
echo "Disabling pi-camera-service..."
sudo systemctl disable pi-camera-service.service 2>/dev/null || true

# Remove service file
echo "Removing service file..."
sudo rm /etc/systemd/system/pi-camera-service.service

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo ""
echo "=== Uninstallation Complete ==="
echo "The service has been removed and will not start on boot."
echo ""
