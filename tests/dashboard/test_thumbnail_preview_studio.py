from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_thumbnail_preview_page_contains_governed_studio():
    html = (ROOT / "dashboard" / "thumbnail-preview.html").read_text(encoding="utf-8")
    assert "Thumbnail Preview Studio" in html
    assert "thumbnailGrid" in html
    assert "assets/thumbnail-preview.js" in html
    assert "Publicação</span><strong>DISABLED" in html


def test_thumbnail_preview_controller_blocks_reference_only_and_requires_permission():
    js = (ROOT / "dashboard" / "assets" / "thumbnail-preview.js").read_text(encoding="utf-8")
    assert "candidate.preview_allowed === true" in js
    assert "candidate.rights_status !== 'reference_only'" in js
    assert "Nenhuma imagem é gerada ou publicada automaticamente" in js


def test_public_package_is_fail_closed():
    package = (ROOT / "dashboard" / "data" / "video_factory_thumbnail_composition.json").read_text(encoding="utf-8")
    assert '"composition_state": "blocked"' in package
    assert '"generation_enabled": false' in package
    assert '"render_enabled": false' in package
    assert '"auto_publish": false' in package
