"""FOOTBALL-SHORTS-AI-0061J — controlled visibility decision and final publication.

Builds a deterministic human visibility decision from a processed 0061I intake.
The contract never performs a network request or changes YouTube visibility.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class ControlledVisibilityError(ValueError):
    pass


CONFIRMATION_PHRASE = "APPLY AUTHORIZED YOUTUBE VISIBILITY ONCE"
SUPPORTED_VISIBILITY = {"private", "unlisted", "public"}
SUPPORTED_STATES = {"ready_for_manual_publication", "no_change_required", "blocked"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlledVisibilityDecision:
    schema: str
    decision_id: str
    youtube_result_id: str
    youtube_video_id: str
    requested_by: str
    decision_note: str
    current_visibility: str
    target_visibility: str
    confirmation_phrase: str
    decision_state: str
    manual_publication_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    visibility_change_executed: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "decision_id": self.decision_id,
            "youtube_result_id": self.youtube_result_id,
            "youtube_video_id": self.youtube_video_id,
            "requested_by": self.requested_by,
            "decision_note": self.decision_note,
            "current_visibility": self.current_visibility,
            "target_visibility": self.target_visibility,
            "confirmation_phrase": self.confirmation_phrase,
            "decision_state": self.decision_state,
            "manual_publication_allowed": self.manual_publication_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "visibility_change_executed": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-visibility-decision.v1":
            raise ControlledVisibilityError("unsupported visibility schema")
        if not self.decision_id.startswith("YTVISIBILITY-"):
            raise ControlledVisibilityError("invalid visibility decision identity")
        if not self.youtube_result_id.startswith("YTRESULT-") or not self.youtube_video_id:
            raise ControlledVisibilityError("invalid YouTube result identity")
        if self.current_visibility not in SUPPORTED_VISIBILITY or self.target_visibility not in SUPPORTED_VISIBILITY:
            raise ControlledVisibilityError("unsupported visibility")
        if self.decision_state not in SUPPORTED_STATES:
            raise ControlledVisibilityError("unsupported decision state")
        if self.decision_state == "ready_for_manual_publication":
            if self.blockers or not self.manual_publication_allowed or self.current_visibility == self.target_visibility:
                raise ControlledVisibilityError("ready decision is inconsistent")
        elif self.manual_publication_allowed:
            raise ControlledVisibilityError("non-ready decision cannot allow publication")
        if self.decision_state == "blocked" and not self.blockers:
            raise ControlledVisibilityError("blocked decision requires blockers")
        if any((self.network_enabled, self.visibility_change_executed, self.auto_publish)):
            raise ControlledVisibilityError("0061J contract cannot execute publication")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ControlledVisibilityError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledVisibilityError("visibility evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_visibility_decision(
    *, youtube_intake: Mapping[str, object], requested_by: str, decision_note: str,
    target_visibility: str, confirmation_phrase: str,
) -> ControlledVisibilityDecision:
    blockers: set[str] = set()
    result_id = str(youtube_intake.get("intake_id") or youtube_intake.get("result_id") or "")
    video_id = str(youtube_intake.get("youtube_video_id", ""))
    current = str(youtube_intake.get("privacy_status") or youtube_intake.get("visibility") or "")
    if youtube_intake.get("intake_state") != "processed": blockers.add("YOUTUBE_VIDEO_NOT_PROCESSED")
    if not result_id.startswith("YTRESULT-"): blockers.add("YOUTUBE_RESULT_ID_INVALID")
    if not video_id: blockers.add("YOUTUBE_VIDEO_ID_REQUIRED")
    if current not in SUPPORTED_VISIBILITY: blockers.add("CURRENT_VISIBILITY_INVALID")
    if target_visibility not in SUPPORTED_VISIBILITY: blockers.add("TARGET_VISIBILITY_INVALID")
    if not requested_by.strip(): blockers.add("HUMAN_REQUESTER_REQUIRED")
    if not decision_note.strip(): blockers.add("VISIBILITY_DECISION_NOTE_REQUIRED")
    if confirmation_phrase != CONFIRMATION_PHRASE: blockers.add("EXPLICIT_HUMAN_VISIBILITY_CONFIRMATION_REQUIRED")
    if youtube_intake.get("blockers"): blockers.add("YOUTUBE_RESULT_HAS_BLOCKERS")

    if blockers:
        state, allowed = "blocked", False
    elif current == target_visibility:
        state, allowed = "no_change_required", False
    else:
        state, allowed = "ready_for_manual_publication", True

    core = {
        "schema": "football-shorts-ai.controlled-visibility-decision.v1",
        "youtube_result_id": result_id,
        "youtube_video_id": video_id,
        "requested_by": requested_by.strip(),
        "decision_note": decision_note.strip(),
        "current_visibility": current,
        "target_visibility": target_visibility,
        "confirmation_phrase": confirmation_phrase,
        "decision_state": state,
        "manual_publication_allowed": allowed,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "visibility_change_executed": False,
        "auto_publish": False,
    }
    decision_id = f"YTVISIBILITY-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "decision_id": decision_id}
    result = ControlledVisibilityDecision(
        schema=core["schema"], decision_id=decision_id, youtube_result_id=result_id,
        youtube_video_id=video_id, requested_by=requested_by.strip(), decision_note=decision_note.strip(),
        current_visibility=current, target_visibility=target_visibility,
        confirmation_phrase=confirmation_phrase, decision_state=state,
        manual_publication_allowed=allowed, blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["CONFIRMATION_PHRASE", "ControlledVisibilityDecision", "ControlledVisibilityError", "build_controlled_visibility_decision", "canonical_sha256"]
