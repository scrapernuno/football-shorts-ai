"""FOOTBALL-SHORTS-AI-0058E — Human review and final variant approval contract."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class DirectorApprovalError(ValueError):
    pass


DECISIONS = {"approved", "rejected", "changes_requested"}
STATES = {"approved", "rejected", "changes_requested", "blocked"}


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class DirectorApprovalReport:
    schema: str
    approval_id: str
    ranking_id: str
    selected_variant_id: str | None
    reviewer_id: str
    decision: str
    notes: str
    approval_state: str
    factory_handover_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "approval_id": self.approval_id,
            "ranking_id": self.ranking_id,
            "selected_variant_id": self.selected_variant_id,
            "reviewer_id": self.reviewer_id,
            "decision": self.decision,
            "notes": self.notes,
            "approval_state": self.approval_state,
            "factory_handover_allowed": self.factory_handover_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.director-approval.v1":
            raise DirectorApprovalError("unsupported approval schema")
        if not self.approval_id.startswith("DIRAPPROVAL-"):
            raise DirectorApprovalError("invalid approval identity")
        if not self.ranking_id.startswith("DIRRANK-"):
            raise DirectorApprovalError("invalid ranking identity")
        if self.decision not in DECISIONS or self.approval_state not in STATES:
            raise DirectorApprovalError("unsupported decision or state")
        if not self.reviewer_id.strip():
            raise DirectorApprovalError("reviewer_id is required")
        if self.decision == "approved":
            if not self.selected_variant_id or not self.selected_variant_id.startswith("DIRVAR-"):
                raise DirectorApprovalError("approved decision requires a selected variant")
            if self.blockers or not self.factory_handover_allowed or self.approval_state != "approved":
                raise DirectorApprovalError("approved report is inconsistent")
        else:
            if self.factory_handover_allowed:
                raise DirectorApprovalError("non-approved report cannot allow handover")
            if not self.blockers:
                raise DirectorApprovalError("non-approved report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.render_enabled, self.auto_publish)):
            raise DirectorApprovalError("0058E cannot enable operational capabilities")
        if len(self.evidence_sha256) != 64 or canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise DirectorApprovalError("approval evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_director_approval(
    *, ranking_report: Mapping[str, object], reviewer_id: str, decision: str,
    selected_variant_id: str | None = None, notes: str = "",
) -> DirectorApprovalReport:
    ranking_id = ranking_report.get("ranking_id")
    if not isinstance(ranking_id, str) or not ranking_id.startswith("DIRRANK-"):
        raise DirectorApprovalError("ranking_id is invalid")
    if decision not in DECISIONS:
        raise DirectorApprovalError("unsupported decision")
    blockers: set[str] = set()
    ranked_ids = tuple(str(v) for v in ranking_report.get("ranked_variant_ids", ()))
    if ranking_report.get("ranking_state") != "ranked":
        blockers.add("DIRECTOR_RANKING_NOT_READY")
    chosen = selected_variant_id or ranking_report.get("recommended_variant_id")
    if decision == "approved":
        if not isinstance(chosen, str) or chosen not in ranked_ids:
            blockers.add("SELECTED_VARIANT_NOT_RANKED")
        if ranking_report.get("blockers"):
            blockers.add("DIRECTOR_RANKING_BLOCKED")
        state = "blocked" if blockers else "approved"
        handover = not blockers
    elif decision == "changes_requested":
        blockers.add("EDITORIAL_CHANGES_REQUESTED")
        state, handover = "changes_requested", False
    else:
        blockers.add("EDITORIAL_VARIANT_REJECTED")
        state, handover = "rejected", False
    core = {
        "schema": "football-shorts-ai.director-approval.v1",
        "ranking_id": ranking_id,
        "selected_variant_id": chosen if isinstance(chosen, str) else None,
        "reviewer_id": reviewer_id.strip(),
        "decision": decision,
        "notes": notes.strip(),
        "approval_state": state,
        "factory_handover_allowed": handover,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    approval_id = f"DIRAPPROVAL-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "approval_id": approval_id}
    report = DirectorApprovalReport(
        approval_id=approval_id, evidence_sha256=canonical_sha256(unsigned),
        ranking_id=ranking_id, selected_variant_id=core["selected_variant_id"],
        reviewer_id=core["reviewer_id"], decision=decision, notes=core["notes"],
        approval_state=state, factory_handover_allowed=handover,
        blockers=tuple(sorted(blockers)), schema=core["schema"],
    )
    report.validate()
    return report


__all__ = ["DirectorApprovalError", "DirectorApprovalReport", "build_director_approval", "canonical_sha256"]
