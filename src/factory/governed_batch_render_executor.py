"""
FOOTBALL-SHORTS-AI-0052B
GOVERNED BATCH RENDER EXECUTOR

Executes one governed activation window through the certified video render
runtime while preserving deterministic order, queue transition authority,
per-video failure isolation, and disabled automatic publishing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

from factory.parallel_render_queue import ParallelRenderQueue, RenderQueueError
from factory.real_batch_factory_activation import RealBatchActivation
from video.rendering import RenderRequest, RenderResult, VideoRenderRuntime


class BatchRenderExecutionError(ValueError):
    """Raised when an activation window cannot be executed safely."""


@dataclass(frozen=True)
class BatchRenderExecutionRecord:
    video_id: str
    production_id: str
    priority: int
    initial_status: str
    final_status: str
    render_result: RenderResult
    error_code: str | None = None
    auto_publish: bool = False

    def validate(self) -> None:
        if not self.video_id.strip():
            raise BatchRenderExecutionError("video_id is required")
        if not self.production_id.strip():
            raise BatchRenderExecutionError("production_id is required")
        if self.priority <= 0:
            raise BatchRenderExecutionError("priority must be greater than zero")
        if self.initial_status not in {"pending", "retry"}:
            raise BatchRenderExecutionError("unsupported initial queue status")
        if self.final_status not in {"completed", "failed"}:
            raise BatchRenderExecutionError("unsupported final queue status")
        if self.auto_publish:
            raise BatchRenderExecutionError("auto publishing must remain disabled")
        if self.render_result.video_id != self.video_id:
            raise BatchRenderExecutionError("render result video_id mismatch")
        if self.final_status == "completed":
            if self.render_result.status != "succeeded":
                raise BatchRenderExecutionError("completed record requires succeeded result")
            if self.error_code is not None:
                raise BatchRenderExecutionError("completed record cannot contain error_code")
        else:
            if self.render_result.status != "failed":
                raise BatchRenderExecutionError("failed record requires failed result")
            if not self.error_code:
                raise BatchRenderExecutionError("failed record requires error_code")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "video_id": self.video_id,
            "production_id": self.production_id,
            "priority": self.priority,
            "initial_status": self.initial_status,
            "final_status": self.final_status,
            "render_result": self.render_result.to_dict(),
            "error_code": self.error_code,
            "auto_publish": False,
        }


@dataclass(frozen=True)
class GovernedBatchRenderOutcome:
    execution_schema: str
    batch_id: str
    queue_id: str
    records: Tuple[BatchRenderExecutionRecord, ...]
    queue: ParallelRenderQueue
    attempted_videos: int
    completed_videos: int
    failed_videos: int
    execution_status: str
    auto_publish: bool = False

    def validate(self) -> None:
        if self.execution_schema != "football-shorts-ai.batch-render-execution.v1":
            raise BatchRenderExecutionError("unsupported execution schema")
        if not self.batch_id.strip() or not self.queue_id.strip():
            raise BatchRenderExecutionError("batch_id and queue_id are required")
        if self.auto_publish or self.queue.auto_publish:
            raise BatchRenderExecutionError("auto publishing must remain disabled")
        self.queue.validate()
        if self.queue.batch_id != self.batch_id or self.queue.queue_id != self.queue_id:
            raise BatchRenderExecutionError("result queue identity mismatch")
        if self.attempted_videos != len(self.records):
            raise BatchRenderExecutionError("attempted_videos count mismatch")
        if self.completed_videos != sum(r.final_status == "completed" for r in self.records):
            raise BatchRenderExecutionError("completed_videos count mismatch")
        if self.failed_videos != sum(r.final_status == "failed" for r in self.records):
            raise BatchRenderExecutionError("failed_videos count mismatch")
        if self.execution_status not in {"completed", "completed_with_failures", "no_work"}:
            raise BatchRenderExecutionError("unsupported execution_status")
        if not self.records and self.execution_status != "no_work":
            raise BatchRenderExecutionError("empty execution must use no_work status")
        priorities = [record.priority for record in self.records]
        if priorities != sorted(priorities):
            raise BatchRenderExecutionError("records are not priority ordered")
        for record in self.records:
            record.validate()

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "execution_schema": self.execution_schema,
            "batch_id": self.batch_id,
            "queue_id": self.queue_id,
            "records": [record.to_dict() for record in self.records],
            "summary": {
                "attempted_videos": self.attempted_videos,
                "completed_videos": self.completed_videos,
                "failed_videos": self.failed_videos,
                "execution_status": self.execution_status,
            },
            "auto_publish": False,
        }


def _failed_result(request: RenderRequest | None, video_id: str, reason: str) -> RenderResult:
    return RenderResult(
        render_id=request.render_id if request is not None else f"RENDER-{video_id}",
        video_id=video_id,
        status="failed",
        failure_reason=reason,
    )


def _error_code(reason: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in reason.upper())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return (normalized or "RENDER_FAILED")[:96]


def _validate_alignment(
    activation: RealBatchActivation,
    queue: ParallelRenderQueue,
) -> None:
    activation.validate()
    queue.validate()
    if activation.batch_id != queue.batch_id or activation.queue_id != queue.queue_id:
        raise BatchRenderExecutionError("activation and queue identity mismatch")
    if activation.auto_publish or queue.auto_publish:
        raise BatchRenderExecutionError("auto publishing must remain disabled")

    queue_by_id = {item.video_id: item for item in queue.items}
    for work in activation.work_items:
        current = queue_by_id.get(work.video_id)
        if current is None:
            raise BatchRenderExecutionError(
                f"activated video is absent from queue: {work.video_id}"
            )
        if current.status != work.queue_status or current.priority != work.priority:
            raise BatchRenderExecutionError(
                f"activation is stale for video_id: {work.video_id}"
            )


def execute_governed_batch(
    activation: RealBatchActivation,
    queue: ParallelRenderQueue,
    requests: Mapping[str, RenderRequest],
    runtime: VideoRenderRuntime,
) -> GovernedBatchRenderOutcome:
    """Execute activated videos deterministically with failure isolation.

    Each video is transitioned explicitly through validated and rendering before
    completion. Missing or invalid requests fail only their own queue item.
    Runtime exceptions are converted into governed failed results.
    """

    _validate_alignment(activation, queue)
    unexpected = set(requests) - {work.video_id for work in activation.work_items}
    if unexpected:
        raise BatchRenderExecutionError(
            "requests contains non-activated video_id values: "
            + ", ".join(sorted(unexpected))
        )

    current_queue = queue
    records: list[BatchRenderExecutionRecord] = []

    for work in sorted(activation.work_items, key=lambda item: (item.priority, item.video_id)):
        request = requests.get(work.video_id)
        if request is None:
            reason = "RenderRequestNotFound: activated video has no complete render request"
            result = _failed_result(None, work.video_id, reason)
            code = "RENDER_REQUEST_NOT_FOUND"
            current_queue = current_queue.transition(work.video_id, "failed", error_code=code)
            records.append(
                BatchRenderExecutionRecord(
                    video_id=work.video_id,
                    production_id=work.production_id,
                    priority=work.priority,
                    initial_status=work.queue_status,
                    final_status="failed",
                    render_result=result,
                    error_code=code,
                )
            )
            continue

        if request.video_id != work.video_id:
            reason = "RenderRequestIdentityMismatch: request video_id differs from activation"
            result = _failed_result(request, work.video_id, reason)
            code = "RENDER_REQUEST_IDENTITY_MISMATCH"
            current_queue = current_queue.transition(work.video_id, "failed", error_code=code)
            records.append(
                BatchRenderExecutionRecord(
                    video_id=work.video_id,
                    production_id=work.production_id,
                    priority=work.priority,
                    initial_status=work.queue_status,
                    final_status="failed",
                    render_result=result,
                    error_code=code,
                )
            )
            continue

        try:
            current_queue = current_queue.transition(work.video_id, "validated")
            current_queue = current_queue.transition(work.video_id, "rendering")
            result = runtime.render(request)
            if result.video_id != work.video_id or result.render_id != request.render_id:
                raise BatchRenderExecutionError("runtime returned mismatched render identity")
        except Exception as exc:
            result = _failed_result(
                request,
                work.video_id,
                f"{type(exc).__name__}: {exc}",
            )

        if result.status == "succeeded":
            current_queue = current_queue.transition(work.video_id, "completed")
            record = BatchRenderExecutionRecord(
                video_id=work.video_id,
                production_id=work.production_id,
                priority=work.priority,
                initial_status=work.queue_status,
                final_status="completed",
                render_result=result,
            )
        else:
            reason = result.failure_reason or "render runtime returned failed without reason"
            code = _error_code(reason)
            try:
                current_queue = current_queue.transition(
                    work.video_id,
                    "failed",
                    error_code=code,
                )
            except RenderQueueError as exc:
                raise BatchRenderExecutionError(
                    f"failed to persist governed failure for {work.video_id}: {exc}"
                ) from exc
            record = BatchRenderExecutionRecord(
                video_id=work.video_id,
                production_id=work.production_id,
                priority=work.priority,
                initial_status=work.queue_status,
                final_status="failed",
                render_result=result,
                error_code=code,
            )
        record.validate()
        records.append(record)

    completed = sum(record.final_status == "completed" for record in records)
    failed = sum(record.final_status == "failed" for record in records)
    status = "no_work" if not records else ("completed_with_failures" if failed else "completed")
    outcome = GovernedBatchRenderOutcome(
        execution_schema="football-shorts-ai.batch-render-execution.v1",
        batch_id=activation.batch_id,
        queue_id=activation.queue_id,
        records=tuple(records),
        queue=current_queue,
        attempted_videos=len(records),
        completed_videos=completed,
        failed_videos=failed,
        execution_status=status,
        auto_publish=False,
    )
    outcome.validate()
    return outcome


__all__ = [
    "BatchRenderExecutionError",
    "BatchRenderExecutionRecord",
    "GovernedBatchRenderOutcome",
    "execute_governed_batch",
]
