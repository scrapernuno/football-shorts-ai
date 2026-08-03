from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from discovery.certify_football_discovery_platform import (
    FootballDiscoveryCertificationError,
    certify_football_discovery_platform,
)
from discovery.external_provider_contract import canonical_sha256


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_certifies_complete_0054_chain() -> None:
    report = certify_football_discovery_platform(repository_root=REPOSITORY_ROOT)

    assert report.status == "CERTIFIED"
    assert report.owned_factory_package_id.startswith("FACTORYPKG-")
    assert report.reference_timeline_state == "blocked"
    assert report.checks == (
        "0054A_EXTERNAL_PROVIDER_CONTRACT",
        "0054B_FOOTBALL_LIBRARY_ENGINE",
        "0054C_CATALOG_PERSISTENCE_AND_EXPORT",
        "0054D_DASHBOARD_VIDEO_BROWSER",
        "0054E_EMBEDDED_PLAYER_AND_CLIP_SELECTION",
        "0054G_INTERACTIVE_TIMELINE_STUDIO",
        "0054E_GOVERNED_CLIP_CONTRACT",
        "0054F_TIMELINE_COMPOSITION_CONTRACT",
        "0054H_STORY_TIMELINE_ENRICHMENT",
        "0054I_TIMELINE_TO_FACTORY_PACKAGE",
    )


def test_final_certification_replay_is_deterministic() -> None:
    first = certify_football_discovery_platform(repository_root=REPOSITORY_ROOT)
    second = certify_football_discovery_platform(repository_root=REPOSITORY_ROOT)

    assert first.to_dict() == second.to_dict()
    assert first.evidence_sha256 == second.evidence_sha256
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_all_unsafe_capabilities_remain_disabled() -> None:
    payload = certify_football_discovery_platform(
        repository_root=REPOSITORY_ROOT
    ).to_dict()

    assert payload["network_enabled"] is False
    assert payload["acquisition_enabled"] is False
    assert payload["ai_execution_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False


def test_missing_dashboard_artifact_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(
        FootballDiscoveryCertificationError,
        match="dashboard artifacts missing",
    ):
        certify_football_discovery_platform(repository_root=tmp_path)


def test_forged_execution_capability_is_rejected() -> None:
    report = certify_football_discovery_platform(repository_root=REPOSITORY_ROOT)
    forged = dataclasses.replace(report, render_enabled=True)

    with pytest.raises(
        FootballDiscoveryCertificationError,
        match="unsafe execution capability",
    ):
        forged.validate()


def test_report_contains_valid_deterministic_evidence() -> None:
    report = certify_football_discovery_platform(repository_root=REPOSITORY_ROOT)

    for value in (
        report.catalog_sha256,
        report.dashboard_evidence_sha256,
        report.evidence_sha256,
    ):
        assert len(value) == 64
        int(value, 16)
