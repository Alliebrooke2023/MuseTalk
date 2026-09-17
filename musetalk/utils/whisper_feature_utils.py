"""Pure index/length arithmetic for chunking Whisper features per video frame.

``AudioProcessor.get_whisper_chunk`` in ``audio_processor.py`` needs torch and a
Whisper encoder, but the arithmetic that decides how many frames there are, how
the audio timeline maps onto them, and how much padding to add is pure. It is
extracted here so it can be unit-tested without torch or model weights, and so
``get_whisper_chunk`` has a single source of truth for these numbers.

Keep this in sync with ``get_whisper_chunk`` when either changes.
"""

import math
from collections import namedtuple

# Whisper encoder emits features at 50 fps; input audio is resampled to 16 kHz.
DEFAULT_SR = 16000
DEFAULT_AUDIO_FPS = 50

ChunkParams = namedtuple(
    "ChunkParams",
    ["whisper_idx_multiplier", "num_frames", "actual_length", "padding_nums"],
)


def feature_length_per_frame(audio_padding_length_left, audio_padding_length_right):
    """Number of whisper feature steps gathered for a single video frame.

    Mirrors::

        2 * (audio_padding_length_left + audio_padding_length_right + 1)
    """
    return 2 * (audio_padding_length_left + audio_padding_length_right + 1)


def compute_chunk_params(librosa_length, fps, sr=DEFAULT_SR, audio_fps=DEFAULT_AUDIO_FPS):
    """Compute the per-clip chunking parameters.

    Args:
        librosa_length: number of audio samples loaded by librosa.
        fps: target video frame rate (coerced to int, as in the original).
        sr: audio sample rate (default 16 kHz).
        audio_fps: whisper feature frame rate (default 50).

    Returns:
        ChunkParams(whisper_idx_multiplier, num_frames, actual_length, padding_nums)
        where:
          * whisper_idx_multiplier = audio_fps / fps
          * num_frames             = floor(librosa_length / sr * fps)
          * actual_length          = floor(librosa_length / sr * audio_fps)
          * padding_nums           = ceil(whisper_idx_multiplier)
    """
    fps = int(fps)
    whisper_idx_multiplier = audio_fps / fps
    num_frames = math.floor((librosa_length / sr) * fps)
    actual_length = math.floor((librosa_length / sr) * audio_fps)
    padding_nums = math.ceil(whisper_idx_multiplier)
    return ChunkParams(whisper_idx_multiplier, num_frames, actual_length, padding_nums)


def frame_audio_index(frame_index, whisper_idx_multiplier):
    """Start index into the whisper feature timeline for a given video frame.

    Mirrors ``math.floor(frame_index * whisper_idx_multiplier)``.
    """
    return math.floor(frame_index * whisper_idx_multiplier)
