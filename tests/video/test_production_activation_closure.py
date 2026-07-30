from __future__ import annotations

from video.certify_production_activation import ARTIFACT, certify


def test_production_activation_closure_certification_passes() -> None:
    report = certify()

    assert report["artifact"] == ARTIFACT
    assert report["status"] == "PASS"
    assert report["activation_readiness"] == "PASS"
    assert report["controlled_render_command"] == "PASS"
    assert report["dashboard_asset_installation"] == "PASS"
    assert report["atomic_library_promotion"] == "PASS"
    assert report["dashboard_playback_verification"] == "PASS"
    assert report["checksum_binding"] == "PASS"
    assert report["workspace_confinement"] == "PASS"
    assert report["fail_closed_governance"] == "PASS"
    assert report["video_count"] == 1
    assert report["playback_check_count"] == 7


def test_production_activation_closure_exposes_complete_evidence_set() -> None:
    report = certify()

    assert set(report["checks"]) == {
        "LIBRARY_ASSET_READY",
        "WORKSPACE_CONFINEMENT",
        "VIDEO_INTEGRITY",
        "MP4_CONTAINER_SIGNATURE",
        "THUMBNAIL_SIGNATURE",
        "WEBVTT_SIGNATURE",
        "HTML5_PLAYER_BINDING",
    }
