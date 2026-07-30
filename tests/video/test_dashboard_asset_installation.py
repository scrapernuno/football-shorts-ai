from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from video.install_dashboard_assets import (
    DashboardAssetInstallationError,
    install_dashboard_assets,
)
from video.rendering import RenderRequest, RenderResult, RenderScene


def _request() -> RenderRequest:
    return RenderRequest(
        render_id="RENDER-0046C",
        video_id="VID-0046C",
        topic="dashboard asset installation",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path="videos/VID-0046C.mp4",
        thumbnail_path="videos/VID-0046C.jpg",
        subtitles_path="videos/VID-0046C.vtt",
        scenes=(
            RenderScene(
                scene_id="scene_01",
                start_second=0,
                end_second=4,
                screen_text="Opening",
                narration="Opening narration",
                visual_prompt="Vertical football opening",
            ),
        ),
    )


def _materialize(root: Path, request: RenderRequest) -> tuple[str, int]:
    payloads = {
        request.output_path: b"governed-video-0046c",
        request.thumbnail_path: b"governed-thumbnail-0046c",
        request.subtitles_path: b"WEBVTT\n\n00:00:00.000 --> 00:00:04.000\nOpening narration\n",
    }
    for relative, payload in payloads.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    video = root / request.output_path
    return hashlib.sha256(video.read_bytes()).hexdigest(), video.stat().st_size


def _result(request: RenderRequest, checksum: str, size: int) -> RenderResult:
    return RenderResult(
        render_id=request.render_id,
        video_id=request.video_id,
        status="succeeded",
        output_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        checksum_sha256=checksum,
        size_bytes=size,
    )


def test_installs_complete_asset_set_and_emits_receipt(tmp_path: Path) -> None:
    request = _request()
    source = tmp_path / "render-staging"
    dashboard = tmp_path / "dashboard"
    checksum, size = _materialize(source, request)

    receipt = install_dashboard_assets(
        request,
        _result(request, checksum, size),
        source_workspace=source,
        dashboard_workspace=dashboard,
    )

    assert receipt.status == "INSTALLED"
    assert receipt.artifact == "FOOTBALL-SHORTS-AI-0046C"
    assert receipt.checksum_sha256 == checksum
    assert receipt.size_bytes == size
    for relative in (
        request.output_path,
        request.thumbnail_path,
        request.subtitles_path,
    ):
        assert (dashboard / relative).read_bytes() == (source / relative).read_bytes()
    assert not list((dashboard / "videos").glob("*.0046c.tmp"))
    assert not list((dashboard / "videos").glob("*.0046c.bak"))


def test_checksum_mismatch_leaves_existing_dashboard_assets_untouched(tmp_path: Path) -> None:
    request = _request()
    source = tmp_path / "render-staging"
    dashboard = tmp_path / "dashboard"
    _, size = _materialize(source, request)
    existing = dashboard / request.output_path
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_bytes(b"existing-dashboard-video")

    with pytest.raises(DashboardAssetInstallationError, match="checksum"):
        install_dashboard_assets(
            request,
            _result(request, "0" * 64, size),
            source_workspace=source,
            dashboard_workspace=dashboard,
        )

    assert existing.read_bytes() == b"existing-dashboard-video"
    assert not (dashboard / request.thumbnail_path).exists()
    assert not (dashboard / request.subtitles_path).exists()


def test_failed_render_result_is_rejected_before_filesystem_mutation(tmp_path: Path) -> None:
    request = _request()
    source = tmp_path / "render-staging"
    dashboard = tmp_path / "dashboard"
    _materialize(source, request)
    failed = RenderResult(
        render_id=request.render_id,
        video_id=request.video_id,
        status="failed",
        failure_reason="ffmpeg failure",
    )

    with pytest.raises(DashboardAssetInstallationError, match="succeeded"):
        install_dashboard_assets(
            request,
            failed,
            source_workspace=source,
            dashboard_workspace=dashboard,
        )

    assert not dashboard.exists()
