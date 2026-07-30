from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


class DashboardPlaybackVerificationError(RuntimeError):
    """Raised when a promoted dashboard video is not safely playable."""


@dataclass(frozen=True, slots=True)
class PlaybackVerificationReport:
    artifact: str
    status: str
    video_id: str
    library_path: str
    html_path: str
    javascript_path: str
    video_path: str
    thumbnail_path: str
    subtitles_path: str
    mime_type: str
    checksum_sha256: str
    size_bytes: int
    checks: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def verify_dashboard_playback(
    *,
    dashboard_workspace: Path = Path("dashboard"),
    library_path: Path = Path("dashboard/data/video_library.json"),
    html_path: Path = Path("dashboard/videos.html"),
    javascript_path: Path = Path("dashboard/assets/video-library.js"),
    video_id: str = "VID-000001",
) -> PlaybackVerificationReport:
    dashboard_root = dashboard_workspace.resolve()
    library = _load_json(library_path)
    videos = library.get("videos")
    if not isinstance(videos, list):
        raise DashboardPlaybackVerificationError("video library videos must be a list")

    matches = [item for item in videos if isinstance(item, dict) and item.get("video_id") == video_id]
    if len(matches) != 1:
        raise DashboardPlaybackVerificationError(
            f"expected exactly one governed video asset for {video_id!r}"
        )
    asset = matches[0]
    if asset.get("status") not in {"ready", "published"}:
        raise DashboardPlaybackVerificationError(
            f"video asset is not playable: status={asset.get('status')!r}"
        )

    file_metadata = asset.get("video_file")
    if not isinstance(file_metadata, dict):
        raise DashboardPlaybackVerificationError("playable video requires video_file metadata")

    video_relative = _required_text(file_metadata, "path")
    thumbnail_relative = _required_text(asset, "thumbnail_path")
    subtitles_relative = _required_text(asset, "subtitles_path")
    mime_type = _required_text(file_metadata, "mime_type")
    expected_checksum = _required_text(file_metadata, "checksum_sha256").casefold()
    expected_size = file_metadata.get("size_bytes")
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise DashboardPlaybackVerificationError("video_file.size_bytes must be a positive integer")

    video_path = _confined(dashboard_root, video_relative)
    thumbnail_path = _confined(dashboard_root, thumbnail_relative)
    subtitles_path = _confined(dashboard_root, subtitles_relative)
    html_resolved = html_path.resolve()
    javascript_resolved = javascript_path.resolve()

    for path, label in (
        (video_path, "video"),
        (thumbnail_path, "thumbnail"),
        (subtitles_path, "subtitles"),
        (html_resolved, "dashboard HTML"),
        (javascript_resolved, "dashboard JavaScript"),
    ):
        if not path.is_file() or path.stat().st_size <= 0:
            raise DashboardPlaybackVerificationError(f"missing or empty {label}: {path}")

    actual_size = video_path.stat().st_size
    if actual_size != expected_size:
        raise DashboardPlaybackVerificationError(
            f"video size mismatch: expected={expected_size} actual={actual_size}"
        )
    actual_checksum = _sha256(video_path)
    if actual_checksum != expected_checksum:
        raise DashboardPlaybackVerificationError("video checksum does not match library evidence")

    if mime_type != "video/mp4":
        raise DashboardPlaybackVerificationError(f"unsupported governed playback MIME type: {mime_type}")
    _verify_mp4_signature(video_path)
    _verify_thumbnail_signature(thumbnail_path)
    _verify_webvtt(subtitles_path)
    _verify_player_binding(html_resolved, javascript_resolved)

    return PlaybackVerificationReport(
        artifact="FOOTBALL-SHORTS-AI-0046E",
        status="PASS",
        video_id=video_id,
        library_path=library_path.as_posix(),
        html_path=html_path.as_posix(),
        javascript_path=javascript_path.as_posix(),
        video_path=video_relative,
        thumbnail_path=thumbnail_relative,
        subtitles_path=subtitles_relative,
        mime_type=mime_type,
        checksum_sha256=actual_checksum,
        size_bytes=actual_size,
        checks=(
            "LIBRARY_ASSET_READY",
            "WORKSPACE_CONFINEMENT",
            "VIDEO_INTEGRITY",
            "MP4_CONTAINER_SIGNATURE",
            "THUMBNAIL_SIGNATURE",
            "WEBVTT_SIGNATURE",
            "HTML5_PLAYER_BINDING",
        ),
    )


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise DashboardPlaybackVerificationError(f"library not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardPlaybackVerificationError(f"invalid video library: {exc}") from exc
    if not isinstance(payload, dict):
        raise DashboardPlaybackVerificationError("video library root must be an object")
    return payload


def _required_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DashboardPlaybackVerificationError(f"{key} must be a non-empty string")
    return value.strip()


def _confined(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise DashboardPlaybackVerificationError("dashboard asset path escaped governed workspace")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_mp4_signature(path: Path) -> None:
    header = path.read_bytes()[:32]
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise DashboardPlaybackVerificationError("video does not expose a valid MP4 ftyp signature")


def _verify_thumbnail_signature(path: Path) -> None:
    header = path.read_bytes()[:12]
    valid = (
        header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"\x89PNG\r\n\x1a\n")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )
    if not valid:
        raise DashboardPlaybackVerificationError("thumbnail signature is not JPEG, PNG, or WebP")


def _verify_webvtt(path: Path) -> None:
    prefix = path.read_text(encoding="utf-8-sig")[:64].lstrip()
    if not prefix.startswith("WEBVTT"):
        raise DashboardPlaybackVerificationError("subtitles file does not start with WEBVTT")


def _verify_player_binding(html_path: Path, javascript_path: Path) -> None:
    html = html_path.read_text(encoding="utf-8")
    javascript = javascript_path.read_text(encoding="utf-8")
    html_tokens = ('id="video-player"', 'assets/video-library.js')
    javascript_tokens = (
        'document.createElement("source")',
        'document.createElement("track")',
        "source.src = file.path",
        "source.type = safeText(file.mime_type, \"video/mp4\")",
        "track.src = video.subtitles_path",
        "player.load()",
    )
    missing = [token for token in (*html_tokens, *javascript_tokens) if token not in (html if token in html_tokens else javascript)]
    if missing:
        raise DashboardPlaybackVerificationError(f"dashboard player binding is incomplete: {missing}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify governed dashboard playback evidence.")
    parser.add_argument("--dashboard-workspace", default="dashboard")
    parser.add_argument("--library", default="dashboard/data/video_library.json")
    parser.add_argument("--html", default="dashboard/videos.html")
    parser.add_argument("--javascript", default="dashboard/assets/video-library.js")
    parser.add_argument("--video-id", default="VID-000001")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        report = verify_dashboard_playback(
            dashboard_workspace=Path(args.dashboard_workspace),
            library_path=Path(args.library),
            html_path=Path(args.html),
            javascript_path=Path(args.javascript),
            video_id=args.video_id,
        )
    except DashboardPlaybackVerificationError as exc:
        print("=" * 72)
        print("FOOTBALL-SHORTS-AI-0046E")
        print("CONTROLLED DASHBOARD PLAYBACK VERIFICATION")
        print("=" * 72)
        print("STATUS=BLOCKED")
        print(f"BLOCKER={exc}")
        return 1
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
