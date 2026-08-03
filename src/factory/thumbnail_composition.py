"""FOOTBALL-SHORTS-AI-0060H — governed thumbnail composition and preview contract."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ThumbnailCompositionError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ThumbnailCandidate:
    candidate_id: str
    source_uri: str
    headline: str
    subheadline: str
    emotion: str
    focal_x: float
    focal_y: float
    crop_scale: float
    contrast_score: float
    face_visibility_score: float
    text_readability_score: float
    click_potential_score: float
    rights_status: str
    preview_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.candidate_id.startswith("THUMBCAND-"):
            raise ThumbnailCompositionError("invalid candidate identity")
        if self.rights_status not in {"owned", "licensed", "reference_only"}:
            raise ThumbnailCompositionError("unsupported rights status")
        for value in (self.focal_x, self.focal_y, self.contrast_score, self.face_visibility_score,
                      self.text_readability_score, self.click_potential_score):
            if not 0 <= value <= 1:
                raise ThumbnailCompositionError("score out of range")
        if not 0.5 <= self.crop_scale <= 3:
            raise ThumbnailCompositionError("crop scale out of range")
        if self.rights_status == "reference_only" and self.preview_allowed:
            raise ThumbnailCompositionError("reference-only thumbnail cannot be previewed")
        if self.preview_allowed and (not self.source_uri or self.blockers):
            raise ThumbnailCompositionError("allowed candidate must be complete")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ThumbnailCompositionError("blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "candidate_id": self.candidate_id,
            "source_uri": self.source_uri,
            "headline": self.headline,
            "subheadline": self.subheadline,
            "emotion": self.emotion,
            "focal_x": round(self.focal_x, 4),
            "focal_y": round(self.focal_y, 4),
            "crop_scale": round(self.crop_scale, 3),
            "contrast_score": round(self.contrast_score, 4),
            "face_visibility_score": round(self.face_visibility_score, 4),
            "text_readability_score": round(self.text_readability_score, 4),
            "click_potential_score": round(self.click_potential_score, 4),
            "rights_status": self.rights_status,
            "preview_allowed": self.preview_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ThumbnailComposition:
    schema: str
    composition_id: str
    source_variant_id: str
    candidates: tuple[ThumbnailCandidate, ...]
    selected_candidate_id: str | None
    composition_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    generation_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "composition_id": self.composition_id,
            "source_variant_id": self.source_variant_id,
            "candidates": [item.to_dict() for item in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "composition_state": self.composition_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "generation_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.thumbnail-composition.v1":
            raise ThumbnailCompositionError("unsupported schema")
        if not self.composition_id.startswith("THUMBCOMP-"):
            raise ThumbnailCompositionError("invalid composition identity")
        if self.composition_state not in {"composed", "review_required", "blocked"}:
            raise ThumbnailCompositionError("unsupported state")
        for item in self.candidates:
            item.validate()
        ids = {item.candidate_id for item in self.candidates}
        if self.selected_candidate_id is not None and self.selected_candidate_id not in ids:
            raise ThumbnailCompositionError("selected candidate missing")
        if self.composition_state == "composed" and (self.blockers or not self.selected_candidate_id):
            raise ThumbnailCompositionError("composed state requires selected candidate")
        if any((self.network_enabled, self.generation_enabled, self.acquisition_enabled,
                self.render_enabled, self.auto_publish)):
            raise ThumbnailCompositionError("0060H cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ThumbnailCompositionError("thumbnail evidence mismatch")


def build_thumbnail_composition(*, source_variant_id: str,
                                candidate_inputs: Sequence[Mapping[str, object]]) -> ThumbnailComposition:
    blockers: set[str] = set()
    if not source_variant_id.startswith("DIRVAR-"):
        blockers.add("APPROVED_VARIANT_MISSING")
    candidates: list[ThumbnailCandidate] = []
    for raw in candidate_inputs:
        candidate_blockers: set[str] = set()
        rights = str(raw.get("rights_status", "reference_only"))
        source_uri = str(raw.get("source_uri", ""))
        headline = str(raw.get("headline", "")).strip()
        if rights == "reference_only":
            candidate_blockers.add("THUMBNAIL_MEDIA_NOT_AUTHORIZED")
        if not source_uri:
            candidate_blockers.add("THUMBNAIL_SOURCE_MISSING")
        if not headline:
            candidate_blockers.add("THUMBNAIL_HEADLINE_MISSING")
        core = {
            "source_uri": source_uri,
            "headline": headline,
            "subheadline": str(raw.get("subheadline", "")).strip(),
            "emotion": str(raw.get("emotion", "neutral")),
            "focal_x": float(raw.get("focal_x", 0.5)),
            "focal_y": float(raw.get("focal_y", 0.5)),
            "crop_scale": float(raw.get("crop_scale", 1.0)),
            "contrast_score": float(raw.get("contrast_score", 0)),
            "face_visibility_score": float(raw.get("face_visibility_score", 0)),
            "text_readability_score": float(raw.get("text_readability_score", 0)),
            "click_potential_score": float(raw.get("click_potential_score", 0)),
            "rights_status": rights,
            "preview_allowed": not candidate_blockers,
            "blockers": tuple(sorted(candidate_blockers)),
        }
        candidate = ThumbnailCandidate(
            candidate_id=f"THUMBCAND-{canonical_sha256(core)[:20].upper()}", **core
        )
        candidate.validate()
        candidates.append(candidate)
    if not candidates:
        blockers.add("THUMBNAIL_CANDIDATES_MISSING")
    allowed = [item for item in candidates if item.preview_allowed]
    selected = max(allowed, key=lambda item: (
        item.click_potential_score, item.text_readability_score, item.contrast_score, item.candidate_id
    ), default=None)
    if candidates and not allowed:
        blockers.add("THUMBNAIL_REVIEW_REQUIRED")
    state = "blocked" if "APPROVED_VARIANT_MISSING" in blockers or not candidates else (
        "review_required" if blockers else "composed"
    )
    base = {
        "schema": "football-shorts-ai.thumbnail-composition.v1",
        "source_variant_id": source_variant_id,
        "candidates": [item.to_dict() for item in candidates],
        "selected_candidate_id": selected.candidate_id if selected else None,
        "composition_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "generation_enabled": False,
        "acquisition_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    composition_id = f"THUMBCOMP-{canonical_sha256(base)[:20].upper()}"
    unsigned = {**base, "composition_id": composition_id}
    result = ThumbnailComposition(
        schema=base["schema"], composition_id=composition_id,
        source_variant_id=source_variant_id, candidates=tuple(candidates),
        selected_candidate_id=base["selected_candidate_id"], composition_state=state,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["ThumbnailCandidate", "ThumbnailComposition", "ThumbnailCompositionError",
           "build_thumbnail_composition", "canonical_sha256"]
