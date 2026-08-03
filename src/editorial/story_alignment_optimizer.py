"""
FOOTBALL-SHORTS-AI-0056E
STORY ALIGNMENT AND SCENE SEQUENCE OPTIMIZER

Builds a deterministic editorial scene sequence from 0056C story matches and the
0056D hook decision. It avoids unnecessary repetition, preserves narrative order
and emits reviewable alignment evidence only. No media, model or publishing
operation is executed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from editorial.story_scene_matching import StorySceneMatchingReport
from editorial.viral_hook_optimizer import ViralHookOptimizationReport


class StoryAlignmentError(ValueError):
    """Raised when governed story alignment evidence is invalid."""


@dataclass(frozen=True)
class AlignedScene:
    order: int
    beat_id: str
    beat_role: str
    beat_text: str
    scene_id: str
    source_rank: int
    match_score: float
    transition: str
    repeated_scene: bool
    render_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if self.order < 1:
            raise StoryAlignmentError("aligned scene order must be positive")
        if not self.beat_id.startswith("BEAT-"):
            raise StoryAlignmentError("invalid beat identity")
        if not self.beat_role.strip() or not self.beat_text.strip():
            raise StoryAlignmentError("beat role and text are required")
        if not self.scene_id.startswith("SCENE-"):
            raise StoryAlignmentError("invalid aligned scene identity")
        if self.source_rank < 1:
            raise StoryAlignmentError("source rank must be positive")
        if not 0.0 <= self.match_score <= 1.0:
            raise StoryAlignmentError("match score must be between 0 and 1")
        if self.transition not in {"cut", "fade", "crossfade", "zoom", "none"}:
            raise StoryAlignmentError("unsupported alignment transition")
        if self.render_allowed and self.blockers:
            raise StoryAlignmentError("renderable aligned scene cannot contain blockers")
        if not self.render_allowed and not self.blockers:
            raise StoryAlignmentError("non-renderable aligned scene requires blockers")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "order": self.order,
            "beat_id": self.beat_id,
            "beat_role": self.beat_role,
            "beat_text": self.beat_text,
            "scene_id": self.scene_id,
            "source_rank": self.source_rank,
            "match_score": self.match_score,
            "transition": self.transition,
            "repeated_scene": self.repeated_scene,
            "render_allowed": self.render_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class StoryAlignmentReport:
    schema: str
    alignment_id: str
    story_match_report_id: str
    hook_optimization_id: str
    scenes: tuple[AlignedScene, ...]
    selected_scene_ids: tuple[str, ...]
    repeated_scene_count: int
    average_match_score: float
    narrative_progression_score: float
    sequence_diversity_score: float
    alignment_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    model_execution_enabled: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.story-alignment.v1":
            raise StoryAlignmentError("unsupported alignment schema")
        if not self.alignment_id.startswith("ALIGN-"):
            raise StoryAlignmentError("invalid alignment identity")
        if not self.story_match_report_id.startswith("STORYMATCH-"):
            raise StoryAlignmentError("invalid story matching identity")
        if not self.hook_optimization_id.startswith("HOOKOPT-"):
            raise StoryAlignmentError("invalid hook optimization identity")
        if not self.scenes:
            raise StoryAlignmentError("alignment requires scenes")
        for expected_order, scene in enumerate(self.scenes, start=1):
            scene.validate()
            if scene.order != expected_order:
                raise StoryAlignmentError("aligned scene order must be contiguous")
        if self.selected_scene_ids != tuple(scene.scene_id for scene in self.scenes):
            raise StoryAlignmentError("selected scene identities are inconsistent")
        expected_repeats = len(self.selected_scene_ids) - len(set(self.selected_scene_ids))
        if self.repeated_scene_count != expected_repeats:
            raise StoryAlignmentError("repeated scene count is inconsistent")
        for name, value in (
            ("average_match_score", self.average_match_score),
            ("narrative_progression_score", self.narrative_progression_score),
            ("sequence_diversity_score", self.sequence_diversity_score),
        ):
            if not 0.0 <= value <= 1.0:
                raise StoryAlignmentError(f"{name} must be between 0 and 1")
        if self.alignment_state not in {"aligned", "blocked"}:
            raise StoryAlignmentError("unsupported alignment state")
        if self.alignment_state == "aligned" and self.blockers:
            raise StoryAlignmentError("aligned report cannot contain blockers")
        if self.alignment_state == "blocked" and not self.blockers:
            raise StoryAlignmentError("blocked report requires blockers")
        if any((
            self.model_execution_enabled,
            self.network_enabled,
            self.acquisition_enabled,
            self.auto_render,
            self.auto_publish,
        )):
            raise StoryAlignmentError("0056E cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise StoryAlignmentError("alignment evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "alignment_id": self.alignment_id,
            "story_match_report_id": self.story_match_report_id,
            "hook_optimization_id": self.hook_optimization_id,
            "scenes": [scene.to_dict() for scene in self.scenes],
            "selected_scene_ids": list(self.selected_scene_ids),
            "repeated_scene_count": self.repeated_scene_count,
            "average_match_score": self.average_match_score,
            "narrative_progression_score": self.narrative_progression_score,
            "sequence_diversity_score": self.sequence_diversity_score,
            "alignment_state": self.alignment_state,
            "blockers": list(self.blockers),
            "model_execution_enabled": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def optimize_story_alignment(
    *,
    matching: StorySceneMatchingReport,
    hook: ViralHookOptimizationReport,
    allow_scene_reuse: bool = False,
) -> StoryAlignmentReport:
    """Create a governed narrative sequence from the matched story beats."""

    if hook.story_match_report_id != matching.report_id:
        raise StoryAlignmentError("hook optimization does not belong to matching report")
    matching.to_dict()
    hook.validate()

    used: set[str] = set()
    aligned: list[AlignedScene] = []
    blockers: set[str] = set(matching.blockers) | set(hook.blockers)

    for order, match in enumerate(matching.matches, start=1):
        if match.beat.role == "hook":
            selected_id = hook.selected_scene_id
            candidate = next(
                (item for item in match.candidates if item.scene_id == selected_id),
                None,
            )
            if candidate is None:
                raise StoryAlignmentError("optimized hook scene is absent from hook beat")
        else:
            candidate = _choose_candidate(
                match.candidates,
                used=used,
                allow_scene_reuse=allow_scene_reuse,
            )
            selected_id = candidate.scene_id

        repeated = selected_id in used
        if repeated and not allow_scene_reuse:
            blockers.add(f"UNAVOIDABLE_SCENE_REUSE:{match.beat.beat_id}")
        used.add(selected_id)

        scene_blockers = tuple(candidate.blockers)
        blockers.update(scene_blockers)
        aligned.append(
            AlignedScene(
                order=order,
                beat_id=match.beat.beat_id,
                beat_role=match.beat.role,
                beat_text=match.beat.text,
                scene_id=selected_id,
                source_rank=candidate.rank,
                match_score=round(float(candidate.total_score), 4),
                transition=_transition_for(order, match.beat.role),
                repeated_scene=repeated,
                render_allowed=candidate.render_allowed,
                blockers=scene_blockers,
            )
        )

    selected_ids = tuple(scene.scene_id for scene in aligned)
    repeated_count = len(selected_ids) - len(set(selected_ids))
    average_match = round(sum(scene.match_score for scene in aligned) / len(aligned), 4)
    progression = _progression_score(tuple(scene.beat_role for scene in aligned))
    diversity = round(len(set(selected_ids)) / len(selected_ids), 4)
    state = "blocked" if blockers else "aligned"

    core = {
        "schema": "football-shorts-ai.story-alignment.v1",
        "story_match_report_id": matching.report_id,
        "hook_optimization_id": hook.optimization_id,
        "scenes": [scene.to_dict() for scene in aligned],
        "selected_scene_ids": list(selected_ids),
        "repeated_scene_count": repeated_count,
        "average_match_score": average_match,
        "narrative_progression_score": progression,
        "sequence_diversity_score": diversity,
        "alignment_state": state,
        "blockers": sorted(blockers),
        "model_execution_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    alignment_id = f"ALIGN-{provisional[:20].upper()}"
    unsigned = {**core, "alignment_id": alignment_id}
    evidence = canonical_sha256(unsigned)
    result = StoryAlignmentReport(
        alignment_id=alignment_id,
        evidence_sha256=evidence,
        scenes=tuple(aligned),
        selected_scene_ids=selected_ids,
        blockers=tuple(unsigned["blockers"]),
        **{
            key: value
            for key, value in unsigned.items()
            if key not in {"alignment_id", "evidence_sha256", "scenes", "selected_scene_ids", "blockers"}
        },
    )
    result.validate()
    return result


def _choose_candidate(candidates, *, used: set[str], allow_scene_reuse: bool):
    renderable = [item for item in candidates if item.render_allowed]
    pool = renderable or list(candidates)
    if not allow_scene_reuse:
        fresh = [item for item in pool if item.scene_id not in used]
        if fresh:
            return fresh[0]
    return pool[0]


def _transition_for(order: int, role: str) -> str:
    if order == 1:
        return "none"
    if role in {"climax", "reaction"}:
        return "cut"
    if role in {"resolution", "cta"}:
        return "fade"
    return "crossfade"


def _progression_score(roles: tuple[str, ...]) -> float:
    expected = {
        "hook": 0,
        "context": 1,
        "development": 2,
        "climax": 3,
        "reaction": 4,
        "resolution": 5,
        "cta": 6,
    }
    values = [expected.get(role, 0) for role in roles]
    if len(values) == 1:
        return 1.0
    forward = sum(1 for left, right in zip(values, values[1:]) if right >= left)
    return round(forward / (len(values) - 1), 4)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise StoryAlignmentError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise StoryAlignmentError("evidence must be hexadecimal") from exc


__all__ = [
    "AlignedScene",
    "StoryAlignmentError",
    "StoryAlignmentReport",
    "canonical_sha256",
    "optimize_story_alignment",
]
