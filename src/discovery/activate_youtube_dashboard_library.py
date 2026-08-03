"""
FOOTBALL-SHORTS-AI-0055A
YOUTUBE DASHBOARD LIBRARY ACTIVATION BOUNDARY

Merges metadata-only YouTube discovery results into the governed Football Library
and atomically exports dashboard/data/football_library.json. A concrete API client,
network permission and secret resolution must be supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from discovery.youtube_discovery_provider import YouTubeDiscoveryProvider
from library.discovery_catalog_persistence import export_dashboard_data, load_catalog
from library.football_library import FootballLibrary


class YouTubeDashboardActivationError(ValueError):
    pass


@dataclass(frozen=True)
class YouTubeDashboardActivationReport:
    status: str
    query: str
    discovered_count: int
    library_asset_count: int
    dashboard_path: str
    blockers: tuple[str, ...]
    network_used: bool
    acquisition_enabled: bool = False
    download_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.status not in {"ACTIVATED", "NOT_ACTIVATED", "BLOCKED"}:
            raise YouTubeDashboardActivationError("unsupported activation status")
        if self.status == "ACTIVATED" and self.blockers:
            raise YouTubeDashboardActivationError("activated report cannot contain blockers")
        if self.status != "ACTIVATED" and not self.blockers:
            raise YouTubeDashboardActivationError("non-activated report requires blockers")
        if self.discovered_count < 0 or self.library_asset_count < 0:
            raise YouTubeDashboardActivationError("counts cannot be negative")
        if self.acquisition_enabled or self.download_enabled or self.auto_publish:
            raise YouTubeDashboardActivationError("automatic media actions are forbidden")


def activate_youtube_dashboard_library(
    *,
    provider: YouTubeDiscoveryProvider,
    query: str,
    dashboard_path: str | Path,
    catalog_path: str | Path | None = None,
    discovered_at: str | None = None,
) -> YouTubeDashboardActivationReport:
    """Discover YouTube metadata and export the merged governed dashboard library."""

    discovery = provider.discover(query, discovered_at=discovered_at)
    destination = Path(dashboard_path)
    if destination.name != "football_library.json":
        raise YouTubeDashboardActivationError(
            "dashboard_path must end with football_library.json"
        )

    if discovery.status != "DISCOVERED":
        report = YouTubeDashboardActivationReport(
            status=discovery.status,
            query=discovery.query,
            discovered_count=0,
            library_asset_count=0,
            dashboard_path=str(destination),
            blockers=discovery.blockers,
            network_used=discovery.network_used,
        )
        report.validate()
        return report

    library = _load_existing_library(catalog_path)
    for asset in discovery.assets:
        library.index(asset)
    export_dashboard_data(destination, library)

    report = YouTubeDashboardActivationReport(
        status="ACTIVATED",
        query=discovery.query,
        discovered_count=len(discovery.assets),
        library_asset_count=len(library),
        dashboard_path=str(destination),
        blockers=(),
        network_used=discovery.network_used,
    )
    report.validate()
    return report


def _load_existing_library(catalog_path: str | Path | None) -> FootballLibrary:
    if catalog_path is None:
        return FootballLibrary()
    source = Path(catalog_path)
    if not source.exists():
        return FootballLibrary()
    return load_catalog(source)


__all__ = [
    "YouTubeDashboardActivationError",
    "YouTubeDashboardActivationReport",
    "activate_youtube_dashboard_library",
]
