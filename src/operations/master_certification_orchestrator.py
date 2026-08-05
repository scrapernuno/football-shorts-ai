"""FOOTBALL-SHORTS-AI-0063A — Master Certification Orchestrator.

Consolidates certification evidence from the principal production, render,
upload, visibility and publication stages into one deterministic platform report.
It never renders, uploads, changes visibility or publishes content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class MasterCertificationError(ValueError):
    pass


REQUIRED_STAGES = (
    "video_factory",
    "render",
    "publication_series",
    "youtube_upload",
    "visibility",
    "publication_execution",
)


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MasterCertificationReport:
    schema: str
    report_id: str
    commit_sha: str
    stages: Mapping[str, str]
    overall_status: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    render_executed: bool = False
    upload_executed: bool = False
    visibility_changed: bool = False
    publication_executed: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "report_id": self.report_id,
            "commit_sha": self.commit_sha,
            "stages": dict(self.stages),
            "overall_status": self.overall_status,
            "blockers": list(self.blockers),
            "render_executed": False,
            "upload_executed": False,
            "visibility_changed": False,
            "publication_executed": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.master-certification.v1":
            raise MasterCertificationError("unsupported master certification schema")
        if not self.report_id.startswith("MASTER-CERT-"):
            raise MasterCertificationError("invalid report identity")
        if not self.commit_sha.strip():
            raise MasterCertificationError("commit_sha is required")
        if tuple(self.stages) != REQUIRED_STAGES:
            raise MasterCertificationError("stage order is not canonical")
        if any(value not in {"PASS", "FAIL"} for value in self.stages.values()):
            raise MasterCertificationError("stage states must be PASS or FAIL")
        if self.overall_status not in {"CERTIFIED", "BLOCKED"}:
            raise MasterCertificationError("unsupported overall status")
        if self.overall_status == "CERTIFIED" and self.blockers:
            raise MasterCertificationError("certified report cannot contain blockers")
        if self.overall_status == "BLOCKED" and not self.blockers:
            raise MasterCertificationError("blocked report requires blockers")
        if any((self.render_executed, self.upload_executed, self.visibility_changed, self.publication_executed)):
            raise MasterCertificationError("0063A is certification-only")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise MasterCertificationError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise MasterCertificationError("master evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_master_certification_report(*, commit_sha: str, stage_results: Mapping[str, bool]) -> MasterCertificationReport:
    stages = {name: "PASS" if stage_results.get(name) is True else "FAIL" for name in REQUIRED_STAGES}
    blockers = tuple(sorted(f"{name.upper()}_CERTIFICATION_FAILED" for name, state in stages.items() if state == "FAIL"))
    overall = "CERTIFIED" if not blockers else "BLOCKED"
    core = {
        "schema": "football-shorts-ai.master-certification.v1",
        "commit_sha": commit_sha.strip(),
        "stages": stages,
        "overall_status": overall,
        "blockers": list(blockers),
        "render_executed": False,
        "upload_executed": False,
        "visibility_changed": False,
        "publication_executed": False,
    }
    report_id = f"MASTER-CERT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "report_id": report_id}
    result = MasterCertificationReport(
        schema=core["schema"], report_id=report_id, commit_sha=commit_sha.strip(),
        stages=stages, overall_status=overall, blockers=blockers,
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["REQUIRED_STAGES", "MasterCertificationError", "MasterCertificationReport", "build_master_certification_report", "canonical_sha256"]
