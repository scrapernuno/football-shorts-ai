"""
FOOTBALL-SHORTS-AI-0058H
AI DIRECTOR DASHBOARD MAIN NAVIGATION AND LIVE PACKAGE EXPORT

Builds a deterministic, fail-closed dashboard package from governed 0058A-0058F
artifacts. This module performs no network access, acquisition, extraction,
rendering or publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping


class AIDirectorPackageExportError(ValueError):
    """Raised when AI Director dashboard evidence is invalid."""


SCHEMA = "football-shorts-ai.ai-director-review-package.v1"


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    if not path.is_file():
        raise AIDirectorPackageExportError(f"input file does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AIDirectorPackageExportError(f"input must contain a JSON object: {path}")
    return payload


def build_review_package(
    *,
    director_report: Mapping[str, object] | None = None,
    narrative_alignment: Mapping[str, object] | None = None,
    timing_optimization: Mapping[str, object] | None = None,
    performance_ranking: Mapping[str, object] | None = None,
    approval: Mapping[str, object] | None = None,
    factory_handover: Mapping[str, object] | None = None,
) -> dict[str, object]:
    director = dict(director_report or {})
    alignment = dict(narrative_alignment or {})
    timing = dict(timing_optimization or {})
    ranking = dict(performance_ranking or {})
    review = dict(approval or {})
    handover = dict(factory_handover or {})

    blockers: set[str] = set()
    if not director:
        blockers.add("AI_DIRECTOR_EVIDENCE_MISSING")
    if not ranking:
        blockers.add("VARIANT_RANKING_EVIDENCE_MISSING")
    if not review or review.get("approval_state") != "approved":
        blockers.add("HUMAN_APPROVAL_REQUIRED")
    if not handover or handover.get("handover_state") != "ready_for_factory":
        blockers.add("FACTORY_HANDOVER_NOT_READY")

    for payload in (director, alignment, timing, ranking, review, handover):
        values = payload.get("blockers", ())
        if isinstance(values, list):
            blockers.update(str(value) for value in values if str(value))

    variants = director.get("variants", ())
    if not isinstance(variants, list):
        variants = []

    state = "ready_for_factory" if not blockers else "blocked"
    unsigned = {
        "schema": SCHEMA,
        "package_state": state,
        "director_report": director,
        "narrative_alignment": alignment,
        "timing_optimization": timing,
        "performance_ranking": ranking,
        "approval": review,
        "factory_handover": handover,
        "variants": variants,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    package_id = f"AIDIRPKG-{canonical_sha256(unsigned)[:20].upper()}"
    package = {
        **unsigned,
        "package_id": package_id,
    }
    package["evidence_sha256"] = canonical_sha256(package)
    return package


def validate_review_package(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != SCHEMA:
        raise AIDirectorPackageExportError("unsupported AI Director package schema")
    package_id = payload.get("package_id")
    if not isinstance(package_id, str) or not package_id.startswith("AIDIRPKG-"):
        raise AIDirectorPackageExportError("invalid AI Director package identity")
    evidence = payload.get("evidence_sha256")
    if not isinstance(evidence, str) or len(evidence) != 64:
        raise AIDirectorPackageExportError("invalid package SHA-256 evidence")
    unsigned = dict(payload)
    unsigned.pop("evidence_sha256", None)
    if canonical_sha256(unsigned) != evidence:
        raise AIDirectorPackageExportError("AI Director package evidence mismatch")
    if any(bool(payload.get(key)) for key in (
        "network_enabled",
        "acquisition_enabled",
        "extraction_enabled",
        "render_enabled",
        "auto_publish",
    )):
        raise AIDirectorPackageExportError("0058H cannot enable operational capabilities")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or blockers != sorted(set(blockers)):
        raise AIDirectorPackageExportError("package blockers must be normalized")
    if payload.get("package_state") == "ready_for_factory" and blockers:
        raise AIDirectorPackageExportError("ready package cannot contain blockers")
    if payload.get("package_state") == "blocked" and not blockers:
        raise AIDirectorPackageExportError("blocked package requires blockers")


def export_review_package(output: Path, **inputs: Mapping[str, object] | None) -> dict[str, object]:
    payload = build_review_package(**inputs)
    validate_review_package(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Export governed AI Director dashboard package")
    parser.add_argument("--director-report", type=Path)
    parser.add_argument("--narrative-alignment", type=Path)
    parser.add_argument("--timing-optimization", type=Path)
    parser.add_argument("--performance-ranking", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--factory-handover", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dashboard/data/ai_director_review_package.json"),
    )
    args = parser.parse_args()
    payload = export_review_package(
        args.output,
        director_report=_load(args.director_report),
        narrative_alignment=_load(args.narrative_alignment),
        timing_optimization=_load(args.timing_optimization),
        performance_ranking=_load(args.performance_ranking),
        approval=_load(args.approval),
        factory_handover=_load(args.factory_handover),
    )
    print(payload["package_state"])
    print(payload["package_id"])
    print(payload["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AIDirectorPackageExportError",
    "build_review_package",
    "canonical_sha256",
    "export_review_package",
    "validate_review_package",
]
