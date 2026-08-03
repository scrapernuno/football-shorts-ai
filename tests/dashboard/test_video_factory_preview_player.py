from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def test_preview_player_files_exist():
    assert (ROOT / "dashboard/video-preview.html").is_file()
    assert (ROOT / "dashboard/assets/video-preview.js").is_file()
    assert (ROOT / "dashboard/assets/video-preview.css").is_file()
    assert (ROOT / "dashboard/data/video_factory_preview_manifest.json").is_file()


def test_preview_page_contains_real_video_element_and_controls():
    html = (ROOT / "dashboard/video-preview.html").read_text(encoding="utf-8")
    for literal in (
        '<video id="previewVideo"',
        'id="playButton"',
        'id="previousButton"',
        'id="nextButton"',
        'id="timeline"',
        'assets/video-preview.js',
    ):
        assert literal in html


def test_player_is_fail_closed_and_blocks_reference_only():
    js = (ROOT / "dashboard/assets/video-preview.js").read_text(encoding="utf-8")
    for literal in (
        "payload.preview_state !== 'preview_ready'",
        "segment.preview_allowed !== true",
        "segment.rights_status === 'reference_only'",
        "Preview não autorizado",
        "Conteúdo reference_only bloqueado",
    ):
        assert literal in js


def test_player_sequences_only_governed_source_ranges():
    js = (ROOT / "dashboard/assets/video-preview.js").read_text(encoding="utf-8")
    for literal in (
        "segment.source_start_seconds",
        "segment.source_end_seconds",
        "video.currentTime",
        "video.playbackRate",
        "loadSegment(state.index + 1, true)",
    ):
        assert literal in js


def test_initial_manifest_is_blocked_and_non_operational():
    payload = json.loads((ROOT / "dashboard/data/video_factory_preview_manifest.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "football-shorts-ai.video-factory-preview.v1"
    assert payload["preview_state"] == "blocked"
    assert payload["segments"] == []
    assert payload["network_enabled"] is False
    assert payload["acquisition_enabled"] is False
    assert payload["extraction_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False
