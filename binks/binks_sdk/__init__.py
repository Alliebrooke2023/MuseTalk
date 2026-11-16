# binks_sdk/__init__.py
"""Binks SDK — local-use camera SDK for IP / IoT / webcam sources.

Public API:
    from binks_sdk import Camera, CameraManager, BinksServer, discover_onvif

Nothing in this package talks to the cloud. Everything runs on your LAN.
"""
from .camera import Camera, CameraManager
from .discovery import discover_onvif
from .store import Store
from .server import BinksServer, serve

__version__ = "1.0.0"
__all__ = [
    "Camera",
    "CameraManager",
    "BinksServer",
    "serve",
    "discover_onvif",
    "Store",
    "__version__",
]
