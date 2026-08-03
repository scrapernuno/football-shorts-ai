"""
FOOTBALL-SHORTS-AI-0058I
AI DIRECTOR END-TO-END CERTIFICATION

Deterministically certifies the governed 0058A-0058H implementation inventory and
its operational safety posture. No network, acquisition, extraction, model training,
rendering or publication is performed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class AIDirectorCertificationError(ValueError):
    """Raised when the governed AI Director implementation cannot be certified."""


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ARTIFACTS = (
    "src/director/ai_director_strategy.py",
    "src/director/narrative_script_alignment.py",
    "src/director/clip_timing_pace_transition.py",
    "src/director/viral_performance_prediction.py",
    "src/director/human_review_final_approval.py",
    "src/director/factory_handover_package.py",
    "src/director/export_ai_director_review_package.py",
    "dashboard/ai-director-review.html",
    "dashboard/assets/ai-director-review.css",
    "dashboard/assets/ai-director-review.js",
    "dashboard/assets/dashboard-ai-director-integration.js",
    "dashboard/data/ai_director_review_package.json",
    "tests/director/test_ai_director_strategy.py",
    "tests/director/test_narrative_script_alignment.py",
    "tests/director/test_clip_timing_pace_transition.py",
    "tests/director/test_viral_performance_prediction.py",
    "tests/director/test_human_review_final_approval.py",
    "tests/director/test_factory_handover_package.py",
    "tests/dashboard/test_ai_director_review_studio.py",
    "tests/dashboard/test_ai_director_dashboard_live_integration.py",
)

DISABLED_CAPABILITIES = (
    "network_enabled",
    "acquisition_enabled",
    "model_training_enabled",
    "extraction_enabled",
    "render_enabled",
    "auto_publish",
)


@dataclass(frozen=True)
class AIDirectorCertificationReport:
    schema: str
    certification_id: str
    status: str
    artifact_count: int
    artifact_manifest_sha256: str
    certified_stages: tuple[str, ...]
    blockers: tuple[str, ...]
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.ai-director-certification.v1":
            raise AIDirectorCertificationError("unsupported certification schema")
        if not self.certification_id.startswith("AIDIRCERT-"):
            raise AIDirectorCertificationError("invalid certification identity")
        if self.status not in {"CERTIFIED", "BLOCKED"}:
            raise AIDirectorCertificationError("unsupported certification status")
        if self.artifact_count != len(REQUIRED_ARTIFACTS):
            raise AIDirectorCertificationError("artifact inventory count mismatch")
        _validate_sha256(self.artifact_manifest_sha256)
        if self.status == "CERTIFIED" and self.blockers:
            raise AIDirectorCertificationError("certified report cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise AIDirectorCertificationError("blocked report requires blockers")
        if any(getattr(self, name) for name in DISABLED_CAPABILITIES):
            raise AIDirectorCertificationError("0058I cannot enable operational capabilities")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "artifact_count": self.artifact_count,
            "artifact_manifest_sha256": self.artifact_manifest_sha256,
            "certified_stages": list(self.certified_stages),
            "blockers": list(self.blockers),
            **{name: False for name in DISABLED_CAPABILITIES},
        }


def certify_ai_director(*, root: Path = ROOT) -> AIDirectorCertificationReport:
    blockers: set[str] = set()
    manifest_rows: list[dict[str, object]] = []

    for relative in REQUIRED_ARTIFACTS:
        path = root / relative
        if not path.is_file():
            blockers.add(f"MISSING_ARTIFACT:{relative}")
            continue
        data = path.read_bytes()
        manifest_rows.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )

    _validate_dashboard_package(root, blockers)
    _validate_dashboard_entrypoints(root, blockers)
    _validate_disabled_capabilities(root, blockers)

    manifest_rows.sort(key=lambda row: str(row["path"]))
    manifest_sha = canonical_sha256(manifest_rows)
    status = "BLOCKED" if blockers else "CERTIFIED"
    core = {
        "schema": "football-shorts-ai.ai-director-certification.v1",
        "status": status,
        "artifact_count": len(REQUIRED_ARTIFACTS),
        "artifact_manifest_sha256": manifest_sha,
        "certified_stages": ["0058A", "0058B", "0058C", "0058D", "0058E", "0058F", "0058G", "0058H"],
        "blockers": sorted(blockers),
        **{name: False for name in DISABLED_CAPABILITIES},
    }
    report = AIDirectorCertificationReport(
        certification_id=f"AIDIRCERT-{canonical_sha256(core)[:20].upper()}",
        status=status,
        artifact_count=len(REQUIRED_ARTIFACTS),
        artifact_manifest_sha256=manifest_sha,
        certified_stages=tuple(core["certified_stages"]),
        blockers=tuple(sorted(blockers)),
        schema=core["schema"],
    )
    report.validate()
    return report


def _validate_dashboard_package(root: Path, blockers: set[str]) -> None:
    path = root / "dashboard/data/ai_director_review_package.json"
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        blockers.add("AI_DIRECTOR_DASHBOARD_PACKAGE_INVALID")
        return
    if not isinstance(payload, dict):
        blockers.add("AI_DIRECTOR_DASHBOARD_PACKAGE_INVALID")
        return
    for capability in ("network_enabled", "acquisition_enabled", "extraction_enabled", "render_enabled", "auto_publish"):
        if payload.get(capability) is True:
            blockers.add(f"FORBIDDEN_CAPABILITY_ENABLED:{capability}")


def _validate_dashboard_entrypoints(root: Path, blockers: set[str]) -> None:
    index = root / "dashboard/index.html"
    if not index.is_file():
        blockers.add("DASHBOARD_INDEX_MISSING")
        return
    text = index.read_text(encoding="utf-8")
    if "dashboard-ai-director-integration.js" not in text:
        blockers.add("AI_DIRECTOR_MAIN_DASHBOARD_ENTRYPOINT_MISSING")

    review = root / "dashboard/ai-director-review.html"
    if review.is_file():
        review_text = review.read_text(encoding="utf-8")
        for required in ("ai-director-review.css", "ai-director-review.js"):
            if required not in review_text:
                blockers.add(f"AI_DIRECTOR_REVIEW_ENTRYPOINT_MISSING:{required}")


def _validate_disabled_capabilities(root: Path, blockers: set[str]) -> None:
    for relative in REQUIRED_ARTIFACTS:
        if not relative.endswith((".py", ".js", ".json")):
            continue
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for capability in DISABLED_CAPABILITIES:
            forbidden_tokens = (f'"{capability}": true', f"'{capability}': True", f"{capability}=True")
            if any(token in text for token in forbidden_tokens):
                blockers.add(f"FORBIDDEN_CAPABILITY_LITERAL:{relative}:{capability}")


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise AIDirectorCertificationError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AIDirectorCertificationError("evidence must be hexadecimal") from exc


def main() -> int:
    report = certify_ai_director()
    print(report.status)
    print(f"CERTIFICATION_ID={report.certification_id}")
    print(f"ARTIFACT_COUNT={report.artifact_count}")
    print(f"ARTIFACT_MANIFEST_SHA256={report.artifact_manifest_sha256}")
    for name in DISABLED_CAPABILITIES:
        print(f"{name.upper()}=DISABLED")
    if report.blockers:
        for blocker in report.blockers:
            print(f"BLOCKER={blocker}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AIDirectorCertificationError",
    "AIDirectorCertificationReport",
    "REQUIRED_ARTIFACTS",
    "canonical_sha256",
    "certify_ai_director",
]
