#!/bin/bash
# Install Pi Camera Service as a systemd service

set -e

echo "=== Installing Pi Camera Service ==="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: Do not run this script as root or with sudo"
    echo "The script will ask for sudo password when needed"
    exit 1
fi

# Get the current directory
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Service directory: $SERVICE_DIR"

# Check if service file exists
if [ ! -f "$SERVICE_DIR/pi-camera-service.service" ]; then
    echo "ERROR: pi-camera-service.service file not found"
    exit 1
fi

# Check if venv exists
if [ ! -d "$SERVICE_DIR/venv" ]; then
    echo "ERROR: Virtual environment not found at $SERVICE_DIR/venv"
    echo "Please create it with: python3 -m venv venv"
    exit 1
fi

# Copy service file to systemd directory
echo "Installing systemd service file..."
sudo cp "$SERVICE_DIR/pi-camera-service.service" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service
echo "Enabling pi-camera-service to start on boot..."
sudo systemctl enable pi-camera-service.service

# Ask if user wants to start now
read -p "Do you want to start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting pi-camera-service..."
    sudo systemctl start pi-camera-service.service
    sleep 2
    echo ""
    echo "Service status:"
    sudo systemctl status pi-camera-service.service --no-pager
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Useful commands:"
echo "  Start service:   sudo systemctl start pi-camera-service"
echo "  Stop service:    sudo systemctl stop pi-camera-service"
echo "  Restart service: sudo systemctl restart pi-camera-service"
echo "  View status:     sudo systemctl status pi-camera-service"
echo "  View logs:       sudo journalctl -u pi-camera-service -f"
echo "  Disable service: sudo systemctl disable pi-camera-service"
echo ""
