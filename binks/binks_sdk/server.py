# binks_sdk/server.py
"""Local HTTP server: REST API + MJPEG proxy + the Binks web app (PWA).

Run:  python -m binks_sdk.server --host 0.0.0.0 --port 8099
Then open http://<this-machine-ip>:8099 on your phone (same Wi-Fi).

Everything is served from this process on your LAN. No external calls.
"""
from __future__ import annotations
import argparse
import json
import mimetypes
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .camera import CameraManager
from .store import Store
from .motion import MotionDetector
from .discovery import discover_onvif

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
_BOUNDARY = "binksframe"


class BinksServer:
    def __init__(self, store_path="binks_data.json", web_dir=WEB_DIR, motion=True):
        self.store = Store(store_path)
        self.web_dir = web_dir
        self.mgr = CameraManager(self.store.cameras())
        self._motion_on = motion
        self._stop = threading.Event()

    def reload_cameras(self):
        self.mgr = CameraManager(self.store.cameras())

    def start_motion(self):
        if not self._motion_on:
            return
        for cam in self.mgr.list():
            if cam.kind in ("simulated", "snapshot") and cam.enabled:
                threading.Thread(target=self._watch, args=(cam.id,), daemon=True).start()

    def _watch(self, cam_id):
        det = MotionDetector()
        while not self._stop.is_set():
            cam = self.mgr.get(cam_id)
            if cam is None:
                return
            try:
                ev = det.check(cam.snapshot())
                if ev:
                    self.store.add_event(cam_id, "Motion detected", {"score": ev["score"]})
            except Exception:
                pass
            time.sleep(2.0)

    def serve(self, host="0.0.0.0", port=8099):
        server = _make_server(self, host, port)
        self.start_motion()
        print(f"Binks running at http://{host}:{port}  (open this on your phone)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nBinks stopped.")
        finally:
            self._stop.set()


def _make_server(app: BinksServer, host, port):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        # ---- helpers ----
        def _json(self, obj, code=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        # ---- routing ----
        def do_GET(self):
            p = urlparse(self.path).path
            if p == "/api/cameras":
                return self._json({"cameras": app.mgr.info()})
            if p == "/api/events":
                return self._json({"events": app.store.events()})
            if p.startswith("/api/cameras/") and p.endswith("/snapshot"):
                return self._snapshot(p.split("/")[3])
            if p.startswith("/api/cameras/") and p.endswith("/stream"):
                return self._stream(p.split("/")[3])
            return self._static(p)

        def do_POST(self):
            p = urlparse(self.path).path
            if p == "/api/cameras":
                cam = app.store.add_camera(self._body())
                app.reload_cameras()
                return self._json({"ok": True, "camera": cam})
            if p == "/api/discover":
                return self._json({"devices": discover_onvif(timeout=3.0)})
            if p == "/api/events":
                b = self._body()
                ev = app.store.add_event(b.get("cam", "camera"), b.get("msg", "Event"))
                return self._json({"ok": True, "event": ev})
            return self._json({"error": "not found"}, 404)

        def do_DELETE(self):
            p = urlparse(self.path).path
            if p.startswith("/api/cameras/"):
                app.store.remove_camera(p.split("/")[3])
                app.reload_cameras()
                return self._json({"ok": True})
            return self._json({"error": "not found"}, 404)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        # ---- media ----
        def _snapshot(self, cam_id):
            cam = app.mgr.get(cam_id)
            if not cam:
                return self._json({"error": "no such camera"}, 404)
            try:
                jpg = cam.snapshot()
            except Exception as e:
                return self._json({"error": str(e)}, 502)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpg)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(jpg)

        def _stream(self, cam_id):
            cam = app.mgr.get(cam_id)
            if not cam:
                return self._json({"error": "no such camera"}, 404)
            self.send_response(200)
            self.send_header("Content-Type",
                             f"multipart/x-mixed-replace; boundary={_BOUNDARY}")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                for frame in cam.frames(fps=10):
                    self.wfile.write(
                        f"--{_BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                        f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _static(self, p):
            if p in ("/", ""):
                p = "/index.html"
            path = os.path.normpath(os.path.join(app.web_dir, p.lstrip("/")))
            if not path.startswith(app.web_dir) or not os.path.isfile(path):
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if p.endswith((".webmanifest", "sw.js")):
                self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer((host, port), Handler)


def serve(host="0.0.0.0", port=8099, store_path="binks_data.json", motion=True):
    BinksServer(store_path=store_path, motion=motion).serve(host, port)


def main():
    ap = argparse.ArgumentParser(description="Binks local camera server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--data", default="binks_data.json", help="camera/events store")
    ap.add_argument("--no-motion", action="store_true", help="disable motion watcher")
    a = ap.parse_args()
    serve(host=a.host, port=a.port, store_path=a.data, motion=not a.no_motion)


if __name__ == "__main__":
    main()
