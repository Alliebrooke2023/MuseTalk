# Binks Cam 🎥

Free, **local-only** camera app + Python SDK for IP / IoT / RTSP / ONVIF / USB
cameras. Brinks-style phone layout, installable as a PWA on iPhone & Android.
No cloud, no account, no subscription — everything runs on your own network.

> Not affiliated with, or connected to, Brinks. "Binks" is an independent,
> self-hosted tool that speaks standard camera protocols (RTSP, ONVIF, MJPEG).

## Run it as a local app (easiest)
- **Windows:** double-click **`Binks.bat`**
- **Mac:** double-click **`Binks.command`**
- **Linux:** `./Binks-Linux.sh`

It installs deps, starts the local server, and opens the app automatically —
in a native window if `pywebview` is installed (`pip install pywebview`), else
your browser. It also prints a `http://<lan-ip>:8099` link to open on your phone.

Or from a terminal:
```bash
pip install -r requirements.txt
python binks.py start      # local app, auto-opens
python binks.py serve      # headless server only
```
Four simulated cameras work instantly — no hardware needed to try it.

## Verify
```bash
python binks.py selftest        # ALL CHECKS PASSED = good install
```

## Add a real camera
```bash
python binks.py add --id cam1 --name "Garage" --kind rtsp \
  --url "rtsp://user:pass@192.168.1.50:554/stream1"
```

See **MANUAL.md** for full instructions: phone install, camera types, the SDK
API, the REST API, and troubleshooting.

## Layout
```
binks/
├── binks.py              CLI entry point
├── selftest.py           hardware-free verification
├── binks_sdk/            the SDK (camera, discovery, motion, store, server)
├── web/                  the phone app (PWA): html/css/js, manifest, icons
├── cameras.example.json  example config
├── requirements.txt
├── run.sh / run.bat
└── MANUAL.md
```

## Requirements
Python 3.9+, Pillow, numpy. ffmpeg on PATH only for RTSP/webcam sources.
