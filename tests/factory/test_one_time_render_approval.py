from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from factory.one_time_render_approval import (
    OneTimeRenderApprovalError,
    build_one_time_render_approval,
)


def _times():
    issued = datetime.now(timezone.utc) + timedelta(minutes=1)
    expires = issued + timedelta(minutes=10)
    return issued.isoformat(), expires.isoformat()


def _dry_run(state="ready"):
    return {
        "dry_run_id": "RENDERDRYRUN-ABCDEF0123456789ABCD",
        "render_order_id": "RENDERORDER-ABCDEF0123456789ABCD",
        "dry_run_state": state,
    }


def _approval(**overrides):
    issued, expires = _times()
    values = {
        "dry_run": _dry_run(),
        "approved_by": "Nuno Freitas",
        "approval_note": "Aprovo uma única renderização controlada.",
        "nonce": "render-once-0123456789",
        "issued_at": issued,
        "expires_at": expires,
        "output_uri": "artifacts/final/football-short.mp4",
    }
    values.update(overrides)
    return build_one_time_render_approval(**values)


def test_builds_single_use_approval_without_executing_ffmpeg():
    approval = _approval()
    approval.validate()
    assert approval.approval_state == "approved"
    assert approval.dispatch_allowed is True
    assert approval.single_use is True
    assert approval.consumed is False
    assert approval.ffmpeg_execution_enabled is False
    assert approval.auto_publish is False


def test_replay_is_deterministic_for_same_inputs():
    issued, expires = _times()
    kwargs = dict(
        dry_run=_dry_run(), approved_by="Nuno Freitas",
        approval_note="Aprovação controlada.", nonce="nonce-0123456789abcdef",
        issued_at=issued, expires_at=expires,
        output_uri="artifacts/final/football-short.mp4",
    )
    assert build_one_time_render_approval(**kwargs).to_dict() == build_one_time_render_approval(**kwargs).to_dict()


def test_blocked_dry_run_is_fail_closed():
    approval = _approval(dry_run=_dry_run("blocked"))
    assert approval.approval_state == "blocked"
    assert approval.dispatch_allowed is False
    assert "RENDER_DRY_RUN_NOT_READY" in approval.blockers


def test_short_nonce_is_rejected_by_policy():
    approval = _approval(nonce="short")
    assert approval.approval_state == "blocked"
    assert "APPROVAL_NONCE_INVALID" in approval.blockers


def test_expired_approval_cannot_dispatch():
    issued = datetime.now(timezone.utc) - timedelta(minutes=20)
    expires = issued + timedelta(minutes=5)
    approval = _approval(issued_at=issued.isoformat(), expires_at=expires.isoformat())
    assert approval.approval_state == "expired"
    assert approval.dispatch_allowed is False
    assert "APPROVAL_EXPIRED" in approval.blockers


def test_consumed_approval_cannot_be_reused():
    approval = _approval(consumed=True)
    assert approval.approval_state == "consumed"
    assert approval.dispatch_allowed is False
    assert "APPROVAL_ALREADY_CONSUMED" in approval.blockers


def test_evidence_tampering_is_detected():
    approval = _approval()
    tampered = replace(approval, approval_note="alterado")
    with pytest.raises(OneTimeRenderApprovalError, match="evidence mismatch"):
        tampered.validate()


def test_operational_capabilities_cannot_be_enabled():
    approval = _approval()
    tampered = replace(approval, ffmpeg_execution_enabled=True)
    with pytest.raises(OneTimeRenderApprovalError, match="operational capabilities"):
        tampered.validate()
