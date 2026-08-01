"""
FOOTBALL-SHORTS-AI-0052E
FACTORY PUBLISHING READINESS

Binds a rendered Video Library asset to the governed Publishing Package and
emits a deterministic readiness decision. This module never publishes, uploads,
schedules, authenticates with a platform, or enables automatic publishing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from publishing.publishing_schema import (
    validate_checklist,
    validate_publishing_payload,
)


class PublishingReadinessError(ValueError):
    """Raised when publishing readiness evidence is malformed or unsafe."""


@dataclass(frozen=True)
class PublishingReadinessDecision:
    schema: str
    video_id: str
    publishing_package_id: str
    platform: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    video_path: str
    thumbnail_path: str
    subtitles_path: str
    checksum_sha256: str
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.publishing-readiness.v1":
            raise PublishingReadinessError("unsupported publishing readiness schema")
        if not self.video_id.strip():
            raise PublishingReadinessError("video_id is required")
        if not self.publishing_package_id.strip():
            raise PublishingReadinessError("publishing_package_id is required")
        if not self.platform.strip():
            raise PublishingReadinessError("platform is required")
        if self.status not in {"ready_for_publish", "blocked"}:
            raise PublishingReadinessError("unsupported publishing readiness status")
        if self.auto_publish:
            raise PublishingReadinessError("automatic publishing must remain disabled")
        if self.status == "ready_for_publish" and self.blockers:
            raise PublishingReadinessError("ready decision cannot contain blockers")
        if self.status == "blocked" and not self.blockers:
            raise PublishingReadinessError("blocked decision requires blockers")
        if set(self.checks.values()) - {True, False}:
            raise PublishingReadinessError("readiness checks must be boolean")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "video_id": self.video_id,
            "publishing_package_id": self.publishing_package_id,
            "platform": self.platform,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "artifacts": {
                "video_path": self.video_path,
                "thumbnail_path": self.thumbnail_path,
                "subtitles_path": self.subtitles_path,
                "checksum_sha256": self.checksum_sha256,
            },
            "auto_publish": False,
        }


def evaluate_publishing_readiness(
    video: Mapping[str, Any],
    publishing_package: Mapping[str, Any],
    *,
    dashboard_root: Path,
) -> PublishingReadinessDecision:
    """Evaluate one rendered Short against governed publishing evidence."""

    validate_publishing_payload(dict(publishing_package))
    checklist = publishing_package.get("checklist")
    if not isinstance(checklist, dict):
        raise PublishingReadinessError("publishing checklist must be an object")
    validate_checklist(checklist)

    video_id = _required_text(video, "video_id")
    publishing_package_id = _required_text(video, "publishing_package_id")
    status = _required_text(video, "status")
    platform = _required_text(video, "platform")

    metadata = publishing_package.get("metadata")
    if not isinstance(metadata, dict):
        raise PublishingReadinessError("publishing metadata must be an object")

    video_file = video.get("video_file")
    if not isinstance(video_file, dict):
        video_file = {}

    video_path = _optional_text(video_file.get("path"))
    thumbnail_path = _optional_text(video.get("thumbnail_path"))
    subtitles_path = _optional_text(video.get("subtitles_path"))
    expected_checksum = _optional_text(video_file.get("checksum_sha256")).lower()

    checks: dict[str, bool] = {
        "video_status_ready": status in {"ready", "published"},
        "platform_match": metadata.get("platform") == platform,
        "title_valid": bool(_optional_text(metadata.get("title"))),
        "description_valid": bool(_optional_text(metadata.get("description"))),
        "hashtags_valid": _valid_hashtags(metadata.get("hashtags")),
        "checklist_title_valid": checklist.get("title_valid") is True,
        "checklist_description_valid": checklist.get("description_valid") is True,
        "checklist_hashtags_valid": checklist.get("hashtags_valid") is True,
        "copyright_review_complete": checklist.get("copyright_review_required") is False,
        "final_confirmation_required": checklist.get("final_confirmation_required") is True,
        "video_file_present": bool(video_path),
        "thumbnail_present": bool(thumbnail_path),
        "subtitles_present": bool(subtitles_path),
        "vertical_dimensions": _positive_int(video.get("width")) == 1080
        and _positive_int(video.get("height")) == 1920,
        "duration_valid": 1.0 <= _positive_float(video.get("duration_seconds")) <= 180.0,
        "checksum_declared": len(expected_checksum) == 64,
        "auto_publish_disabled": True,
    }

    root = dashboard_root.resolve()
    resolved_video = _resolve_artifact(root, video_path)
    resolved_thumbnail = _resolve_artifact(root, thumbnail_path)
    resolved_subtitles = _resolve_artifact(root, subtitles_path)

    checks["video_file_exists"] = resolved_video.is_file() if resolved_video else False
    checks["thumbnail_exists"] = resolved_thumbnail.is_file() if resolved_thumbnail else False
    checks["subtitles_exists"] = resolved_subtitles.is_file() if resolved_subtitles else False
    checks["video_is_mp4"] = (
        resolved_video is not None
        and resolved_video.suffix.lower() == ".mp4"
        and _has_mp4_signature(resolved_video)
    )
    checks["checksum_matches"] = (
        resolved_video is not None
        and resolved_video.is_file()
        and len(expected_checksum) == 64
        and _sha256(resolved_video) == expected_checksum
    )

    blockers = tuple(
        key.upper()
        for key, passed in checks.items()
        if not passed
    )
    decision = PublishingReadinessDecision(
        schema="football-shorts-ai.publishing-readiness.v1",
        video_id=video_id,
        publishing_package_id=publishing_package_id,
        platform=platform,
        status="ready_for_publish" if not blockers else "blocked",
        checks=checks,
        blockers=blockers,
        video_path=video_path,
        thumbnail_path=thumbnail_path,
        subtitles_path=subtitles_path,
        checksum_sha256=expected_checksum,
        auto_publish=False,
    )
    decision.validate()
    return decision


def evaluate_library(
    video_library: Mapping[str, Any],
    publishing_package: Mapping[str, Any],
    *,
    dashboard_root: Path,
) -> tuple[PublishingReadinessDecision, ...]:
    videos = video_library.get("videos")
    if not isinstance(videos, list):
        raise PublishingReadinessError("video library videos must be a list")
    return tuple(
        evaluate_publishing_readiness(
            video,
            publishing_package,
            dashboard_root=dashboard_root,
        )
        for video in videos
        if isinstance(video, dict)
    )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PublishingReadinessError(f"JSON root must be an object: {path}")
    return payload


def _resolve_artifact(root: Path, value: str) -> Path | None:
    if not value:
        return None
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise PublishingReadinessError("artifact path escaped dashboard workspace")
    return candidate


def _has_mp4_signature(path: Path) -> bool:
    header = path.read_bytes()[:16]
    return len(header) >= 12 and header[4:8] == b"ftyp"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = _optional_text(payload.get(key))
    if not value:
        raise PublishingReadinessError(f"{key} is required")
    return value


def _optional_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _valid_hashtags(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.startswith("#") for item in value)
    )


def _positive_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def _positive_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value) if value > 0 else 0.0


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    dashboard_root = root / "dashboard"
    library = load_json(dashboard_root / "data" / "video_library.json")
    package = load_json(root / "output" / "publishing_package.json")
    decisions = evaluate_library(library, package, dashboard_root=dashboard_root)

    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0052E")
    print("FACTORY PUBLISHING READINESS")
    print("=" * 72)
    for decision in decisions:
        print(json.dumps(decision.to_dict(), ensure_ascii=False, sort_keys=True))
    print("AUTO_PUBLISH=DISABLED")
    return 0 if decisions and all(item.status == "ready_for_publish" for item in decisions) else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PublishingReadinessDecision",
    "PublishingReadinessError",
    "evaluate_library",
    "evaluate_publishing_readiness",
    "load_json",
    "main",
]
