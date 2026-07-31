"""
FOOTBALL-SHORTS-AI-0051D
BATCH DASHBOARD MANAGEMENT

Transforms governed parallel render queue state into a deterministic,
read-only dashboard model. This module does not render video, access the
network, mutate queue state, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from factory.parallel_render_queue import (
    ParallelRenderQueue,
    RenderQueueItem,
    queue_status_counts,
)


class BatchDashboardError(ValueError):
    """Raised when a safe dashboard projection cannot be produced."""


_TERMINAL_STATES = frozenset({"completed", "failed"})


@dataclass(frozen=True)
class DashboardVideoRow:
    video_id: str
    priority: int
    status: str
    attempts: int
    progress_percent: int
    error_code: str | None = None

    def validate(self) -> None:
        if not self.video_id.strip():
            raise BatchDashboardError("video_id is required")
        if self.priority <= 0:
            raise BatchDashboardError("priority must be greater than zero")
        if self.attempts < 0:
            raise BatchDashboardError("attempts cannot be negative")
        if not 0 <= self.progress_percent <= 100:
            raise BatchDashboardError("progress_percent must be between 0 and 100")
        if self.status == "failed" and not self.error_code:
            raise BatchDashboardError("failed rows require error_code")
        if self.status != "failed" and self.error_code is not None:
            raise BatchDashboardError(
                "error_code is only allowed for failed rows"
            )


@dataclass(frozen=True)
class BatchDashboardModel:
    dashboard_schema: str
    queue_id: str
    batch_id: str
    max_parallel: int
    videos: Tuple[DashboardVideoRow, ...]
    status_counts: Mapping[str, int]
    total_videos: int
    completed_videos: int
    failed_videos: int
    active_renders: int
    completion_percent: int
    batch_status: str
    auto_publish: bool = False

    def validate(self) -> None:
        if self.dashboard_schema != "football-shorts-ai.batch-dashboard.v1":
            raise BatchDashboardError("unsupported dashboard schema")
        if not self.queue_id.strip():
            raise BatchDashboardError("queue_id is required")
        if not self.batch_id.strip():
            raise BatchDashboardError("batch_id is required")
        if self.max_parallel <= 0:
            raise BatchDashboardError("max_parallel must be greater than zero")
        if self.auto_publish:
            raise BatchDashboardError("auto publishing must remain disabled")
        if not self.videos:
            raise BatchDashboardError("dashboard requires at least one video")

        ids = [row.video_id for row in self.videos]
        if len(ids) != len(set(ids)):
            raise BatchDashboardError("duplicate video_id values are not allowed")

        for row in self.videos:
            row.validate()

        if self.total_videos != len(self.videos):
            raise BatchDashboardError("total_videos does not match video rows")
        if self.completed_videos != self.status_counts.get("completed", 0):
            raise BatchDashboardError("completed_videos count mismatch")
        if self.failed_videos != self.status_counts.get("failed", 0):
            raise BatchDashboardError("failed_videos count mismatch")
        if self.active_renders != self.status_counts.get("rendering", 0):
            raise BatchDashboardError("active_renders count mismatch")
        if self.active_renders > self.max_parallel:
            raise BatchDashboardError("active render count exceeds queue limit")
        if not 0 <= self.completion_percent <= 100:
            raise BatchDashboardError(
                "completion_percent must be between 0 and 100"
            )
        if self.batch_status not in {
            "queued",
            "running",
            "completed",
            "completed_with_failures",
        }:
            raise BatchDashboardError("unsupported batch_status")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable deterministic dashboard payload."""

        self.validate()
        return {
            "dashboard_schema": self.dashboard_schema,
            "queue_id": self.queue_id,
            "batch_id": self.batch_id,
            "max_parallel": self.max_parallel,
            "videos": [
                {
                    "video_id": row.video_id,
                    "priority": row.priority,
                    "status": row.status,
                    "attempts": row.attempts,
                    "progress_percent": row.progress_percent,
                    "error_code": row.error_code,
                }
                for row in self.videos
            ],
            "status_counts": dict(sorted(self.status_counts.items())),
            "summary": {
                "total_videos": self.total_videos,
                "completed_videos": self.completed_videos,
                "failed_videos": self.failed_videos,
                "active_renders": self.active_renders,
                "completion_percent": self.completion_percent,
                "batch_status": self.batch_status,
            },
            "auto_publish": False,
        }


def _progress_for(item: RenderQueueItem) -> int:
    return {
        "pending": 0,
        "validated": 20,
        "retry": 20,
        "rendering": 60,
        "failed": 100,
        "completed": 100,
    }[item.status]


def _batch_status(counts: Mapping[str, int], total: int) -> str:
    terminal = counts.get("completed", 0) + counts.get("failed", 0)
    if terminal == total:
        return (
            "completed_with_failures"
            if counts.get("failed", 0)
            else "completed"
        )
    if counts.get("rendering", 0) or counts.get("validated", 0):
        return "running"
    if counts.get("retry", 0):
        return "running"
    return "queued"


def build_batch_dashboard_model(
    queue: ParallelRenderQueue,
) -> BatchDashboardModel:
    """Project a validated queue into a stable dashboard representation."""

    queue.validate()
    ordered_items = tuple(
        sorted(queue.items, key=lambda item: (item.priority, item.video_id))
    )
    rows = tuple(
        DashboardVideoRow(
            video_id=item.video_id,
            priority=item.priority,
            status=item.status,
            attempts=item.attempts,
            progress_percent=_progress_for(item),
            error_code=item.error_code,
        )
        for item in ordered_items
    )
    counts = queue_status_counts(ordered_items)
    total = len(rows)
    completed = counts["completed"]
    failed = counts["failed"]
    terminal = completed + failed
    completion_percent = (terminal * 100) // total

    model = BatchDashboardModel(
        dashboard_schema="football-shorts-ai.batch-dashboard.v1",
        queue_id=queue.queue_id,
        batch_id=queue.batch_id,
        max_parallel=queue.max_parallel,
        videos=rows,
        status_counts=counts,
        total_videos=total,
        completed_videos=completed,
        failed_videos=failed,
        active_renders=counts["rendering"],
        completion_percent=completion_percent,
        batch_status=_batch_status(counts, total),
        auto_publish=False,
    )
    model.validate()
    return model


__all__ = [
    "BatchDashboardError",
    "DashboardVideoRow",
    "BatchDashboardModel",
    "build_batch_dashboard_model",
]
