"""
FOOTBALL-SHORTS-AI-0057G
CINEMATIC AND VISUAL QUALITY ANALYSIS CONTRACT

Deterministic, reviewable scene-quality evidence derived from 0057A vision scenes.
No network, acquisition, model training, rendering or publication is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_vision_pipeline import FootballVisionReport


class CinematicVisualQualityError(ValueError):
    pass


SUPPORTED_STATES = {"analyzed", "review_required", "blocked"}


@dataclass(frozen=True)
class SceneVisualQuality:
    scene_id: str
    sharpness_score: float
    stability_score: float
    exposure_score: float
    contrast_score: float
    framing_score: float
    scoreboard_legibility_score: float
    subject_visibility_score: float
    ball_visibility_score: float
    vertical_crop_score: float
    cinematic_score: float
    visual_quality_score: float
    hook_visual_score: float
    confidence: float
    evidence_frame_ids: tuple[str, ...]
    review_required: bool

    def validate(self, vision: FootballVisionReport) -> None:
        scene_ids = {scene.scene_id for scene in vision.scenes}
        frame_ids = {frame.frame_id for frame in vision.frames}
        if self.scene_id not in scene_ids:
            raise CinematicVisualQualityError("unknown scene_id")
        for name, value in self.__dict__.items():
            if name.endswith("_score") or name == "confidence":
                if not 0.0 <= float(value) <= 1.0:
                    raise CinematicVisualQualityError(f"{name} must be between 0 and 1")
        if not self.evidence_frame_ids or any(item not in frame_ids for item in self.evidence_frame_ids):
            raise CinematicVisualQualityError("valid evidence frames are required")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "sharpness_score": round(self.sharpness_score, 4),
            "stability_score": round(self.stability_score, 4),
            "exposure_score": round(self.exposure_score, 4),
            "contrast_score": round(self.contrast_score, 4),
            "framing_score": round(self.framing_score, 4),
            "scoreboard_legibility_score": round(self.scoreboard_legibility_score, 4),
            "subject_visibility_score": round(self.subject_visibility_score, 4),
            "ball_visibility_score": round(self.ball_visibility_score, 4),
            "vertical_crop_score": round(self.vertical_crop_score, 4),
            "cinematic_score": round(self.cinematic_score, 4),
            "visual_quality_score": round(self.visual_quality_score, 4),
            "hook_visual_score": round(self.hook_visual_score, 4),
            "confidence": round(self.confidence, 4),
            "evidence_frame_ids": list(self.evidence_frame_ids),
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class CinematicVisualQualityReport:
    schema: str
    quality_id: str
    vision_report_id: str
    provider_name: str
    scenes: tuple[SceneVisualQuality, ...]
    best_visual_scene_id: str | None
    best_hook_visual_scene_id: str | None
    average_visual_quality_score: float
    quality_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport) -> None:
        vision.validate()
        if self.schema != "football-shorts-ai.cinematic-visual-quality.v1":
            raise CinematicVisualQualityError("unsupported schema")
        if not self.quality_id.startswith("VISQUAL-"):
            raise CinematicVisualQualityError("invalid quality identity")
        if self.vision_report_id != vision.report_id:
            raise CinematicVisualQualityError("vision identity mismatch")
        if self.quality_state not in SUPPORTED_STATES:
            raise CinematicVisualQualityError("unsupported quality state")
        for scene in self.scenes:
            scene.validate(vision)
        scene_ids = {scene.scene_id for scene in self.scenes}
        for selected in (self.best_visual_scene_id, self.best_hook_visual_scene_id):
            if selected is not None and selected not in scene_ids:
                raise CinematicVisualQualityError("selected scene is unknown")
        if not 0.0 <= self.average_visual_quality_score <= 1.0:
            raise CinematicVisualQualityError("average score must be between 0 and 1")
        if self.quality_state == "analyzed" and (self.blockers or not self.scenes):
            raise CinematicVisualQualityError("analyzed report requires unblocked scenes")
        if self.quality_state in {"review_required", "blocked"} and not self.blockers:
            raise CinematicVisualQualityError("non-ready report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise CinematicVisualQualityError("0057G cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise CinematicVisualQualityError("quality evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "quality_id": self.quality_id,
            "vision_report_id": self.vision_report_id,
            "provider_name": self.provider_name,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "best_visual_scene_id": self.best_visual_scene_id,
            "best_hook_visual_scene_id": self.best_hook_visual_scene_id,
            "average_visual_quality_score": self.average_visual_quality_score,
            "quality_state": self.quality_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_cinematic_visual_quality_report(*, vision: FootballVisionReport, provider_name: str,
                                           measurements: Sequence[Mapping[str, object]] = (),
                                           minimum_confidence: float = 0.70) -> CinematicVisualQualityReport:
    vision.validate()
    if not 0.0 <= minimum_confidence <= 1.0:
        raise CinematicVisualQualityError("minimum_confidence must be between 0 and 1")
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    parsed = tuple(_scene(item, minimum_confidence) for item in measurements)
    if vision.pipeline_state == "analyzed" and not parsed:
        blockers.add("VISUAL_QUALITY_EVIDENCE_MISSING")
    if any(item.review_required for item in parsed):
        blockers.add("VISUAL_QUALITY_REVIEW_REQUIRED")
    state = "blocked" if vision.pipeline_state != "analyzed" or not parsed else ("review_required" if blockers else "analyzed")
    best_visual = max(parsed, key=lambda item: (item.visual_quality_score, item.scene_id), default=None)
    best_hook = max(parsed, key=lambda item: (item.hook_visual_score, item.scene_id), default=None)
    average = round(sum(item.visual_quality_score for item in parsed) / len(parsed), 4) if parsed else 0.0
    core = {
        "schema": "football-shorts-ai.cinematic-visual-quality.v1",
        "vision_report_id": vision.report_id,
        "provider_name": provider_name.strip(),
        "scenes": [item.to_dict() for item in parsed],
        "best_visual_scene_id": None if best_visual is None else best_visual.scene_id,
        "best_hook_visual_scene_id": None if best_hook is None else best_hook.scene_id,
        "average_visual_quality_score": average,
        "quality_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    quality_id = f"VISQUAL-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "quality_id": quality_id}
    result = CinematicVisualQualityReport(
        quality_id=quality_id,
        evidence_sha256=canonical_sha256(unsigned),
        vision_report_id=vision.report_id,
        provider_name=provider_name.strip(),
        scenes=parsed,
        best_visual_scene_id=core["best_visual_scene_id"],
        best_hook_visual_scene_id=core["best_hook_visual_scene_id"],
        average_visual_quality_score=average,
        quality_state=state,
        blockers=tuple(sorted(blockers)),
        schema=core["schema"],
    )
    result.validate(vision)
    return result


def _scene(item: Mapping[str, object], minimum_confidence: float) -> SceneVisualQuality:
    values = {name: float(item.get(name, 0.0)) for name in (
        "sharpness_score", "stability_score", "exposure_score", "contrast_score",
        "framing_score", "scoreboard_legibility_score", "subject_visibility_score",
        "ball_visibility_score", "vertical_crop_score", "confidence")}
    cinematic = round(0.22 * values["framing_score"] + 0.20 * values["stability_score"] +
                      0.18 * values["contrast_score"] + 0.20 * values["exposure_score"] +
                      0.20 * values["vertical_crop_score"], 4)
    visual = round(0.25 * values["sharpness_score"] + 0.18 * values["stability_score"] +
                   0.15 * values["exposure_score"] + 0.12 * values["contrast_score"] +
                   0.15 * values["subject_visibility_score"] + 0.15 * values["ball_visibility_score"], 4)
    hook = round(0.35 * visual + 0.30 * cinematic + 0.20 * values["subject_visibility_score"] +
                 0.15 * values["ball_visibility_score"], 4)
    return SceneVisualQuality(
        scene_id=str(item["scene_id"]),
        cinematic_score=cinematic,
        visual_quality_score=visual,
        hook_visual_score=hook,
        evidence_frame_ids=tuple(str(value) for value in item.get("evidence_frame_ids", ())),
        review_required=values["confidence"] < minimum_confidence,
        **values,
    )


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise CinematicVisualQualityError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CinematicVisualQualityError("evidence must be hexadecimal") from exc


__all__ = ["CinematicVisualQualityError", "SceneVisualQuality", "CinematicVisualQualityReport",
           "build_cinematic_visual_quality_report", "canonical_sha256"]
