"""
FOOTBALL-SHORTS-AI-0052A
REAL BATCH FACTORY ACTIVATION

Binds a governed batch production plan and parallel render queue to concrete,
deterministic render requests for multiple Shorts.

This module prepares real render work but does not execute FFmpeg, access the
network, publish content, or mutate queue state implicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from factory.batch_production_planner import BatchProductionPlan
from factory.parallel_render_queue import ParallelRenderQueue, RenderQueueItem
from video.first_real_render import RenderRequest


class RealBatchActivationError(ValueError):
    """Raised when a real batch cannot be activated safely."""


@dataclass(frozen=True)
class ActivatedRenderWork:
    """One concrete render request bound to governed queue metadata."""

    video_id: str
    production_id: str
    queue_id: str
    batch_id: str
    priority: int
    queue_status: str
    render_request: RenderRequest
    auto_publish: bool = False

    def validate(self) -> None:
        if not self.video_id.strip():
            raise RealBatchActivationError("video_id is required")
        if not self.production_id.strip():
            raise RealBatchActivationError("production_id is required")
        if not self.queue_id.strip():
            raise RealBatchActivationError("queue_id is required")
        if not self.batch_id.strip():
            raise RealBatchActivationError("batch_id is required")
        if self.priority <= 0:
            raise RealBatchActivationError("priority must be greater than zero")
        if self.queue_status not in {"pending", "retry"}:
            raise RealBatchActivationError(
                "activated work must originate from pending or retry state"
            )
        if self.auto_publish:
            raise RealBatchActivationError("auto publishing must remain disabled")
        if self.render_request.video_id != self.video_id:
            raise RealBatchActivationError("render request video_id mismatch")
        if self.render_request.production_id != self.production_id:
            raise RealBatchActivationError("render request production_id mismatch")
        if self.render_request.format != "vertical_9_16":
            raise RealBatchActivationError("unsupported render format")
        if self.render_request.resolution != "1080x1920":
            raise RealBatchActivationError("unsupported render resolution")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "video_id": self.video_id,
            "production_id": self.production_id,
            "queue_id": self.queue_id,
            "batch_id": self.batch_id,
            "priority": self.priority,
            "queue_status": self.queue_status,
            "render_request": {
                "video_id": self.render_request.video_id,
                "production_id": self.render_request.production_id,
                "format": self.render_request.format,
                "resolution": self.render_request.resolution,
                "status": self.render_request.status,
            },
            "auto_publish": False,
        }


@dataclass(frozen=True)
class RealBatchActivation:
    """Deterministic activation result for the next available render slots."""

    activation_schema: str
    batch_id: str
    queue_id: str
    max_parallel: int
    work_items: Tuple[ActivatedRenderWork, ...]
    total_planned_videos: int
    activated_videos: int
    remaining_videos: int
    auto_publish: bool = False

    def validate(self) -> None:
        if self.activation_schema != "football-shorts-ai.real-batch-activation.v1":
            raise RealBatchActivationError("unsupported activation schema")
        if not self.batch_id.strip():
            raise RealBatchActivationError("batch_id is required")
        if not self.queue_id.strip():
            raise RealBatchActivationError("queue_id is required")
        if self.max_parallel <= 0:
            raise RealBatchActivationError("max_parallel must be greater than zero")
        if self.auto_publish:
            raise RealBatchActivationError("auto publishing must remain disabled")
        if self.activated_videos != len(self.work_items):
            raise RealBatchActivationError("activated_videos count mismatch")
        if self.activated_videos > self.max_parallel:
            raise RealBatchActivationError("activation exceeds parallel limit")
        if self.total_planned_videos <= 0:
            raise RealBatchActivationError("total_planned_videos must be positive")
        if self.remaining_videos != self.total_planned_videos - self.activated_videos:
            raise RealBatchActivationError("remaining_videos count mismatch")

        video_ids = [item.video_id for item in self.work_items]
        if len(video_ids) != len(set(video_ids)):
            raise RealBatchActivationError("duplicate activated video_id values")

        priorities = [item.priority for item in self.work_items]
        if priorities != sorted(priorities):
            raise RealBatchActivationError("work items are not priority ordered")

        for item in self.work_items:
            item.validate()
            if item.batch_id != self.batch_id:
                raise RealBatchActivationError("work item batch_id mismatch")
            if item.queue_id != self.queue_id:
                raise RealBatchActivationError("work item queue_id mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "activation_schema": self.activation_schema,
            "batch_id": self.batch_id,
            "queue_id": self.queue_id,
            "max_parallel": self.max_parallel,
            "work_items": [item.to_dict() for item in self.work_items],
            "summary": {
                "total_planned_videos": self.total_planned_videos,
                "activated_videos": self.activated_videos,
                "remaining_videos": self.remaining_videos,
            },
            "auto_publish": False,
        }


def _default_production_id(video_id: str) -> str:
    normalized = video_id.strip().upper().replace("VID-", "")
    if not normalized:
        raise RealBatchActivationError("cannot derive production_id")
    return f"PRODUCTION-{normalized}"


def _validate_plan_queue_alignment(
    plan: BatchProductionPlan,
    queue: ParallelRenderQueue,
) -> None:
    plan.validate()
    queue.validate()

    if plan.batch_id != queue.batch_id:
        raise RealBatchActivationError("plan and queue batch_id values differ")

    plan_ids = tuple(item.video_id for item in plan.videos)
    queue_ids = tuple(item.video_id for item in queue.items)
    if set(plan_ids) != set(queue_ids):
        raise RealBatchActivationError("plan and queue video sets differ")

    if plan.auto_publish or queue.auto_publish:
        raise RealBatchActivationError("auto publishing must remain disabled")


def _build_work_item(
    queue: ParallelRenderQueue,
    item: RenderQueueItem,
    production_ids: Mapping[str, str],
) -> ActivatedRenderWork:
    production_id = production_ids.get(item.video_id) or _default_production_id(
        item.video_id
    )
    request = RenderRequest(
        video_id=item.video_id,
        production_id=production_id,
        format="vertical_9_16",
        resolution="1080x1920",
        status="READY",
    )
    work = ActivatedRenderWork(
        video_id=item.video_id,
        production_id=production_id,
        queue_id=queue.queue_id,
        batch_id=queue.batch_id,
        priority=item.priority,
        queue_status=item.status,
        render_request=request,
        auto_publish=False,
    )
    work.validate()
    return work


def activate_real_batch(
    plan: BatchProductionPlan,
    queue: ParallelRenderQueue,
    *,
    production_ids: Mapping[str, str] | None = None,
) -> RealBatchActivation:
    """Prepare concrete render requests for the queue's available slots.

    The returned activation is read-only. Callers must explicitly perform queue
    transitions and execute rendering in later governed stages.
    """

    _validate_plan_queue_alignment(plan, queue)
    resolved_ids = dict(production_ids or {})

    unknown_ids = set(resolved_ids) - {item.video_id for item in plan.videos}
    if unknown_ids:
        unknown = ", ".join(sorted(unknown_ids))
        raise RealBatchActivationError(
            f"production_ids contains unknown video_id values: {unknown}"
        )

    next_items = queue.next_pending()
    work_items = tuple(
        _build_work_item(queue, item, resolved_ids) for item in next_items
    )

    activation = RealBatchActivation(
        activation_schema="football-shorts-ai.real-batch-activation.v1",
        batch_id=plan.batch_id,
        queue_id=queue.queue_id,
        max_parallel=queue.max_parallel,
        work_items=work_items,
        total_planned_videos=len(plan.videos),
        activated_videos=len(work_items),
        remaining_videos=len(plan.videos) - len(work_items),
        auto_publish=False,
    )
    activation.validate()
    return activation


__all__ = [
    "RealBatchActivationError",
    "ActivatedRenderWork",
    "RealBatchActivation",
    "activate_real_batch",
]
