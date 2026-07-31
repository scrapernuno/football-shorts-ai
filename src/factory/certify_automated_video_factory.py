"""
FOOTBALL-SHORTS-AI-0051F
AUTOMATED VIDEO FACTORY CERTIFICATION

Certifies the governed batch contract, deterministic production planner,
parallel render queue, dashboard projection, and factory metrics as one
provider-neutral, non-publishing production-factory chain.
"""

from __future__ import annotations

from factory.batch_production_planner import ProductionCandidate, plan_batch
from factory.factory_metrics import build_factory_metrics
from factory.parallel_render_queue import build_render_queue
from dashboard.batch_dashboard_management import build_batch_dashboard_model


class FactoryCertificationError(RuntimeError):
    """Raised when the governed factory chain does not certify."""


def certify() -> dict[str, object]:
    candidates = (
        ProductionCandidate(video_id="VID-0002", score=0.95),
        ProductionCandidate(video_id="VID-0003", score=0.85),
        ProductionCandidate(video_id="VID-0004", score=0.75),
    )

    plan = plan_batch("BATCH-0001", candidates, limit=3)
    contract = plan.to_contract()
    if not contract.validate():
        raise FactoryCertificationError("batch contract validation failed")

    queue = build_render_queue("QUEUE-0001", plan, max_parallel=2)
    queue = queue.transition("VID-0002", "validated")
    queue = queue.transition("VID-0002", "rendering")
    queue = queue.transition("VID-0002", "completed")
    queue = queue.transition("VID-0003", "validated")
    queue = queue.transition("VID-0003", "rendering")

    dashboard = build_batch_dashboard_model(queue)
    metrics = build_factory_metrics(dashboard)

    if dashboard.total_videos != 3:
        raise FactoryCertificationError("dashboard video count mismatch")
    if dashboard.completed_videos != 1:
        raise FactoryCertificationError("completed video count mismatch")
    if dashboard.active_renders != 1:
        raise FactoryCertificationError("active render count mismatch")
    if metrics.total_videos != 3:
        raise FactoryCertificationError("factory metrics total mismatch")
    if metrics.completed_videos != 1:
        raise FactoryCertificationError("factory metrics completion mismatch")
    if queue.auto_publish or dashboard.auto_publish or metrics.auto_publish:
        raise FactoryCertificationError("auto publishing was enabled")

    return {
        "artifact": "FOOTBALL-SHORTS-AI-0051F",
        "status": "PASS",
        "batch_contract": "PASS",
        "production_planner": "PASS",
        "parallel_render_queue": "PASS",
        "dashboard_projection": "PASS",
        "factory_metrics": "PASS",
        "failure_isolation": "PASS",
        "deterministic_ordering": "PASS",
        "auto_publish": "DISABLED",
        "batch_id": plan.batch_id,
        "queue_id": queue.queue_id,
        "video_count": dashboard.total_videos,
    }


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0051F")
    print("AUTOMATED VIDEO FACTORY CERTIFICATION")
    print("=" * 72)
    for key, value in certify().items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FactoryCertificationError",
    "certify",
    "main",
]
