from __future__ import annotations

import dataclasses
import hashlib

import pytest

from vision.football_vision_pipeline import (
    FootballVisionPipelineError,
    VisionAnalysisRequest,
    build_football_vision_report,
    canonical_sha256,
)


def _request(*, rights_status: str = "owned") -> VisionAnalysisRequest:
    return VisionAnalysisRequest(
        asset_id="EXT-VISION001",
        source_uri="file:///authorized/football-match.mp4",
        source_sha256=hashlib.sha256(b"authorized-video").hexdigest(),
        duration_seconds=8.0,
        rights_status=rights_status,
        sample_fps=2.0,
    )


def _frames() -> list[dict[str, object]]:
    return [
        {
            "frame_number": 0,
            "timestamp_seconds": 0.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-0").hexdigest(),
        },
        {
            "frame_number": 4,
            "timestamp_seconds": 2.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-4").hexdigest(),
        },
        {
            "frame_number": 10,
            "timestamp_seconds": 5.0,
            "width": 1920,
            "height": 1080,
            "frame_sha256": hashlib.sha256(b"frame-10").hexdigest(),
        },
    ]


def _evidence() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    frames = _frames()
    provisional = build_football_vision_report(
        request=_request(),
        provider_name="deterministic-test-provider",
        frames=frames,
        scenes=[
            {
                "start_seconds": 0.0,
                "end_seconds": 8.0,
                "representative_frame_id": "VFRAME-PLACEHOLDER",
                "event_ids": [],
                "motion_score": 0.8,
                "visual_quality_score": 0.9,
            }
        ],
    ) if False else None
    from vision.football_vision_pipeline import _frame

    parsed_frames = [_frame(item) for item in frames]
    events = [
        {
            "event_type": "shot",
            "start_seconds": 0.5,
            "end_seconds": 2.0,
            "confidence": 0.94,
            "labels": ["ball visible", "shot"],
            "evidence_frame_ids": [parsed_frames[0].frame_id, parsed_frames[1].frame_id],
        },
        {
            "event_type": "goal",
            "start_seconds": 2.0,
            "end_seconds": 5.0,
            "confidence": 0.98,
            "labels": ["goal", "net"],
            "evidence_frame_ids": [parsed_frames[1].frame_id, parsed_frames[2].frame_id],
        },
    ]
    from vision.football_vision_pipeline import _event

    parsed_events = [_event(item) for item in events]
    scenes = [
        {
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "representative_frame_id": parsed_frames[0].frame_id,
            "event_ids": [parsed_events[0].event_id],
            "motion_score": 0.91,
            "visual_quality_score": 0.88,
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 8.0,
            "representative_frame_id": parsed_frames[2].frame_id,
            "event_ids": [parsed_events[1].event_id],
            "motion_score": 0.84,
            "visual_quality_score": 0.93,
        },
    ]
    return frames, events, scenes


def test_builds_authorized_provider_neutral_vision_report() -> None:
    frames, events, scenes = _evidence()
    report = build_football_vision_report(
        request=_request(),
        provider_name="opencv-local",
        frames=frames,
        events=events,
        scenes=scenes,
    )

    assert report.pipeline_state == "analyzed"
    assert report.blockers == ()
    assert report.report_id.startswith("VISION-")
    assert len(report.frames) == 3
    assert len(report.events) == 2
    assert len(report.scenes) == 2
    assert report.events[0].event_type == "shot"
    assert report.events[1].event_type == "goal"
    assert report.network_enabled is False
    assert report.acquisition_enabled is False
    assert report.model_training_enabled is False
    assert report.render_enabled is False
    assert report.auto_publish is False


def test_reference_only_asset_is_fail_closed() -> None:
    report = build_football_vision_report(
        request=_request(rights_status="reference_only"),
        provider_name="metadata-only",
    )

    assert report.pipeline_state == "blocked"
    assert report.blockers == ("REFERENCE_ONLY_VISION_ANALYSIS_BLOCKED",)
    assert report.frames == ()
    assert report.events == ()
    assert report.scenes == ()


def test_authorized_request_requires_frames_and_scenes() -> None:
    report = build_football_vision_report(
        request=_request(),
        provider_name="empty-provider",
    )
    assert report.pipeline_state == "blocked"
    assert report.blockers == ("VISION_EVIDENCE_INCOMPLETE",)


def test_rejects_invalid_frame_event_and_scene_evidence() -> None:
    frames, events, scenes = _evidence()
    frames[0]["timestamp_seconds"] = 9.0
    with pytest.raises(FootballVisionPipelineError, match="outside asset duration"):
        build_football_vision_report(
            request=_request(),
            provider_name="invalid-provider",
            frames=frames,
            events=events,
            scenes=scenes,
        )

    frames, events, scenes = _evidence()
    events[0]["confidence"] = 1.2
    with pytest.raises(FootballVisionPipelineError, match="between 0 and 1"):
        build_football_vision_report(
            request=_request(),
            provider_name="invalid-provider",
            frames=frames,
            events=events,
            scenes=scenes,
        )

    frames, events, scenes = _evidence()
    scenes[1]["start_seconds"] = 1.5
    with pytest.raises(FootballVisionPipelineError, match="cannot overlap"):
        build_football_vision_report(
            request=_request(),
            provider_name="invalid-provider",
            frames=frames,
            events=events,
            scenes=scenes,
        )


def test_identity_and_replay_are_deterministic() -> None:
    frames, events, scenes = _evidence()
    first = build_football_vision_report(
        request=_request(),
        provider_name="deterministic-provider",
        frames=frames,
        events=events,
        scenes=scenes,
    )
    second = build_football_vision_report(
        request=_request(),
        provider_name="deterministic-provider",
        frames=frames,
        events=events,
        scenes=scenes,
    )

    assert first.report_id == second.report_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_evidence_tampering_and_operational_capabilities_fail_closed() -> None:
    frames, events, scenes = _evidence()
    report = build_football_vision_report(
        request=_request(),
        provider_name="secure-provider",
        frames=frames,
        events=events,
        scenes=scenes,
    )

    forged_hash = dataclasses.replace(report, evidence_sha256="0" * 64)
    with pytest.raises(FootballVisionPipelineError, match="evidence mismatch"):
        forged_hash.validate()

    forged_network = dataclasses.replace(report, network_enabled=True)
    with pytest.raises(FootballVisionPipelineError, match="operational capabilities"):
        forged_network.validate()

    forged_render = dataclasses.replace(report, render_enabled=True)
    with pytest.raises(FootballVisionPipelineError, match="operational capabilities"):
        forged_render.validate()


def test_request_governance_limits_are_enforced() -> None:
    with pytest.raises(FootballVisionPipelineError, match="unsupported rights_status"):
        dataclasses.replace(_request(), rights_status="unknown").validate()

    with pytest.raises(FootballVisionPipelineError, match="sample_fps"):
        dataclasses.replace(_request(), sample_fps=60.0).validate()

    with pytest.raises(FootballVisionPipelineError, match="SHA-256"):
        dataclasses.replace(_request(), source_sha256="invalid").validate()
