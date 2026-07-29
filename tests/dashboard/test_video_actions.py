from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "videos.html"
JAVASCRIPT = ROOT / "dashboard" / "assets" / "video-library.js"
CSS = ROOT / "dashboard" / "assets" / "video-library.css"


def test_governed_action_controls_exist() -> None:
    source = HTML.read_text(encoding="utf-8")
    assert 'id="download-video-action"' in source
    assert 'id="publishing-studio-action"' in source
    assert 'id="copy-publishing-id-action"' in source
    assert 'aria-disabled="true"' in source


def test_download_is_fail_closed_and_status_gated() -> None:
    source = JAVASCRIPT.read_text(encoding="utf-8")
    assert "function resetActions()" in source
    assert "function configureActions(video)" in source
    assert 'video.status === "ready" || video.status === "published"' in source
    assert 'download.href = file.path' in source
    assert 'download.setAttribute("download"' in source


def test_publishing_handoff_requires_package_evidence() -> None:
    source = JAVASCRIPT.read_text(encoding="utf-8")
    assert "publishing_package_id" in source
    assert 'setActionEnabled(byId("publishing-studio-action"), true)' in source
    assert "navigator.clipboard.writeText" in source


def test_action_styles_include_disabled_state() -> None:
    source = CSS.read_text(encoding="utf-8")
    assert ".video-actions" in source
    assert ".action-button.is-disabled" in source
    assert "pointer-events: none" in source
