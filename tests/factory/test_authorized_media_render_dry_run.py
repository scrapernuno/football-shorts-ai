from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from factory.authorized_media_render_dry_run import (
    RenderDryRunError,
    build_render_dry_run,
)


def _order(uri: str, sha256: str, *, state: str = "ready") -> dict[str, object]:
    return {
        "order_id": "RENDERORDER-1234567890ABCDEF1234",
        "render_package_id": "RENDERPKG-1234567890ABCDEF1234",
        "order_state": state,
        "execution_requested": True,
        "ffmpeg_binary": "ffmpeg",
        "ffmpeg_args": ["-hide_banner", "-nostdin", "-y", "-i", uri, "artifacts/final/out.mp4"],
        "output_uri": "artifacts/final/out.mp4",
        "expected_assets": [[uri, sha256]],
    }


def test_valid_authorized_media_produces_ready_dry_run(tmp_path):
    media = tmp_path / "media" / "clip.mp4"
    media.parent.mkdir()
    media.write_bytes(b"authorized-video-fixture")
    sha = hashlib.sha256(media.read_bytes()).hexdigest()

    report = build_render_dry_run(order=_order("media/clip.mp4", sha), root=tmp_path)

    assert report.dry_run_state == "ready"
    assert report.blockers == ()
    assert report.execution_allowed is False
    assert report.ffmpeg_execution_enabled is False
    assert report.assets[0].exists is True
    assert report.assets[0].hash_matches is True
    report.validate()


def test_missing_media_is_fail_closed(tmp_path):
    report = build_render_dry_run(order=_order("media/missing.mp4", "a" * 64), root=tmp_path)
    assert report.dry_run_state == "blocked"
    assert "AUTHORIZED_MEDIA_FILE_MISSING" in report.blockers


def test_hash_mismatch_is_fail_closed(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"actual")
    report = build_render_dry_run(order=_order("clip.mp4", "b" * 64), root=tmp_path)
    assert report.dry_run_state == "blocked"
    assert "AUTHORIZED_MEDIA_HASH_MISMATCH" in report.blockers


def test_blocked_order_remains_blocked(tmp_path):
    report = build_render_dry_run(order=_order("clip.mp4", "c" * 64, state="blocked"), root=tmp_path)
    assert "RENDER_ORDER_NOT_READY" in report.blockers


def test_replay_is_deterministic(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"same")
    sha = hashlib.sha256(media.read_bytes()).hexdigest()
    first = build_render_dry_run(order=_order("clip.mp4", sha), root=tmp_path)
    second = build_render_dry_run(order=_order("clip.mp4", sha), root=tmp_path)
    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_evidence_tampering_is_detected(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"same")
    sha = hashlib.sha256(media.read_bytes()).hexdigest()
    report = build_render_dry_run(order=_order("clip.mp4", sha), root=tmp_path)
    with pytest.raises(RenderDryRunError, match="evidence mismatch"):
        replace(report, output_uri="changed.mp4").validate()


def test_operational_capabilities_cannot_be_enabled(tmp_path):
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"same")
    sha = hashlib.sha256(media.read_bytes()).hexdigest()
    report = build_render_dry_run(order=_order("clip.mp4", sha), root=tmp_path)
    with pytest.raises(RenderDryRunError):
        replace(report, ffmpeg_execution_enabled=True).validate()
    with pytest.raises(RenderDryRunError):
        replace(report, execution_allowed=True).validate()
