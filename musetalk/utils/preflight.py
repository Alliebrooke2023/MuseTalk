"""Startup checks for the two things every fresh clone is missing: the
pretrained weights under ./models and a usable ffmpeg.

Weights are not checked into the repo (see download_weights.sh), so without
them every entrypoint dies deep inside model construction with a traceback
that does not name the missing file. These checks run before any model is
built and name the exact paths plus the command that fetches them.

Path computation is kept separate from the filesystem lookup so the logic is
testable without any weights on disk: required_weight_paths() is pure, and
missing_weights() takes the existence predicate as an argument.
"""

import os
import shutil
import subprocess
import sys

DOWNLOAD_HINT = "sh download_weights.sh   (Windows: download_weights.bat)"

# Weights every inference run touches, regardless of version.
_COMMON_WEIGHTS = (
    os.path.join("sd-vae", "config.json"),
    os.path.join("sd-vae", "diffusion_pytorch_model.bin"),
    os.path.join("whisper", "config.json"),
    os.path.join("whisper", "pytorch_model.bin"),
    os.path.join("whisper", "preprocessor_config.json"),
    # DWPose: musetalk.utils.preprocessing builds this at import time.
    os.path.join("dwpose", "dw-ll_ucoco_384.pth"),
    # BiSeNet face parsing, used to build the blending masks.
    os.path.join("face-parse-bisent", "79999_iter.pth"),
    os.path.join("face-parse-bisent", "resnet18-5c106cde.pth"),
)

# UNet weights differ per version; see --version in the inference scripts.
_UNET_WEIGHTS = {
    "v1": (
        os.path.join("musetalk", "pytorch_model.bin"),
        os.path.join("musetalk", "musetalk.json"),
    ),
    "v15": (
        os.path.join("musetalkV15", "unet.pth"),
        os.path.join("musetalkV15", "musetalk.json"),
    ),
}

# Only the training pipeline loads SyncNet.
_TRAINING_WEIGHTS = (os.path.join("syncnet", "latentsync_syncnet.pt"),)


def required_weight_paths(
    version="v15", model_root="models", include_training=False, unet_paths=None
):
    """Return the weight paths a run needs, rooted at model_root.

    unet_paths overrides the version's default UNet weights, for callers that
    accept --unet_model_path / --unet_config: those are the files actually
    loaded, so they are what should be checked.

    Pure: computes paths only, touches no filesystem.
    """
    if version not in _UNET_WEIGHTS:
        raise ValueError(
            f"unknown version {version!r}, expected one of {sorted(_UNET_WEIGHTS)}"
        )
    relative = _COMMON_WEIGHTS
    if include_training:
        relative += _TRAINING_WEIGHTS
    paths = [os.path.join(model_root, rel) for rel in relative]
    if unet_paths is None:
        unet = [os.path.join(model_root, rel) for rel in _UNET_WEIGHTS[version]]
    else:
        unet = list(unet_paths)
    return unet + paths


def missing_weights(
    version="v15",
    model_root="models",
    include_training=False,
    unet_paths=None,
    exists=os.path.exists,
):
    """Return the required weight paths that are not present, in order."""
    return [
        path
        for path in required_weight_paths(
            version, model_root, include_training, unet_paths
        )
        if not exists(path)
    ]


def find_ffmpeg(extra_dir=None, which=shutil.which):
    """Return a usable ffmpeg path, preferring PATH, else extra_dir.

    Returns None when neither has one.
    """
    found = which("ffmpeg")
    if found:
        return found
    if extra_dir:
        candidate = which("ffmpeg", path=extra_dir)
        if candidate:
            return candidate
    return None


def ffmpeg_runs(executable="ffmpeg", run=subprocess.run):
    """True when the executable answers `-version`.

    Separate from find_ffmpeg: a binary can be on PATH yet fail to run (wrong
    architecture, missing shared libraries).
    """
    try:
        run([executable, "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def format_report(missing, ffmpeg, model_root="models"):
    """Render the human-facing report. Empty string means nothing to say."""
    lines = []
    if missing:
        lines.append(
            f"Missing {len(missing)} pretrained weight file(s) under ./{model_root}:"
        )
        lines.extend(f"  - {path}" for path in missing)
        lines.append(f"Download them with:\n  {DOWNLOAD_HINT}")
    if not ffmpeg:
        if missing:
            lines.append("")
        lines.append(
            "ffmpeg was not found on PATH. Install it, or pass --ffmpeg_path "
            "<dir containing ffmpeg> / set FFMPEG_PATH."
        )
    return "\n".join(lines)


def check_environment(
    version="v15",
    model_root="models",
    include_training=False,
    unet_paths=None,
    ffmpeg_dir=None,
    exists=os.path.exists,
    which=shutil.which,
):
    """Check weights and ffmpeg.

    Returns (missing_weight_paths, ffmpeg_path_or_None, report_text).
    """
    missing = missing_weights(
        version, model_root, include_training, unet_paths, exists=exists
    )
    ffmpeg = find_ffmpeg(ffmpeg_dir, which=which)
    return missing, ffmpeg, format_report(missing, ffmpeg, model_root)


def enforce(
    version="v15",
    model_root="models",
    include_training=False,
    unet_paths=None,
    ffmpeg_dir=None,
    skip=False,
    exists=os.path.exists,
    which=shutil.which,
    out=None,
):
    """Report on the environment, and stop the run if weights are missing.

    Missing weights are fatal: every code path downstream needs them, and
    failing here names the files instead of crashing inside model
    construction. A missing ffmpeg is only a warning, matching the existing
    behaviour of the entrypoints -- some setups resolve it later.

    Returns the ffmpeg path that was found, or None.
    """
    stream = out if out is not None else sys.stderr
    if skip:
        return find_ffmpeg(ffmpeg_dir, which=which)

    missing, ffmpeg, report = check_environment(
        version=version,
        model_root=model_root,
        include_training=include_training,
        unet_paths=unet_paths,
        ffmpeg_dir=ffmpeg_dir,
        exists=exists,
        which=which,
    )
    if report:
        print(report, file=stream)
    if missing:
        print(
            "\nAborting before model load. Re-run with --skip_preflight to "
            "bypass this check.",
            file=stream,
        )
        raise SystemExit(1)
    return ffmpeg
