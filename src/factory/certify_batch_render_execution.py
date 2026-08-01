"""
FOOTBALL-SHORTS-AI-0052C
BATCH RENDER CERTIFICATION

Deterministically certifies the governed batch render executor across success,
per-video failure isolation, ordered execution, queue transitions, identity
preservation, final counters, and disabled automatic publishing.
"""

from __future__ import annotations

from dataclasses import dataclass

from factory.batch_production_planner import ProductionCandidate, plan_batch
from factory.governed_batch_render_executor import execute_governed_batch
from factory.parallel_render_queue import build_render_queue
from factory.real_batch_factory_activation import activate_real_batch
from video.rendering import RenderRequest, RenderResult, RenderScene


class BatchRenderCertificationError(RuntimeError):
    """Raised when the governed batch rendering chain does not certify."""


@dataclass
class DeterministicCertificationRuntime:
    """Pure deterministic runtime used only for certification.

    VID-0003 fails intentionally. All other activated videos succeed with stable
    governed outputs. The runtime performs no FFmpeg execution, network access,
    publication, or filesystem mutation.
    """

    calls: list[str]

    def render(self, request: RenderRequest) -> RenderResult:
        self.calls.append(request.video_id)
        if request.video_id == "VID-0003":
            return RenderResult(
                render_id=request.render_id,
                video_id=request.video_id,
                status="failed",
                failure_reason="CertificationFailure: deterministic isolated failure",
            )

        return RenderResult(
            render_id=request.render_id,
            video_id=request.video_id,
            status="succeeded",
            output_path=request.output_path,
            thumbnail_path=request.thumbnail_path,
            subtitles_path=request.subtitles_path,
            checksum_sha256=(request.video_id.encode("utf-8").hex() + "0" * 64)[:64],
            size_bytes=1024 + int(request.video_id.rsplit("-", 1)[-1]),
        )


def _request(video_id: str) -> RenderRequest:
    return RenderRequest(
        render_id=f"RENDER-{video_id}",
        video_id=video_id,
        topic=f"Certification topic for {video_id}",
        width=1080,
        height=1920,
        fps=30,
        container="mp4",
        output_path=f"videos/{video_id}.mp4",
        thumbnail_path=f"videos/{video_id}.jpg",
        subtitles_path=f"videos/{video_id}.vtt",
        scenes=(
            RenderScene(
                scene_id=f"{video_id}-SCENE-001",
                start_second=0.0,
                end_second=4.0,
                screen_text=f"Certified {video_id}",
                narration=f"Deterministic certification narration for {video_id}.",
                visual_prompt=f"Vertical football short visual for {video_id}.",
            ),
        ),
    )


def certify() -> dict[str, object]:
    candidates = (
        ProductionCandidate(video_id="VID-0002", score=0.95),
        ProductionCandidate(video_id="VID-0003", score=0.85),
        ProductionCandidate(video_id="VID-0004", score=0.75),
    )
    plan = plan_batch("BATCH-0002", candidates, limit=3)
    queue = build_render_queue("QUEUE-0002", plan, max_parallel=3)
    activation = activate_real_batch(
        plan,
        queue,
        production_ids={
            "VID-0002": "PRODUCTION-0002",
            "VID-0003": "PRODUCTION-0003",
            "VID-0004": "PRODUCTION-0004",
        },
    )

    if tuple(work.video_id for work in activation.work_items) != (
        "VID-0002",
        "VID-0003",
        "VID-0004",
    ):
        raise BatchRenderCertificationError("activation ordering mismatch")

    requests = {
        "VID-0002": _request("VID-0002"),
        "VID-0003": _request("VID-0003"),
        "VID-0004": _request("VID-0004"),
    }
    runtime = DeterministicCertificationRuntime(calls=[])
    outcome = execute_governed_batch(activation, queue, requests, runtime)
    outcome.validate()

    if tuple(runtime.calls) != ("VID-0002", "VID-0003", "VID-0004"):
        raise BatchRenderCertificationError("runtime execution ordering mismatch")
    if outcome.attempted_videos != 3:
        raise BatchRenderCertificationError("attempted video count mismatch")
    if outcome.completed_videos != 2:
        raise BatchRenderCertificationError("completed video count mismatch")
    if outcome.failed_videos != 1:
        raise BatchRenderCertificationError("failed video count mismatch")
    if outcome.execution_status != "completed_with_failures":
        raise BatchRenderCertificationError("execution status mismatch")

    records = {record.video_id: record for record in outcome.records}
    if records["VID-0002"].final_status != "completed":
        raise BatchRenderCertificationError("VID-0002 did not complete")
    if records["VID-0003"].final_status != "failed":
        raise BatchRenderCertificationError("VID-0003 failure was not isolated")
    if records["VID-0004"].final_status != "completed":
        raise BatchRenderCertificationError(
            "VID-0004 did not continue after isolated failure"
        )
    if records["VID-0003"].error_code is None:
        raise BatchRenderCertificationError("failed record lacks governed error code")

    queue_states = {item.video_id: item.status for item in outcome.queue.items}
    if queue_states != {
        "VID-0002": "completed",
        "VID-0003": "failed",
        "VID-0004": "completed",
    }:
        raise BatchRenderCertificationError("final queue states mismatch")

    queue_attempts = {item.video_id: item.attempts for item in outcome.queue.items}
    if queue_attempts != {
        "VID-0002": 1,
        "VID-0003": 1,
        "VID-0004": 1,
    }:
        raise BatchRenderCertificationError("render attempt counters mismatch")

    for video_id, record in records.items():
        request = requests[video_id]
        if record.render_result.video_id != request.video_id:
            raise BatchRenderCertificationError("video identity was not preserved")
        if record.render_result.render_id != request.render_id:
            raise BatchRenderCertificationError("render identity was not preserved")

    if plan.auto_publish or queue.auto_publish:
        raise BatchRenderCertificationError("auto publishing enabled before execution")
    if activation.auto_publish or outcome.auto_publish or outcome.queue.auto_publish:
        raise BatchRenderCertificationError("auto publishing enabled during execution")

    second_runtime = DeterministicCertificationRuntime(calls=[])
    second_outcome = execute_governed_batch(
        activation,
        queue,
        requests,
        second_runtime,
    )
    if outcome.to_dict() != second_outcome.to_dict():
        raise BatchRenderCertificationError("batch execution is not deterministic")

    return {
        "artifact": "FOOTBALL-SHORTS-AI-0052C",
        "status": "PASS",
        "real_batch_activation": "PASS",
        "governed_batch_executor": "PASS",
        "priority_ordering": "PASS",
        "parallel_window": "PASS",
        "successful_renders": 2,
        "isolated_failures": 1,
        "continuation_after_failure": "PASS",
        "queue_transitions": "PASS",
        "identity_preservation": "PASS",
        "counter_integrity": "PASS",
        "deterministic_replay": "PASS",
        "auto_publish": "DISABLED",
        "batch_id": outcome.batch_id,
        "queue_id": outcome.queue_id,
        "attempted_videos": outcome.attempted_videos,
        "completed_videos": outcome.completed_videos,
        "failed_videos": outcome.failed_videos,
    }


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0052C")
    print("BATCH RENDER CERTIFICATION")
    print("=" * 72)
    for key, value in certify().items():
        print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BatchRenderCertificationError",
    "DeterministicCertificationRuntime",
    "certify",
    "main",
]
