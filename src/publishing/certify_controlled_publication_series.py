"""FOOTBALL-SHORTS-AI-0061J — deterministic certification for series 0061A–0061J."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ControlledPublicationCertificationError(ValueError):
    pass


REQUIRED_FILES = (
    "src/factory/controlled_render_authorization.py",
    "src/factory/controlled_ffmpeg_execution_gate.py",
    "src/factory/run_controlled_render.py",
    "src/factory/render_result_intake.py",
    "src/factory/human_render_review_publishing_handover.py",
    "src/publishing/controlled_youtube_publishing_gate.py",
    "src/publishing/controlled_youtube_upload_workflow_binding.py",
    "src/publishing/controlled_oauth_resumable_upload_activation.py",
    "src/publishing/youtube_upload_result_intake.py",
    "src/publishing/controlled_visibility_final_publication.py",
)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ControlledPublicationSeriesCertification:
    schema: str
    certification_id: str
    status: str
    file_hashes: Mapping[str, str]
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    evidence_sha256: str
    automatic_render: bool = False
    automatic_upload: bool = False
    automatic_publication: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-publication-series-certification.v1":
            raise ControlledPublicationCertificationError("unsupported certification schema")
        if not self.certification_id.startswith("PUBLICATIONCERT-"):
            raise ControlledPublicationCertificationError("invalid certification identity")
        if self.status not in {"CERTIFIED", "BLOCKED"}:
            raise ControlledPublicationCertificationError("unsupported certification status")
        if self.status == "CERTIFIED" and self.blockers:
            raise ControlledPublicationCertificationError("certified result cannot have blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise ControlledPublicationCertificationError("blocked result requires blockers")
        if self.automatic_render or self.automatic_upload or self.automatic_publication:
            raise ControlledPublicationCertificationError("automatic operations must remain disabled")
        unsigned = {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "file_hashes": dict(self.file_hashes),
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "automatic_render": False,
            "automatic_upload": False,
            "automatic_publication": False,
        }
        if canonical_sha256(unsigned) != self.evidence_sha256:
            raise ControlledPublicationCertificationError("certification evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "file_hashes": dict(self.file_hashes),
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "automatic_render": False,
            "automatic_upload": False,
            "automatic_publication": False,
            "evidence_sha256": self.evidence_sha256,
        }


def certify_controlled_publication_series(root: Path) -> ControlledPublicationSeriesCertification:
    hashes: dict[str, str] = {}
    blockers: list[str] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            blockers.append(f"MISSING:{relative}")
            continue
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    checks = {
        "all_required_files_present": len(hashes) == len(REQUIRED_FILES),
        "automatic_render_disabled": True,
        "automatic_upload_disabled": True,
        "automatic_publication_disabled": True,
    }
    status = "CERTIFIED" if not blockers and all(checks.values()) else "BLOCKED"
    core = {
        "schema": "football-shorts-ai.controlled-publication-series-certification.v1",
        "status": status,
        "file_hashes": hashes,
        "checks": checks,
        "blockers": sorted(blockers),
        "automatic_render": False,
        "automatic_upload": False,
        "automatic_publication": False,
    }
    cert_id = f"PUBLICATIONCERT-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "certification_id": cert_id}
    result = ControlledPublicationSeriesCertification(
        schema=core["schema"], certification_id=cert_id, status=status,
        file_hashes=hashes, checks=checks, blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["ControlledPublicationSeriesCertification", "ControlledPublicationCertificationError", "certify_controlled_publication_series"]
