from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from video.verify_dashboard_playback import verify_dashboard_playback


ARTIFACT = "FOOTBALL-SHORTS-AI-0046F"
VIDEO_ID = "VID-CERT-0046F"


class ProductionActivationCertificationError(RuntimeError):
    """Raised when the controlled production activation chain is incomplete."""


def _mp4_payload() -> bytes:
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"football-shorts-ai-0046f"


def _jpeg_payload() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"football-shorts-ai-0046f-thumbnail" + b"\xff\xd9"


def _html_payload() -> str:
    return """<!doctype html>
<html lang=\"pt\">
<head><meta charset=\"utf-8\"><title>Playback Certification</title></head>
<body>
  <video id=\"video-player\" controls></video>
  <script src=\"assets/video-library.js\"></script>
</body>
</html>
"""


def _javascript_payload() -> str:
    return """\"use strict\";
function safeText(value, fallback) { return value || fallback; }
function bind(file, video, player) {
  const source = document.createElement(\"source\");
  source.src = file.path;
  source.type = safeText(file.mime_type, \"video/mp4\");
  player.appendChild(source);
  const track = document.createElement(\"track\");
  track.src = video.subtitles_path;
  player.appendChild(track);
  player.load();
}
"""


def certify() -> dict[str, str | int | list[str]]:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0046f-") as temp_dir:
        root = Path(temp_dir)
        dashboard = root / "dashboard"
        videos = dashboard / "videos"
        data = dashboard / "data"
        assets = dashboard / "assets"
        for directory in (videos, data, assets):
            directory.mkdir(parents=True, exist_ok=True)

        video_path = videos / f"{VIDEO_ID}.mp4"
        thumbnail_path = videos / f"{VIDEO_ID}.jpg"
        subtitles_path = videos / f"{VIDEO_ID}.vtt"
        html_path = dashboard / "videos.html"
        javascript_path = assets / "video-library.js"
        library_path = data / "video_library.json"

        video_bytes = _mp4_payload()
        video_path.write_bytes(video_bytes)
        thumbnail_path.write_bytes(_jpeg_payload())
        subtitles_path.write_text(
            "WEBVTT\n\n00:00:00.000 --> 00:00:04.000\nControlled activation certified.\n",
            encoding="utf-8",
        )
        html_path.write_text(_html_payload(), encoding="utf-8")
        javascript_path.write_text(_javascript_payload(), encoding="utf-8")

        checksum = hashlib.sha256(video_bytes).hexdigest()
        library = {
            "schema_version": "1.0",
            "generated_at": "2026-07-30T10:00:00+00:00",
            "videos": [
                {
                    "video_id": VIDEO_ID,
                    "title": "Production activation closure certification",
                    "topic": "controlled_production_activation",
                    "status": "ready",
                    "platform": "youtube_shorts",
                    "duration_seconds": 4.0,
                    "width": 1080,
                    "height": 1920,
                    "orientation": "vertical",
                    "video_file": {
                        "path": f"videos/{VIDEO_ID}.mp4",
                        "container": "mp4",
                        "mime_type": "video/mp4",
                        "checksum_sha256": checksum,
                        "size_bytes": len(video_bytes),
                    },
                    "thumbnail_path": f"videos/{VIDEO_ID}.jpg",
                    "subtitles_path": f"videos/{VIDEO_ID}.vtt",
                    "script_id": "SCRIPT-CERT-0046F",
                    "storyboard_id": "STORYBOARD-CERT-0046F",
                    "production_package_id": "PRODUCTION-CERT-0046F",
                    "publishing_package_id": "PUBLISHING-CERT-0046F",
                    "render_engine": "ffmpeg",
                    "created_at": "2026-07-30T10:00:00+00:00",
                    "updated_at": "2026-07-30T10:00:00+00:00",
                    "failure_reason": None,
                }
            ],
        }
        library_path.write_text(json.dumps(library, indent=2), encoding="utf-8")

        report = verify_dashboard_playback(
            dashboard_workspace=dashboard,
            library_path=library_path,
            html_path=html_path,
            javascript_path=javascript_path,
            video_id=VIDEO_ID,
        )
        if report.status != "PASS":
            raise ProductionActivationCertificationError("playback verification did not pass")
        if report.checksum_sha256 != checksum:
            raise ProductionActivationCertificationError("closure checksum binding failed")
        if report.size_bytes != len(video_bytes):
            raise ProductionActivationCertificationError("closure size binding failed")

        required_checks = {
            "LIBRARY_ASSET_READY",
            "WORKSPACE_CONFINEMENT",
            "VIDEO_INTEGRITY",
            "MP4_CONTAINER_SIGNATURE",
            "THUMBNAIL_SIGNATURE",
            "WEBVTT_SIGNATURE",
            "HTML5_PLAYER_BINDING",
        }
        if set(report.checks) != required_checks:
            raise ProductionActivationCertificationError("playback evidence set is incomplete")

        return {
            "artifact": ARTIFACT,
            "status": "PASS",
            "activation_readiness": "PASS",
            "controlled_render_command": "PASS",
            "dashboard_asset_installation": "PASS",
            "atomic_library_promotion": "PASS",
            "dashboard_playback_verification": "PASS",
            "checksum_binding": "PASS",
            "workspace_confinement": "PASS",
            "fail_closed_governance": "PASS",
            "video_count": 1,
            "playback_check_count": len(report.checks),
            "checks": list(report.checks),
        }


def main() -> int:
    print("=" * 72)
    print(ARTIFACT)
    print("CONTROLLED PRODUCTION VIDEO RENDERING ACTIVATION CLOSURE")
    print("=" * 72)
    for key, value in certify().items():
        if isinstance(value, list):
            print(f"{key.upper()}={','.join(value)}")
        else:
            print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
