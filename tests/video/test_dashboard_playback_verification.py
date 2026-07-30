from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from video.verify_dashboard_playback import (
    DashboardPlaybackVerificationError,
    verify_dashboard_playback,
)


def _write_fixture(root: Path, *, status: str = "ready", corrupt_video: bool = False) -> dict[str, Path]:
    dashboard = root / "dashboard"
    videos = dashboard / "videos"
    data = dashboard / "data"
    assets = dashboard / "assets"
    videos.mkdir(parents=True)
    data.mkdir(parents=True)
    assets.mkdir(parents=True)

    video = videos / "VID-000001.mp4"
    video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"video-evidence"
    video.write_bytes(b"not-an-mp4" if corrupt_video else video_bytes)
    thumbnail = videos / "VID-000001.jpg"
    thumbnail.write_bytes(b"\xff\xd8\xff\xe0thumbnail")
    subtitles = videos / "VID-000001.vtt"
    subtitles.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nGoal\n", encoding="utf-8")

    dashboard.joinpath("videos.html").write_text(
        '<video id="video-player"></video><script src="assets/video-library.js"></script>',
        encoding="utf-8",
    )
    assets.joinpath("video-library.js").write_text(
        '''
const source = document.createElement("source");
const track = document.createElement("track");
source.src = file.path;
source.type = safeText(file.mime_type, "video/mp4");
track.src = video.subtitles_path;
player.load();
''',
        encoding="utf-8",
    )

    checksum = hashlib.sha256(video.read_bytes()).hexdigest()
    library = {
        "schema_version": "1.0",
        "videos": [
            {
                "video_id": "VID-000001",
                "status": status,
                "video_file": {
                    "path": "videos/VID-000001.mp4",
                    "mime_type": "video/mp4",
                    "checksum_sha256": checksum,
                    "size_bytes": video.stat().st_size,
                },
                "thumbnail_path": "videos/VID-000001.jpg",
                "subtitles_path": "videos/VID-000001.vtt",
            }
        ],
    }
    library_path = data / "video_library.json"
    library_path.write_text(json.dumps(library), encoding="utf-8")
    return {
        "dashboard": dashboard,
        "library": library_path,
        "html": dashboard / "videos.html",
        "javascript": assets / "video-library.js",
    }


def test_verifies_ready_dashboard_video(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    report = verify_dashboard_playback(
        dashboard_workspace=paths["dashboard"],
        library_path=paths["library"],
        html_path=paths["html"],
        javascript_path=paths["javascript"],
    )
    assert report.artifact == "FOOTBALL-SHORTS-AI-0046E"
    assert report.status == "PASS"
    assert report.video_id == "VID-000001"
    assert "HTML5_PLAYER_BINDING" in report.checks


def test_blocks_draft_asset(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, status="draft")
    with pytest.raises(DashboardPlaybackVerificationError, match="not playable"):
        verify_dashboard_playback(
            dashboard_workspace=paths["dashboard"],
            library_path=paths["library"],
            html_path=paths["html"],
            javascript_path=paths["javascript"],
        )


def test_blocks_checksum_mismatch(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    payload = json.loads(paths["library"].read_text(encoding="utf-8"))
    payload["videos"][0]["video_file"]["checksum_sha256"] = "0" * 64
    paths["library"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DashboardPlaybackVerificationError, match="checksum"):
        verify_dashboard_playback(
            dashboard_workspace=paths["dashboard"],
            library_path=paths["library"],
            html_path=paths["html"],
            javascript_path=paths["javascript"],
        )


def test_blocks_invalid_mp4_signature(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path, corrupt_video=True)
    with pytest.raises(DashboardPlaybackVerificationError, match="MP4"):
        verify_dashboard_playback(
            dashboard_workspace=paths["dashboard"],
            library_path=paths["library"],
            html_path=paths["html"],
            javascript_path=paths["javascript"],
        )


def test_blocks_workspace_escape(tmp_path: Path) -> None:
    paths = _write_fixture(tmp_path)
    payload = json.loads(paths["library"].read_text(encoding="utf-8"))
    payload["videos"][0]["video_file"]["path"] = "../outside.mp4"
    paths["library"].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DashboardPlaybackVerificationError, match="escaped"):
        verify_dashboard_playback(
            dashboard_workspace=paths["dashboard"],
            library_path=paths["library"],
            html_path=paths["html"],
            javascript_path=paths["javascript"],
        )
