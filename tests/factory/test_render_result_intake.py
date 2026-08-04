from dataclasses import replace

import pytest

from factory.render_result_intake import (
    RenderResultIntakeError,
    build_render_result_intake,
)


def _result():
    return {
        "execution_id": "FFMPEGEXEC-1234567890ABCDEF1234",
        "render_package_id": "RENDERPKG-1234567890ABCDEF1234",
        "output_uri": "artifacts/final/football-short.mp4",
        "output_sha256": "a" * 64,
        "return_code": 0,
        "publication_performed": False,
        "network_used": False,
    }


def _probe():
    return {
        "duration_seconds": 28.4,
        "width": 1080,
        "height": 1920,
        "video_codec": "h264",
        "audio_codec": "aac",
    }


def test_successful_render_is_ready_for_human_review():
    intake = build_render_result_intake(result=_result(), probe=_probe(), reviewer="Nuno")
    intake.validate()
    assert intake.review_state == "ready_for_review"
    assert intake.blockers == ()
    assert intake.publication_allowed is False
    assert intake.auto_publish is False
    assert intake.network_enabled is False


def test_invalid_dimensions_fail_closed():
    probe = {**_probe(), "width": 1920, "height": 1080}
    intake = build_render_result_intake(result=_result(), probe=probe, reviewer="Nuno")
    assert intake.review_state == "blocked"
    assert "RENDER_DIMENSIONS_INVALID" in intake.blockers


def test_missing_reviewer_is_blocked():
    intake = build_render_result_intake(result=_result(), probe=_probe(), reviewer="")
    assert "HUMAN_REVIEWER_REQUIRED" in intake.blockers


def test_reported_publication_or_network_is_blocked():
    result = {**_result(), "publication_performed": True, "network_used": True}
    intake = build_render_result_intake(result=result, probe=_probe(), reviewer="Nuno")
    assert "PROHIBITED_OPERATION_REPORTED" in intake.blockers


def test_replay_is_deterministic():
    left = build_render_result_intake(result=_result(), probe=_probe(), reviewer="Nuno")
    right = build_render_result_intake(result=_result(), probe=_probe(), reviewer="Nuno")
    assert left.to_dict() == right.to_dict()


def test_evidence_tampering_is_rejected():
    intake = build_render_result_intake(result=_result(), probe=_probe(), reviewer="Nuno")
    with pytest.raises(RenderResultIntakeError, match="evidence mismatch"):
        replace(intake, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    intake = build_render_result_intake(result=_result(), probe=_probe(), reviewer="Nuno")
    with pytest.raises(RenderResultIntakeError, match="cannot enable"):
        replace(intake, auto_publish=True).validate()
