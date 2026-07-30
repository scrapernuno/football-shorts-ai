from __future__ import annotations

import json
from pathlib import Path

from video.audit_production_activation import audit


def _production_package() -> dict:
    return {
        "topic": "governed activation",
        "format": "vertical_9_16",
        "resolution": "1080x1920",
        "scenes": [
            {
                "scene_id": "scene_01",
                "start_second": 0,
                "end_second": 8,
                "screen_text": "Activation",
                "narration": "Controlled production activation.",
                "visual_prompt": "Vertical football editorial visual",
            }
        ],
    }


def _video_library() -> dict:
    return {
        "schema_version": "1.0",
        "generated_at": "2026-07-30T08:00:00+00:00",
        "videos": [
            {
                "video_id": "VID-000001",
                "title": "Governed football short",
                "topic": "governed activation",
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
                "created_at": "2026-07-30T08:00:00+00:00",
                "updated_at": "2026-07-30T08:00:00+00:00",
                "failure_reason": None,
            }
        ],
    }


def test_readiness_passes_with_complete_local_inputs(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "output"
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    output.mkdir()
    library.parent.mkdir(parents=True)
    (output / "production_package.json").write_text(
        json.dumps(_production_package()), encoding="utf-8"
    )
    library.write_text(json.dumps(_video_library()), encoding="utf-8")
    monkeypatch.setattr("video.audit_production_activation.shutil.which", lambda _: "/usr/bin/ffmpeg")

    report = audit(
        production_package_path=output / "production_package.json",
        video_library_path=library,
        dashboard_workspace=dashboard,
    )

    assert report.status == "PASS"
    assert report.blockers == ()


def test_missing_production_package_is_fail_closed(tmp_path: Path, monkeypatch) -> None:
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    library.parent.mkdir(parents=True)
    library.write_text(json.dumps(_video_library()), encoding="utf-8")
    monkeypatch.setattr("video.audit_production_activation.shutil.which", lambda _: "/usr/bin/ffmpeg")

    report = audit(
        production_package_path=tmp_path / "output" / "production_package.json",
        video_library_path=library,
        dashboard_workspace=dashboard,
    )

    assert report.status == "BLOCKED"
    assert report.production_package == "BLOCKED"
    assert report.render_request == "BLOCKED"
    assert any("missing production package" in blocker for blocker in report.blockers)


def test_missing_ffmpeg_is_reported_without_mutation(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "output"
    dashboard = tmp_path / "dashboard"
    library = dashboard / "data" / "video_library.json"
    output.mkdir()
    library.parent.mkdir(parents=True)
    production_path = output / "production_package.json"
    production_path.write_text(json.dumps(_production_package()), encoding="utf-8")
    original_library = json.dumps(_video_library(), indent=2)
    library.write_text(original_library, encoding="utf-8")
    monkeypatch.setattr("video.audit_production_activation.shutil.which", lambda _: None)

    report = audit(
        production_package_path=production_path,
        video_library_path=library,
        dashboard_workspace=dashboard,
    )

    assert report.status == "BLOCKED"
    assert report.ffmpeg_binary == "BLOCKED"
    assert library.read_text(encoding="utf-8") == original_library
