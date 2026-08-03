"""
FOOTBALL-SHORTS-AI-0056J
EDITORIAL INTELLIGENCE FINAL CERTIFICATION

Executes deterministic owned-media and reference-only scenarios across 0056A-0056I.
No network, media acquisition, model execution, rendering, training or publication
is performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from editorial.automatic_timeline_builder import build_automatic_timeline
from editorial.editorial_quality_scoring import score_editorial_quality
from editorial.football_scene_understanding import build_football_scene_understanding
from editorial.performance_feedback_learning import build_performance_feedback_learning
from editorial.semantic_scene_indexer import build_semantic_scene_index
from editorial.story_alignment_optimizer import optimize_story_alignment
from editorial.story_scene_matching import build_story_scene_matching
from editorial.viral_hook_optimizer import optimize_viral_hook


class EditorialIntelligenceCertificationError(ValueError):
    """Raised when the 0056 certification evidence is incomplete or inconsistent."""


@dataclass(frozen=True)
class EditorialIntelligenceCertification:
    schema: str
    certification_id: str
    status: str
    owned_scenario: Mapping[str, object]
    reference_scenario: Mapping[str, object]
    dashboard_artifacts: tuple[str, ...]
    controls: Mapping[str, bool]
    evidence_sha256: str

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.editorial-intelligence-certification.v1":
            raise EditorialIntelligenceCertificationError("unsupported certification schema")
        if not self.certification_id.startswith("EDITORIALCERT-"):
            raise EditorialIntelligenceCertificationError("invalid certification identity")
        if self.status != "CERTIFIED":
            raise EditorialIntelligenceCertificationError("editorial intelligence is not certified")
        if self.owned_scenario.get("timeline_state") != "ready_for_review":
            raise EditorialIntelligenceCertificationError("owned scenario is not ready for review")
        if self.owned_scenario.get("score_state") != "scored":
            raise EditorialIntelligenceCertificationError("owned scenario is not scored")
        if self.reference_scenario.get("timeline_state") != "blocked":
            raise EditorialIntelligenceCertificationError("reference scenario must remain blocked")
        if self.reference_scenario.get("score_state") != "blocked":
            raise EditorialIntelligenceCertificationError("reference score must remain blocked")
        required = {
            "dashboard/editorial-review.html",
            "dashboard/assets/editorial-review.css",
            "dashboard/assets/editorial-review.js",
        }
        if not required.issubset(set(self.dashboard_artifacts)):
            raise EditorialIntelligenceCertificationError("editorial review dashboard artifacts are incomplete")
        if any(self.controls.values()):
            raise EditorialIntelligenceCertificationError("automatic or operational capability is enabled")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise EditorialIntelligenceCertificationError("certification evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "owned_scenario": dict(self.owned_scenario),
            "reference_scenario": dict(self.reference_scenario),
            "dashboard_artifacts": list(self.dashboard_artifacts),
            "controls": dict(self.controls),
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def certify_editorial_intelligence(*, repository_root: Path | str = Path(".")) -> EditorialIntelligenceCertification:
    root = Path(repository_root)
    owned = _run_scenario(rights_status="owned")
    reference = _run_scenario(rights_status="reference_only")
    artifacts = tuple(
        path
        for path in (
            "dashboard/editorial-review.html",
            "dashboard/assets/editorial-review.css",
            "dashboard/assets/editorial-review.js",
        )
        if (root / path).is_file()
    )
    controls = {
        "network_enabled": False,
        "model_execution_enabled": False,
        "acquisition_enabled": False,
        "analytics_fetch_enabled": False,
        "weight_update_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    core = {
        "schema": "football-shorts-ai.editorial-intelligence-certification.v1",
        "status": "CERTIFIED",
        "owned_scenario": owned,
        "reference_scenario": reference,
        "dashboard_artifacts": list(artifacts),
        "controls": controls,
    }
    provisional = canonical_sha256(core)
    certification_id = f"EDITORIALCERT-{provisional[:20].upper()}"
    unsigned = {**core, "certification_id": certification_id}
    evidence = canonical_sha256(unsigned)
    result = EditorialIntelligenceCertification(
        certification_id=certification_id,
        evidence_sha256=evidence,
        owned_scenario=owned,
        reference_scenario=reference,
        dashboard_artifacts=artifacts,
        controls=controls,
        **{key: value for key, value in unsigned.items() if key not in {"certification_id", "evidence_sha256", "owned_scenario", "reference_scenario", "dashboard_artifacts", "controls"}},
    )
    result.validate()
    return result


def _run_scenario(*, rights_status: str) -> dict[str, object]:
    render_allowed = rights_status == "owned"
    asset = {
        "asset_id": f"EXT-CERT-{rights_status.upper()}",
        "provider": "local_library" if render_allowed else "youtube",
        "provider_asset_id": f"cert-{rights_status}",
        "rights_status": rights_status,
        "preview_allowed": True,
        "render_allowed": render_allowed,
        "evidence_sha256": hashlib.sha256(rights_status.encode("utf-8")).hexdigest(),
    }
    segments = [
        {
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "scene_type": "shot",
            "shot_type": "close_up",
            "emotion": "surprise",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["hook", "shot", "spectacular"],
            "ball_visible": True,
            "face_visible": True,
            "motion_intensity": 0.98,
            "visual_quality": 0.94,
            "emotion_intensity": 0.96,
            "hook_potential": 0.99,
            "climax_potential": 0.72,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 5.0,
            "scene_type": "goal",
            "shot_type": "wide",
            "emotion": "celebration",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["goal", "net", "climax"],
            "ball_visible": True,
            "scoreboard_visible": True,
            "crowd_reaction": 0.99,
            "motion_intensity": 0.90,
            "visual_quality": 0.96,
            "emotion_intensity": 1.0,
            "hook_potential": 0.84,
            "climax_potential": 1.0,
        },
        {
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "scene_type": "celebration",
            "shot_type": "medium",
            "emotion": "joy",
            "players": ["Cristiano Ronaldo"],
            "teams": ["Portugal"],
            "competition": "UEFA Nations League",
            "semantic_tags": ["celebration", "crowd", "reaction"],
            "face_visible": True,
            "crowd_reaction": 0.96,
            "motion_intensity": 0.76,
            "visual_quality": 0.92,
            "emotion_intensity": 0.98,
            "hook_potential": 0.72,
            "climax_potential": 0.88,
        },
    ]
    story = {
        "beats": [
            {
                "role": "hook",
                "text": "Ninguém esperava este remate de Cristiano Ronaldo.",
                "keywords": ["remate", "surpresa", "shot"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["shot"],
                "emotions": ["surprise"],
            },
            {
                "role": "climax",
                "text": "A bola entrou e decidiu tudo.",
                "keywords": ["goal", "net", "climax"],
                "players": ["Cristiano Ronaldo"],
                "actions": ["goal"],
                "emotions": ["celebration"],
            },
            {
                "role": "reaction",
                "text": "O estádio explodiu na celebração.",
                "keywords": ["celebration", "crowd", "reaction"],
                "actions": ["celebration"],
                "emotions": ["joy"],
            },
        ]
    }

    index = build_semantic_scene_index(asset=asset, segments=segments)
    understanding = build_football_scene_understanding(index)
    matching = build_story_scene_matching(story=story, index=index, understanding=understanding)
    hook = optimize_viral_hook(matching=matching, index=index, understanding=understanding)
    alignment = optimize_story_alignment(matching=matching, hook=hook)
    score = score_editorial_quality(
        alignment=alignment,
        hook=hook,
        matching=matching,
        index=index,
        understanding=understanding,
    )
    timeline = build_automatic_timeline(
        title=f"0056 certification {rights_status}",
        alignment=alignment,
        score=score,
        index=index,
    )
    feedback = build_performance_feedback_learning(
        timeline=timeline,
        editorial_score=score,
        publication={
            "publication_id": f"PUB-{rights_status.upper()}",
            "platform": "youtube",
            "views": 2500,
            "likes": 180,
            "comments": 24,
            "shares": 35,
            "average_view_duration_seconds": min(7.0, timeline.total_duration_seconds),
            "retention_3s": 0.82,
            "retention_10s": 0.68,
            "completion_rate": 0.61,
            "impressions": 9000,
            "click_through_rate": 0.071,
        },
    )
    return {
        "scene_index_state": index.index_state,
        "understanding_state": understanding.report_state,
        "matching_state": matching.report_state,
        "hook_state": hook.optimization_state,
        "alignment_state": alignment.alignment_state,
        "score_state": score.score_state,
        "timeline_state": timeline.timeline_state,
        "learning_state": feedback.learning_state,
        "scene_count": len(index.scenes),
        "timeline_scene_count": len(timeline.scenes),
        "editorial_quality_score": score.editorial_quality_score,
        "viral_potential_score": score.viral_potential_score,
        "blockers": sorted(set((*index.blockers, *matching.blockers, *hook.blockers, *alignment.blockers, *score.blockers, *timeline.blockers))),
    }


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise EditorialIntelligenceCertificationError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise EditorialIntelligenceCertificationError("evidence must be hexadecimal") from exc


if __name__ == "__main__":
    certification = certify_editorial_intelligence()
    print(certification.status)
    print(f"CERTIFICATION_ID={certification.certification_id}")
    print(f"EVIDENCE_SHA256={certification.evidence_sha256}")
    for name, enabled in certification.controls.items():
        print(f"{name.upper()}={'ENABLED' if enabled else 'DISABLED'}")


__all__ = [
    "EditorialIntelligenceCertification",
    "EditorialIntelligenceCertificationError",
    "canonical_sha256",
    "certify_editorial_intelligence",
]
