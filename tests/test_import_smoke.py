"""Import smoke tests for the dependency-light utility modules.

These catch syntax errors and broken imports in the pure helpers without pulling
in torch / mmpose / tensorflow (which are not installed in CI). Modules that
initialize models at import time (e.g. ``preprocessing``) are deliberately not
imported here.
"""

import importlib

import pytest

LIGHTWEIGHT_MODULES = [
    "musetalk.utils.bbox_utils",
    "musetalk.utils.whisper_feature_utils",
    "musetalk.utils.audio_utils",
]


@pytest.mark.parametrize("module_name", LIGHTWEIGHT_MODULES)
def test_module_imports(module_name):
    assert importlib.import_module(module_name) is not None


def test_blending_imports_if_cv2_available():
    # blending needs PIL/numpy/cv2 but no model weights; skip cleanly if the
    # imaging stack is unavailable in the environment.
    pytest.importorskip("cv2")
    pytest.importorskip("PIL")
    module = importlib.import_module("musetalk.utils.blending")
    assert hasattr(module, "get_crop_box")
