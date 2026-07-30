from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from video.library_promotion import load_video_library, promote_render_result
from video.render_production_video import build_plan
from video.rendering import RenderRequest, RenderResult


class ProductionPromotionError(RuntimeError):
    """Raised when installed dashboard assets cannot be promoted safely."""


@dataclass(frozen=True, slots=True)
class ProductionPromotionPlan:
    artifact: str
    video_id: str
    render_id: str
    library_path: str
    video_path: str
    thumbnail_path: str
    subtitles_path: str
    checksum_sha256: str
    size_bytes: int
    current_status: str
    target_status: str = "ready"

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def build_promotion_plan(
    *,
    production_package_path: Path = Path("output/production_package.json"),
    dashboard_workspace: Path = Path("dashboard"),
    library_path: Path = Path("dashboard/data/video_library.json"),
    video_id: str = "VID-000001",
    render_id: str = "RENDER-000001",
) -> tuple[ProductionPromotionPlan, RenderRequest, RenderResult]:
    _, request = build_plan(
        production_package_path=production_package_path,
        dashboard_workspace=dashboard_workspace,
        video_id=video_id,
        render_id=render_id,
    )

    dashboard_root = dashboard_workspace.resolve()
    video_path = _confined(dashboard_root, request.output_path)
    thumbnail_path = _confined(dashboard_root, request.thumbnail_path)
    subtitles_path = _confined(dashboard_root, request.subtitles_path)

    for path in (video_path, thumbnail_path, subtitles_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise ProductionPromotionError(f"missing or empty installed dashboard asset: {path}")

    library = load_video_library(library_path)
    matches = [asset for asset in library.videos if asset.video_id == request.video_id]
    if len(matches) != 1:
        raise ProductionPromotionError(
            f"expected exactly one governed library asset for {request.video_id!r}"
        )
    asset = matches[0]
    if asset.status == "published":
        raise ProductionPromotionError("published video assets cannot be promoted or replaced")
    if asset.width != request.width or asset.height != request.height:
        raise ProductionPromotionError("render dimensions do not match governed library asset")
    if abs(asset.duration_seconds - request.duration_seconds) > 0.001:
        raise ProductionPromotionError("render duration does not match governed library asset")

    checksum = _sha256(video_path)
    size_bytes = video_path.stat().st_size
    result = RenderResult(
        render_id=request.render_id,
        video_id=request.video_id,
        status="succeeded",
        output_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        checksum_sha256=checksum,
        size_bytes=size_bytes,
    )
    plan = ProductionPromotionPlan(
        artifact="FOOTBALL-SHORTS-AI-0046D",
        video_id=request.video_id,
        render_id=request.render_id,
        library_path=library_path.as_posix(),
        video_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        checksum_sha256=checksum,
        size_bytes=size_bytes,
        current_status=asset.status,
    )
    return plan, request, result


def execute_promotion(**kwargs) -> tuple[ProductionPromotionPlan, dict]:
    plan, request, result = build_promotion_plan(**kwargs)
    promoted = promote_render_result(
        Path(plan.library_path),
        request,
        result,
        render_engine="ffmpeg",
    )
    asset = next(item for item in promoted.videos if item.video_id == request.video_id)
    if asset.status != "ready" or asset.video_file is None:
        raise ProductionPromotionError("atomic library promotion did not produce a ready asset")
    if asset.video_file.checksum_sha256 != result.checksum_sha256:
        raise ProductionPromotionError("promoted checksum does not match installed video evidence")
    return plan, asset.to_dict()


def _confined(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ProductionPromotionError("dashboard asset path escaped governed workspace")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or execute atomic promotion of installed production video assets."
    )
    parser.add_argument("--production-package", default="output/production_package.json")
    parser.add_argument("--dashboard-workspace", default="dashboard")
    parser.add_argument("--library", default="dashboard/data/video_library.json")
    parser.add_argument("--video-id", default="VID-000001")
    parser.add_argument("--render-id", default="RENDER-000001")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Atomically update the governed video library. Without this flag, only validate and plan.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    common = {
        "production_package_path": Path(args.production_package),
        "dashboard_workspace": Path(args.dashboard_workspace),
        "library_path": Path(args.library),
        "video_id": args.video_id,
        "render_id": args.render_id,
    }
    if args.execute:
        plan, asset = execute_promotion(**common)
        payload = {"mode": "EXECUTE", "plan": plan.to_dict(), "asset": asset}
    else:
        plan, _, _ = build_promotion_plan(**common)
        payload = {"mode": "PLAN", "plan": plan.to_dict()}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
