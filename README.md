# Pi Camera Service

Micro-service FastAPI pour contrôler une caméra Raspberry Pi (Picamera2/libcamera)
et streamer un flux H.264 vers MediaMTX (RTSP).

## Installation

```bash
sudo apt install python3-venv python3-picamera2 libcamera-apps ffmpeg git
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
