"""FOOTBALL-SHORTS-AI-0061D — one-time human render approval.

Creates a short-lived, single-use dispatch approval bound to a certified 0061C
dry-run. This module never executes FFmpeg or publishes content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


class OneTimeRenderApprovalError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OneTimeRenderApprovalError("invalid approval timestamp") from exc
    if parsed.tzinfo is None:
        raise OneTimeRenderApprovalError("approval timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class OneTimeRenderApproval:
    schema: str
    approval_id: str
    dry_run_id: str
    render_order_id: str
    approved_by: str
    approval_note: str
    nonce: str
    issued_at: str
    expires_at: str
    output_uri: str
    approval_state: str
    single_use: bool
    consumed: bool
    dispatch_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    ffmpeg_execution_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "approval_id": self.approval_id,
            "dry_run_id": self.dry_run_id,
            "render_order_id": self.render_order_id,
            "approved_by": self.approved_by,
            "approval_note": self.approval_note,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "output_uri": self.output_uri,
            "approval_state": self.approval_state,
            "single_use": self.single_use,
            "consumed": self.consumed,
            "dispatch_allowed": self.dispatch_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "ffmpeg_execution_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.one-time-render-approval.v1":
            raise OneTimeRenderApprovalError("unsupported approval schema")
        if not self.approval_id.startswith("RENDERAPPROVAL-"):
            raise OneTimeRenderApprovalError("invalid approval identity")
        if not self.dry_run_id.startswith("RENDERDRYRUN-"):
            raise OneTimeRenderApprovalError("invalid dry-run identity")
        if not self.render_order_id.startswith("RENDERORDER-"):
            raise OneTimeRenderApprovalError("invalid render order identity")
        if self.approval_state not in {"approved", "blocked", "expired", "consumed"}:
            raise OneTimeRenderApprovalError("unsupported approval state")
        issued = _parse_utc(self.issued_at)
        expires = _parse_utc(self.expires_at)
        if expires <= issued:
            raise OneTimeRenderApprovalError("approval expiry must follow issue time")
        if not self.single_use:
            raise OneTimeRenderApprovalError("0061D approvals must be single-use")
        if self.approval_state == "approved" and (self.blockers or self.consumed or not self.dispatch_allowed):
            raise OneTimeRenderApprovalError("approved state must be unblocked and unused")
        if self.approval_state != "approved" and self.dispatch_allowed:
            raise OneTimeRenderApprovalError("non-approved state cannot allow dispatch")
        if any((self.network_enabled, self.acquisition_enabled, self.ffmpeg_execution_enabled, self.auto_publish)):
            raise OneTimeRenderApprovalError("0061D cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise OneTimeRenderApprovalError("approval evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_one_time_render_approval(
    *,
    dry_run: Mapping[str, object],
    approved_by: str,
    approval_note: str,
    nonce: str,
    issued_at: str,
    expires_at: str,
    output_uri: str,
    consumed: bool = False,
) -> OneTimeRenderApproval:
    blockers: set[str] = set()
    dry_run_id = str(dry_run.get("dry_run_id", ""))
    render_order_id = str(dry_run.get("render_order_id") or dry_run.get("order_id") or "")
    if dry_run.get("dry_run_state") != "ready":
        blockers.add("RENDER_DRY_RUN_NOT_READY")
    if not dry_run_id.startswith("RENDERDRYRUN-"):
        blockers.add("RENDER_DRY_RUN_ID_INVALID")
    if not render_order_id.startswith("RENDERORDER-"):
        blockers.add("RENDER_ORDER_ID_INVALID")
    if not approved_by.strip():
        blockers.add("HUMAN_APPROVER_REQUIRED")
    if not approval_note.strip():
        blockers.add("HUMAN_APPROVAL_NOTE_REQUIRED")
    if len(nonce.strip()) < 16:
        blockers.add("APPROVAL_NONCE_INVALID")
    if not output_uri.strip():
        blockers.add("RENDER_OUTPUT_URI_MISSING")

    issued = _parse_utc(issued_at)
    expires = _parse_utc(expires_at)
    if expires <= issued:
        blockers.add("APPROVAL_EXPIRY_INVALID")
    now = datetime.now(timezone.utc)
    expired = expires <= now
    if expired:
        blockers.add("APPROVAL_EXPIRED")
    if consumed:
        blockers.add("APPROVAL_ALREADY_CONSUMED")

    state = "consumed" if consumed else "expired" if expired else "blocked" if blockers else "approved"
    core = {
        "schema": "football-shorts-ai.one-time-render-approval.v1",
        "dry_run_id": dry_run_id,
        "render_order_id": render_order_id,
        "approved_by": approved_by.strip(),
        "approval_note": approval_note.strip(),
        "nonce": nonce.strip(),
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "output_uri": output_uri.strip(),
        "approval_state": state,
        "single_use": True,
        "consumed": bool(consumed),
        "dispatch_allowed": state == "approved",
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "ffmpeg_execution_enabled": False,
        "auto_publish": False,
    }
    approval_id = f"RENDERAPPROVAL-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "approval_id": approval_id}
    result = OneTimeRenderApproval(
        schema=core["schema"], approval_id=approval_id, dry_run_id=dry_run_id,
        render_order_id=render_order_id, approved_by=approved_by.strip(),
        approval_note=approval_note.strip(), nonce=nonce.strip(), issued_at=core["issued_at"],
        expires_at=core["expires_at"], output_uri=output_uri.strip(), approval_state=state,
        single_use=True, consumed=bool(consumed), dispatch_allowed=state == "approved",
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["OneTimeRenderApproval", "OneTimeRenderApprovalError", "build_one_time_render_approval", "canonical_sha256"]
