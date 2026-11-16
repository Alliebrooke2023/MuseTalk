# Binks Cam — Manual

A free, **local-only** camera app + SDK. It talks to your cameras over your own
Wi-Fi/LAN and serves a phone app (Brinks-style layout) you open in any browser or
install to your home screen. Nothing is sent to the cloud.

Works with: generic IP cameras (RTSP/ONVIF), snapshot-URL cams, MJPEG cams, USB
webcams, and a built-in **simulated** camera so you can try everything with no
hardware.

---

## 1. What's in the box

| Piece | What it does |
|---|---|
| `binks_sdk/` | The Python SDK (import it in your own code) |
| `binks.py` | Command-line tool: serve, discover, add, snapshot, selftest |
| `web/` | The phone app (PWA) — installable on iPhone & Android |
| `selftest.py` | Verifies the install with no camera attached |
| `cameras.example.json` | Example camera config |

---

## 2. Requirements

- Python 3.9+
- `pip install -r requirements.txt` (Pillow + numpy)
- **ffmpeg** on your PATH — only needed for real RTSP cameras and USB webcams.
  Simulated/snapshot/MJPEG cameras do not need it.
  - Windows: download from ffmpeg.org, add the `bin` folder to PATH, or pass
    `--ffmpeg_path` via the `FFMPEG_PATH` environment variable.
  - Mac: `brew install ffmpeg`  • Linux: `sudo apt install ffmpeg`

---

## 3. Quick start (60 seconds)

**Local app — just double-click:**
- Windows: **`Binks.bat`**  •  Mac: **`Binks.command`**  •  Linux: **`Binks-Linux.sh`**

It installs dependencies, starts the local server, and opens the app itself — in a
native desktop window if `pywebview` is installed (`pip install pywebview`),
otherwise your default browser. Four simulated cameras appear immediately. Tap one
to watch the live feed, hit 📸 to save a snapshot. Close the window to stop it.

**Or from a terminal:**
```powershell
cd C:\binks
python -m pip install -r requirements.txt
python binks.py start      # local app: auto-opens the UI, auto-picks a free port
```
```bash
python binks.py serve      # headless server only (no auto-open)
```

Either way it prints a `http://<this-computer-ip>:8099` link — open that on your
**phone on the same Wi-Fi** to use it from the phone.

> Find your computer's IP: Windows `ipconfig` (IPv4 Address) • Mac/Linux `ipconfig getifaddr en0` or `hostname -I`.

---

## 4. Install it on your phone (PWA)

The app is a Progressive Web App — it installs like a native app, no store needed.

- **iPhone (Safari):** open the URL → Share → **Add to Home Screen**.
- **Android (Chrome):** open the URL → menu ⋮ → **Install app** / **Add to Home Screen**.

It gets its own icon and opens full-screen. The UI shell works offline; live
feeds need the Binks server running on your network.

---

## 5. Add your real cameras

### A) From the app (easiest)
Settings tab → **Add a camera** → pick the type, paste the URL, tap **Add camera**.

