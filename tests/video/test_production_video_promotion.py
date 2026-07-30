from __future__ import annotations

import json
from pathlib import Path

import pytest

from video.promote_production_video import (
    ProductionPromotionError,
    build_promotion_plan,
    execute_promotion,
)


def _production_package(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "topic": "football short demo",
                "production_status": "completed",
                "scenes": [
                    {
                        "scene_id": "scene_01",
                        "start_second": 0,
                        "end_second": 8,
                        "screen_text": "Opening",
                        "narration": "Opening narration",
                        "visual_prompt": "Vertical football scene",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _library(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "generated_at": "2026-07-30T00:00:00+00:00",
                "videos": [
                    {
                        "video_id": "VID-000001",
                        "title": "Test video",
                        "topic": "football short demo",
                        "status": "draft",
                        "platform": "youtube_shorts",
                        "duration_seconds": 8.0,
                        "width": 1080,
                        "height": 1920,
                        "orientation": "vertical",
                        "video_file": None,
                        "thumbnail_path": None,
                        "subtitles_path": None,
                        "script_id": "SCRIPT-000001",
                        "storyboard_id": "STORYBOARD-000001",
                        "production_package_id": "PRODUCTION-000001",
                        "publishing_package_id": "PUBLISHING-000001",
                        "render_engine": None,
                        "created_at": "2026-07-30T00:00:00+00:00",
                        "updated_at": "2026-07-30T00:00:00+00:00",
                        "failure_reason": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _assets(dashboard: Path) -> None:
    videos = dashboard / "videos"
    videos.mkdir(parents=True, exist_ok=True)
    (videos / "VID-000001.mp4").write_bytes(b"governed-video")
    (videos / "VID-000001.jpg").write_bytes(b"thumbnail")
    (videos / "VID-000001.vtt").write_text("WEBVTT\n", encoding="utf-8")


def test_plan_validates_assets_without_mutating_library(tmp_path: Path) -> None:
    package = tmp_path / "output" / "production_package.json"
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    _production_package(package)
    _library(library)
    _assets(dashboard)
    before = library.read_bytes()

    plan, request, result = build_promotion_plan(
        production_package_path=package,
        dashboard_workspace=dashboard,
        library_path=library,
    )

    assert plan.artifact == "FOOTBALL-SHORTS-AI-0046D"
    assert plan.current_status == "draft"
    assert plan.target_status == "ready"
    assert request.video_id == "VID-000001"
    assert result.status == "succeeded"
    assert library.read_bytes() == before


def test_execute_atomically_promotes_real_library_entry(tmp_path: Path) -> None:
    package = tmp_path / "output" / "production_package.json"
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    _production_package(package)
    _library(library)
    _assets(dashboard)

    plan, asset = execute_promotion(
        production_package_path=package,
        dashboard_workspace=dashboard,
        library_path=library,
    )

    persisted = json.loads(library.read_text(encoding="utf-8"))["videos"][0]
    assert plan.video_id == "VID-000001"
    assert asset["status"] == "ready"
    assert persisted["status"] == "ready"
    assert persisted["video_file"]["path"] == "videos/VID-000001.mp4"
    assert persisted["thumbnail_path"] == "videos/VID-000001.jpg"
    assert persisted["subtitles_path"] == "videos/VID-000001.vtt"
    assert persisted["render_engine"] == "ffmpeg"
    assert not list(library.parent.glob(".*.tmp"))


def test_plan_fails_closed_when_installed_asset_is_missing(tmp_path: Path) -> None:
    package = tmp_path / "output" / "production_package.json"
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    _production_package(package)
    _library(library)
    _assets(dashboard)
    (dashboard / "videos" / "VID-000001.jpg").unlink()

    with pytest.raises(ProductionPromotionError, match="missing or empty"):
        build_promotion_plan(
            production_package_path=package,
            dashboard_workspace=dashboard,
            library_path=library,
        )
