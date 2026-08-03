from dataclasses import replace

import pytest

from director.factory_handover_package import (
    FactoryHandoverError,
    build_factory_handover_package,
)


def _approval(*, state="approved", allowed=True):
    return {
        "approval_id": "DIRAPPROVAL-00000000000000000001",
        "selected_variant_id": "DIRVAR-00000000000000000001",
        "approval_state": state,
        "factory_handover_allowed": allowed,
    }


def _optimization(*, state="optimized", render_allowed=True):
    return {
        "optimization_id": "DIROPT-00000000000000000001",
        "optimization_state": state,
        "timeline_items": [
            {
                "beat_id": "DIRBEAT-00000000000000000001",
                "clip_id": "VIRALCLIP-00000000000000000001",
                "source_start_seconds": 1.0,
                "source_end_seconds": 3.0,
                "timeline_start_seconds": 0.0,
                "timeline_end_seconds": 2.0,
                "script_text": "Ninguém esperava este remate.",
                "transition_in": "cut",
                "transition_out": "cut",
                "playback_rate": 1.0,
                "render_allowed": render_allowed,
                "evidence_ids": ["DIRBEAT-00000000000000000001", "VIRALCLIP-00000000000000000001"],
            },
            {
                "beat_id": "DIRBEAT-00000000000000000002",
                "clip_id": "VIRALCLIP-00000000000000000002",
                "source_start_seconds": 4.0,
                "source_end_seconds": 7.0,
                "timeline_start_seconds": 2.0,
                "timeline_end_seconds": 5.0,
                "script_text": "E depois surgiu o golo decisivo.",
                "transition_in": "cut",
                "transition_out": "fade",
                "playback_rate": 1.0,
                "render_allowed": render_allowed,
                "evidence_ids": ["DIRBEAT-00000000000000000002", "VIRALCLIP-00000000000000000002"],
            },
        ],
    }


def test_builds_ready_factory_handover_package():
    report = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(),
    )

    report.validate()
    assert report.handover_state == "ready_for_factory"
    assert report.blockers == ()
    assert report.format == "9:16"
    assert (report.width, report.height, report.fps) == (1080, 1920, 30)
    assert report.total_duration_seconds == 5.0
    assert len(report.timeline_items) == 2
    assert report.timeline_items[0].timeline_end_seconds == report.timeline_items[1].timeline_start_seconds


def test_missing_approval_is_blocked():
    report = build_factory_handover_package(
        approval_report=_approval(state="changes_requested", allowed=False),
        optimization_report=_optimization(),
    )

    assert report.handover_state == "blocked"
    assert "DIRECTOR_APPROVAL_NOT_GRANTED" in report.blockers
    assert "FACTORY_HANDOVER_NOT_ALLOWED" in report.blockers


def test_non_renderable_item_requires_review():
    report = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(render_allowed=False),
    )

    assert report.handover_state == "review_required"
    assert "FACTORY_ITEM_RENDER_NOT_ALLOWED" in report.blockers


def test_missing_timeline_requires_review():
    optimization = _optimization()
    optimization["timeline_items"] = []
    report = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=optimization,
    )

    assert report.handover_state == "review_required"
    assert "FACTORY_TIMELINE_MISSING" in report.blockers


def test_replay_is_deterministic():
    first = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(),
    )
    second = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(),
    )

    assert first == second
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampered_evidence_is_rejected():
    report = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(),
    )

    with pytest.raises(FactoryHandoverError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_invalid_fps_is_rejected():
    with pytest.raises(FactoryHandoverError, match="unsupported frame rate"):
        build_factory_handover_package(
            approval_report=_approval(),
            optimization_report=_optimization(),
            fps=29,
        )


def test_operational_capabilities_cannot_be_enabled():
    report = build_factory_handover_package(
        approval_report=_approval(),
        optimization_report=_optimization(),
    )

    with pytest.raises(FactoryHandoverError, match="cannot enable operational capabilities"):
        replace(report, render_enabled=True).validate()
