from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "timeline-studio.html"
CSS = ROOT / "dashboard" / "assets" / "timeline-studio.css"
JS = ROOT / "dashboard" / "assets" / "timeline-studio.js"


def test_timeline_studio_assets_exist() -> None:
    assert HTML.is_file()
    assert CSS.is_file()
    assert JS.is_file()


def test_page_exposes_timeline_and_factory_readiness_controls() -> None:
    html = HTML.read_text(encoding="utf-8")
    assert 'id="timeline-list"' in html
    assert 'id="factory-status"' in html
    assert 'id="prepare-factory"' in html
    assert 'id="project-title"' in html
    assert 'id="fps"' in html
    assert 'id="voiceover-state"' in html
    assert 'id="music-state"' in html
    assert 'id="captions-state"' in html


def test_studio_consumes_governed_clip_proposals() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert 'football-shorts-ai.clip-proposals.v1' in javascript
    assert 'football-shorts-ai.timeline-project.v1' in javascript
    assert "normalizeClips" in javascript
    assert "duration_seconds" in javascript
    assert "transition" in javascript


def test_reference_only_clips_block_factory_readiness() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert "clip.render_allowed !== true" in javascript
    assert "reference_only" in javascript
    assert 'status: readiness() ? "READY_FOR_FACTORY_PREPARATION" : "BLOCKED"' in javascript
    assert 'byId("prepare-factory").disabled = !readiness()' in javascript


def test_studio_supports_reordering_and_removal() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert 'draggable="true"' in javascript
    assert 'addEventListener("dragstart"' in javascript
    assert 'addEventListener("drop"' in javascript
    assert "move-up" in javascript
    assert "move-down" in javascript
    assert "removeClip" in javascript


def test_composition_is_vertical_and_actions_remain_disabled() -> None:
    javascript = JS.read_text(encoding="utf-8")
    assert 'format: "9:16"' in javascript
    assert 'resolution: "1080x1920"' in javascript
    assert "render_enabled: false" in javascript
    assert "auto_acquire: false" in javascript
    assert "auto_render: false" in javascript
    assert "auto_publish: false" in javascript


def test_no_provider_download_or_publication_runtime_is_present() -> None:
    javascript = JS.read_text(encoding="utf-8").lower()
    forbidden = (
        "youtube-dl",
        "yt-dlp",
        "tiktokapi",
        "videos.insert",
        "publishvideo",
        "fetch(asset.provider_url",
    )
    for marker in forbidden:
        assert marker not in javascript


def test_timeline_layout_is_responsive() -> None:
    css = CSS.read_text(encoding="utf-8")
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 620px)" in css
    assert "grid-template-columns: 1fr" in css
