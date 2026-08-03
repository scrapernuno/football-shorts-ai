"""
FOOTBALL-SHORTS-AI-0053B
HUMAN PUBLICATION APPROVAL GATE

Issues and validates deterministic human-approval evidence for governed
publication requests. Approval evidence is bound to one video, one publishing
package, one platform and one publishing-readiness checksum. This module never
authenticates with a platform, uploads, schedules or publishes content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping

from publishing.governed_publication_contract import HumanApproval


SUPPORTED_APPROVAL_DECISIONS = {
    "approved",
    "rejected",
    "revoked",
}

DEFAULT_APPROVAL_TTL_SECONDS = 24 * 60 * 60
MAX_APPROVAL_TTL_SECONDS = 7 * 24 * 60 * 60


class HumanPublicationApprovalGateError(ValueError):
    """Raised when publication approval evidence is invalid or unusable."""


@dataclass(frozen=True)
class PublicationApprovalSubject:
    video_id: str
    publishing_package_id: str
    platform: str
    readiness_evidence_sha256: str

    def validate(self) -> None:
        for name, value in {
            "video_id": self.video_id,
            "publishing_package_id": self.publishing_package_id,
            "platform": self.platform,
        }.items():
            if not value.strip():
                raise HumanPublicationApprovalGateError(f"{name} is required")
        if not _is_sha256(self.readiness_evidence_sha256):
            raise HumanPublicationApprovalGateError(
                "readiness_evidence_sha256 must be SHA-256"
            )

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "video_id": self.video_id,
            "publishing_package_id": self.publishing_package_id,
            "platform": self.platform,
            "readiness_evidence_sha256": self.readiness_evidence_sha256,
        }


@dataclass(frozen=True)
class PublicationApprovalEvidence:
    schema: str
    approval_id: str
    subject: PublicationApprovalSubject
    decision: str
    approved_by: str
    approval_reference: str
    decided_at: str
    expires_at: str
    reason: str
    evidence_sha256: str
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.publication-approval.v1":
            raise HumanPublicationApprovalGateError(
                "unsupported publication approval schema"
            )
        if not self.approval_id.startswith("APR-"):
            raise HumanPublicationApprovalGateError("invalid approval_id")
        self.subject.validate()
        if self.decision not in SUPPORTED_APPROVAL_DECISIONS:
            raise HumanPublicationApprovalGateError(
                "unsupported approval decision"
            )
        if not self.approved_by.strip():
            raise HumanPublicationApprovalGateError("approved_by is required")
        if not self.approval_reference.strip():
            raise HumanPublicationApprovalGateError(
                "approval_reference is required"
            )
        if not self.reason.strip():
            raise HumanPublicationApprovalGateError("approval reason is required")

        decided = _parse_utc_timestamp(self.decided_at)
        expires = _parse_utc_timestamp(self.expires_at)
        if expires <= decided:
            raise HumanPublicationApprovalGateError(
                "approval expiry must be after decision time"
            )
        if expires - decided > timedelta(seconds=MAX_APPROVAL_TTL_SECONDS):
            raise HumanPublicationApprovalGateError(
                "approval lifetime exceeds governed maximum"
            )
        if not _is_sha256(self.evidence_sha256):
            raise HumanPublicationApprovalGateError(
                "evidence_sha256 must be SHA-256"
            )
        if self.evidence_sha256 != _approval_evidence_sha256(self):
            raise HumanPublicationApprovalGateError(
                "approval evidence checksum mismatch"
            )
        if self.execution_enabled:
            raise HumanPublicationApprovalGateError(
                "publication execution remains disabled"
            )
        if self.auto_publish:
            raise HumanPublicationApprovalGateError(
                "automatic publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "approval_id": self.approval_id,
            "subject": self.subject.to_dict(),
            "decision": self.decision,
            "approved_by": self.approved_by,
            "approval_reference": self.approval_reference,
            "decided_at": self.decided_at,
            "expires_at": self.expires_at,
            "reason": self.reason,
            "evidence_sha256": self.evidence_sha256,
            "execution_enabled": False,
            "auto_publish": False,
        }


@dataclass(frozen=True)
class ApprovalValidationResult:
    schema: str
    status: str
    approval_id: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    human_approval: HumanApproval | None
    execution_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.approval-validation.v1":
            raise HumanPublicationApprovalGateError(
                "unsupported approval validation schema"
            )
        if self.status not in {"APPROVED", "BLOCKED"}:
            raise HumanPublicationApprovalGateError(
                "unsupported approval validation status"
            )
        if set(self.checks.values()) - {True, False}:
            raise HumanPublicationApprovalGateError(
                "approval checks must be boolean"
            )
        if self.status == "APPROVED":
            if self.blockers or self.human_approval is None:
                raise HumanPublicationApprovalGateError(
                    "approved validation is internally inconsistent"
                )
        elif not self.blockers or self.human_approval is not None:
            raise HumanPublicationApprovalGateError(
                "blocked validation is internally inconsistent"
            )
        if self.execution_enabled or self.auto_publish:
            raise HumanPublicationApprovalGateError(
                "approval gate cannot activate publication"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        approval = None
        if self.human_approval is not None:
            approval = {
                "approved": self.human_approval.approved,
                "approved_by": self.human_approval.approved_by,
                "approved_at": self.human_approval.approved_at,
                "approval_reference": self.human_approval.approval_reference,
            }
        return {
            "schema": self.schema,
            "status": self.status,
            "approval_id": self.approval_id,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "human_approval": approval,
            "execution_enabled": False,
            "auto_publish": False,
        }


def issue_publication_approval(
    *,
    subject: PublicationApprovalSubject,
    decision: str,
    approved_by: str,
    approval_reference: str,
    decided_at: str,
    reason: str,
    ttl_seconds: int = DEFAULT_APPROVAL_TTL_SECONDS,
) -> PublicationApprovalEvidence:
    """Issue immutable approval evidence without enabling publication."""

    subject.validate()
    if decision not in SUPPORTED_APPROVAL_DECISIONS:
        raise HumanPublicationApprovalGateError(
            "unsupported approval decision"
        )
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
        raise HumanPublicationApprovalGateError("ttl_seconds must be an integer")
    if ttl_seconds <= 0 or ttl_seconds > MAX_APPROVAL_TTL_SECONDS:
        raise HumanPublicationApprovalGateError(
            "ttl_seconds is outside the governed range"
        )

    decided = _parse_utc_timestamp(decided_at)
    expires_at = _format_utc(decided + timedelta(seconds=ttl_seconds))
    identity = {
        "subject": subject.to_dict(),
        "decision": decision,
        "approved_by": approved_by.strip(),
        "approval_reference": approval_reference.strip(),
        "decided_at": _format_utc(decided),
        "expires_at": expires_at,
        "reason": reason.strip(),
    }
    approval_id = f"APR-{canonical_sha256(identity)[:20].upper()}"

    provisional = PublicationApprovalEvidence(
        schema="football-shorts-ai.publication-approval.v1",
        approval_id=approval_id,
        subject=subject,
        decision=decision,
        approved_by=approved_by.strip(),
        approval_reference=approval_reference.strip(),
        decided_at=_format_utc(decided),
        expires_at=expires_at,
        reason=reason.strip(),
        evidence_sha256="0" * 64,
        execution_enabled=False,
        auto_publish=False,
    )
    evidence = PublicationApprovalEvidence(
        **{
            **provisional.__dict__,
            "evidence_sha256": _approval_evidence_sha256(provisional),
        }
    )
    evidence.validate()
    return evidence


def validate_publication_approval(
    *,
    evidence: PublicationApprovalEvidence,
    expected_subject: PublicationApprovalSubject,
    evaluated_at: str,
) -> ApprovalValidationResult:
    """Validate approval evidence against current publication facts."""

    evidence.validate()
    expected_subject.validate()
    now = _parse_utc_timestamp(evaluated_at)
    expires = _parse_utc_timestamp(evidence.expires_at)

    checks = {
        "decision_approved": evidence.decision == "approved",
        "subject_matches": evidence.subject == expected_subject,
        "not_expired": now <= expires,
        "decision_not_future_dated": _parse_utc_timestamp(evidence.decided_at) <= now,
        "evidence_integrity_valid": (
            evidence.evidence_sha256 == _approval_evidence_sha256(evidence)
        ),
        "execution_disabled": not evidence.execution_enabled,
        "auto_publish_disabled": not evidence.auto_publish,
    }
    blockers = tuple(
        name.upper()
        for name, passed in checks.items()
        if not passed
    )

    approval = None
    if not blockers:
        approval = HumanApproval(
            approved=True,
            approved_by=evidence.approved_by,
            approved_at=evidence.decided_at,
            approval_reference=evidence.approval_id,
        )
        approval.validate()

    result = ApprovalValidationResult(
        schema="football-shorts-ai.approval-validation.v1",
        status="APPROVED" if not blockers else "BLOCKED",
        approval_id=evidence.approval_id,
        checks=checks,
        blockers=blockers,
        human_approval=approval,
        execution_enabled=False,
        auto_publish=False,
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _approval_evidence_sha256(evidence: PublicationApprovalEvidence) -> str:
    return canonical_sha256(
        {
            "schema": evidence.schema,
            "approval_id": evidence.approval_id,
            "subject": evidence.subject.to_dict(),
            "decision": evidence.decision,
            "approved_by": evidence.approved_by,
            "approval_reference": evidence.approval_reference,
            "decided_at": evidence.decided_at,
            "expires_at": evidence.expires_at,
            "reason": evidence.reason,
            "execution_enabled": False,
            "auto_publish": False,
        }
    )


def _is_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _parse_utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HumanPublicationApprovalGateError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HumanPublicationApprovalGateError(
            "timestamp must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise HumanPublicationApprovalGateError("timestamp must use UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ApprovalValidationResult",
    "DEFAULT_APPROVAL_TTL_SECONDS",
    "HumanPublicationApprovalGateError",
    "MAX_APPROVAL_TTL_SECONDS",
    "PublicationApprovalEvidence",
    "PublicationApprovalSubject",
    "SUPPORTED_APPROVAL_DECISIONS",
    "canonical_sha256",
    "issue_publication_approval",
    "validate_publication_approval",
]
