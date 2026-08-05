"""FOOTBALL-SHORTS-AI-0062C — publication result intake.

Records and validates one controlled 0062A/0062B YouTube visibility execution.
No network request, credential access, visibility change, upload or automatic
publication is performed by this intake contract.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class PublicationResultIntakeError(ValueError):
    pass


SUPPORTED_VISIBILITY = {"private", "unlisted", "public"}
SUPPORTED_STATES = {"confirmed", "review_required", "blocked"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PublicationResultIntake:
    schema: str
    intake_id: str
    execution_id: str
    decision_id: str
    youtube_video_id: str
    previous_visibility: str
    requested_visibility: str
    verified_visibility: str
    publication_url: str
    intake_state: str
    publication_confirmed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_used_by_intake: bool = False
    credentials_read_by_intake: bool = False
    visibility_change_executed_by_intake: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "intake_id": self.intake_id,
            "execution_id": self.execution_id,
            "decision_id": self.decision_id,
            "youtube_video_id": self.youtube_video_id,
            "previous_visibility": self.previous_visibility,
            "requested_visibility": self.requested_visibility,
            "verified_visibility": self.verified_visibility,
            "publication_url": self.publication_url,
            "intake_state": self.intake_state,
            "publication_confirmed": self.publication_confirmed,
            "blockers": list(self.blockers),
            "network_used_by_intake": False,
            "credentials_read_by_intake": False,
            "visibility_change_executed_by_intake": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.publication-result-intake.v1":
            raise PublicationResultIntakeError("unsupported intake schema")
        if not self.intake_id.startswith("YTPUBRESULT-"):
            raise PublicationResultIntakeError("invalid intake identity")
        if not self.execution_id.startswith("YTVISEXEC-"):
            raise PublicationResultIntakeError("invalid execution identity")
        if not self.decision_id.startswith("YTVISIBILITY-"):
            raise PublicationResultIntakeError("invalid decision identity")
        if not self.youtube_video_id:
            raise PublicationResultIntakeError("youtube_video_id is required")
        if self.previous_visibility not in SUPPORTED_VISIBILITY:
            raise PublicationResultIntakeError("invalid previous visibility")
        if self.requested_visibility not in SUPPORTED_VISIBILITY:
            raise PublicationResultIntakeError("invalid requested visibility")
        if self.verified_visibility not in SUPPORTED_VISIBILITY:
            raise PublicationResultIntakeError("invalid verified visibility")
        if self.intake_state not in SUPPORTED_STATES:
            raise PublicationResultIntakeError("unsupported intake state")
        if self.intake_state == "confirmed":
            if self.blockers or not self.publication_confirmed:
                raise PublicationResultIntakeError("confirmed intake is inconsistent")
            if self.verified_visibility != self.requested_visibility:
                raise PublicationResultIntakeError("confirmed visibility mismatch")
        elif self.publication_confirmed:
            raise PublicationResultIntakeError("non-confirmed intake cannot confirm publication")
        if self.intake_state == "blocked" and not self.blockers:
            raise PublicationResultIntakeError("blocked intake requires blockers")
        if any((self.network_used_by_intake, self.credentials_read_by_intake,
                self.visibility_change_executed_by_intake, self.auto_publish)):
            raise PublicationResultIntakeError("0062C intake cannot perform external operations")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise PublicationResultIntakeError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise PublicationResultIntakeError("publication intake evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_publication_result_intake(
    *, execution_result: Mapping[str, object]
) -> PublicationResultIntake:
    blockers: set[str] = set()
    execution_id = str(execution_result.get("execution_id", ""))
    decision_id = str(execution_result.get("decision_id", ""))
    video_id = str(execution_result.get("youtube_video_id", ""))
    previous = str(execution_result.get("previous_visibility", ""))
    requested = str(execution_result.get("requested_visibility", ""))
    verified = str(execution_result.get("verified_visibility", ""))
    state = str(execution_result.get("execution_state", ""))

    if not execution_id.startswith("YTVISEXEC-"):
        blockers.add("VISIBILITY_EXECUTION_ID_INVALID")
    if not decision_id.startswith("YTVISIBILITY-"):
        blockers.add("VISIBILITY_DECISION_ID_INVALID")
    if not video_id:
        blockers.add("YOUTUBE_VIDEO_ID_REQUIRED")
    if previous not in SUPPORTED_VISIBILITY:
        blockers.add("PREVIOUS_VISIBILITY_INVALID")
    if requested not in SUPPORTED_VISIBILITY:
        blockers.add("REQUESTED_VISIBILITY_INVALID")
    if verified not in SUPPORTED_VISIBILITY:
        blockers.add("VERIFIED_VISIBILITY_INVALID")
    if execution_result.get("credentials_persisted") is True:
        blockers.add("CREDENTIAL_PERSISTENCE_REPORTED")
    if execution_result.get("auto_publish") is True:
        blockers.add("AUTOMATIC_PUBLICATION_REPORTED")

    if state == "published":
        if execution_result.get("visibility_change_executed") is not True:
            blockers.add("VISIBILITY_CHANGE_NOT_EXECUTED")
        if execution_result.get("network_used") is not True:
            blockers.add("CONTROLLED_NETWORK_EXECUTION_NOT_REPORTED")
        if verified != requested:
            blockers.add("YOUTUBE_VISIBILITY_NOT_CONFIRMED")
    elif state == "no_change":
        if previous != requested or verified != requested:
            blockers.add("NO_CHANGE_VISIBILITY_INCONSISTENT")
    else:
        blockers.add("VISIBILITY_EXECUTION_NOT_SUCCESSFUL")

    if execution_result.get("blockers"):
        blockers.add("VISIBILITY_EXECUTION_HAS_BLOCKERS")

    publication_confirmed = not blockers and state in {"published", "no_change"}
    intake_state = "confirmed" if publication_confirmed else "blocked"
    publication_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
    core = {
        "schema": "football-shorts-ai.publication-result-intake.v1",
        "execution_id": execution_id,
        "decision_id": decision_id,
        "youtube_video_id": video_id,
        "previous_visibility": previous,
        "requested_visibility": requested,
        "verified_visibility": verified if verified in SUPPORTED_VISIBILITY else "private",
        "publication_url": publication_url,
        "intake_state": intake_state,
        "publication_confirmed": publication_confirmed,
        "blockers": sorted(blockers),
        "network_used_by_intake": False,
        "credentials_read_by_intake": False,
        "visibility_change_executed_by_intake": False,
        "auto_publish": False,
    }
    intake_id = f"YTPUBRESULT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "intake_id": intake_id}
    result = PublicationResultIntake(
        schema=core["schema"], intake_id=intake_id, execution_id=execution_id,
        decision_id=decision_id, youtube_video_id=video_id,
        previous_visibility=previous, requested_visibility=requested,
        verified_visibility=core["verified_visibility"], publication_url=publication_url,
        intake_state=intake_state, publication_confirmed=publication_confirmed,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = [
    "PublicationResultIntake", "PublicationResultIntakeError",
    "build_publication_result_intake", "canonical_sha256",
]
