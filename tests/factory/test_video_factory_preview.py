from dataclasses import replace

import pytest

from factory.video_factory_preview import (
    VideoFactoryPreviewError,
    build_video_factory_preview,
)


def _handover(*, state="ready_for_factory", render_allowed=True):
    return {
        "package_id": "FACTORYPKG-0060A000000000000001",
        "handover_state": state,
        "items": [
            {
                "factory_item_id": "FACTORYITEM-HOOK",
                "asset_id": "ASSET-OWNED-001",
                "clip_id": "VIRALCLIP-HOOK",
                "role": "hook",
                "script_text": "O momento que mudou o jogo.",
                "source_start_seconds": 10.0,
                "source_end_seconds": 13.0,
                "timeline_start_seconds": 0.0,
                "timeline_end_seconds": 3.0,
                "playback_rate": 1.0,
                "transition": "cut",
                "render_allowed": render_allowed,
            },
            {
                "factory_item_id": "FACTORYITEM-CLIMAX",
                "asset_id": "ASSET-OWNED-001",
                "clip_id": "VIRALCLIP-CLIMAX",
                "role": "climax",
                "script_text": "E então chegou o golo.",
                "source_start_seconds": 42.0,
                "source_end_seconds": 46.0,
                "timeline_start_seconds": 3.0,
                "timeline_end_seconds": 7.0,
                "playback_rate": 1.0,
                "transition": "match_cut",
                "render_allowed": render_allowed,
            },
        ],
    }


def _media(*, rights="owned", uri="media/owned-match.mp4"):
    return {
        "ASSET-OWNED-001": {
            "media_uri": uri,
            "rights_status": rights,
        }
    }


def test_builds_browser_preview_for_authorized_media():
    report = build_video_factory_preview(handover=_handover(), media=_media())
    report.validate()
    assert report.preview_state == "preview_ready"
    assert report.blockers == ()
    assert report.total_duration_seconds == 7.0
    assert len(report.segments) == 2
    assert all(item.preview_allowed for item in report.segments)
    assert report.segments[0].media_uri == "media/owned-match.mp4"


def test_reference_only_media_is_fail_closed():
    report = build_video_factory_preview(
        handover=_handover(),
        media=_media(rights="reference_only"),
    )
    assert report.preview_state == "review_required"
    assert "PREVIEW_MEDIA_NOT_ALLOWED" in report.blockers
    assert not any(item.preview_allowed for item in report.segments)


def test_missing_media_source_requires_review():
    report = build_video_factory_preview(handover=_handover(), media={})
    assert report.preview_state == "review_required"
    assert "PREVIEW_SOURCE_MISSING" in report.blockers


def test_blocked_handover_remains_blocked():
    report = build_video_factory_preview(
        handover=_handover(state="blocked"),
        media=_media(),
    )
    assert report.preview_state == "blocked"
    assert "FACTORY_HANDOVER_NOT_READY" in report.blockers


def test_render_rights_block_preview_segment():
    report = build_video_factory_preview(
        handover=_handover(render_allowed=False),
        media=_media(),
    )
    assert report.preview_state == "review_required"
    assert "FACTORY_ITEM_RENDER_NOT_ALLOWED" in report.blockers


def test_replay_is_deterministic():
    first = build_video_factory_preview(handover=_handover(), media=_media())
    second = build_video_factory_preview(handover=_handover(), media=_media())
    assert first.preview_id == second.preview_id
    assert first.evidence_sha256 == second.evidence_sha256
    assert first.to_dict() == second.to_dict()


def test_tampered_evidence_is_rejected():
    report = build_video_factory_preview(handover=_handover(), media=_media())
    with pytest.raises(VideoFactoryPreviewError, match="evidence mismatch"):
        replace(report, evidence_sha256="0" * 64).validate()


def test_operational_capabilities_cannot_be_enabled():
    report = build_video_factory_preview(handover=_handover(), media=_media())
    for field in (
        "network_enabled",
        "acquisition_enabled",
        "extraction_enabled",
        "render_enabled",
        "auto_publish",
    ):
        with pytest.raises(VideoFactoryPreviewError, match="operational capabilities"):
            replace(report, **{field: True}).validate()


def test_non_continuous_timeline_is_rejected():
    report = build_video_factory_preview(handover=_handover(), media=_media())
    broken = replace(
        report,
        segments=(report.segments[0], replace(report.segments[1], timeline_start_seconds=4.0)),
    )
    with pytest.raises(VideoFactoryPreviewError, match="timeline must be continuous"):
        broken.validate()
