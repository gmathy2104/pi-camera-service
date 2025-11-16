# Pi Camera Service - Systemd Setup

This guide explains how to set up the Pi Camera Service to start automatically on boot using systemd.

## Prerequisites

**Important:** The virtual environment must be created with `--system-site-packages` to access `picamera2`:

```bash
# Create virtual environment with system packages access
python3 -m venv --system-site-packages venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Quick Installation

```bash
# From the project directory
./install-service.sh
```

That's it! The service will now start automatically when the Raspberry Pi boots.

---

## Manual Installation (if you prefer)

If you want to install manually instead of using the script:

```bash
# Copy service file to systemd
sudo cp pi-camera-service.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable pi-camera-service

# Start service now
sudo systemctl start pi-camera-service

# Check status
sudo systemctl status pi-camera-service
```

---

## Service Management Commands

### Start/Stop/Restart

```bash
# Start the service
sudo systemctl start pi-camera-service

# Stop the service
sudo systemctl stop pi-camera-service

# Restart the service
sudo systemctl restart pi-camera-service
```

### Status and Logs

```bash
# Check service status
sudo systemctl status pi-camera-service

# View logs (live tail)
sudo journalctl -u pi-camera-service -f

# View last 100 lines of logs
sudo journalctl -u pi-camera-service -n 100

# View logs since boot
sudo journalctl -u pi-camera-service -b
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot (already done by install script)
sudo systemctl enable pi-camera-service

# Disable auto-start on boot
sudo systemctl disable pi-camera-service

# Check if enabled
sudo systemctl is-enabled pi-camera-service
```

---

## Configuration

### Using Environment Variables

Edit the service file to add environment variables:

```bash
sudo nano /etc/systemd/system/pi-camera-service.service
```

Add environment variables in the `[Service]` section:

```ini
[Service]
# ... existing config ...
Environment="CAMERA_API_KEY=your-secret-key"
Environment="CAMERA_LOG_LEVEL=INFO"
Environment="CAMERA_PORT=8000"
Environment="CAMERA_WIDTH=1920"
Environment="CAMERA_HEIGHT=1080"
```

After editing, reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

### Using .env File (Recommended)

The service will automatically read from `.env` in the project directory:

```bash
# Edit the .env file
nano /home/gmathy/pi-camera-service/.env

# Restart service to apply changes
sudo systemctl restart pi-camera-service
```

---

## Troubleshooting

### Service won't start

```bash
# Check detailed status
sudo systemctl status pi-camera-service

# Check logs for errors
sudo journalctl -u pi-camera-service -n 50
```

### Common Issues and Solutions

#### 1. `ModuleNotFoundError: No module named 'picamera2'`

**Problem:** Virtual environment can't access system-installed picamera2.

**Solution:** Recreate venv with `--system-site-packages`:
```bash
# Backup old venv
mv venv venv.old

# Create new venv with system packages access
python3 -m venv --system-site-packages venv

# Install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Restart service
sudo systemctl restart pi-camera-service
```

#### 2. `FileNotFoundError: No such file or directory: 'ffmpeg'`

**Problem:** systemd service can't find ffmpeg in PATH.

**Solution:** This should already be fixed in the service file. Verify PATH includes `/usr/bin`:
```bash
# Check service file
grep "Environment.*PATH" /etc/systemd/system/pi-camera-service.service

# Should show:
# Environment="PATH=/home/gmathy/pi-camera-service/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
```

If not, update the service file and reload:
```bash
sudo cp pi-camera-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

#### 3. Other Common Issues

- **Virtual environment missing:** Create with `python3 -m venv --system-site-packages venv`
- **Dependencies not installed:** `pip install -r requirements.txt`
- **Camera in use:** Stop other camera services
- **Permissions:** Add user to video group: `sudo usermod -a -G video gmathy`

### Add user to video group (if permission denied)

```bash
sudo usermod -a -G video gmathy
# Log out and back in for changes to take effect
```

### Service starts but camera doesn't work

```bash
# Test camera manually
rpicam-hello --list-cameras

# Check if MediaMTX is running
sudo systemctl status mediamtx

# Check logs for specific error
sudo journalctl -u pi-camera-service -f
```

### Service crashes on boot

```bash
# Check if MediaMTX starts before camera service
# The service file includes: After=mediamtx.service

# If MediaMTX takes time to start, increase RestartSec
sudo nano /etc/systemd/system/pi-camera-service.service
# Change: RestartSec=5  (or higher, like 10)

sudo systemctl daemon-reload
sudo systemctl restart pi-camera-service
```

---

## Uninstallation

To remove the service:

```bash
# Using the uninstall script
./uninstall-service.sh

# Or manually:
sudo systemctl stop pi-camera-service
sudo systemctl disable pi-camera-service
sudo rm /etc/systemd/system/pi-camera-service.service
sudo systemctl daemon-reload
```

---

## Monitoring

### Check if service is running

```bash
# Quick check
sudo systemctl is-active pi-camera-service

# Detailed status
sudo systemctl status pi-camera-service

# Test the API
curl http://localhost:8000/health
```

### Automatic restart on failure

The service is configured to automatically restart if it crashes:
- `Restart=always` - Always restart on failure
- `RestartSec=5` - Wait 5 seconds before restarting

### View restart history

```bash
# See how many times service restarted
sudo systemctl status pi-camera-service | grep -i restart
```

---

## Integration with MediaMTX

The service is configured to start after MediaMTX:

```ini
After=network.target mediamtx.service
Wants=mediamtx.service
```

This ensures:
1. Network is available
2. MediaMTX is started before camera service
3. Both services start automatically on boot

---

## Production Checklist

- [ ] Service installed: `./install-service.sh`
- [ ] Service enabled: `sudo systemctl is-enabled pi-camera-service`
- [ ] Service running: `sudo systemctl is-active pi-camera-service`
- [ ] MediaMTX running: `sudo systemctl is-active mediamtx`
- [ ] Camera accessible: `rpicam-hello --list-cameras`
- [ ] API responding: `curl http://localhost:8000/health`
- [ ] Video streaming: Test RTSP with VLC
- [ ] Logs clean: `sudo journalctl -u pi-camera-service -n 20`
- [ ] Configuration set: Check `.env` file
- [ ] Reboot test: `sudo reboot` and verify both services start

---

## Useful Aliases (Optional)

Add these to your `~/.bashrc` for convenience:

```bash
# Pi Camera Service aliases
alias cam-status='sudo systemctl status pi-camera-service'
alias cam-start='sudo systemctl start pi-camera-service'
alias cam-stop='sudo systemctl stop pi-camera-service'
alias cam-restart='sudo systemctl restart pi-camera-service'
alias cam-logs='sudo journalctl -u pi-camera-service -f'
alias cam-test='curl http://localhost:8000/health'
```

Then run: `source ~/.bashrc`

---

## Support

If you encounter issues:

1. Check logs: `sudo journalctl -u pi-camera-service -f`
2. Check service status: `sudo systemctl status pi-camera-service`
3. Test camera hardware: `rpicam-hello --list-cameras`
4. Verify MediaMTX: `sudo systemctl status mediamtx`
5. Check configuration: `cat .env`
