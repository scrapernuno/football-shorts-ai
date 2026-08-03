import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_preview_page_loads_voiceover_controller():
    html = (ROOT / "dashboard/video-preview.html").read_text(encoding="utf-8")
    assert 'assets/video-voiceover-preview.js' in html
    assert '<video id="previewVideo"' in html


def test_voiceover_controller_is_fail_closed():
    script = (ROOT / "dashboard/assets/video-voiceover-preview.js").read_text(encoding="utf-8")
    assert "synchronization_state !== 'synchronized'" in script
    assert "audio_allowed === true" in script
    assert "video.addEventListener('timeupdate', sync)" in script
    assert "fetch(TRACK_URL" in script
    assert "fetch(PREVIEW_URL" in script
    assert "speechSynthesis" not in script
    assert "MediaRecorder" not in script


def test_public_voiceover_track_starts_blocked():
    payload = json.loads((ROOT / "dashboard/data/video_factory_voiceover_track.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "football-shorts-ai.voiceover-track.v1"
    assert payload["synchronization_state"] == "blocked"
    assert payload["cues"] == []
    assert payload["network_enabled"] is False
    assert payload["synthesis_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False
