import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_preview_page_loads_motion_graphics_controller():
    html = (ROOT / "dashboard/video-preview.html").read_text(encoding="utf-8")
    assert 'assets/video-motion-graphics-overlay.js' in html
    assert '<video id="previewVideo"' in html


def test_motion_graphics_controller_is_fail_closed():
    source = (ROOT / "dashboard/assets/video-motion-graphics-overlay.js").read_text(encoding="utf-8")
    assert "graphics_state !== 'composed'" in source
    assert "cue.overlay_allowed === true" in source
    assert "video.addEventListener('timeupdate', render)" in source
    assert "render_enabled" not in source
    assert "auto_publish" not in source


def test_public_motion_graphics_package_is_blocked_by_default():
    payload = json.loads((ROOT / "dashboard/data/video_factory_motion_graphics_track.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "football-shorts-ai.motion-graphics-track.v1"
    assert payload["graphics_state"] == "blocked"
    assert payload["cues"] == []
    assert payload["network_enabled"] is False
    assert payload["generation_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False
