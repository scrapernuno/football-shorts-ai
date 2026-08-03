from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from director.certify_ai_director import (
    AIDirectorCertificationError,
    REQUIRED_ARTIFACTS,
    certify_ai_director,
)


def test_certifies_complete_ai_director_inventory() -> None:
    report = certify_ai_director()

    report.validate()
    assert report.status == "CERTIFIED"
    assert report.blockers == ()
    assert report.artifact_count == len(REQUIRED_ARTIFACTS)
    assert report.certified_stages == (
        "0058A",
        "0058B",
        "0058C",
        "0058D",
        "0058E",
        "0058F",
        "0058G",
        "0058H",
    )
    assert report.certification_id.startswith("AIDIRCERT-")


def test_replay_is_deterministic() -> None:
    first = certify_ai_director()
    second = certify_ai_director()

    assert first == second
    assert first.to_dict() == second.to_dict()


def test_missing_artifact_is_fail_closed(tmp_path: Path) -> None:
    for relative in REQUIRED_ARTIFACTS[1:]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith(".json"):
            path.write_text("{}", encoding="utf-8")
        else:
            path.write_text("placeholder", encoding="utf-8")

    index = tmp_path / "dashboard/index.html"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        '<script src="assets/dashboard-ai-director-integration.js"></script>',
        encoding="utf-8",
    )
    review = tmp_path / "dashboard/ai-director-review.html"
    review.write_text(
        '<link href="assets/ai-director-review.css"><script src="assets/ai-director-review.js"></script>',
        encoding="utf-8",
    )

    report = certify_ai_director(root=tmp_path)

    assert report.status == "BLOCKED"
    assert any(item.startswith("MISSING_ARTIFACT:") for item in report.blockers)


def test_tampered_report_is_rejected() -> None:
    report = certify_ai_director()
    tampered = replace(report, certification_id="INVALID")

    with pytest.raises(AIDirectorCertificationError, match="invalid certification identity"):
        tampered.validate()


def test_operational_capabilities_cannot_be_enabled() -> None:
    report = certify_ai_director()

    for field in (
        "network_enabled",
        "acquisition_enabled",
        "model_training_enabled",
        "extraction_enabled",
        "render_enabled",
        "auto_publish",
    ):
        with pytest.raises(AIDirectorCertificationError, match="cannot enable operational capabilities"):
            replace(report, **{field: True}).validate()
