"""FOOTBALL-SHORTS-AI-0062A — controlled YouTube visibility execution.

Executes one injected YouTube visibility update only after a valid 0061J decision
and an explicit second human confirmation. Secret values and access tokens are
never persisted. Automatic publication remains forbidden.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Mapping


class ControlledVisibilityExecutionError(ValueError):
    pass


EXECUTION_CONFIRMATION = "EXECUTE AUTHORIZED VISIBILITY CHANGE ONCE"
SUPPORTED_VISIBILITY = {"private", "unlisted", "public"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlledVisibilityExecutionResult:
    schema: str
    execution_id: str
    decision_id: str
    youtube_video_id: str
    previous_visibility: str
    requested_visibility: str
    verified_visibility: str
    execution_state: str
    visibility_change_executed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_used: bool
    credentials_persisted: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "execution_id": self.execution_id,
            "decision_id": self.decision_id,
            "youtube_video_id": self.youtube_video_id,
            "previous_visibility": self.previous_visibility,
            "requested_visibility": self.requested_visibility,
            "verified_visibility": self.verified_visibility,
            "execution_state": self.execution_state,
            "visibility_change_executed": self.visibility_change_executed,
            "blockers": list(self.blockers),
            "network_used": self.network_used,
            "credentials_persisted": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-visibility-execution.v1":
            raise ControlledVisibilityExecutionError("unsupported execution schema")
        if not self.execution_id.startswith("YTVISEXEC-"):
            raise ControlledVisibilityExecutionError("invalid execution identity")
        if not self.decision_id.startswith("YTVISIBILITY-") or not self.youtube_video_id:
            raise ControlledVisibilityExecutionError("invalid visibility decision binding")
        if self.previous_visibility not in SUPPORTED_VISIBILITY:
            raise ControlledVisibilityExecutionError("invalid previous visibility")
        if self.requested_visibility not in SUPPORTED_VISIBILITY:
            raise ControlledVisibilityExecutionError("invalid requested visibility")
        if self.verified_visibility not in SUPPORTED_VISIBILITY:
            raise ControlledVisibilityExecutionError("invalid verified visibility")
        if self.execution_state not in {"published", "no_change", "blocked", "failed"}:
            raise ControlledVisibilityExecutionError("unsupported execution state")
        if self.execution_state == "published":
            if self.blockers or not self.visibility_change_executed or not self.network_used:
                raise ControlledVisibilityExecutionError("published result is inconsistent")
            if self.verified_visibility != self.requested_visibility:
                raise ControlledVisibilityExecutionError("published visibility was not verified")
        if self.execution_state == "no_change" and self.visibility_change_executed:
            raise ControlledVisibilityExecutionError("no-change result cannot execute update")
        if self.execution_state in {"blocked", "failed"} and not self.blockers:
            raise ControlledVisibilityExecutionError("blocked or failed result requires blockers")
        if self.credentials_persisted or self.auto_publish:
            raise ControlledVisibilityExecutionError("credential persistence and auto-publish are forbidden")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ControlledVisibilityExecutionError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledVisibilityExecutionError("execution evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def execute_controlled_visibility_change(
    *,
    decision: Mapping[str, object],
    execution_confirmation: str,
    update_visibility: Callable[[str, str], Mapping[str, object]],
    verify_visibility: Callable[[str], Mapping[str, object]],
) -> ControlledVisibilityExecutionResult:
    blockers: set[str] = set()
    decision_id = str(decision.get("decision_id", ""))
    video_id = str(decision.get("youtube_video_id", ""))
    previous = str(decision.get("current_visibility", ""))
    requested = str(decision.get("target_visibility", ""))

    if decision.get("decision_state") not in {"ready_for_manual_publication", "no_change_required"}:
        blockers.add("VISIBILITY_DECISION_NOT_READY")
    if decision.get("decision_state") == "ready_for_manual_publication" and decision.get("manual_publication_allowed") is not True:
        blockers.add("MANUAL_PUBLICATION_NOT_ALLOWED")
    if not decision_id.startswith("YTVISIBILITY-"):
        blockers.add("VISIBILITY_DECISION_ID_INVALID")
    if not video_id:
        blockers.add("YOUTUBE_VIDEO_ID_REQUIRED")
    if previous not in SUPPORTED_VISIBILITY or requested not in SUPPORTED_VISIBILITY:
        blockers.add("VISIBILITY_VALUE_INVALID")
    if execution_confirmation != EXECUTION_CONFIRMATION:
        blockers.add("SECOND_HUMAN_CONFIRMATION_REQUIRED")
    if decision.get("blockers"):
        blockers.add("VISIBILITY_DECISION_HAS_BLOCKERS")

    network_used = False
    executed = False
    verified = previous if previous in SUPPORTED_VISIBILITY else "private"
    state = "blocked" if blockers else "no_change" if previous == requested else "failed"

    if not blockers and previous != requested:
        network_used = True
        update_result = update_visibility(video_id, requested)
        if str(update_result.get("youtube_video_id", video_id)) != video_id:
            blockers.add("YOUTUBE_UPDATE_VIDEO_ID_MISMATCH")
        elif str(update_result.get("privacy_status", "")) != requested:
            blockers.add("YOUTUBE_UPDATE_NOT_ACCEPTED")
        else:
            executed = True
            verification = verify_visibility(video_id)
            verified = str(verification.get("privacy_status", ""))
            if str(verification.get("youtube_video_id", video_id)) != video_id:
                blockers.add("YOUTUBE_VERIFICATION_VIDEO_ID_MISMATCH")
            if verified != requested:
                blockers.add("YOUTUBE_VISIBILITY_VERIFICATION_FAILED")
        state = "published" if not blockers else "failed"

    core = {
        "schema": "football-shorts-ai.controlled-visibility-execution.v1",
        "decision_id": decision_id,
        "youtube_video_id": video_id,
        "previous_visibility": previous,
        "requested_visibility": requested,
        "verified_visibility": verified,
        "execution_state": state,
        "visibility_change_executed": executed,
        "blockers": sorted(blockers),
        "network_used": network_used,
        "credentials_persisted": False,
        "auto_publish": False,
    }
    execution_id = f"YTVISEXEC-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "execution_id": execution_id}
    result = ControlledVisibilityExecutionResult(
        schema=core["schema"], execution_id=execution_id, decision_id=decision_id,
        youtube_video_id=video_id, previous_visibility=previous,
        requested_visibility=requested, verified_visibility=verified,
        execution_state=state, visibility_change_executed=executed,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
        network_used=network_used,
    )
    result.validate()
    return result


__all__ = [
    "EXECUTION_CONFIRMATION", "ControlledVisibilityExecutionError",
    "ControlledVisibilityExecutionResult", "canonical_sha256",
    "execute_controlled_visibility_change",
]
