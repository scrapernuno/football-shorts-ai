from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "discovery.html"
JS = ROOT / "dashboard" / "assets" / "discovery-library.js"
CSS = ROOT / "dashboard" / "assets" / "discovery-library.css"


def test_discovery_browser_files_exist() -> None:
    assert HTML.is_file()
    assert JS.is_file()
    assert CSS.is_file()


def test_browser_reads_canonical_dashboard_library_export() -> None:
    source = JS.read_text(encoding="utf-8")
    assert 'const DATA_URL = "data/football_library.json";' in source
    assert "extractLibrary" in source
    assert "library.assets" in source


def test_browser_exposes_search_filters_cards_and_preview() -> None:
    markup = HTML.read_text(encoding="utf-8")
    source = JS.read_text(encoding="utf-8")

    for element_id in (
        "search-input",
        "provider-filter",
        "rights-filter",
        "state-filter",
        "sort-filter",
        "preview-filter",
        "video-grid",
        "preview-dialog",
    ):
        assert f'id="{element_id}"' in markup

    assert "video-card" in source
    assert "preview-button" in source
    assert "showModal" in source
    assert "provider_url" in source
    assert "embed_url" in source


def test_browser_displays_rights_and_renderability_fail_closed() -> None:
    source = JS.read_text(encoding="utf-8")
    assert "rights_status" in source
    assert "render_allowed" in source
    assert "preview_allowed" in source
    assert "previewDisabled" in source


def test_browser_has_no_media_acquisition_or_publication_runtime() -> None:
    source = JS.read_text(encoding="utf-8").lower()
    forbidden = (
        "auto_acquire = true",
        "auto_publish = true",
        "downloadvideo",
        "download_video",
        "yt-dlp",
        "youtube-dl",
        "publishvideo",
        "publish_video",
    )
    for fragment in forbidden:
        assert fragment not in source


def test_discovery_browser_is_responsive() -> None:
    stylesheet = CSS.read_text(encoding="utf-8")
    assert "@media (max-width: 1100px)" in stylesheet
    assert "@media (max-width: 700px)" in stylesheet
    assert ".video-grid" in stylesheet
