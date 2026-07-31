"""
FOOTBALL-SHORTS-AI-0051B
BATCH PRODUCTION PLANNER

Deterministically selects and orders governed video candidates for a batch.
Provider neutral, auditable, and auto-publishing disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from factory.batch_video_generation_contract import (
    BatchVideoGenerationContract,
    BatchVideoItem,
)


class BatchPlanningError(ValueError):
    """Raised when a governed production batch cannot be planned safely."""


@dataclass(frozen=True)
class ProductionCandidate:
    video_id: str
    score: float
    production_ready: bool = True

    def validate(self) -> None:
        if not self.video_id.strip():
            raise BatchPlanningError("video_id is required")
        if not 0.0 <= self.score <= 1.0:
            raise BatchPlanningError("score must be between 0.0 and 1.0")


@dataclass(frozen=True)
class BatchProductionPlan:
    batch_id: str
    videos: Tuple[BatchVideoItem, ...]
    selection_policy: str = "highest_score_first"
    auto_publish: bool = False

    def validate(self) -> None:
        if not self.batch_id.strip():
            raise BatchPlanningError("batch_id is required")
        ids = [item.video_id for item in self.videos]
        if not ids:
            raise BatchPlanningError("at least one video is required")
        if len(ids) != len(set(ids)):
            raise BatchPlanningError("duplicate video_id values are not allowed")
        if self.auto_publish:
            raise BatchPlanningError("auto publishing must remain disabled")

    def to_contract(self) -> BatchVideoGenerationContract:
        self.validate()
        contract = BatchVideoGenerationContract(
            batch_id=self.batch_id,
            videos=list(self.videos),
            auto_publish=False,
        )
        if not contract.validate():
            raise BatchPlanningError("generated batch contract is invalid")
        return contract


def plan_batch(
    batch_id: str,
    candidates: Iterable[ProductionCandidate],
    *,
    limit: int,
) -> BatchProductionPlan:
    """Create a deterministic highest-score-first production plan.

    Ties are resolved by ``video_id`` so identical inputs always produce the same
    plan. Candidates that are not production-ready are excluded fail-closed.
    """

    if limit <= 0:
        raise BatchPlanningError("limit must be greater than zero")

    validated: list[ProductionCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate.validate()
        if candidate.video_id in seen:
            raise BatchPlanningError(
                f"duplicate candidate video_id: {candidate.video_id}"
            )
        seen.add(candidate.video_id)
        if candidate.production_ready:
            validated.append(candidate)

    ordered = sorted(validated, key=lambda item: (-item.score, item.video_id))
    selected = ordered[:limit]
    if not selected:
        raise BatchPlanningError("no production-ready candidates available")

    videos = tuple(
        BatchVideoItem(
            video_id=candidate.video_id,
            priority="high" if index == 0 else "medium",
            status="selected",
        )
        for index, candidate in enumerate(selected)
    )
    plan = BatchProductionPlan(batch_id=batch_id, videos=videos)
    plan.validate()
    return plan


__all__ = [
    "BatchPlanningError",
    "ProductionCandidate",
    "BatchProductionPlan",
    "plan_batch",
]
