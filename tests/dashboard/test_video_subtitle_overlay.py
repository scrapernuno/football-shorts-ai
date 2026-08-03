from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_preview_page_loads_subtitle_overlay():
    html = (ROOT / "dashboard/video-preview.html").read_text(encoding="utf-8")
    assert '<video id="previewVideo"' in html
    assert 'assets/video-subtitle-overlay.js' in html


def test_overlay_is_fail_closed_and_non_operational():
    script = (ROOT / "dashboard/assets/video-subtitle-overlay.js").read_text(encoding="utf-8")
    assert "subtitle_state !== 'generated'" in script
    assert "video.addEventListener('timeupdate'" in script
    assert "render_enabled" not in script
    assert "auto_publish" not in script


def test_public_subtitle_package_is_blocked_initially():
    payload = (ROOT / "dashboard/data/video_factory_subtitle_track.json").read_text(encoding="utf-8")
    assert '"subtitle_state": "blocked"' in payload
    assert '"render_enabled": false' in payload
    assert '"auto_publish": false' in payload
