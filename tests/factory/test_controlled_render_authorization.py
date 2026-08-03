from dataclasses import replace

import pytest

from factory.controlled_render_authorization import (
    RenderAuthorizationError,
    build_controlled_render_authorization,
)


def _render_package(state="ready_for_authorization"):
    return {
        "render_package_id": "RENDERPKG-ABCDEF0123456789ABCD",
        "package_state": state,
    }


def _media(**overrides):
    payload = {
        "kind": "video",
        "local_uri": "dashboard/media/authorized-match.mp4",
        "sha256": "a" * 64,
        "rights_status": "owned",
        "rights_reference": "OWNER-DECLARATION-001",
        "owner_confirmation": True,
    }
    payload.update(overrides)
    return payload


def test_authorizes_complete_owned_media_without_enabling_execution():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Nuno Freitas",
        authorization_note="Autorizo o uso deste ficheiro próprio para renderização controlada.",
        media_inputs=[_media()],
    )
    result.validate()
    assert result.authorization_state == "authorized"
    assert result.blockers == ()
    assert result.assets[0].intake_allowed is True
    assert result.render_execution_allowed is False
    assert result.ffmpeg_execution_enabled is False
    assert result.auto_publish is False


def test_licensed_media_is_supported_with_rights_reference():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Licença verificada.",
        media_inputs=[_media(rights_status="licensed", rights_reference="LICENSE-2026-001")],
    )
    assert result.authorization_state == "authorized"


def test_reference_only_media_is_fail_closed():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Revisão.",
        media_inputs=[_media(rights_status="reference_only")],
    )
    assert result.authorization_state == "review_required"
    assert "MEDIA_INTAKE_REVIEW_REQUIRED" in result.blockers
    assert "MEDIA_NOT_AUTHORIZED" in result.assets[0].blockers
    assert result.assets[0].intake_allowed is False


def test_invalid_hash_requires_review():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Revisão.",
        media_inputs=[_media(sha256="invalid")],
    )
    assert result.authorization_state == "review_required"
    assert "MEDIA_SHA256_MISSING_OR_INVALID" in result.assets[0].blockers


def test_render_package_not_ready_is_blocked():
    result = build_controlled_render_authorization(
        render_package=_render_package("blocked"),
        reviewer="Editor",
        authorization_note="Revisão.",
        media_inputs=[_media()],
    )
    assert result.authorization_state == "blocked"
    assert "RENDER_PACKAGE_NOT_READY" in result.blockers


def test_reviewer_and_note_are_mandatory():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="",
        authorization_note="",
        media_inputs=[_media()],
    )
    assert result.authorization_state == "review_required"
    assert "HUMAN_REVIEWER_REQUIRED" in result.blockers
    assert "AUTHORIZATION_NOTE_REQUIRED" in result.blockers


def test_empty_media_is_blocked():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Revisão.",
        media_inputs=[],
    )
    assert result.authorization_state == "blocked"
    assert "AUTHORIZED_MEDIA_MISSING" in result.blockers


def test_replay_is_deterministic():
    kwargs = dict(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Autorizado.",
        media_inputs=[_media()],
    )
    first = build_controlled_render_authorization(**kwargs)
    second = build_controlled_render_authorization(**kwargs)
    assert first.to_dict() == second.to_dict()
    assert first.authorization_id == second.authorization_id
    assert first.evidence_sha256 == second.evidence_sha256


def test_tampering_is_detected():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Autorizado.",
        media_inputs=[_media()],
    )
    with pytest.raises(RenderAuthorizationError, match="evidence mismatch"):
        replace(result, reviewer="Outro revisor").validate()


def test_execution_capabilities_cannot_be_enabled():
    result = build_controlled_render_authorization(
        render_package=_render_package(),
        reviewer="Editor",
        authorization_note="Autorizado.",
        media_inputs=[_media()],
    )
    with pytest.raises(RenderAuthorizationError, match="cannot enable operational capabilities"):
        replace(result, ffmpeg_execution_enabled=True).validate()
    with pytest.raises(RenderAuthorizationError, match="cannot enable render execution"):
        replace(result, render_execution_allowed=True).validate()
