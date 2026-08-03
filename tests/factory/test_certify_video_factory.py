from dataclasses import replace
from pathlib import Path

import pytest

from factory.certify_video_factory import REQUIRED_FILES, certify


def test_certifies_complete_video_factory_inventory() -> None:
    report = certify()
    report.validate()
    assert report.state == "certified"
    assert report.blockers == ()
    assert len(report.inventory) == len(REQUIRED_FILES)
    assert report.certification_id.startswith("FACTORYCERT-")


def test_replay_is_deterministic() -> None:
    assert certify().to_dict() == certify().to_dict()


def test_missing_required_file_is_fail_closed(tmp_path: Path) -> None:
    present = tmp_path / "present.txt"
    present.write_text("safe", encoding="utf-8")
    report = certify(tmp_path, ("present.txt", "missing.txt"))
    assert report.state == "blocked"
    assert "REQUIRED_FILE_MISSING:missing.txt" in report.blockers


def test_operational_capability_true_is_fail_closed(tmp_path: Path) -> None:
    target = tmp_path / "unsafe.json"
    target.write_text('{"render_enabled": true}', encoding="utf-8")
    report = certify(tmp_path, ("unsafe.json",))
    assert report.state == "blocked"
    assert any(item.startswith("OPERATIONAL_CAPABILITY_ENABLED:unsafe.json") for item in report.blockers)


def test_evidence_tampering_is_detected() -> None:
    report = certify()
    with pytest.raises(ValueError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled() -> None:
    report = certify()
    with pytest.raises(ValueError, match="cannot enable"):
        replace(report, ffmpeg_execution_enabled=True).validate()
