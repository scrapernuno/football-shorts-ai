from dataclasses import replace

import pytest

from operations.master_certification_orchestrator import (
    REQUIRED_STAGES,
    MasterCertificationError,
    build_master_certification_report,
)


def _passing():
    return {name: True for name in REQUIRED_STAGES}


def test_builds_certified_master_report():
    report = build_master_certification_report(commit_sha="abc123", stage_results=_passing())
    assert report.overall_status == "CERTIFIED"
    assert report.blockers == ()
    assert all(value == "PASS" for value in report.stages.values())
    assert report.report_id.startswith("MASTER-CERT-")
    assert report.to_dict()["publication_executed"] is False


def test_one_failed_stage_blocks_platform():
    stages = _passing()
    stages["render"] = False
    report = build_master_certification_report(commit_sha="abc123", stage_results=stages)
    assert report.overall_status == "BLOCKED"
    assert report.stages["render"] == "FAIL"
    assert report.blockers == ("RENDER_CERTIFICATION_FAILED",)


def test_missing_stage_fails_closed():
    stages = _passing()
    del stages["youtube_upload"]
    report = build_master_certification_report(commit_sha="abc123", stage_results=stages)
    assert report.overall_status == "BLOCKED"
    assert "YOUTUBE_UPLOAD_CERTIFICATION_FAILED" in report.blockers


def test_replay_is_deterministic():
    first = build_master_certification_report(commit_sha="abc123", stage_results=_passing())
    second = build_master_certification_report(commit_sha="abc123", stage_results=_passing())
    assert first.to_dict() == second.to_dict()


def test_tampering_is_rejected():
    report = build_master_certification_report(commit_sha="abc123", stage_results=_passing())
    with pytest.raises(MasterCertificationError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_execution_cannot_be_enabled():
    report = build_master_certification_report(commit_sha="abc123", stage_results=_passing())
    with pytest.raises(MasterCertificationError, match="certification-only"):
        replace(report, upload_executed=True).validate()
