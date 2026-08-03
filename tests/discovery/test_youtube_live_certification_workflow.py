from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "youtube-discovery-live-certification.yml"
CERTIFIER = ROOT / "src" / "discovery" / "certify_live_youtube_dashboard.py"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_live_workflow_and_certifier_exist() -> None:
    assert WORKFLOW.is_file()
    assert CERTIFIER.is_file()


def test_activation_is_manual_and_secret_governed() -> None:
    text = _text()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text
    assert "YOUTUBE_DATA_API_KEY: ${{ secrets.YOUTUBE_DATA_API_KEY }}" in text
    assert "Required secret YOUTUBE_DATA_API_KEY is unavailable." in text
    assert "environment: youtube-discovery" in text


def test_workflow_has_pages_authority_and_three_stage_chain() -> None:
    text = _text()
    assert "contents: write" in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "activate-and-build:" in text
    assert "deploy-pages:" in text
    assert "verify-publication:" in text
    assert "needs: activate-and-build" in text
    assert "needs: deploy-pages" in text
    assert "actions/deploy-pages@v4" in text


def test_publication_is_certified_by_public_sha256() -> None:
    text = _text()
    assert "data/football_library.json" in text
    assert "PUBLIC_LIBRARY_URL" in text
    assert "curl --fail --silent --show-error" in text
    assert "certify_live_youtube_dashboard" in text
    assert 'assert result.status == "LIVE_CERTIFIED"' in text
    assert "PUBLIC_LIBRARY_SHA256" in text


def test_evidence_is_retained_and_commit_is_optional() -> None:
    text = _text()
    assert "youtube-live-predeploy-${{ github.run_id }}" in text
    assert "youtube-live-certification-${{ github.run_id }}" in text
    assert "retention-days: 30" in text
    assert "commit_dashboard:" in text
    assert "default: false" in text
    assert "if: ${{ inputs.commit_dashboard }}" in text


def test_no_media_execution_capability_is_introduced() -> None:
    text = _text().lower()
    assert "yt-dlp" not in text
    assert "ffmpeg" not in text
    assert "videos.insert" not in text
    assert "download_enabled" not in text
    assert "render_enabled" not in text
    assert "publishing_enabled" not in text
