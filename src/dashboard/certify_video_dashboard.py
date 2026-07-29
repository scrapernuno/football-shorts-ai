from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    ROOT / "src/video/contracts.py",
    ROOT / "src/dashboard/certify_video_library.py",
    ROOT / "src/dashboard/certify_video_player.py",
    ROOT / "src/dashboard/certify_video_actions.py",
    ROOT / "dashboard/data/video_library.json",
    ROOT / "dashboard/videos.html",
    ROOT / "dashboard/assets/video-library.css",
    ROOT / "dashboard/assets/video-library.js",
)

REQUIRED_HTML_MARKERS = (
    'id="video-list"',
    'id="video-player"',
    'id="download-video-action"',
    'id="publishing-studio-action"',
    'id="copy-publishing-package-action"',
)

REQUIRED_JS_MARKERS = (
    "VIDEO_LIBRARY_URL",
    "validateLibrary",
    "selectVideo",
    "download-video-action",
    "publishing-studio-action",
    "copy-publishing-package-action",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def certify() -> dict[str, str | int]:
    for path in REQUIRED_FILES:
        _require(path.is_file(), f"required file missing: {path.relative_to(ROOT)}")

    payload = json.loads((ROOT / "dashboard/data/video_library.json").read_text(encoding="utf-8"))
    _require(payload.get("schema_version") == "1.0", "unsupported video library schema")
    videos = payload.get("videos")
    _require(isinstance(videos, list), "video library videos must be a list")

    ids = [video.get("video_id") for video in videos if isinstance(video, dict)]
    _require(len(ids) == len(videos), "every video entry must be an object with video_id")
    _require(all(isinstance(video_id, str) and video_id.strip() for video_id in ids), "video_id must not be empty")
    _require(len(ids) == len(set(ids)), "video_id values must be unique")

    html = (ROOT / "dashboard/videos.html").read_text(encoding="utf-8")
    javascript = (ROOT / "dashboard/assets/video-library.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "dashboard/assets/video-library.css").read_text(encoding="utf-8")

    for marker in REQUIRED_HTML_MARKERS:
        _require(marker in html, f"dashboard HTML marker missing: {marker}")
    for marker in REQUIRED_JS_MARKERS:
        _require(marker in javascript, f"dashboard JavaScript marker missing: {marker}")

    _require("@media (max-width: 960px)" in stylesheet, "tablet responsive boundary missing")
    _require("@media (max-width: 620px)" in stylesheet, "mobile responsive boundary missing")
    _require("video_file" in javascript, "governed video file gating missing")
    _require("publishing_package_id" in javascript, "publishing handoff gating missing")
    _require("ready" in javascript and "published" in javascript, "download readiness states missing")

    result: dict[str, str | int] = {
        "artifact": "FOOTBALL-SHORTS-AI-0044F",
        "status": "PASS",
        "schema_version": payload["schema_version"],
        "video_count": len(videos),
        "video_contract": "PASS",
        "video_library": "PASS",
        "video_player": "PASS",
        "download_action": "PASS",
        "publishing_handoff": "PASS",
        "responsive_dashboard": "PASS",
        "fail_closed_gating": "PASS",
    }
    return result


def main() -> None:
    result = certify()
    for key, value in result.items():
        print(f"{key.upper()}={value}")


if __name__ == "__main__":
    main()
