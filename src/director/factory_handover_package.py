"""
FOOTBALL-SHORTS-AI-0058F
AI DIRECTOR FACTORY HANDOVER PACKAGE CONTRACT

Builds a deterministic, reviewable handover package from a valid human approval
and optimized director timeline. It performs no network access, acquisition,
extraction, rendering or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class FactoryHandoverError(ValueError):
    """Raised when a governed factory handover package is invalid."""


SUPPORTED_STATES = {"ready_for_factory", "review_required", "blocked"}


@dataclass(frozen=True)
class FactoryTimelineItem:
    item_id: str
    beat_id: str
    clip_id: str
    source_start_seconds: float
    source_end_seconds: float
    timeline_start_seconds: float
    timeline_end_seconds: float
    script_text: str
    transition_in: str
    transition_out: str
    playback_rate: float
    render_allowed: bool
    evidence_ids: tuple[str, ...]

    def validate(self) -> None:
        if not self.item_id.startswith("FACTORYITEM-"):
            raise FactoryHandoverError("invalid factory timeline item identity")
        if not self.beat_id.startswith("DIRBEAT-"):
            raise FactoryHandoverError("invalid director beat identity")
        if not self.clip_id.startswith("VIRALCLIP-"):
            raise FactoryHandoverError("invalid viral clip identity")
        if not 0.0 <= self.source_start_seconds < self.source_end_seconds:
            raise FactoryHandoverError("invalid source timing")
        if not 0.0 <= self.timeline_start_seconds < self.timeline_end_seconds:
            raise FactoryHandoverError("invalid timeline timing")
        if not self.script_text.strip():
            raise FactoryHandoverError("script text is required")
        if not 0.5 <= self.playback_rate <= 2.0:
            raise FactoryHandoverError("playback rate is outside governed limits")
        if tuple(sorted(set(self.evidence_ids))) != self.evidence_ids or not self.evidence_ids:
            raise FactoryHandoverError("evidence identities must be normalized and non-empty")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "item_id": self.item_id,
            "beat_id": self.beat_id,
            "clip_id": self.clip_id,
            "source_start_seconds": round(self.source_start_seconds, 3),
            "source_end_seconds": round(self.source_end_seconds, 3),
            "timeline_start_seconds": round(self.timeline_start_seconds, 3),
            "timeline_end_seconds": round(self.timeline_end_seconds, 3),
            "script_text": self.script_text,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "playback_rate": round(self.playback_rate, 4),
            "render_allowed": self.render_allowed,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class FactoryHandoverPackage:
    schema: str
    package_id: str
    approval_id: str
    variant_id: str | None
    optimization_id: str
    format: str
    width: int
    height: int
    fps: int
    timeline_items: tuple[FactoryTimelineItem, ...]
    total_duration_seconds: float
    handover_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.factory-handover-package.v1":
            raise FactoryHandoverError("unsupported factory handover schema")
        if not self.package_id.startswith("FACTORYPKG-"):
            raise FactoryHandoverError("invalid factory package identity")
        if not self.approval_id.startswith("DIRAPPROVAL-"):
            raise FactoryHandoverError("invalid approval identity")
        if self.variant_id is not None and not self.variant_id.startswith("DIRVAR-"):
            raise FactoryHandoverError("invalid variant identity")
        if not self.optimization_id.startswith("DIROPT-"):
            raise FactoryHandoverError("invalid optimization identity")
        if self.format != "9:16" or (self.width, self.height) != (1080, 1920):
            raise FactoryHandoverError("factory package must use governed vertical format")
        if self.fps not in {24, 25, 30, 50, 60}:
            raise FactoryHandoverError("unsupported frame rate")
        if self.handover_state not in SUPPORTED_STATES:
            raise FactoryHandoverError("unsupported handover state")
        for item in self.timeline_items:
            item.validate()
        ordered = sorted(self.timeline_items, key=lambda value: (value.timeline_start_seconds, value.item_id))
        if tuple(ordered) != self.timeline_items:
            raise FactoryHandoverError("timeline items must be ordered")
        for previous, current in zip(self.timeline_items, self.timeline_items[1:]):
            if current.timeline_start_seconds < previous.timeline_end_seconds - 0.001:
                raise FactoryHandoverError("timeline items overlap")
        expected_duration = max((item.timeline_end_seconds for item in self.timeline_items), default=0.0)
        if abs(expected_duration - self.total_duration_seconds) > 0.001:
            raise FactoryHandoverError("total duration is inconsistent")
        if self.handover_state == "ready_for_factory":
            if self.blockers or not self.timeline_items or not all(item.render_allowed for item in self.timeline_items):
                raise FactoryHandoverError("ready package requires renderable unblocked timeline")
        elif not self.blockers:
            raise FactoryHandoverError("non-ready package requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise FactoryHandoverError("0058F cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise FactoryHandoverError("factory handover evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "package_id": self.package_id,
            "approval_id": self.approval_id,
            "variant_id": self.variant_id,
            "optimization_id": self.optimization_id,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "timeline_items": [item.to_dict() for item in self.timeline_items],
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "handover_state": self.handover_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_factory_handover_package(
    *,
    approval_report: Mapping[str, object],
    optimization_report: Mapping[str, object],
    fps: int = 30,
) -> FactoryHandoverPackage:
    approval_id = _required_id(approval_report, "approval_id", "DIRAPPROVAL-")
    optimization_id = _required_id(optimization_report, "optimization_id", "DIROPT-")
    blockers: set[str] = set()
    if approval_report.get("approval_state") != "approved":
        blockers.add("DIRECTOR_APPROVAL_NOT_GRANTED")
    if approval_report.get("factory_handover_allowed") is not True:
        blockers.add("FACTORY_HANDOVER_NOT_ALLOWED")
    if optimization_report.get("optimization_state") != "optimized":
        blockers.add("TIMING_OPTIMIZATION_NOT_READY")

    variant_id = approval_report.get("selected_variant_id")
    if variant_id is not None:
        variant_id = str(variant_id)
    items: list[FactoryTimelineItem] = []
    raw_items = optimization_report.get("timeline_items", optimization_report.get("items", ()))
    if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes)):
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            evidence_ids = tuple(sorted(set(str(value) for value in raw.get("evidence_ids", ()) if str(value))))
            core = {
                "beat_id": str(raw.get("beat_id", "")),
                "clip_id": str(raw.get("clip_id", "")),
                "source_start_seconds": float(raw.get("source_start_seconds", 0.0)),
                "source_end_seconds": float(raw.get("source_end_seconds", 0.0)),
                "timeline_start_seconds": float(raw.get("timeline_start_seconds", 0.0)),
                "timeline_end_seconds": float(raw.get("timeline_end_seconds", 0.0)),
                "script_text": str(raw.get("script_text", "")).strip(),
                "transition_in": str(raw.get("transition_in", "cut")),
                "transition_out": str(raw.get("transition_out", "cut")),
                "playback_rate": float(raw.get("playback_rate", 1.0)),
                "render_allowed": bool(raw.get("render_allowed", False)),
                "evidence_ids": evidence_ids,
            }
            item_id = f"FACTORYITEM-{canonical_sha256({**core, 'evidence_ids': list(evidence_ids)})[:20].upper()}"
            items.append(FactoryTimelineItem(item_id=item_id, **core))
    items.sort(key=lambda value: (value.timeline_start_seconds, value.item_id))
    if not items:
        blockers.add("FACTORY_TIMELINE_MISSING")
    if any(not item.render_allowed for item in items):
        blockers.add("FACTORY_ITEM_RENDER_NOT_ALLOWED")

    state = "ready_for_factory" if not blockers else "blocked" if "DIRECTOR_APPROVAL_NOT_GRANTED" in blockers else "review_required"
    duration = max((item.timeline_end_seconds for item in items), default=0.0)
    core = {
        "schema": "football-shorts-ai.factory-handover-package.v1",
        "approval_id": approval_id,
        "variant_id": variant_id,
        "optimization_id": optimization_id,
        "format": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": int(fps),
        "timeline_items": [item.to_dict() for item in items],
        "total_duration_seconds": round(duration, 3),
        "handover_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    package_id = f"FACTORYPKG-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "package_id": package_id}
    result = FactoryHandoverPackage(
        package_id=package_id,
        evidence_sha256=canonical_sha256(unsigned),
        approval_id=approval_id,
        variant_id=variant_id,
        optimization_id=optimization_id,
        format="9:16",
        width=1080,
        height=1920,
        fps=int(fps),
        timeline_items=tuple(items),
        total_duration_seconds=round(duration, 3),
        handover_state=state,
        blockers=tuple(sorted(blockers)),
        schema="football-shorts-ai.factory-handover-package.v1",
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_id(payload: Mapping[str, object], key: str, prefix: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.startswith(prefix):
        raise FactoryHandoverError(f"{key} must start with {prefix}")
    return value


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise FactoryHandoverError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise FactoryHandoverError("evidence must be hexadecimal") from exc


__all__ = [
    "FactoryHandoverError",
    "FactoryHandoverPackage",
    "FactoryTimelineItem",
    "build_factory_handover_package",
    "canonical_sha256",
]
