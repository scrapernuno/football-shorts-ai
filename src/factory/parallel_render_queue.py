"""
FOOTBALL-SHORTS-AI-0051C
PARALLEL RENDER QUEUE

Deterministic, provider-neutral queue state for governed batch rendering.
The module does not execute FFmpeg, perform network access, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Tuple

from factory.batch_production_planner import BatchProductionPlan


class RenderQueueError(ValueError):
    """Raised when a render queue transition is invalid or unsafe."""


_ALLOWED_STATES = frozenset(
    {
        "pending",
        "validated",
        "rendering",
        "completed",
        "failed",
        "retry",
    }
)

_ALLOWED_TRANSITIONS = {
    "pending": frozenset({"validated", "failed"}),
    "validated": frozenset({"rendering", "failed"}),
    "rendering": frozenset({"completed", "failed"}),
    "failed": frozenset({"retry"}),
    "retry": frozenset({"validated", "failed"}),
    "completed": frozenset(),
}


@dataclass(frozen=True)
class RenderQueueItem:
    video_id: str
    priority: int
    status: str = "pending"
    attempts: int = 0
    error_code: str | None = None

    def validate(self) -> None:
        if not self.video_id.strip():
            raise RenderQueueError("video_id is required")
        if self.priority <= 0:
            raise RenderQueueError("priority must be greater than zero")
        if self.status not in _ALLOWED_STATES:
            raise RenderQueueError(f"unsupported queue status: {self.status}")
        if self.attempts < 0:
            raise RenderQueueError("attempts cannot be negative")
        if self.status == "failed" and not self.error_code:
            raise RenderQueueError("failed items require error_code")
        if self.status != "failed" and self.error_code is not None:
            raise RenderQueueError("error_code is only allowed for failed items")


@dataclass(frozen=True)
class ParallelRenderQueue:
    queue_id: str
    batch_id: str
    items: Tuple[RenderQueueItem, ...]
    max_parallel: int = 3
    auto_publish: bool = False

    def validate(self) -> None:
        if not self.queue_id.strip():
            raise RenderQueueError("queue_id is required")
        if not self.batch_id.strip():
            raise RenderQueueError("batch_id is required")
        if self.max_parallel <= 0:
            raise RenderQueueError("max_parallel must be greater than zero")
        if self.auto_publish:
            raise RenderQueueError("auto publishing must remain disabled")
        if not self.items:
            raise RenderQueueError("queue must contain at least one item")

        ids = [item.video_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise RenderQueueError("duplicate video_id values are not allowed")

        priorities = [item.priority for item in self.items]
        if len(priorities) != len(set(priorities)):
            raise RenderQueueError("queue priorities must be unique")

        for item in self.items:
            item.validate()

        rendering_count = sum(item.status == "rendering" for item in self.items)
        if rendering_count > self.max_parallel:
            raise RenderQueueError("parallel render limit exceeded")

    def transition(
        self,
        video_id: str,
        target_status: str,
        *,
        error_code: str | None = None,
    ) -> "ParallelRenderQueue":
        if target_status not in _ALLOWED_STATES:
            raise RenderQueueError(f"unsupported target status: {target_status}")

        updated: list[RenderQueueItem] = []
        found = False
        for item in self.items:
            if item.video_id != video_id:
                updated.append(item)
                continue

            found = True
            if target_status not in _ALLOWED_TRANSITIONS[item.status]:
                raise RenderQueueError(
                    f"invalid transition for {video_id}: "
                    f"{item.status} -> {target_status}"
                )

            next_attempts = item.attempts + (1 if target_status == "rendering" else 0)
            next_error = error_code if target_status == "failed" else None
            updated.append(
                replace(
                    item,
                    status=target_status,
                    attempts=next_attempts,
                    error_code=next_error,
                )
            )

        if not found:
            raise RenderQueueError(f"video_id not found in queue: {video_id}")

        queue = replace(self, items=tuple(updated))
        queue.validate()
        return queue

    def next_pending(self) -> Tuple[RenderQueueItem, ...]:
        """Return deterministic pending work without mutating queue state."""

        available_slots = self.max_parallel - sum(
            item.status == "rendering" for item in self.items
        )
        if available_slots <= 0:
            return tuple()

        candidates = sorted(
            (
                item
                for item in self.items
                if item.status in {"pending", "retry"}
            ),
            key=lambda item: (item.priority, item.video_id),
        )
        return tuple(candidates[:available_slots])


def build_render_queue(
    queue_id: str,
    plan: BatchProductionPlan,
    *,
    max_parallel: int = 3,
) -> ParallelRenderQueue:
    """Build a deterministic render queue from a validated production plan."""

    plan.validate()
    items = tuple(
        RenderQueueItem(
            video_id=item.video_id,
            priority=index,
            status="pending",
        )
        for index, item in enumerate(plan.videos, start=1)
    )
    queue = ParallelRenderQueue(
        queue_id=queue_id,
        batch_id=plan.batch_id,
        items=items,
        max_parallel=max_parallel,
        auto_publish=False,
    )
    queue.validate()
    return queue


def queue_status_counts(
    items: Iterable[RenderQueueItem],
) -> dict[str, int]:
    counts = {state: 0 for state in sorted(_ALLOWED_STATES)}
    for item in items:
        item.validate()
        counts[item.status] += 1
    return counts


__all__ = [
    "RenderQueueError",
    "RenderQueueItem",
    "ParallelRenderQueue",
    "build_render_queue",
    "queue_status_counts",
]
