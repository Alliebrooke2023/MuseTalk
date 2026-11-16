# binks_sdk/launch.py
"""Launch Binks as a local desktop app.

Starts the server in a background thread, then opens the app:
  - in a native desktop window if `pywebview` is installed (pip install pywebview)
  - otherwise in your default web browser.

Use:  python binks.py start        (or double-click Binks.bat / Binks.command)
"""
from __future__ import annotations
import socket
import threading
import time
import webbrowser

from .server import BinksServer, _make_server


def _free_port(preferred: int) -> int:
    for p in (preferred, 0):
        try:
            s = socket.socket()
            s.bind(("127.0.0.1", p))
            port = s.getsockname()[1]
            s.close()
            return port
        except OSError:
            continue
    return preferred


def start(port: int = 8099, store_path: str = "binks_data.json",
          motion: bool = True, window: bool = True):
    port = _free_port(port)
    app = BinksServer(store_path=store_path, motion=motion)
    srv = _make_server(app, "0.0.0.0", port)
    app.start_motion()
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{port}"
    lan = _lan_ip()
    print(f"Binks is running.\n  This device: {url}")
    if lan:
        print(f"  On your phone (same Wi-Fi): http://{lan}:{port}")
    time.sleep(0.4)

    if window and _try_window(url):
        srv.shutdown()
        return
    # fallback: open browser and stay alive
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("Close this window (or press Ctrl+C) to stop Binks.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nBinks stopped.")
        srv.shutdown()


def _try_window(url: str) -> bool:
    try:
        import webview  # pywebview, optional
    except Exception:
        return False
    try:
        webview.create_window("Binks Cam", url, width=460, height=860,
                              resizable=True)
        webview.start()  # blocks until the window is closed
        return True
    except Exception:
        return False


def _lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None
