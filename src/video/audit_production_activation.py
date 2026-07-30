from __future__ import annotations

import argparse
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
    video_id: str
    render_id: str
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
            "video_id": self.video_id,
            "render_id": self.render_id,
            "blockers": list(self.blockers),
        }


def audit(
    *,
    production_package_path: Path = Path("output/production_package.json"),
    video_library_path: Path = Path("dashboard/data/video_library.json"),
    dashboard_workspace: Path = Path("dashboard"),
    ffmpeg_binary: str = "ffmpeg",
    video_id: str = "VID-000001",
    render_id: str = "RENDER-000001",
) -> ActivationReadinessReport:
    blockers: list[str] = []
    production_status = "PASS"
    request_status = "PASS"
    library_status = "PASS"
    workspace_status = "PASS"
    ffmpeg_status = "PASS"

    normalized_video_id = video_id.strip()
    normalized_render_id = render_id.strip()
    if not normalized_video_id:
        request_status = "BLOCKED"
        blockers.append("video_id must not be empty")
    if not normalized_render_id:
        request_status = "BLOCKED"
        blockers.append("render_id must not be empty")

    production_package: dict | None = None
    request = None
    if not production_package_path.is_file():
        production_status = "BLOCKED"
        blockers.append(f"missing production package: {production_package_path.as_posix()}")
    else:
        try:
            payload = json.loads(production_package_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("production package root must be an object")
            if payload.get("production_status") not in {None, "completed"}:
                raise ValueError("production package is not completed")
            production_package = payload
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            production_status = "BLOCKED"
            blockers.append(f"invalid production package: {exc}")

    if production_package is not None and request_status == "PASS":
        try:
            request = build_render_request(
                production_package,
                render_id=normalized_render_id,
                video_id=normalized_video_id,
            )
        except (TypeError, ValueError, KeyError) as exc:
            request_status = "BLOCKED"
            blockers.append(f"production package cannot build a governed render request: {exc}")
    elif production_package is None:
        request_status = "BLOCKED"

    if not video_library_path.is_file():
        library_status = "BLOCKED"
        blockers.append(f"missing video library: {video_library_path.as_posix()}")
    else:
        try:
            library = load_video_library(video_library_path)
            matches = [asset for asset in library.videos if asset.video_id == normalized_video_id]
            if len(matches) != 1:
                raise ValueError(
                    f"expected exactly one governed library asset for {normalized_video_id!r}"
                )
            asset = matches[0]
            if asset.status == "published":
                raise ValueError("published video assets cannot be activated or replaced")
            if request is not None:
                if asset.width != request.width or asset.height != request.height:
                    raise ValueError("library dimensions do not match render request")
                if abs(asset.duration_seconds - request.duration_seconds) > 0.001:
                    raise ValueError("library duration does not match render request")
        except Exception as exc:  # normalized by the governed loader
            library_status = "BLOCKED"
            blockers.append(f"invalid video library activation target: {exc}")

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
        artifact="FOOTBALL-SHORTS-AI-0047B",
        status="PASS" if not blockers else "BLOCKED",
        production_package=production_status,
        render_request=request_status,
        video_library=library_status,
        dashboard_workspace=workspace_status,
        ffmpeg_binary=ffmpeg_status,
        video_id=normalized_video_id,
        render_id=normalized_render_id,
        blockers=tuple(blockers),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit one controlled production video activation target."
    )
    parser.add_argument("--production-package", default="output/production_package.json")
    parser.add_argument("--video-library", default="dashboard/data/video_library.json")
    parser.add_argument("--dashboard-workspace", default="dashboard")
    parser.add_argument("--ffmpeg-binary", default="ffmpeg")
    parser.add_argument("--video-id", default="VID-000001")
    parser.add_argument("--render-id", default="RENDER-000001")
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = audit(
        production_package_path=Path(args.production_package),
        video_library_path=Path(args.video_library),
        dashboard_workspace=Path(args.dashboard_workspace),
        ffmpeg_binary=args.ffmpeg_binary,
        video_id=args.video_id,
        render_id=args.render_id,
    )
    print("=" * 72)
    print(report.artifact)
    print("CONTROLLED PRODUCTION VIDEO ACTIVATION TARGET READINESS AUDIT")
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
