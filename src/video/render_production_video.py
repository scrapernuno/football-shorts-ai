from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from video.ffmpeg_runtime import FfmpegRenderRuntime, FfmpegRuntimeConfig
from video.rendering import RenderRequest, RenderResult, build_render_request


@dataclass(frozen=True, slots=True)
class ProductionRenderPlan:
    artifact: str
    production_package_path: str
    dashboard_workspace: str
    video_id: str
    render_id: str
    output_path: str
    thumbnail_path: str
    subtitles_path: str
    duration_seconds: float
    scene_count: int

    def to_dict(self) -> dict[str, str | float | int]:
        return {
            "artifact": self.artifact,
            "production_package_path": self.production_package_path,
            "dashboard_workspace": self.dashboard_workspace,
            "video_id": self.video_id,
            "render_id": self.render_id,
            "output_path": self.output_path,
            "thumbnail_path": self.thumbnail_path,
            "subtitles_path": self.subtitles_path,
            "duration_seconds": self.duration_seconds,
            "scene_count": self.scene_count,
        }


def load_production_package(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"unable to read production package: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("production package root must be an object")
    if payload.get("production_status") != "completed":
        raise RuntimeError("production package is not completed")
    return payload


def build_plan(
    *,
    production_package_path: Path = Path("output/production_package.json"),
    dashboard_workspace: Path = Path("dashboard"),
    video_id: str = "VID-000001",
    render_id: str = "RENDER-000001",
) -> tuple[ProductionRenderPlan, RenderRequest]:
    package = load_production_package(production_package_path)
    request = build_render_request(
        package,
        render_id=render_id,
        video_id=video_id,
        output_prefix="videos",
        container="mp4",
    )
    plan = ProductionRenderPlan(
        artifact="FOOTBALL-SHORTS-AI-0046B",
        production_package_path=production_package_path.as_posix(),
        dashboard_workspace=dashboard_workspace.as_posix(),
        video_id=request.video_id,
        render_id=request.render_id,
        output_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        duration_seconds=request.duration_seconds,
        scene_count=len(request.scenes),
    )
    return plan, request


def execute_render(
    *,
    production_package_path: Path = Path("output/production_package.json"),
    dashboard_workspace: Path = Path("dashboard"),
    video_id: str = "VID-000001",
    render_id: str = "RENDER-000001",
    runtime_factory: Callable[[FfmpegRuntimeConfig], FfmpegRenderRuntime] = FfmpegRenderRuntime,
) -> tuple[ProductionRenderPlan, RenderResult]:
    plan, request = build_plan(
        production_package_path=production_package_path,
        dashboard_workspace=dashboard_workspace,
        video_id=video_id,
        render_id=render_id,
    )
    runtime = runtime_factory(FfmpegRuntimeConfig(workspace=dashboard_workspace))
    result = runtime.render(request)
    if result.status != "succeeded":
        raise RuntimeError(f"controlled production render failed: {result.failure_reason}")
    return plan, result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute one controlled production video render."
    )
    parser.add_argument("--production-package", default="output/production_package.json")
    parser.add_argument("--dashboard-workspace", default="dashboard")
    parser.add_argument("--video-id", default="VID-000001")
    parser.add_argument("--render-id", default="RENDER-000001")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Materialize MP4, VTT and thumbnail. Without this flag, only emit the governed plan.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    common = {
        "production_package_path": Path(args.production_package),
        "dashboard_workspace": Path(args.dashboard_workspace),
        "video_id": args.video_id,
        "render_id": args.render_id,
    }
    if args.execute:
        plan, result = execute_render(**common)
        payload = {"mode": "EXECUTE", "plan": plan.to_dict(), "result": result.to_dict()}
    else:
        plan, _ = build_plan(**common)
        payload = {"mode": "PLAN", "plan": plan.to_dict()}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
