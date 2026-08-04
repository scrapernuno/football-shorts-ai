"""FOOTBALL-SHORTS-AI-0061E — human render review and publishing handover.

Records the final human decision for a controlled render intake and prepares an
inert publishing handover. It never uploads or publishes media.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class HumanRenderReviewError(ValueError):
    pass


SUPPORTED_DECISIONS = {"approved", "rejected", "changes_requested"}
SUPPORTED_STATES = {"approved_for_handover", "rejected", "changes_requested", "blocked"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublishingHandover:
    schema: str
    handover_id: str
    intake_id: str
    render_package_id: str
    output_uri: str
    output_sha256: str
    reviewer: str
    decision: str
    review_note: str
    title: str
    description: str
    tags: tuple[str, ...]
    privacy_status: str
    handover_state: str
    publishing_handover_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    upload_enabled: bool = False
    publish_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "handover_id": self.handover_id,
            "intake_id": self.intake_id,
            "render_package_id": self.render_package_id,
            "output_uri": self.output_uri,
            "output_sha256": self.output_sha256,
            "reviewer": self.reviewer,
            "decision": self.decision,
            "review_note": self.review_note,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "privacy_status": self.privacy_status,
            "handover_state": self.handover_state,
            "publishing_handover_allowed": self.publishing_handover_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "upload_enabled": False,
            "publish_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.human-render-review-handover.v1":
            raise HumanRenderReviewError("unsupported handover schema")
        if not self.handover_id.startswith("PUBHANDOVER-"):
            raise HumanRenderReviewError("invalid handover identity")
        if not self.intake_id.startswith("RENDERINTAKE-"):
            raise HumanRenderReviewError("invalid intake identity")
        if not self.render_package_id.startswith("RENDERPKG-"):
            raise HumanRenderReviewError("invalid render package identity")
        if self.decision not in SUPPORTED_DECISIONS:
            raise HumanRenderReviewError("unsupported review decision")
        if self.handover_state not in SUPPORTED_STATES:
            raise HumanRenderReviewError("unsupported handover state")
        if self.privacy_status not in {"private", "unlisted", "public"}:
            raise HumanRenderReviewError("unsupported privacy status")
        if self.handover_state == "approved_for_handover":
            if self.blockers or not self.publishing_handover_allowed:
                raise HumanRenderReviewError("approved handover must be unblocked and allowed")
        elif self.publishing_handover_allowed:
            raise HumanRenderReviewError("non-approved handover cannot be allowed")
        if tuple(sorted(set(self.tags))) != self.tags:
            raise HumanRenderReviewError("tags must be normalized")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise HumanRenderReviewError("blockers must be normalized")
        if any((self.network_enabled, self.upload_enabled, self.publish_enabled, self.auto_publish)):
            raise HumanRenderReviewError("0061E cannot enable publishing capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise HumanRenderReviewError("handover evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_publishing_handover(
    *,
    intake: Mapping[str, object],
    reviewer: str,
    decision: str,
    review_note: str,
    title: str,
    description: str,
    tags: tuple[str, ...] | list[str],
    privacy_status: str = "private",
) -> PublishingHandover:
    blockers: set[str] = set()
    intake_id = str(intake.get("intake_id", ""))
    render_package_id = str(intake.get("render_package_id", ""))
    output_uri = str(intake.get("output_uri", ""))
    output_sha256 = str(intake.get("output_sha256", "")).lower()

    if intake.get("review_state") != "ready_for_review":
        blockers.add("RENDER_INTAKE_NOT_READY")
    if not intake_id.startswith("RENDERINTAKE-"):
        blockers.add("RENDER_INTAKE_ID_INVALID")
    if not render_package_id.startswith("RENDERPKG-"):
        blockers.add("RENDER_PACKAGE_ID_INVALID")
    if not output_uri:
        blockers.add("RENDER_OUTPUT_URI_MISSING")
    if len(output_sha256) != 64 or any(c not in "0123456789abcdef" for c in output_sha256):
        blockers.add("RENDER_OUTPUT_SHA256_INVALID")
    if not reviewer.strip():
        blockers.add("HUMAN_REVIEWER_REQUIRED")
    if decision not in SUPPORTED_DECISIONS:
        blockers.add("REVIEW_DECISION_INVALID")
    if not review_note.strip():
        blockers.add("REVIEW_NOTE_REQUIRED")
    if decision == "approved" and not title.strip():
        blockers.add("PUBLISHING_TITLE_REQUIRED")
    if decision == "approved" and not description.strip():
        blockers.add("PUBLISHING_DESCRIPTION_REQUIRED")
    if privacy_status not in {"private", "unlisted", "public"}:
        blockers.add("PRIVACY_STATUS_INVALID")

    if "RENDER_INTAKE_NOT_READY" in blockers or "RENDER_INTAKE_ID_INVALID" in blockers:
        state = "blocked"
    elif decision == "approved" and not blockers:
        state = "approved_for_handover"
    elif decision == "rejected":
        blockers.add("RENDER_REJECTED_BY_HUMAN")
        state = "rejected"
    elif decision == "changes_requested":
        blockers.add("RENDER_CHANGES_REQUESTED")
        state = "changes_requested"
    else:
        state = "blocked"

    normalized_tags = tuple(sorted({str(tag).strip() for tag in tags if str(tag).strip()}))
    allowed = state == "approved_for_handover"
    core = {
        "schema": "football-shorts-ai.human-render-review-handover.v1",
        "intake_id": intake_id,
        "render_package_id": render_package_id,
        "output_uri": output_uri,
        "output_sha256": output_sha256,
        "reviewer": reviewer.strip(),
        "decision": decision,
        "review_note": review_note.strip(),
        "title": title.strip(),
        "description": description.strip(),
        "tags": list(normalized_tags),
        "privacy_status": privacy_status,
        "handover_state": state,
        "publishing_handover_allowed": allowed,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "upload_enabled": False,
        "publish_enabled": False,
        "auto_publish": False,
    }
    handover_id = f"PUBHANDOVER-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "handover_id": handover_id}
    result = PublishingHandover(
        schema=core["schema"], handover_id=handover_id, intake_id=intake_id,
        render_package_id=render_package_id, output_uri=output_uri,
        output_sha256=output_sha256, reviewer=reviewer.strip(), decision=decision,
        review_note=review_note.strip(), title=title.strip(), description=description.strip(),
        tags=normalized_tags, privacy_status=privacy_status, handover_state=state,
        publishing_handover_allowed=allowed, blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = [
    "HumanRenderReviewError",
    "PublishingHandover",
    "build_publishing_handover",
    "canonical_sha256",
]
