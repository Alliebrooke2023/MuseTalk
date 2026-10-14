"""Tests for musetalk.utils.preflight.

The point of the module is to be importable and checkable without any weights
on disk, so every test here injects its own `exists` / `which` predicate
rather than touching the filesystem.
"""

import io
import os

import pytest

from musetalk.utils import preflight


def nothing_exists(path):
    return False


def everything_exists(path):
    return True


def only(*present):
    present = set(present)
    return lambda path: path in present


def no_ffmpeg(name, path=None):
    return None


def ffmpeg_on_path(name, path=None):
    return "/usr/bin/ffmpeg" if path is None else None


def ffmpeg_only_in_dir(name, path=None):
    return os.path.join(path, "ffmpeg") if path else None


class TestRequiredWeightPaths:
    def test_v15_includes_unet_and_shared_weights(self):
        paths = preflight.required_weight_paths("v15")
        assert os.path.join("models", "musetalkV15", "unet.pth") in paths
        assert os.path.join("models", "sd-vae", "config.json") in paths
        assert os.path.join("models", "dwpose", "dw-ll_ucoco_384.pth") in paths

    def test_v1_uses_the_v1_checkpoint_name(self):
        paths = preflight.required_weight_paths("v1")
        assert os.path.join("models", "musetalk", "pytorch_model.bin") in paths
        assert os.path.join("models", "musetalkV15", "unet.pth") not in paths

    def test_syncnet_is_training_only(self):
        syncnet = os.path.join("models", "syncnet", "latentsync_syncnet.pt")
        assert syncnet not in preflight.required_weight_paths("v15")
        assert syncnet in preflight.required_weight_paths("v15", include_training=True)

    def test_model_root_is_honoured(self):
        paths = preflight.required_weight_paths("v15", model_root="/opt/w")
        assert all(p.startswith("/opt/w") for p in paths)

    def test_unet_paths_override_the_version_defaults(self):
        paths = preflight.required_weight_paths(
            "v15", unet_paths=("/custom/unet.pth", "/custom/cfg.json")
        )
        assert "/custom/unet.pth" in paths
        assert "/custom/cfg.json" in paths
        assert os.path.join("models", "musetalkV15", "unet.pth") not in paths
        # shared weights are still required
        assert os.path.join("models", "sd-vae", "config.json") in paths

    def test_unknown_version_is_rejected(self):
        with pytest.raises(ValueError, match="unknown version"):
            preflight.required_weight_paths("v2")

    def test_paths_are_unique(self):
        paths = preflight.required_weight_paths("v15", include_training=True)
        assert len(paths) == len(set(paths))


class TestMissingWeights:
    def test_all_missing_when_nothing_exists(self):
        expected = preflight.required_weight_paths("v15")
        assert preflight.missing_weights("v15", exists=nothing_exists) == expected

    def test_none_missing_when_everything_exists(self):
        assert preflight.missing_weights("v15", exists=everything_exists) == []

    def test_reports_only_the_absent_files(self):
        required = preflight.required_weight_paths("v15")
        present = only(*required[1:])
        assert preflight.missing_weights("v15", exists=present) == [required[0]]

    def test_order_follows_required_paths(self):
        required = preflight.required_weight_paths("v15")
        missing = preflight.missing_weights("v15", exists=nothing_exists)
        assert missing == required


class TestFindFfmpeg:
    def test_prefers_path(self):
        assert preflight.find_ffmpeg("/opt/ff", which=ffmpeg_on_path) == "/usr/bin/ffmpeg"

    def test_falls_back_to_extra_dir(self):
        found = preflight.find_ffmpeg("/opt/ff", which=ffmpeg_only_in_dir)
        assert found == os.path.join("/opt/ff", "ffmpeg")

    def test_none_when_nowhere(self):
        assert preflight.find_ffmpeg("/opt/ff", which=no_ffmpeg) is None

    def test_no_extra_dir_does_not_crash(self):
        assert preflight.find_ffmpeg(None, which=ffmpeg_only_in_dir) is None


class TestFfmpegRuns:
    def test_true_when_the_call_succeeds(self):
        assert preflight.ffmpeg_runs(run=lambda *a, **k: None) is True

    def test_false_when_the_call_raises(self):
        def boom(*args, **kwargs):
            raise OSError("not found")

        assert preflight.ffmpeg_runs(run=boom) is False


class TestFormatReport:
    def test_empty_when_all_good(self):
        assert preflight.format_report([], "/usr/bin/ffmpeg") == ""

    def test_lists_each_missing_file_and_the_download_command(self):
        report = preflight.format_report(["models/a.pth", "models/b.bin"], "ffmpeg")
        assert "models/a.pth" in report
        assert "models/b.bin" in report
        assert preflight.DOWNLOAD_HINT in report
        assert "2 pretrained weight file(s)" in report

    def test_mentions_ffmpeg_only_when_absent(self):
        assert "ffmpeg was not found" in preflight.format_report([], None)
        assert "ffmpeg was not found" not in preflight.format_report([], "ffmpeg")

    def test_covers_both_problems_at_once(self):
        report = preflight.format_report(["models/a.pth"], None)
        assert "models/a.pth" in report
        assert "ffmpeg was not found" in report


class TestCheckEnvironment:
    def test_clean_environment_reports_nothing(self):
        missing, ffmpeg, report = preflight.check_environment(
            exists=everything_exists, which=ffmpeg_on_path
        )
        assert missing == []
        assert ffmpeg == "/usr/bin/ffmpeg"
        assert report == ""

    def test_broken_environment_reports_both(self):
        missing, ffmpeg, report = preflight.check_environment(
            exists=nothing_exists, which=no_ffmpeg
        )
        assert missing
        assert ffmpeg is None
        assert preflight.DOWNLOAD_HINT in report


class TestEnforce:
    def test_returns_ffmpeg_and_stays_quiet_when_healthy(self):
        out = io.StringIO()
        found = preflight.enforce(
            exists=everything_exists, which=ffmpeg_on_path, out=out
        )
        assert found == "/usr/bin/ffmpeg"
        assert out.getvalue() == ""

    def test_exits_when_weights_are_missing(self):
        out = io.StringIO()
        with pytest.raises(SystemExit) as excinfo:
            preflight.enforce(exists=nothing_exists, which=ffmpeg_on_path, out=out)
        assert excinfo.value.code == 1
        assert preflight.DOWNLOAD_HINT in out.getvalue()
        assert "--skip_preflight" in out.getvalue()

    def test_missing_ffmpeg_alone_is_not_fatal(self):
        out = io.StringIO()
        found = preflight.enforce(exists=everything_exists, which=no_ffmpeg, out=out)
        assert found is None
        assert "ffmpeg was not found" in out.getvalue()

    def test_skip_bypasses_the_check_entirely(self):
        out = io.StringIO()
        found = preflight.enforce(
            skip=True, exists=nothing_exists, which=ffmpeg_on_path, out=out
        )
        assert found == "/usr/bin/ffmpeg"
        assert out.getvalue() == ""

    def test_unet_paths_are_checked_as_given(self):
        required = set(preflight.required_weight_paths("v15"))
        present = only(*required)  # version defaults present, custom path not
        out = io.StringIO()
        with pytest.raises(SystemExit):
            preflight.enforce(
                unet_paths=("/custom/unet.pth", "/custom/cfg.json"),
                exists=present,
                which=ffmpeg_on_path,
                out=out,
            )
        assert "/custom/unet.pth" in out.getvalue()
