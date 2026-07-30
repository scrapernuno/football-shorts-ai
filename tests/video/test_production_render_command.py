from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Sequence

from video.ffmpeg_runtime import FfmpegRenderRuntime
from video.render_production_video import build_plan, execute_render


def _package() -> dict:
    return {
        "topic": "football short demo",
        "format": "vertical_9_16",
        "resolution": "1080x1920",
        "production_status": "completed",
        "scenes": [
            {
                "scene_id": "scene_01",
                "start_second": 0,
                "end_second": 4,
                "screen_text": "Opening",
                "narration": "Opening narration.",
                "visual_prompt": "Vertical football opening",
            },
            {
                "scene_id": "scene_02",
                "start_second": 4,
                "end_second": 8,
                "screen_text": "Finish",
                "narration": "Finish narration.",
                "visual_prompt": "Vertical football finish",
            },
        ],
    }


def _write_package(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_package()), encoding="utf-8")


def _runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    output = Path(command[-1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"governed-render-output")
    return subprocess.CompletedProcess(list(command), 0, "", "")


def test_plan_is_deterministic_and_does_not_write_assets(tmp_path: Path) -> None:
    package = tmp_path / "output" / "production_package.json"
    dashboard = tmp_path / "dashboard"
    _write_package(package)

    first, first_request = build_plan(
        production_package_path=package,
        dashboard_workspace=dashboard,
        video_id="VID-0046B",
        render_id="RENDER-0046B",
    )
    second, second_request = build_plan(
        production_package_path=package,
        dashboard_workspace=dashboard,
        video_id="VID-0046B",
        render_id="RENDER-0046B",
    )

    assert first == second
    assert first_request == second_request
    assert first.output_path == "videos/VID-0046B.mp4"
    assert first.thumbnail_path == "videos/VID-0046B.jpg"
    assert first.subtitles_path == "videos/VID-0046B.vtt"
    assert first.scene_count == 2
    assert not dashboard.exists()


def test_execute_materializes_all_governed_outputs(tmp_path: Path) -> None:
    package = tmp_path / "output" / "production_package.json"
    dashboard = tmp_path / "dashboard"
    _write_package(package)

    def factory(config):
        return FfmpegRenderRuntime(config, runner=_runner)

    plan, result = execute_render(
        production_package_path=package,
        dashboard_workspace=dashboard,
        video_id="VID-0046B",
        render_id="RENDER-0046B",
        runtime_factory=factory,
    )

    assert result.status == "succeeded"
    assert result.video_id == plan.video_id
    assert result.render_id == plan.render_id
    assert result.checksum_sha256 is not None
    assert result.size_bytes and result.size_bytes > 0
    assert (dashboard / plan.output_path).is_file()
    assert (dashboard / plan.thumbnail_path).is_file()
    assert (dashboard / plan.subtitles_path).is_file()


def test_incomplete_production_package_fails_closed(tmp_path: Path) -> None:
    package = tmp_path / "production_package.json"
    package.write_text(json.dumps({"topic": "demo", "production_status": "draft"}), encoding="utf-8")

    try:
        build_plan(production_package_path=package)
    except RuntimeError as exc:
        assert "not completed" in str(exc)
    else:
        raise AssertionError("incomplete production package was accepted")
