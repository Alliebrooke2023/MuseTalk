"""Regression tests for the whisper-chunk arithmetic in
``musetalk.utils.whisper_feature_utils`` (extracted from
``AudioProcessor.get_whisper_chunk``, which requires torch + a Whisper encoder).
"""

import math

from musetalk.utils.whisper_feature_utils import (
    ChunkParams,
    compute_chunk_params,
    feature_length_per_frame,
    frame_audio_index,
)


class TestFeatureLengthPerFrame:
    def test_default_padding(self):
        # 2 * (2 + 2 + 1) = 10, the documented "T, 10, 5, 384" width
        assert feature_length_per_frame(2, 2) == 10

    def test_zero_padding(self):
        assert feature_length_per_frame(0, 0) == 2

    def test_asymmetric_padding(self):
        assert feature_length_per_frame(1, 3) == 2 * (1 + 3 + 1)


class TestComputeChunkParams:
    def test_returns_named_tuple(self):
        params = compute_chunk_params(librosa_length=16000, fps=25)
        assert isinstance(params, ChunkParams)

    def test_one_second_at_25fps(self):
        # 1s of audio at 16kHz -> 16000 samples
        params = compute_chunk_params(librosa_length=16000, fps=25)
        assert params.whisper_idx_multiplier == 50 / 25  # 2.0
        assert params.num_frames == 25          # floor(1.0 * 25)
        assert params.actual_length == 50       # floor(1.0 * 50)
        assert params.padding_nums == 2         # ceil(2.0)

    def test_fps_coerced_to_int(self):
        # A float fps must behave exactly like its int() truncation.
        assert compute_chunk_params(16000, 25.9) == compute_chunk_params(16000, 25)

    def test_partial_second_uses_floor(self):
        # 1.5s -> num_frames floor(1.5*25)=37, actual_length floor(1.5*50)=75
        params = compute_chunk_params(librosa_length=24000, fps=25)
        assert params.num_frames == 37
        assert params.actual_length == 75

    def test_matches_reference_formula_across_inputs(self):
        sr, audio_fps = 16000, 50
        for librosa_length in (0, 8000, 16000, 33333, 480000):
            for fps in (12, 24, 25, 30):
                params = compute_chunk_params(librosa_length, fps)
                assert params.whisper_idx_multiplier == audio_fps / fps
                assert params.num_frames == math.floor((librosa_length / sr) * fps)
                assert params.actual_length == math.floor((librosa_length / sr) * audio_fps)
                assert params.padding_nums == math.ceil(audio_fps / fps)


class TestFrameAudioIndex:
    def test_floor_behavior(self):
        # multiplier 2.0 -> frame 3 maps to audio index 6
        assert frame_audio_index(3, 2.0) == 6

    def test_non_integer_multiplier_floors(self):
        # 50/30 = 1.666..., frame 2 -> floor(3.333) = 3
        assert frame_audio_index(2, 50 / 30) == 3

    def test_frame_zero_is_zero(self):
        assert frame_audio_index(0, 50 / 24) == 0
