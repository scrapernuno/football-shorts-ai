from dataclasses import replace

import pytest

from publishing.youtube_upload_result_intake import (
    YouTubeUploadResultIntakeError,
    build_youtube_upload_result_intake,
)


def _upload():
    return {"upload_id": "YTUPLOAD-ABCDEF0123456789ABCD", "status": "UPLOADED", "youtube_video_id": "abc123XYZ90"}


def _snapshot(**updates):
    value = {"channel_id": "UC-FOOTBALL", "processing_status": "succeeded", "upload_status": "processed", "privacy_status": "unlisted", "embeddable": True}
    value.update(updates); return value


def test_successful_processing_is_ready_for_dashboard():
    result = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(), expected_channel_id="UC-FOOTBALL")
    assert result.intake_state == "processed"
    assert result.blockers == ()
    assert result.watch_url.endswith("abc123XYZ90")
    assert result.thumbnail_url.endswith("abc123XYZ90/hqdefault.jpg")
    assert result.visibility_change_allowed is False
    result.validate()


def test_processing_pending_is_fail_closed():
    result = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(processing_status="processing"), expected_channel_id="UC-FOOTBALL")
    assert result.intake_state == "processing"
    assert "YOUTUBE_PROCESSING_PENDING" in result.blockers


def test_channel_mismatch_requires_review():
    result = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(channel_id="UC-WRONG"), expected_channel_id="UC-FOOTBALL")
    assert result.intake_state == "review_required"
    assert "YOUTUBE_CHANNEL_MISMATCH" in result.blockers


def test_failed_upload_is_blocked():
    upload = {**_upload(), "status": "BLOCKED", "youtube_video_id": ""}
    result = build_youtube_upload_result_intake(upload_result=upload, processing_snapshot=_snapshot(), expected_channel_id="UC-FOOTBALL")
    assert result.intake_state == "blocked"


def test_replay_is_deterministic():
    first = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(), expected_channel_id="UC-FOOTBALL")
    second = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(), expected_channel_id="UC-FOOTBALL")
    assert first.to_dict() == second.to_dict()


def test_tampering_and_external_operations_are_rejected():
    result = build_youtube_upload_result_intake(upload_result=_upload(), processing_snapshot=_snapshot(), expected_channel_id="UC-FOOTBALL")
    with pytest.raises(YouTubeUploadResultIntakeError):
        replace(result, publish_enabled=True).validate()
    with pytest.raises(YouTubeUploadResultIntakeError):
        replace(result, evidence_sha256="0" * 64).validate()
