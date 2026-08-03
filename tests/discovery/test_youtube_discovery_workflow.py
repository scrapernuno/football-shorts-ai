from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "youtube-discovery-sync.yml"
ENTRYPOINT = ROOT / "src" / "discovery" / "run_youtube_discovery_sync.py"


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_and_entrypoint_exist() -> None:
    assert WORKFLOW.is_file()
    assert ENTRYPOINT.is_file()


def test_workflow_is_manual_and_secret_governed() -> None:
    text = _workflow_text()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text
    assert "YOUTUBE_DATA_API_KEY: ${{ secrets.YOUTUBE_DATA_API_KEY }}" in text
    assert "environment: youtube-discovery" in text
    assert "Required secret YOUTUBE_DATA_API_KEY is unavailable." in text


def test_workflow_uses_controlled_entrypoint_and_metadata_contract() -> None:
    text = _workflow_text()
    assert "run_youtube_discovery_sync.py" in text
    assert "--activate" in text
    assert "dashboard/data/football_library.json" in text
    assert "youtube-discovery-sync-report.json" in text
    assert 'report["metadata_only"] is True' in text
    assert 'report["download_enabled"] is False' in text
    assert 'report["acquisition_enabled"] is False' in text
    assert 'report["render_enabled"] is False' in text
    assert 'report["publishing_enabled"] is False' in text


def test_workflow_has_governed_limits_and_evidence_upload() -> None:
    text = _workflow_text()
    assert 'test "${{ inputs.max_results }}" -le 50' in text
    assert '[[ "${{ inputs.region_code }}" =~ ^[A-Z]{2}$ ]]' in text
    assert "actions/upload-artifact@v4" in text
    assert "retention-days: 14" in text
    assert "if-no-files-found: error" in text
    assert "timeout-minutes: 10" in text
    assert "cancel-in-progress: false" in text


def test_dashboard_commit_requires_explicit_boolean_input() -> None:
    text = _workflow_text()
    assert "commit_dashboard:" in text
    assert "default: false" in text
    assert "if: ${{ inputs.commit_dashboard }}" in text
    assert "git push origin HEAD:main" in text


def test_workflow_has_minimum_required_permissions() -> None:
    payload = yaml.safe_load(_workflow_text())
    assert payload["permissions"] == {"contents": "write"}
    assert set(payload["jobs"]) == {"synchronize"}


def test_entrypoint_never_exposes_unsafe_switches() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    assert "--activate" in text
    assert "download" not in text.lower()
    assert "acquisition" not in text.lower()
    assert "render_enabled" not in text
    assert "publishing_enabled" not in text
    assert "YOUTUBE_DATA_API_KEY" not in text
    assert '"evidence_sha256"' in text
