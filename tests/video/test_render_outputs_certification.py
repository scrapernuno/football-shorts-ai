from __future__ import annotations

from video.certify_render_outputs import certify


def test_governed_render_output_certification_passes() -> None:
    result = certify()

    assert result == {
        "artifact": "FOOTBALL-SHORTS-AI-0045D",
        "status": "PASS",
        "video_output": "PASS",
        "subtitle_vtt": "PASS",
        "thumbnail_output": "PASS",
        "checksum_capture": "PASS",
        "size_capture": "PASS",
        "fail_closed_contract": "PASS",
        "scene_count": 2,
    }
