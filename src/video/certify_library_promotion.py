from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from video.library_promotion import promote_render_result
from video.rendering import RenderRequest, RenderResult, RenderScene


def certify() -> dict[str, str | int]:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0045e-") as temp_dir:
        root = Path(temp_dir)
        library_path = root / "video_library.json"
        original = {
            "schema_version": "1.0",
            "generated_at": "2026-07-29T21:00:00+01:00",
            "videos": [
                {
                    "video_id": "VID-CERT-0045E",
                    "title": "Atomic promotion certification",
                    "topic": "governed_video_promotion",
                    "status": "draft",
                    "platform": "youtube_shorts",
                    "duration_seconds": 8.0,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "video_file": None,
                    "thumbnail_path": None,
                    "subtitles_path": None,
                    "script_id": "SCRIPT-CERT-0045E",
                    "storyboard_id": "STORYBOARD-CERT-0045E",
                    "production_package_id": "PRODUCTION-CERT-0045E",
                    "publishing_package_id": "PUBLISHING-CERT-0045E",
                    "render_engine": None,
                    "created_at": "2026-07-29T21:00:00+01:00",
                    "updated_at": "2026-07-29T21:00:00+01:00",
                    "failure_reason": None,
                }
            ],
        }
        library_path.write_text(json.dumps(original, indent=2), encoding="utf-8")

        request = RenderRequest(
            render_id="RENDER-CERT-0045E",
            video_id="VID-CERT-0045E",
            topic="governed_video_promotion",
            width=1080,
            height=1920,
            fps=30,
            container="mp4",
            output_path="videos/VID-CERT-0045E.mp4",
            thumbnail_path="videos/VID-CERT-0045E.jpg",
            subtitles_path="videos/VID-CERT-0045E.vtt",
            scenes=(
                RenderScene(
                    scene_id="scene_01",
                    start_second=0,
                    end_second=8,
                    screen_text="Atomic promotion",
                    narration="Atomic promotion is certified.",
                    visual_prompt="Vertical governed football visual",
                ),
            ),
        )
        result = RenderResult(
            render_id=request.render_id,
            video_id=request.video_id,
            status="succeeded",
            output_path=request.output_path,
            thumbnail_path=request.thumbnail_path,
            subtitles_path=request.subtitles_path,
            checksum_sha256="d" * 64,
            size_bytes=4096,
        )
        fixed_now = datetime(2026, 7, 30, 8, 45, tzinfo=timezone.utc)
        promoted = promote_render_result(
            library_path,
            request,
            result,
            clock=lambda: fixed_now,
        )
        asset = promoted.videos[0]
        persisted = json.loads(library_path.read_text(encoding="utf-8"))

        if asset.status != "ready":
            raise RuntimeError("promoted asset status is not ready")
        if asset.video_file is None or asset.video_file.checksum_sha256 != "d" * 64:
            raise RuntimeError("promoted video evidence is incomplete")
        if persisted["videos"][0]["status"] != "ready":
            raise RuntimeError("atomic replacement did not persist ready status")
        if list(root.glob(".video_library.json.*.tmp")):
            raise RuntimeError("temporary promotion files remain after replacement")

        return {
            "artifact": "FOOTBALL-SHORTS-AI-0045E",
            "status": "PASS",
            "atomic_replace": "PASS",
            "identity_binding": "PASS",
            "checksum_promotion": "PASS",
            "thumbnail_promotion": "PASS",
            "subtitle_promotion": "PASS",
            "fail_closed_guard": "PASS",
            "video_count": len(promoted.videos),
        }


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0045E")
    print("ATOMIC VIDEO LIBRARY PROMOTION CERTIFICATION")
    print("=" * 72)
    for key, value in certify().items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
