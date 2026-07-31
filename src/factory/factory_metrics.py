"""
FOOTBALL-SHORTS-AI-0051E
FACTORY METRICS

Computes deterministic, read-only operational metrics from the governed batch
dashboard model. This module does not render videos, mutate queue state, access
the network, or publish content.
"""

from __future__ import annotations

from dataclasses import dataclass

from dashboard.batch_dashboard_management import BatchDashboardModel


class FactoryMetricsError(ValueError):
    """Raised when factory metrics cannot be derived safely."""


@dataclass(frozen=True)
class FactoryMetrics:
    batch_id: str
    queue_id: str
    total_videos: int
    completed_videos: int
    failed_videos: int
    active_renders: int
    pending_videos: int
    retry_videos: int
    success_rate_percent: int
    failure_rate_percent: int
    completion_percent: int
    average_attempts: float
    batch_status: str
    auto_publish: bool = False

    def validate(self) -> None:
        if not self.batch_id.strip():
            raise FactoryMetricsError("batch_id is required")
        if not self.queue_id.strip():
            raise FactoryMetricsError("queue_id is required")
        if self.total_videos <= 0:
            raise FactoryMetricsError("total_videos must be greater than zero")
        for name, value in (
            ("completed_videos", self.completed_videos),
            ("failed_videos", self.failed_videos),
            ("active_renders", self.active_renders),
            ("pending_videos", self.pending_videos),
            ("retry_videos", self.retry_videos),
        ):
            if value < 0:
                raise FactoryMetricsError(f"{name} cannot be negative")
        for name, value in (
            ("success_rate_percent", self.success_rate_percent),
            ("failure_rate_percent", self.failure_rate_percent),
            ("completion_percent", self.completion_percent),
        ):
            if not 0 <= value <= 100:
                raise FactoryMetricsError(f"{name} must be between 0 and 100")
        if self.average_attempts < 0:
            raise FactoryMetricsError("average_attempts cannot be negative")
        if self.auto_publish:
            raise FactoryMetricsError("auto publishing must remain disabled")
        if self.batch_status not in {
            "queued",
            "running",
            "completed",
            "completed_with_failures",
        }:
            raise FactoryMetricsError("unsupported batch_status")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "batch_id": self.batch_id,
            "queue_id": self.queue_id,
            "total_videos": self.total_videos,
            "completed_videos": self.completed_videos,
            "failed_videos": self.failed_videos,
            "active_renders": self.active_renders,
            "pending_videos": self.pending_videos,
            "retry_videos": self.retry_videos,
            "success_rate_percent": self.success_rate_percent,
            "failure_rate_percent": self.failure_rate_percent,
            "completion_percent": self.completion_percent,
            "average_attempts": self.average_attempts,
            "batch_status": self.batch_status,
            "auto_publish": False,
        }


def build_factory_metrics(model: BatchDashboardModel) -> FactoryMetrics:
    """Derive stable batch metrics from a validated dashboard model."""

    model.validate()
    counts = model.status_counts
    terminal = model.completed_videos + model.failed_videos
    success_rate = (
        (model.completed_videos * 100) // terminal if terminal else 0
    )
    failure_rate = (
        (model.failed_videos * 100) // terminal if terminal else 0
    )
    average_attempts = round(
        sum(row.attempts for row in model.videos) / model.total_videos,
        2,
    )

    metrics = FactoryMetrics(
        batch_id=model.batch_id,
        queue_id=model.queue_id,
        total_videos=model.total_videos,
        completed_videos=model.completed_videos,
        failed_videos=model.failed_videos,
        active_renders=model.active_renders,
        pending_videos=counts.get("pending", 0),
        retry_videos=counts.get("retry", 0),
        success_rate_percent=success_rate,
        failure_rate_percent=failure_rate,
        completion_percent=model.completion_percent,
        average_attempts=average_attempts,
        batch_status=model.batch_status,
        auto_publish=False,
    )
    metrics.validate()
    return metrics


__all__ = [
    "FactoryMetricsError",
    "FactoryMetrics",
    "build_factory_metrics",
]
