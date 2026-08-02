"""
FOOTBALL-SHORTS-AI-0052F
FACTORY PRODUCTION CERTIFICATION

Final deterministic certification for Factory v1. The certification validates
that the governed batch factory, dashboard video library and publishing
readiness authorities are present and mutually consistent. It never renders,
uploads, schedules or publishes content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from publishing.factory_publishing_readiness import (
    PublishingReadinessDecision,
    evaluate_library,
    load_json,
)


class FactoryProductionCertificationError(ValueError):
    """Raised when Factory v1 cannot be certified safely."""


@dataclass(frozen=True)
class FactoryProductionCertification:
    schema: str
    factory_version: str
    status: str
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    video_count: int
    ready_for_publish_count: int
    evidence_sha256: str
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.factory-certification.v1":
            raise FactoryProductionCertificationError("unsupported certification schema")
        if self.factory_version != "1.0":
            raise FactoryProductionCertificationError("unsupported factory version")
        if self.status not in {"CERTIFIED", "BLOCKED"}:
            raise FactoryProductionCertificationError("unsupported certification status")
        if self.auto_publish:
            raise FactoryProductionCertificationError("automatic publishing must remain disabled")
        if self.video_count < 0 or self.ready_for_publish_count < 0:
            raise FactoryProductionCertificationError("invalid certification counters")
        if self.ready_for_publish_count > self.video_count:
            raise FactoryProductionCertificationError("ready count exceeds video count")
        if set(self.checks.values()) - {True, False}:
            raise FactoryProductionCertificationError("certification checks must be boolean")
        if self.status == "CERTIFIED" and self.blockers:
            raise FactoryProductionCertificationError("certified result cannot contain blockers")
        if self.status == "BLOCKED" and not self.blockers:
            raise FactoryProductionCertificationError("blocked result requires blockers")
        if len(self.evidence_sha256) != 64:
            raise FactoryProductionCertificationError("invalid evidence checksum")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "factory_version": self.factory_version,
            "status": self.status,
            "checks": dict(self.checks),
            "blockers": list(self.blockers),
            "video_count": self.video_count,
            "ready_for_publish_count": self.ready_for_publish_count,
            "evidence_sha256": self.evidence_sha256,
            "auto_publish": False,
        }


def certify_factory_production(
    *,
    project_root: Path,
    video_library: Mapping[str, Any],
    publishing_package: Mapping[str, Any],
) -> FactoryProductionCertification:
    """Certify Factory v1 using only persisted governed evidence."""

    root = project_root.resolve()
    dashboard_root = root / "dashboard"

    required_sources = (
        "src/factory/batch_video_generation_contract.py",
        "src/factory/batch_production_planner.py",
        "src/factory/parallel_render_queue.py",
        "src/dashboard/batch_dashboard_management.py",
        "src/factory/real_batch_factory_activation.py",
        "src/factory/governed_batch_render_executor.py",
        "src/factory/certify_batch_render_execution.py",
        "src/publishing/factory_publishing_readiness.py",
    )
    required_dashboard = (
        "dashboard/index.html",
        "dashboard/videos.html",
        "dashboard/assets/dashboard.js",
        "dashboard/assets/video-library.js",
        "dashboard/data/video_library.json",
    )

    decisions = evaluate_library(
        video_library,
        publishing_package,
        dashboard_root=dashboard_root,
    )
    ready = tuple(item for item in decisions if item.status == "ready_for_publish")

    checks: dict[str, bool] = {
        "factory_sources_present": all((root / path).is_file() for path in required_sources),
        "dashboard_assets_present": all((root / path).is_file() for path in required_dashboard),
        "video_library_non_empty": bool(decisions),
        "all_videos_ready_for_publish": bool(decisions) and len(ready) == len(decisions),
        "publishing_readiness_auto_publish_disabled": all(not item.auto_publish for item in decisions),
        "dashboard_video_library_linked": _contains_text(
            root / "dashboard/index.html",
            'id="video-library"',
        ) and _contains_text(root / "dashboard/index.html", "videos.html"),
        "html5_player_present": _contains_text(
            root / "dashboard/videos.html",
            'id="video-player"',
        ),
        "video_library_runtime_present": _contains_text(
            root / "dashboard/assets/video-library.js",
            "data/video_library.json",
        ),
        "auto_publish_disabled": True,
    }

    evidence = {
        "checks": checks,
        "decisions": [item.to_dict() for item in decisions],
        "required_sources": list(required_sources),
        "required_dashboard": list(required_dashboard),
        "auto_publish": False,
    }
    evidence_sha256 = _canonical_sha256(evidence)
    blockers = tuple(name.upper() for name, passed in checks.items() if not passed)

    result = FactoryProductionCertification(
        schema="football-shorts-ai.factory-certification.v1",
        factory_version="1.0",
        status="CERTIFIED" if not blockers else "BLOCKED",
        checks=checks,
        blockers=blockers,
        video_count=len(decisions),
        ready_for_publish_count=len(ready),
        evidence_sha256=evidence_sha256,
        auto_publish=False,
    )
    result.validate()
    return result


def _contains_text(path: Path, text: str) -> bool:
    return path.is_file() and text in path.read_text(encoding="utf-8")


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    library = load_json(root / "dashboard/data/video_library.json")
    package = load_json(root / "output/publishing_package.json")
    result = certify_factory_production(
        project_root=root,
        video_library=library,
        publishing_package=package,
    )

    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0052F")
    print("FACTORY PRODUCTION CERTIFICATION")
    print("=" * 72)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    print("AUTO_PUBLISH=DISABLED")
    return 0 if result.status == "CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FactoryProductionCertification",
    "FactoryProductionCertificationError",
    "certify_factory_production",
    "main",
]
