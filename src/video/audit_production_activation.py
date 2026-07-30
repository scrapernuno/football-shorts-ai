from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from video.library_promotion import load_video_library
from video.rendering import build_render_request


@dataclass(frozen=True, slots=True)
class ActivationReadinessReport:
    artifact: str
    status: str
    production_package: str
    render_request: str
    video_library: str
    dashboard_workspace: str
    ffmpeg_binary: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "production_package": self.production_package,
            "render_request": self.render_request,
            "video_library": self.video_library,
            "dashboard_workspace": self.dashboard_workspace,
            "ffmpeg_binary": self.ffmpeg_binary,
            "blockers": list(self.blockers),
        }


def audit(
    *,
    production_package_path: Path = Path("output/production_package.json"),
    video_library_path: Path = Path("dashboard/data/video_library.json"),
    dashboard_workspace: Path = Path("dashboard"),
    ffmpeg_binary: str = "ffmpeg",
) -> ActivationReadinessReport:
    blockers: list[str] = []
    production_status = "PASS"
    request_status = "PASS"
    library_status = "PASS"
    workspace_status = "PASS"
    ffmpeg_status = "PASS"

    production_package: dict | None = None
    if not production_package_path.is_file():
        production_status = "BLOCKED"
        blockers.append(f"missing production package: {production_package_path.as_posix()}")
    else:
        try:
            payload = json.loads(production_package_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("production package root must be an object")
            production_package = payload
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            production_status = "BLOCKED"
            blockers.append(f"invalid production package: {exc}")

    if production_package is not None:
        try:
            build_render_request(
                production_package,
                render_id="RENDER-READINESS-0046A",
                video_id="VID-READINESS-0046A",
            )
        except (TypeError, ValueError, KeyError) as exc:
            request_status = "BLOCKED"
            blockers.append(f"production package cannot build a governed render request: {exc}")
    else:
        request_status = "BLOCKED"

    if not video_library_path.is_file():
        library_status = "BLOCKED"
        blockers.append(f"missing video library: {video_library_path.as_posix()}")
    else:
        try:
            load_video_library(video_library_path)
        except Exception as exc:  # normalized by the governed loader
            library_status = "BLOCKED"
            blockers.append(f"invalid video library: {exc}")

    if not dashboard_workspace.is_dir():
        workspace_status = "BLOCKED"
        blockers.append(f"missing dashboard workspace: {dashboard_workspace.as_posix()}")
    else:
        videos_dir = dashboard_workspace / "videos"
        if videos_dir.exists() and not videos_dir.is_dir():
            workspace_status = "BLOCKED"
            blockers.append(f"dashboard video target is not a directory: {videos_dir.as_posix()}")

    resolved_ffmpeg = shutil.which(ffmpeg_binary)
    if resolved_ffmpeg is None:
        ffmpeg_status = "BLOCKED"
        blockers.append(f"FFmpeg binary is not available: {ffmpeg_binary}")

    return ActivationReadinessReport(
        artifact="FOOTBALL-SHORTS-AI-0046A",
        status="PASS" if not blockers else "BLOCKED",
        production_package=production_status,
        render_request=request_status,
        video_library=library_status,
        dashboard_workspace=workspace_status,
        ffmpeg_binary=ffmpeg_status,
        blockers=tuple(blockers),
    )


def main() -> int:
    report = audit()
    print("=" * 72)
    print(report.artifact)
    print("CONTROLLED PRODUCTION VIDEO RENDERING ACTIVATION READINESS AUDIT")
    print("=" * 72)
    for key, value in report.to_dict().items():
        if key == "blockers":
            print(f"BLOCKER_COUNT={len(value)}")
            for index, blocker in enumerate(value, start=1):
                print(f"BLOCKER_{index}={blocker}")
        else:
            print(f"{key.upper()}={value}")
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
