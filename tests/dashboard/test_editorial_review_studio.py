from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "editorial-review.html"
CSS = ROOT / "dashboard" / "assets" / "editorial-review.css"
JS = ROOT / "dashboard" / "assets" / "editorial-review.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_editorial_review_assets_exist() -> None:
    assert HTML.is_file()
    assert CSS.is_file()
    assert JS.is_file()


def test_page_exposes_human_editorial_review_gate() -> None:
    text = _read(HTML)
    assert "FOOTBALL-SHORTS-AI-0056H" in text
    assert "Editorial Review Studio" in text
    assert 'id="decision"' in text
    assert 'value="approved"' in text
    assert 'value="changes_requested"' in text
    assert 'id="review-notes"' in text
    assert 'id="approve-factory"' in text
    assert "Revisão humana obrigatória" in text


def test_dashboard_loads_governed_editorial_package_and_local_fallback() -> None:
    text = _read(JS)
    assert 'data/editorial_review_package.json' in text
    assert 'football-shorts-ai.automatic-timeline.v1' in text
    assert 'cache: "no-store"' in text
    assert "localStorage.getItem(TIMELINE_KEY)" in text
    assert "Importar JSON" in _read(HTML)


def test_review_displays_story_scene_alignment_scores_and_rights() -> None:
    html = _read(HTML)
    js = _read(JS)
    for identifier in (
        "quality-score",
        "viral-score",
        "retention-score",
        "rights-score",
        "scene-list",
        "blockers",
    ):
        assert f'id="{identifier}"' in html
    assert "beat_text" in js
    assert "match_score" in js
    assert "source_start_seconds" in js
    assert "timeline_start_seconds" in js
    assert "render_allowed" in js
    assert "alternatives_by_beat" in js


def test_factory_handover_requires_ready_package_and_explicit_approval() -> None:
    text = _read(JS)
    assert 'decision === "approved"' in text
    assert "isReady(state.package)" in text
    assert "ready_for_factory_preparation" in text
    assert "approve-factory\").disabled" in text
    assert "Handover editorial aprovado" in text


def test_review_evidence_keeps_operational_capabilities_disabled() -> None:
    text = _read(JS)
    assert "acquisition_enabled: false" in text
    assert "render_enabled: false" in text
    assert "auto_render: false" in text
    assert "auto_publish: false" in text
    assert "Nenhuma renderização foi iniciada" in text
    assert "yt-dlp" not in text
    assert "ffmpeg" not in text.lower()
    assert "videos.insert" not in text


def test_review_can_save_and_export_deterministic_structure() -> None:
    text = _read(JS)
    assert 'schema: "football-shorts-ai.editorial-review.v1"' in text
    assert "selected_scenes" in text
    assert "original_scene_id" in text
    assert "selected_scene_id" in text
    assert "editorial_review_evidence.json" in text
    assert "localStorage.setItem(REVIEW_KEY" in text


def test_review_studio_is_responsive() -> None:
    text = _read(CSS)
    assert "@media (max-width: 1000px)" in text
    assert "@media (max-width: 680px)" in text
    assert ".workspace-grid" in text
    assert "grid-template-columns: 1fr" in text
