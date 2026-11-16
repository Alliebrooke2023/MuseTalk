# binks_sdk/camera.py
"""Camera abstraction. One Camera object per physical/virtual source.

Supported source kinds (field "kind" in the camera dict):
    simulated   - a synthetic feed, no hardware needed (for testing / demo)
    snapshot    - an HTTP URL that returns a single JPEG per GET
    mjpeg       - an HTTP multipart/x-mixed-replace MJPEG stream URL
    rtsp        - an rtsp:// URL (decoded with ffmpeg)
    webcam      - a local device index (uses ffmpeg v4l2, Linux only)

A Camera gives you two things:
    .snapshot()     -> bytes (a single JPEG)
    .frames()       -> generator of JPEG bytes (MJPEG frames)

Credentials go in the URL (rtsp://user:pass@host) or user/password fields;
they are kept locally and only ever sent to the camera itself.
"""
from __future__ import annotations
import io
import os
import time
import shutil
import threading
import subprocess
import urllib.request
from datetime import datetime

FFMPEG = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg"
_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"


def _auth_opener(user, password):
    if not user:
        return urllib.request.build_opener()
    mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, "", user, password or "")
    handler = urllib.request.HTTPBasicAuthHandler(mgr)
    return urllib.request.build_opener(handler)


class Camera:
    def __init__(self, cam: dict):
        self.id = str(cam.get("id") or cam.get("name") or "cam")
        self.name = cam.get("name", self.id)
        self.loc = cam.get("loc", "")
        self.kind = cam.get("kind", "simulated")
        self.url = cam.get("url", "")
        self.user = cam.get("user", "")
        self.password = cam.get("password", "")
        self.enabled = cam.get("enabled", True)
        self._raw = cam
        self._lock = threading.Lock()

    def info(self) -> dict:
        return {
            "id": self.id, "name": self.name, "loc": self.loc,
            "kind": self.kind, "enabled": self.enabled,
            "live": self.kind != "simulated",
        }

    # ---- snapshot ---------------------------------------------------------
    def snapshot(self) -> bytes:
        if self.kind == "simulated":
            return _sim_jpeg(self.name, self.loc)
        if self.kind == "snapshot":
            return _http_bytes(self.url, self.user, self.password)
        if self.kind == "mjpeg":
            for frame in self.frames(limit=1):
                return frame
            raise RuntimeError("no frame from mjpeg source")
        if self.kind in ("rtsp", "webcam"):
            return self._ffmpeg_snapshot()
        raise ValueError(f"unknown camera kind: {self.kind}")

    def _ffmpeg_snapshot(self) -> bytes:
        src = self.url
        cmd = [FFMPEG, "-nostdin", "-loglevel", "error"]
        if self.kind == "rtsp":
            cmd += ["-rtsp_transport", "tcp", "-i", src]
        else:  # webcam
            cmd += ["-f", "v4l2", "-i", src or "/dev/video0"]
        cmd += ["-frames:v", "1", "-f", "image2", "-c:v", "mjpeg", "-"]
        out = subprocess.run(cmd, capture_output=True, timeout=20).stdout
        if not out.startswith(_JPEG_SOI):
            raise RuntimeError(f"ffmpeg returned no JPEG for {self.id}")
        return out

    # ---- streaming --------------------------------------------------------
    def frames(self, limit: int | None = None, fps: int = 10):
        if self.kind == "simulated":
            yield from _sim_frames(self.name, self.loc, limit, fps)
        elif self.kind == "snapshot":
            yield from _snapshot_poll(self, limit, fps)
        elif self.kind == "mjpeg":
            yield from _mjpeg_stream(self.url, self.user, self.password, limit)
        elif self.kind in ("rtsp", "webcam"):
            yield from self._ffmpeg_frames(limit, fps)
        else:
            raise ValueError(f"unknown camera kind: {self.kind}")

    def _ffmpeg_frames(self, limit, fps):
        cmd = [FFMPEG, "-nostdin", "-loglevel", "error"]
        if self.kind == "rtsp":
            cmd += ["-rtsp_transport", "tcp", "-i", self.url]
        else:
            cmd += ["-f", "v4l2", "-i", self.url or "/dev/video0"]
        cmd += ["-r", str(fps), "-f", "mjpeg", "-c:v", "mjpeg", "-q:v", "6", "-"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            yield from _split_mjpeg(proc.stdout, limit)
        finally:
            proc.kill()


# ---- source helpers -------------------------------------------------------
def _http_bytes(url, user, password, timeout=15) -> bytes:
    opener = _auth_opener(user, password)
    with opener.open(url, timeout=timeout) as r:
        return r.read()


def _snapshot_poll(cam: Camera, limit, fps):
    n, delay = 0, 1.0 / max(1, fps)
    while limit is None or n < limit:
        try:
            yield cam.snapshot()
        except Exception:
            yield _sim_jpeg(cam.name, "offline")
        n += 1
        time.sleep(delay)


def _mjpeg_stream(url, user, password, limit):
    opener = _auth_opener(user, password)
    r = opener.open(url, timeout=15)
    yield from _split_mjpeg(r, limit)


def _split_mjpeg(stream, limit):
    """Pull concatenated JPEGs out of a byte stream by SOI/EOI markers."""
    buf = b""
    n = 0
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        buf += chunk
        while True:
            i = buf.find(_JPEG_SOI)
            j = buf.find(_JPEG_EOI, i + 2) if i != -1 else -1
            if i == -1 or j == -1:
                break
            yield buf[i:j + 2]
            buf = buf[j + 2:]
            n += 1
            if limit is not None and n >= limit:
                return


# ---- simulated source (Pillow) -------------------------------------------
def _sim_jpeg(name, loc) -> bytes:
    from PIL import Image, ImageDraw
    t = time.time()
    w, h = 640, 400
    bg = (12, 19, 29)
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    # moving "subject" so motion detection has something to see
    x = int((w - 80) * (0.5 + 0.45 * __import__("math").sin(t)))
    y = int(h * 0.55)
    d.rectangle([20, 20, w - 20, h - 20], outline=(44, 64, 84), width=2)
    d.ellipse([x, y, x + 70, y + 110], fill=(100, 215, 200))
    d.rectangle([x - 15, y + 60, x + 85, y + 180], fill=(100, 215, 200))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d.text((34, 30), f"BINKS  {name}", fill=(237, 244, 252))
    d.text((34, 46), loc or "simulated feed", fill=(157, 179, 197))
    d.text((34, h - 40), stamp, fill=(255, 209, 102))
    d.ellipse([w - 48, 30, w - 36, 42], fill=(192, 57, 43))
    d.text((w - 110, 30), "LIVE", fill=(255, 163, 163))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=70)
    return out.getvalue()


def _sim_frames(name, loc, limit, fps):
    n, delay = 0, 1.0 / max(1, fps)
    while limit is None or n < limit:
        yield _sim_jpeg(name, loc)
        n += 1
        time.sleep(delay)


# ---- manager --------------------------------------------------------------
class CameraManager:
    def __init__(self, cams: list[dict] | None = None):
        self._cams: dict[str, Camera] = {}
        for c in (cams or []):
            self.add(c)

    def add(self, cam: dict) -> Camera:
        c = Camera(cam)
        self._cams[c.id] = c
        return c

    def remove(self, cam_id: str):
        self._cams.pop(cam_id, None)

    def get(self, cam_id: str) -> Camera | None:
        return self._cams.get(cam_id)

    def list(self) -> list[Camera]:
        return list(self._cams.values())

    def info(self) -> list[dict]:
        return [c.info() for c in self._cams.values()]
