from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_editorial_dashboard_assets_exist() -> None:
    assert (ROOT / "dashboard/editorial-review.html").is_file()
    assert (ROOT / "dashboard/assets/editorial-review.js").is_file()
    assert (ROOT / "dashboard/assets/dashboard-editorial-integration.js").is_file()
    assert (ROOT / "dashboard/data/editorial_review_package.json").is_file()


def test_dashboard_integration_exposes_review_navigation_and_metrics() -> None:
    source = (ROOT / "dashboard/assets/dashboard-editorial-integration.js").read_text(encoding="utf-8")
    for fragment in (
        "Editorial Review",
        "editorial-review.html",
        "Editorial Intelligence",
        "ei-quality",
        "ei-viral",
        "ei-retention",
        "ei-rights",
        "READY_FOR_REVIEW",
        "EVIDENCE_MISSING",
    ):
        assert fragment in source


def test_public_package_is_fail_closed() -> None:
    payload = json.loads(
        (ROOT / "dashboard/data/editorial_review_package.json").read_text(encoding="utf-8")
    )
    assert payload["schema"] == "football-shorts-ai.editorial-review-package.v1"
    assert payload["review_required"] is True
    assert payload["factory_handover_enabled"] is False
    assert payload["network_enabled"] is False
    assert payload["acquisition_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_render"] is False
    assert payload["auto_publish"] is False
    assert payload["timeline"]["timeline_state"] == "blocked"
    assert payload["scorecard"]["score_state"] == "blocked"
    assert payload["blockers"]


def test_activation_workflow_is_idempotent_and_minimally_privileged() -> None:
    workflow = (ROOT / ".github/workflows/editorial-dashboard-integration.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "contents: write" in workflow
    assert "dashboard-editorial-integration.js" in workflow
    assert "if marker not in text" in workflow
    assert "git diff --quiet" in workflow
    forbidden = ("curl ", "wget ", "ffmpeg", "yt-dlp", "videos.insert", "auto_publish: true")
    assert all(fragment not in workflow for fragment in forbidden)
