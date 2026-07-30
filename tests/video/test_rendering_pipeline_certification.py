from video.certify_rendering_pipeline import certify


def test_final_governed_rendering_pipeline_certification() -> None:
    evidence = certify()

    assert evidence["artifact"] == "FOOTBALL-SHORTS-AI-0045F"
    assert evidence["status"] == "PASS"
    assert evidence["production_to_request"] == "PASS"
    assert evidence["request_to_runtime"] == "PASS"
    assert evidence["video_output"] == "PASS"
    assert evidence["subtitle_output"] == "PASS"
    assert evidence["thumbnail_output"] == "PASS"
    assert evidence["checksum_binding"] == "PASS"
    assert evidence["atomic_library_promotion"] == "PASS"
    assert evidence["dashboard_asset_ready"] == "PASS"
    assert evidence["scene_count"] == 2
    assert evidence["video_count"] == 1