### B) From the command line
```powershell
python binks.py add --id garage --name "Garage" --kind rtsp ^
  --url "rtsp://user:pass@192.168.1.50:554/stream1"
```
(Use `^` for line breaks in PowerShell, `\` in bash, or put it on one line.)

### Camera types

| `--kind` | `--url` example | Notes |
|---|---|---|
| `rtsp` | `rtsp://user:pass@192.168.1.50:554/stream1` | Most IP cams. Needs ffmpeg. |
| `snapshot` | `http://192.168.1.60/snapshot.jpg` | Returns one JPEG per request. |
| `mjpeg` | `http://192.168.1.61/video.mjpg` | Multipart MJPEG stream. |
| `webcam` | `/dev/video0` (Linux) | USB camera. Needs ffmpeg. |
| `simulated` | — | Built-in test feed, no hardware. |

Credentials: put them in the URL (`rtsp://user:pass@host`) or pass
`--user` / `--password`. They are stored locally in `binks_data.json` and only
ever sent to the camera itself.

### Finding cameras automatically
```powershell
python binks.py discover
```
Sends an ONVIF/WS-Discovery probe on your LAN and prints any cameras that answer,
with their service address. Then add each with the right `rtsp`/`snapshot` URL
(check your camera's manual for its RTSP path). An empty result is normal on some
networks — just add by URL.

> **Finding the RTSP path:** most cameras publish it in their manual or web admin
> page. Common patterns: `/stream1`, `/h264Preview_01_main`, `/live/ch00_0`,
> `/cam/realmonitor?channel=1&subtype=0`.

---

## 6. Using the app

- **Cameras tab** — grid of all cameras with a live thumbnail. Tap any to open the
  full-screen viewer (live MJPEG). 📸 saves a snapshot to your phone's downloads.
- **Events tab** — motion events detected locally by Binks (camera + time + score).
- **Settings tab** — add cameras, scan the LAN, or grant this phone's own camera so
  the viewer can show the phone's live camera too.

Motion detection runs automatically for simulated and snapshot cameras (frame
differencing, CPU only). Disable it with `python binks.py serve --no-motion`.

---

## 7. Use the SDK in your own code

```python
# myscript.py
from binks_sdk import CameraManager

mgr = CameraManager([
    {"id": "door", "name": "Door", "kind": "rtsp",
     "url": "rtsp://user:pass@192.168.1.50:554/stream1"},
])
cam = mgr.get("door")

# one JPEG
open("frame.jpg", "wb").write(cam.snapshot())

# a stream of JPEG frames
for i, jpg in enumerate(cam.frames(limit=30, fps=10)):
    open(f"f{i:03}.jpg", "wb").write(jpg)
```

Motion detection on any JPEG source:
```python
from binks_sdk.motion import MotionDetector
det = MotionDetector(threshold=0.04)
for jpg in cam.frames():
    ev = det.check(jpg)
    if ev:
        print("motion!", ev)
```

Embed the server in your own app:
```python
from binks_sdk import serve
serve(host="0.0.0.0", port=8099)       # blocking
```

### SDK reference (short)
- `CameraManager(list_of_dicts)` → `.get(id)`, `.list()`, `.info()`, `.add(dict)`, `.remove(id)`
- `Camera.snapshot()` → `bytes` (JPEG)
- `Camera.frames(limit=None, fps=10)` → generator of JPEG `bytes`
- `MotionDetector(threshold, cooldown).check(jpeg)` → event `dict` or `None`
- `discover_onvif(timeout=3.0)` → `list[{"xaddr","address"}]`
- `Store(path)` → `.cameras()`, `.add_camera()`, `.events()`, `.add_event()`
- `serve(host, port, store_path, motion)` → runs REST API + web app

### REST API (served by `binks.py serve`)
| Method | Path | Result |
|---|---|---|
| GET | `/api/cameras` | list cameras |
| POST | `/api/cameras` | add camera (JSON body) |
| DELETE | `/api/cameras/{id}` | remove camera |
| GET | `/api/cameras/{id}/snapshot` | one JPEG |
| GET | `/api/cameras/{id}/stream` | MJPEG stream |
| GET | `/api/events` | motion events |
| POST | `/api/discover` | ONVIF scan |

---

## 8. Verify / troubleshoot

```powershell
python binks.py selftest
```
Runs all internal checks with no hardware. If it prints **ALL CHECKS PASSED**,
the install is good and the problem is network/camera config.

- **Phone can't load the page:** phone and computer must be on the same Wi-Fi;
  allow the port through the computer's firewall (Windows will prompt on first run).
- **Real camera is black / errors:** confirm ffmpeg is installed (`ffmpeg -version`);
  test the RTSP URL in VLC first (Media → Open Network Stream).
- **Snapshot won't save on iPhone:** Safari downloads go to Files app → Downloads.
- **Port already in use:** `python binks.py serve --port 9000`.

---

## 9. Privacy

Binks never contacts any server but your own cameras. Camera config and events
live in `binks_data.json` next to the app. Delete it to reset. Snapshots stay on
the device that took them.

---

## 10. Native phone app (Android / iOS)

`mobile/` is a native app project with this same UI bundled inside. It talks to
the Binks server on your computer over Wi-Fi. See **mobile/README.md** for how to
get the Android APK (cloud-built, nothing to install) or build for iPhone on a Mac.
After installing: Settings → Binks server → `http://<computer-ip>:8099` → Connect.
