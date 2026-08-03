"""
FOOTBALL-SHORTS-AI-0054E
GOVERNED CLIP SELECTION CONTRACT

Creates deterministic clip proposals from 0054A external video assets. The
contract records timestamps and editorial intent only. It never downloads,
extracts, transforms or publishes provider media.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from discovery.external_provider_contract import ExternalVideoAsset


class GovernedClipSelectionError(ValueError):
    """Raised when a clip proposal is malformed or exceeds governed limits."""


SUPPORTED_CLIP_STATES = {
    "proposed",
    "reviewed",
    "approved_for_project",
    "blocked",
    "archived",
}

SUPPORTED_INTENTS = {
    "reference",
    "analysis",
    "commentary",
    "story_context",
    "production_source",
}

MAX_CLIP_DURATION_SECONDS = 15.0
MIN_CLIP_DURATION_SECONDS = 0.5


@dataclass(frozen=True)
class GovernedClipSelection:
    schema: str
    clip_id: str
    asset_id: str
    provider: str
    provider_asset_id: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    editorial_intent: str
    note: str
    clip_state: str
    rights_status: str
    preview_allowed: bool
    render_allowed: bool
    acquisition_allowed: bool
    source_evidence_sha256: str
    evidence_sha256: str
    auto_acquire: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.governed-clip-selection.v1":
            raise GovernedClipSelectionError("unsupported clip selection schema")
        if not self.clip_id.startswith("CLIP-"):
            raise GovernedClipSelectionError("clip_id must start with CLIP-")
        if not self.asset_id.startswith("EXT-"):
            raise GovernedClipSelectionError("asset_id must identify an external asset")
        if self.start_seconds < 0:
            raise GovernedClipSelectionError("start_seconds must be non-negative")
        if self.end_seconds <= self.start_seconds:
            raise GovernedClipSelectionError("end_seconds must be greater than start_seconds")
        expected_duration = round(self.end_seconds - self.start_seconds, 3)
        if round(self.duration_seconds, 3) != expected_duration:
            raise GovernedClipSelectionError("duration_seconds is inconsistent")
        if not MIN_CLIP_DURATION_SECONDS <= self.duration_seconds <= MAX_CLIP_DURATION_SECONDS:
            raise GovernedClipSelectionError("clip duration is outside governed limits")
        if self.editorial_intent not in SUPPORTED_INTENTS:
            raise GovernedClipSelectionError("unsupported editorial intent")
        if self.clip_state not in SUPPORTED_CLIP_STATES:
            raise GovernedClipSelectionError("unsupported clip state")
        if not self.preview_allowed:
            raise GovernedClipSelectionError("clip selection requires preview capability")
        if self.rights_status == "reference_only":
            if self.render_allowed or self.acquisition_allowed:
                raise GovernedClipSelectionError(
                    "reference-only clip cannot be acquired or rendered"
                )
            if self.editorial_intent == "production_source":
                raise GovernedClipSelectionError(
                    "reference-only clip cannot be a production source"
                )
        if self.clip_state == "approved_for_project" and not self.render_allowed:
            raise GovernedClipSelectionError(
                "non-renderable clip cannot be approved for project"
            )
        if not _is_sha256(self.source_evidence_sha256):
            raise GovernedClipSelectionError("source evidence must be SHA-256")
        if not _is_sha256(self.evidence_sha256):
            raise GovernedClipSelectionError("clip evidence must be SHA-256")
        if self.auto_acquire or self.auto_render or self.auto_publish:
            raise GovernedClipSelectionError("automatic media actions are forbidden")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "clip_id": self.clip_id,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "provider_asset_id": self.provider_asset_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "editorial_intent": self.editorial_intent,
            "note": self.note,
            "clip_state": self.clip_state,
            "rights_status": self.rights_status,
            "preview_allowed": self.preview_allowed,
            "render_allowed": self.render_allowed,
            "acquisition_allowed": self.acquisition_allowed,
            "source_evidence_sha256": self.source_evidence_sha256,
            "evidence_sha256": self.evidence_sha256,
            "auto_acquire": False,
            "auto_render": False,
            "auto_publish": False,
        }


def build_governed_clip_selection(
    *,
    asset: ExternalVideoAsset,
    start_seconds: float,
    end_seconds: float,
    editorial_intent: str = "reference",
    note: str = "",
    clip_state: str = "proposed",
) -> GovernedClipSelection:
    asset.validate()
    start = round(float(start_seconds), 3)
    end = round(float(end_seconds), 3)
    duration = round(end - start, 3)

    if asset.duration_seconds is not None and end > asset.duration_seconds:
        raise GovernedClipSelectionError("clip end exceeds source duration")

    source_evidence = canonical_sha256(asset.to_dict())
    unsigned: dict[str, object] = {
        "schema": "football-shorts-ai.governed-clip-selection.v1",
        "asset_id": asset.asset_id,
        "provider": asset.provider,
        "provider_asset_id": asset.provider_asset_id,
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": duration,
        "editorial_intent": editorial_intent,
        "note": note.strip(),
        "clip_state": clip_state,
        "rights_status": asset.rights_status,
        "preview_allowed": asset.preview_allowed,
        "render_allowed": asset.render_allowed,
        "acquisition_allowed": asset.acquisition_allowed,
        "source_evidence_sha256": source_evidence,
        "auto_acquire": False,
        "auto_render": False,
        "auto_publish": False,
    }
    evidence_sha256 = canonical_sha256(unsigned)
    result = GovernedClipSelection(
        schema="football-shorts-ai.governed-clip-selection.v1",
        clip_id=f"CLIP-{evidence_sha256[:20].upper()}",
        asset_id=asset.asset_id,
        provider=asset.provider,
        provider_asset_id=asset.provider_asset_id,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=duration,
        editorial_intent=editorial_intent,
        note=note.strip(),
        clip_state=clip_state,
        rights_status=asset.rights_status,
        preview_allowed=asset.preview_allowed,
        render_allowed=asset.render_allowed,
        acquisition_allowed=asset.acquisition_allowed,
        source_evidence_sha256=source_evidence,
        evidence_sha256=evidence_sha256,
        auto_acquire=False,
        auto_render=False,
        auto_publish=False,
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "GovernedClipSelection",
    "GovernedClipSelectionError",
    "MAX_CLIP_DURATION_SECONDS",
    "MIN_CLIP_DURATION_SECONDS",
    "SUPPORTED_CLIP_STATES",
    "SUPPORTED_INTENTS",
    "build_governed_clip_selection",
    "canonical_sha256",
]
