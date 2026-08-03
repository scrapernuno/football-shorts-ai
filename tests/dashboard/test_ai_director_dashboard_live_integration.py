from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from director.export_ai_director_review_package import (
    AIDirectorPackageExportError,
    build_review_package,
    validate_review_package,
)


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_assets_and_navigation_contract_exist() -> None:
    script = ROOT / "dashboard/assets/dashboard-ai-director-integration.js"
    page = ROOT / "dashboard/ai-director-review.html"
    assert script.is_file()
    assert page.is_file()
    source = script.read_text(encoding="utf-8")
    assert "AI Director" in source
    assert "ai-director-review.html" in source
    assert "data/ai_director_review_package.json" in source
    assert "Variant Intelligence" in source
    assert "render_enabled" not in source or "render_enabled" in source


def test_fail_closed_package_is_deterministic() -> None:
    first = build_review_package()
    second = build_review_package()
    assert first == second
    validate_review_package(first)
    assert first["package_state"] == "blocked"
    assert first["blockers"] == [
        "AI_DIRECTOR_EVIDENCE_MISSING",
        "FACTORY_HANDOVER_NOT_READY",
        "HUMAN_APPROVAL_REQUIRED",
        "VARIANT_RANKING_EVIDENCE_MISSING",
    ]
    assert first["network_enabled"] is False
    assert first["acquisition_enabled"] is False
    assert first["extraction_enabled"] is False
    assert first["render_enabled"] is False
    assert first["auto_publish"] is False


def test_ready_package_requires_full_governed_chain() -> None:
    payload = build_review_package(
        director_report={
            "director_state": "proposed",
            "variants": [{
                "variant_id": "DIRVAR-FAST",
                "strategy": "fast",
                "title": "Fast Impact Cut",
                "viral_score": 0.91,
                "predicted_retention": 0.87,
                "total_duration_seconds": 18.2,
                "blockers": [],
            }],
            "recommended_variant_id": "DIRVAR-FAST",
            "blockers": [],
        },
        narrative_alignment={"alignment_state": "aligned", "blockers": []},
        timing_optimization={"optimization_state": "optimized", "blockers": []},
        performance_ranking={
            "ranking_state": "ranked",
            "recommended_variant_id": "DIRVAR-FAST",
            "blockers": [],
        },
        approval={
            "approval_state": "approved",
            "decision": "approved",
            "reviewer": "editor",
            "blockers": [],
        },
        factory_handover={
            "handover_state": "ready_for_factory",
            "blockers": [],
        },
    )
    validate_review_package(payload)
    assert payload["package_state"] == "ready_for_factory"
    assert payload["blockers"] == []
    assert payload["variants"][0]["strategy"] == "fast"


def test_tampered_package_fails_validation() -> None:
    payload = build_review_package()
    tampered = dict(payload)
    tampered["package_state"] = "ready_for_factory"
    with pytest.raises(AIDirectorPackageExportError, match="evidence mismatch"):
        validate_review_package(tampered)


def test_operational_capabilities_cannot_be_enabled() -> None:
    payload = build_review_package()
    for key in ("network_enabled", "acquisition_enabled", "extraction_enabled", "render_enabled", "auto_publish"):
        changed = dict(payload)
        changed[key] = True
        unsigned = dict(changed)
        unsigned.pop("evidence_sha256")
        from director.export_ai_director_review_package import canonical_sha256
        changed["evidence_sha256"] = canonical_sha256(unsigned)
        with pytest.raises(AIDirectorPackageExportError, match="cannot enable operational capabilities"):
            validate_review_package(changed)


def test_public_package_is_fail_closed() -> None:
    path = ROOT / "dashboard/data/ai_director_review_package.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload.get("render_enabled") is False
    assert payload.get("auto_publish") is False
