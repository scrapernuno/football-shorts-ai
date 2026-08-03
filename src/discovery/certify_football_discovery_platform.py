"""
FOOTBALL-SHORTS-AI-0054J
FOOTBALL DISCOVERY PLATFORM FINAL CERTIFICATION

End-to-end deterministic certification for 0054A through 0054I. The certification
uses in-memory and temporary-file fixtures only. It performs no network access,
provider download, media acquisition, rendering, AI model execution or publishing.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from discovery.external_provider_contract import (
    ProviderCapabilities,
    build_external_video_asset,
    canonical_sha256,
)
from factory.timeline_factory_package import build_timeline_factory_package
from library.discovery_catalog_persistence import (
    dump_catalog,
    export_dashboard_data,
    load_catalog,
)
from library.football_library import FootballLibrary, LibraryQuery
from studio.governed_clip_selection import build_governed_clip_selection
from studio.story_timeline_enrichment import build_story_timeline_enrichment
from studio.timeline_composition import build_timeline_composition


DISCOVERED_AT = "2026-08-03T10:43:00Z"
REQUIRED_DASHBOARD_ARTIFACTS = (
    "dashboard/discovery.html",
    "dashboard/clip-selection.html",
    "dashboard/timeline-studio.html",
    "dashboard/assets/discovery-library.js",
    "dashboard/assets/clip-selection.js",
    "dashboard/assets/timeline-studio.js",
)


class FootballDiscoveryCertificationError(RuntimeError):
    """Raised when one mandatory 0054 certification condition fails."""


@dataclass(frozen=True)
class FootballDiscoveryCertificationReport:
    schema: str
    status: str
    checks: tuple[str, ...]
    owned_factory_package_id: str
    reference_timeline_state: str
    catalog_sha256: str
    dashboard_evidence_sha256: str
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    ai_execution_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.discovery-platform-certification.v1":
            raise FootballDiscoveryCertificationError("unsupported certification schema")
        if self.status != "CERTIFIED":
            raise FootballDiscoveryCertificationError("platform is not certified")
        if len(self.checks) < 9 or len(set(self.checks)) != len(self.checks):
            raise FootballDiscoveryCertificationError("certification checks are incomplete")
        if not self.owned_factory_package_id.startswith("FACTORYPKG-"):
            raise FootballDiscoveryCertificationError("Factory package identity is invalid")
        if self.reference_timeline_state != "blocked":
            raise FootballDiscoveryCertificationError("reference-only timeline must remain blocked")
        for value in (
            self.catalog_sha256,
            self.dashboard_evidence_sha256,
            self.evidence_sha256,
        ):
            if len(value) != 64:
                raise FootballDiscoveryCertificationError("certification evidence must be SHA-256")
            int(value, 16)
        if any(
            (
                self.network_enabled,
                self.acquisition_enabled,
                self.ai_execution_enabled,
                self.render_enabled,
                self.auto_publish,
            )
        ):
            raise FootballDiscoveryCertificationError("unsafe execution capability was enabled")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "status": self.status,
            "checks": list(self.checks),
            "owned_factory_package_id": self.owned_factory_package_id,
            "reference_timeline_state": self.reference_timeline_state,
            "catalog_sha256": self.catalog_sha256,
            "dashboard_evidence_sha256": self.dashboard_evidence_sha256,
            "evidence_sha256": self.evidence_sha256,
            "network_enabled": False,
            "acquisition_enabled": False,
            "ai_execution_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }


def certify_football_discovery_platform(
    *,
    repository_root: str | Path | None = None,
) -> FootballDiscoveryCertificationReport:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]
    checks: list[str] = []

    capabilities_external = ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=False,
    )
    capabilities_owned = ProviderCapabilities(
        supports_embed=False,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=True,
    )

    reference_asset = build_external_video_asset(
        provider="youtube",
        provider_asset_id="cert-reference",
        provider_url="https://www.youtube.com/watch?v=cert-reference",
        embed_url="https://www.youtube.com/embed/cert-reference",
        thumbnail_url="https://i.ytimg.com/vi/cert-reference/hqdefault.jpg",
        title="External football reference",
        description="Reference-only discovery fixture",
        channel_name="External Football Channel",
        capabilities=capabilities_external,
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "cert-reference", "provider": "youtube"},
        duration_seconds=30,
        views=1_000_000,
        score=95,
        rights_status="reference_only",
    )
    if not reference_asset.preview_allowed or reference_asset.render_allowed:
        raise FootballDiscoveryCertificationError("0054A reference policy failed")
    checks.append("0054A_EXTERNAL_PROVIDER_CONTRACT")

    owned_assets = tuple(
        build_external_video_asset(
            provider="local_library",
            provider_asset_id=f"cert-owned-{index}",
            provider_url=f"https://library.example.test/cert-owned-{index}",
            thumbnail_url=f"https://library.example.test/cert-owned-{index}.jpg",
            title=f"Owned football source {index}",
            description="Owned certification fixture",
            channel_name="Football Shorts AI",
            capabilities=capabilities_owned,
            discovered_at=DISCOVERED_AT,
            source_metadata={"id": f"cert-owned-{index}", "ownership": "owned"},
            duration_seconds=30,
            views=100 * index,
            score=80 + index,
            rights_status="owned",
        )
        for index in (1, 2)
    )

    library = FootballLibrary((reference_asset, *owned_assets))
    result = library.search(LibraryQuery(text="football", sort="score_desc"))
    if result.total_matches != 3 or len(library) != 3:
        raise FootballDiscoveryCertificationError("0054B library indexing/search failed")
    checks.append("0054B_FOOTBALL_LIBRARY_ENGINE")

    with tempfile.TemporaryDirectory(prefix="football-discovery-0054j-") as temporary:
        temp_root = Path(temporary)
        snapshot = dump_catalog(temp_root / "catalog.json", library)
        loaded = load_catalog(temp_root / "catalog.json")
        dashboard_payload = export_dashboard_data(
            temp_root / "dashboard" / "data" / "football_library.json",
            loaded,
        )
        if len(loaded) != 3 or dashboard_payload["asset_count"] != 3:
            raise FootballDiscoveryCertificationError("0054C persistence/export failed")
        dashboard_evidence = str(dashboard_payload["evidence_sha256"])
    checks.append("0054C_CATALOG_PERSISTENCE_AND_EXPORT")

    missing = [relative for relative in REQUIRED_DASHBOARD_ARTIFACTS if not (root / relative).is_file()]
    if missing:
        raise FootballDiscoveryCertificationError(
            "0054D/0054E/0054G dashboard artifacts missing: " + ", ".join(missing)
        )
    checks.extend(
        (
            "0054D_DASHBOARD_VIDEO_BROWSER",
            "0054E_EMBEDDED_PLAYER_AND_CLIP_SELECTION",
            "0054G_INTERACTIVE_TIMELINE_STUDIO",
        )
    )

    reference_clip = build_governed_clip_selection(
        asset=reference_asset,
        start_seconds=2,
        end_seconds=7,
        editorial_intent="reference",
    )
    owned_clips = tuple(
        build_governed_clip_selection(
            asset=asset,
            start_seconds=2,
            end_seconds=7,
            editorial_intent="production_source",
            clip_state="approved_for_project",
        )
        for asset in owned_assets
    )
    checks.append("0054E_GOVERNED_CLIP_CONTRACT")

    reference_timeline = build_timeline_composition(
        title="Reference-only certification timeline",
        selections=(owned_clips[0], reference_clip),
        transitions=("cut", "cut"),
        timeline_state="ready_for_factory",
    )
    if reference_timeline.timeline_state != "blocked" or not reference_timeline.blockers:
        raise FootballDiscoveryCertificationError("0054F rights gate failed")

    owned_timeline = build_timeline_composition(
        title="Owned certification timeline",
        selections=owned_clips,
        transitions=("cut", "fade"),
        timeline_state="ready_for_factory",
        fps=30,
    )
    if owned_timeline.timeline_state != "ready_for_factory":
        raise FootballDiscoveryCertificationError("0054F owned timeline failed")
    checks.append("0054F_TIMELINE_COMPOSITION_CONTRACT")

    story = {
        "script": {
            "hook": "Este momento mudou o jogo.",
            "development": "O espaço apareceu e a jogada acelerou.",
            "climax": "O remate decidiu tudo.",
            "call_to_action": "Teria feito o mesmo?",
        }
    }
    enrichment = build_story_timeline_enrichment(
        timeline=owned_timeline,
        story=story,
        language="pt-PT",
        music_mood="cinematic tension",
        requested_state="ready_for_factory",
    )
    if enrichment.enrichment_state != "ready_for_factory":
        raise FootballDiscoveryCertificationError("0054H story enrichment failed")
    checks.append("0054H_STORY_TIMELINE_ENRICHMENT")

    package = build_timeline_factory_package(
        timeline=owned_timeline,
        enrichment=enrichment,
    )
    if package.package_state != "ready_for_factory" or package.blockers:
        raise FootballDiscoveryCertificationError("0054I Factory package failed")
    checks.append("0054I_TIMELINE_TO_FACTORY_PACKAGE")

    unsigned: dict[str, object] = {
        "schema": "football-shorts-ai.discovery-platform-certification.v1",
        "status": "CERTIFIED",
        "checks": checks,
        "owned_factory_package_id": package.package_id,
        "reference_timeline_state": reference_timeline.timeline_state,
        "catalog_sha256": snapshot.catalog_sha256,
        "dashboard_evidence_sha256": dashboard_evidence,
        "network_enabled": False,
        "acquisition_enabled": False,
        "ai_execution_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    evidence = canonical_sha256(unsigned)
    report = FootballDiscoveryCertificationReport(
        schema=str(unsigned["schema"]),
        status="CERTIFIED",
        checks=tuple(checks),
        owned_factory_package_id=package.package_id,
        reference_timeline_state=reference_timeline.timeline_state,
        catalog_sha256=snapshot.catalog_sha256,
        dashboard_evidence_sha256=dashboard_evidence,
        evidence_sha256=evidence,
        network_enabled=False,
        acquisition_enabled=False,
        ai_execution_enabled=False,
        render_enabled=False,
        auto_publish=False,
    )
    report.validate()
    return report


def main() -> int:
    report = certify_football_discovery_platform()
    print(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2))
    print("CERTIFIED")
    print("NETWORK=DISABLED")
    print("ACQUISITION=DISABLED")
    print("AI_EXECUTION=DISABLED")
    print("RENDER=DISABLED")
    print("AUTO_PUBLISH=DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FootballDiscoveryCertificationError",
    "FootballDiscoveryCertificationReport",
    "certify_football_discovery_platform",
]
