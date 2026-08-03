"""
FOOTBALL-SHORTS-AI-0056K
EDITORIAL INTELLIGENCE DASHBOARD INTEGRATION AND LIVE DATA EXPORT

Builds the public, review-only package consumed by dashboard/editorial-review.html.
The exporter never acquires media, renders video, trains models or publishes content.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence


class EditorialReviewExportError(ValueError):
    """Raised when editorial review evidence is incomplete or unsafe."""


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_editorial_review_package(
    *,
    timeline: Mapping[str, object],
    scorecard: Mapping[str, object],
    alternatives_by_beat: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
) -> dict[str, object]:
    timeline_id = _required_text(timeline, "timeline_id")
    score_id = _required_text(scorecard, "score_id")
    if not timeline_id.startswith("AUTOTIMELINE-"):
        raise EditorialReviewExportError("timeline_id must reference AUTOTIMELINE evidence")
    if not score_id.startswith("EDITSCORE-"):
        raise EditorialReviewExportError("score_id must reference EDITSCORE evidence")
    if scorecard.get("alignment_id") != timeline.get("alignment_id"):
        raise EditorialReviewExportError("timeline and scorecard alignment evidence do not match")

    scenes = timeline.get("clips", timeline.get("scenes", []))
    if not isinstance(scenes, list) or not scenes:
        raise EditorialReviewExportError("timeline scenes are required")

    normalized_scenes: list[dict[str, object]] = []
    for scene in scenes:
        if not isinstance(scene, Mapping):
            raise EditorialReviewExportError("timeline scene must be an object")
        normalized_scenes.append(_normalize_scene(scene))

    alternatives = _normalize_alternatives(alternatives_by_beat or {})
    blockers = sorted(
        {
            *[str(value) for value in timeline.get("blockers", []) if str(value)],
            *[str(value) for value in scorecard.get("blockers", []) if str(value)],
            *[
                str(value)
                for scene in normalized_scenes
                for value in scene.get("blockers", [])
                if str(value)
            ],
        }
    )

    core: dict[str, object] = {
        "schema": "football-shorts-ai.editorial-review-package.v1",
        "timeline": {
            **dict(timeline),
            "scenes": normalized_scenes,
        },
        "scorecard": dict(scorecard),
        "alternatives_by_beat": alternatives,
        "blockers": blockers,
        "review_required": True,
        "factory_handover_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    evidence = canonical_sha256(core)
    package = {
        **core,
        "package_id": f"EDITORIALPKG-{evidence[:20].upper()}",
        "evidence_sha256": evidence,
    }
    validate_editorial_review_package(package)
    return package


def validate_editorial_review_package(package: Mapping[str, object]) -> None:
    if package.get("schema") != "football-shorts-ai.editorial-review-package.v1":
        raise EditorialReviewExportError("unsupported editorial review package schema")
    package_id = _required_text(package, "package_id")
    if not package_id.startswith("EDITORIALPKG-"):
        raise EditorialReviewExportError("invalid package identity")
    timeline = package.get("timeline")
    scorecard = package.get("scorecard")
    if not isinstance(timeline, Mapping) or not isinstance(scorecard, Mapping):
        raise EditorialReviewExportError("timeline and scorecard are required")
    scenes = timeline.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise EditorialReviewExportError("review package requires scenes")
    if package.get("review_required") is not True:
        raise EditorialReviewExportError("human editorial review must remain required")
    for flag in (
        "factory_handover_enabled",
        "network_enabled",
        "acquisition_enabled",
        "render_enabled",
        "auto_render",
        "auto_publish",
    ):
        if package.get(flag) is not False:
            raise EditorialReviewExportError(f"{flag} must remain disabled")
    evidence = _required_text(package, "evidence_sha256")
    if len(evidence) != 64:
        raise EditorialReviewExportError("evidence must be SHA-256")
    unsigned = {key: value for key, value in package.items() if key not in {"package_id", "evidence_sha256"}}
    if canonical_sha256(unsigned) != evidence:
        raise EditorialReviewExportError("editorial review package evidence mismatch")


def export_editorial_review_package(
    *,
    timeline: Mapping[str, object],
    scorecard: Mapping[str, object],
    alternatives_by_beat: Mapping[str, Sequence[Mapping[str, object]]] | None = None,
    output_path: Path | str = Path("dashboard/data/editorial_review_package.json"),
) -> Path:
    package = build_editorial_review_package(
        timeline=timeline,
        scorecard=scorecard,
        alternatives_by_beat=alternatives_by_beat,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination


def _normalize_scene(scene: Mapping[str, object]) -> dict[str, object]:
    required = ("beat_id", "scene_id", "beat_role", "beat_text")
    for key in required:
        _required_text(scene, key)
    return {
        "order": int(scene.get("order", 0)),
        "beat_id": str(scene["beat_id"]),
        "beat_role": str(scene["beat_role"]),
        "beat_text": str(scene["beat_text"]),
        "scene_id": str(scene["scene_id"]),
        "provider": str(scene.get("provider", "unknown")),
        "source_start_seconds": float(scene.get("source_start_seconds", 0.0)),
        "source_end_seconds": float(scene.get("source_end_seconds", 0.0)),
        "timeline_start_seconds": float(scene.get("timeline_start_seconds", 0.0)),
        "timeline_end_seconds": float(scene.get("timeline_end_seconds", 0.0)),
        "duration_seconds": float(scene.get("duration_seconds", 0.0)),
        "transition": str(scene.get("transition", "cut")),
        "match_score": float(scene.get("match_score", 0.0)),
        "render_allowed": scene.get("render_allowed") is True,
        "rights_status": str(scene.get("rights_status", "unknown")),
        "blockers": sorted({str(value) for value in scene.get("blockers", []) if str(value)}),
    }


def _normalize_alternatives(
    values: Mapping[str, Sequence[Mapping[str, object]]],
) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for beat_id, candidates in values.items():
        if not str(beat_id).startswith("BEAT-"):
            raise EditorialReviewExportError("alternative key must reference BEAT evidence")
        result[str(beat_id)] = [
            {
                "scene_id": _required_text(candidate, "scene_id"),
                "match_score": float(candidate.get("match_score", 0.0)),
                "render_allowed": candidate.get("render_allowed") is True,
                "label": str(candidate.get("label", candidate.get("scene_id", "Alternativa"))),
            }
            for candidate in candidates
        ]
    return result


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EditorialReviewExportError(f"{key} is required")
    return value.strip()


__all__ = [
    "EditorialReviewExportError",
    "build_editorial_review_package",
    "canonical_sha256",
    "export_editorial_review_package",
    "validate_editorial_review_package",
]
