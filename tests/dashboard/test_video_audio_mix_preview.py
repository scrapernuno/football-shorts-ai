from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_preview_page_loads_audio_mix_controller():
    html = (ROOT / "dashboard/video-preview.html").read_text(encoding="utf-8")
    assert 'assets/video-audio-mix-preview.js' in html
    assert 'id="previewVideo"' in html


def test_audio_mix_controller_is_fail_closed_and_supports_ducking():
    js = (ROOT / "dashboard/assets/video-audio-mix-preview.js").read_text(encoding="utf-8")
    assert "track.mix_state !== 'mixed'" in js
    assert "cue.audio_allowed === true" in js
    assert "duck_under_voiceover_db" in js
    assert "window.videoFactoryVoiceover" in js
    assert "render" not in js.lower() or "render_enabled" not in js


def test_public_audio_mix_package_starts_blocked():
    import json

    payload = json.loads((ROOT / "dashboard/data/video_factory_audio_mix_track.json").read_text(encoding="utf-8"))
    assert payload["mix_state"] == "blocked"
    assert payload["cues"] == []
    assert payload["network_enabled"] is False
    assert payload["generation_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False
