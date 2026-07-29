from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PRODUCTION_ENGINE = ROOT / "src" / "engines" / "production_engine.py"
VIDEO_CONTRACT = ROOT / "src" / "video" / "contracts.py"
VIDEO_LIBRARY = ROOT / "dashboard" / "data" / "video_library.json"
DASHBOARD_PLAYER = ROOT / "dashboard" / "assets" / "video-library.js"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0045A")
    print("GOVERNED VIDEO RENDERING INTEGRATION READINESS AUDIT")
    print("=" * 72)

    required_files = (
        PRODUCTION_ENGINE,
        VIDEO_CONTRACT,
        VIDEO_LIBRARY,
        DASHBOARD_PLAYER,
    )
    for path in required_files:
        require(path.is_file(), f"required file missing: {path.relative_to(ROOT)}")

    production_source = PRODUCTION_ENGINE.read_text(encoding="utf-8")
    contract_source = VIDEO_CONTRACT.read_text(encoding="utf-8")
    player_source = DASHBOARD_PLAYER.read_text(encoding="utf-8")
    library = json.loads(VIDEO_LIBRARY.read_text(encoding="utf-8"))

    production_markers = (
        '"format": "vertical_9_16"',
        '"resolution": "1080x1920"',
        '"scenes": scenes',
        '"screen_text": screen_text',
        '"narration": narration',
        '"visual_prompt": visual_prompt',
        '"audio_guidance"',
    )
    for marker in production_markers:
        require(marker in production_source, f"production rendering input missing: {marker}")

    contract_markers = (
        "class VideoFileReference",
        "class VideoAsset",
        "checksum_sha256",
        "size_bytes",
        'VideoContainer = Literal["mp4", "webm"]',
    )
    for marker in contract_markers:
        require(marker in contract_source, f"video output contract missing: {marker}")

    require(library.get("schema_version") == "1.0", "unsupported video library schema")
    require(isinstance(library.get("videos"), list), "video library videos must be a list")
    require("video_file" in player_source, "dashboard does not consume rendered video files")

    blockers = {
        "render_runtime": "MISSING",
        "ffmpeg_invocation": "MISSING",
        "scene_asset_materialization": "MISSING",
        "voiceover_materialization": "MISSING",
        "subtitle_vtt_emission": "MISSING",
        "thumbnail_emission": "MISSING",
        "checksum_and_size_capture": "MISSING",
        "atomic_video_library_update": "MISSING",
    }

    print("PRODUCTION_PACKAGE_INPUT=READY")
    print("VIDEO_OUTPUT_CONTRACT=READY")
    print("DASHBOARD_CONSUMER=READY")
    print(f"VIDEO_LIBRARY_COUNT={len(library['videos'])}")
    for name, status in blockers.items():
        print(f"{name.upper()}={status}")
    print("READINESS_STATUS=BLOCKED_PENDING_RENDER_RUNTIME")
    print("STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
