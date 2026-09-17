"""Tests for ``musetalk.utils.audio_utils.ensure_wav`` (the "convert all audio to
WAV 16kHz PCM before processing" fix).

ffmpeg is not required: the one call to ``subprocess.run`` is patched so the pure
path/branch logic can be checked in isolation.
"""

import os
from unittest import mock

from musetalk.utils.audio_utils import ensure_wav


class TestEnsureWav:
    def test_nonexistent_path_returned_unchanged(self):
        # No conversion attempted for a path that does not exist.
        with mock.patch("musetalk.utils.audio_utils.subprocess.run") as run:
            result = ensure_wav("/does/not/exist.mp3")
        assert result == "/does/not/exist.mp3"
        run.assert_not_called()

    def test_non_string_input_returned_unchanged(self):
        with mock.patch("musetalk.utils.audio_utils.subprocess.run") as run:
            assert ensure_wav(None) is None
        run.assert_not_called()

    def test_default_target_path_derivation(self, tmp_path):
        src = tmp_path / "clip.mp3"
        src.write_bytes(b"not really audio")
        with mock.patch("musetalk.utils.audio_utils.subprocess.run") as run:
            result = ensure_wav(str(src))
        assert result == str(tmp_path / "clip_16k.wav")
        run.assert_called_once()

    def test_explicit_target_path_used(self, tmp_path):
        src = tmp_path / "clip.ogg"
        src.write_bytes(b"x")
        target = str(tmp_path / "out.wav")
        with mock.patch("musetalk.utils.audio_utils.subprocess.run") as run:
            result = ensure_wav(str(src), target)
        assert result == target
        run.assert_called_once()

    def test_ffmpeg_command_shape(self, tmp_path):
        src = tmp_path / "clip.m4a"
        src.write_bytes(b"x")
        with mock.patch("musetalk.utils.audio_utils.subprocess.run") as run:
            ensure_wav(str(src))
        cmd = run.call_args.args[0]
        # 16 kHz, mono, PCM signed 16-bit little-endian output via ffmpeg.
        assert cmd[0] == "ffmpeg"
        assert cmd[cmd.index("-ar") + 1] == "16000"
        assert cmd[cmd.index("-ac") + 1] == "1"
        assert cmd[cmd.index("-c:a") + 1] == "pcm_s16le"
        assert run.call_args.kwargs.get("check") is True
