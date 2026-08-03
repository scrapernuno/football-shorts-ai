"""
FOOTBALL-SHORTS-AI-0055C
CONTROLLED YOUTUBE DISCOVERY EXECUTION AND DASHBOARD SYNCHRONIZATION

Composes the governed 0055A discovery provider with the 0055B HTTP client and
secret resolver. Execution is disabled by default and remains metadata-only.
No video download, media acquisition, rendering or publishing is performed.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from discovery.activate_youtube_dashboard_library import (
    YouTubeDashboardActivationReport,
    activate_youtube_dashboard_library,
)
from discovery.environment_secret_resolver import (
    EnvironmentSecretPolicy,
    EnvironmentSecretResolver,
)
from discovery.youtube_data_api_http_client import (
    YouTubeDataApiHttpClient,
    YouTubeDataApiHttpError,
    YouTubeDataApiHttpPolicy,
)
from discovery.youtube_discovery_provider import (
    YouTubeDiscoveryPolicy,
    YouTubeDiscoveryProvider,
)


class YouTubeDiscoverySyncError(RuntimeError):
    """Raised when the controlled synchronization contract is invalid."""


@dataclass(frozen=True)
class YouTubeDiscoverySyncPolicy:
    enabled: bool = False
    network_enabled: bool = False
    secret_resolution_enabled: bool = False
    dashboard_write_enabled: bool = False
    max_results: int = 12
    region_code: str = "PT"
    relevance_language: str = "pt"
    video_duration: str = "short"
    safe_search: str = "moderate"
    timeout_seconds: float = 10.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    metadata_only: bool = True
    download_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    publishing_enabled: bool = False

    def validate(self) -> None:
        if self.enabled and not (
            self.network_enabled
            and self.secret_resolution_enabled
            and self.dashboard_write_enabled
        ):
            raise YouTubeDiscoverySyncError(
                "enabled synchronization requires network, secret resolution and dashboard write"
            )
        if not self.metadata_only:
            raise YouTubeDiscoverySyncError("synchronization must remain metadata-only")
        if any(
            (
                self.download_enabled,
                self.acquisition_enabled,
                self.render_enabled,
                self.publishing_enabled,
            )
        ):
            raise YouTubeDiscoverySyncError("media execution capabilities are forbidden")


@dataclass(frozen=True)
class YouTubeDiscoverySyncReport:
    schema: str
    status: str
    query: str
    discovered_count: int
    library_asset_count: int
    dashboard_path: str
    blockers: tuple[str, ...]
    network_used: bool
    dashboard_written: bool
    evidence_sha256: str
    metadata_only: bool = True
    download_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    publishing_enabled: bool = False

    def validate(self) -> None:
        import hashlib

        if self.schema != "football-shorts-ai.youtube-discovery-sync.v1":
            raise YouTubeDiscoverySyncError("unsupported synchronization schema")
        if self.status not in {"SYNCHRONIZED", "NOT_ACTIVATED", "BLOCKED"}:
            raise YouTubeDiscoverySyncError("unsupported synchronization status")
        if self.status == "SYNCHRONIZED":
            if self.blockers or not self.dashboard_written:
                raise YouTubeDiscoverySyncError("synchronized report is inconsistent")
        elif not self.blockers or self.dashboard_written:
            raise YouTubeDiscoverySyncError("non-success synchronization report is inconsistent")
        if self.discovered_count < 0 or self.library_asset_count < 0:
            raise YouTubeDiscoverySyncError("synchronization counts cannot be negative")
        if not self.metadata_only or any(
            (
                self.download_enabled,
                self.acquisition_enabled,
                self.render_enabled,
                self.publishing_enabled,
            )
        ):
            raise YouTubeDiscoverySyncError("unsafe media capability detected")
        if len(self.evidence_sha256) != 64:
            raise YouTubeDiscoverySyncError("evidence must be SHA-256")
        try:
            int(self.evidence_sha256, 16)
        except ValueError as exc:
            raise YouTubeDiscoverySyncError("evidence must be hexadecimal") from exc
        expected = hashlib.sha256(
            json.dumps(self._unsigned(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        if expected != self.evidence_sha256:
            raise YouTubeDiscoverySyncError("synchronization evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": self.status,
            "query": self.query,
            "discovered_count": self.discovered_count,
            "library_asset_count": self.library_asset_count,
            "dashboard_path": self.dashboard_path,
            "blockers": list(self.blockers),
            "network_used": self.network_used,
            "dashboard_written": self.dashboard_written,
            "metadata_only": True,
            "download_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "publishing_enabled": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def execute_youtube_discovery_sync(
    *,
    query: str,
    dashboard_path: str | Path,
    report_path: str | Path,
    policy: YouTubeDiscoverySyncPolicy,
    catalog_path: str | Path | None = None,
    discovered_at: str | None = None,
    environment: Mapping[str, str] | None = None,
    open_url: Callable[..., object] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> YouTubeDiscoverySyncReport:
    """Run one explicitly activated metadata discovery and dashboard synchronization."""

    import hashlib

    policy.validate()
    normalized_query = query.strip()
    if not normalized_query:
        raise YouTubeDiscoverySyncError("query is required")
    destination = Path(dashboard_path)
    report_destination = Path(report_path)

    if not policy.enabled:
        return _write_report(
            report_destination,
            _report(
                status="NOT_ACTIVATED",
                query=normalized_query,
                discovered_count=0,
                library_asset_count=0,
                dashboard_path=str(destination),
                blockers=("YOUTUBE_DISCOVERY_SYNC_NOT_ACTIVATED",),
                network_used=False,
                dashboard_written=False,
            ),
        )

    try:
        resolver = EnvironmentSecretResolver(
            policy=EnvironmentSecretPolicy(enabled=True),
            environment=environment,
        )
        client_kwargs: dict[str, object] = {
            "secret_resolver": resolver,
            "policy": YouTubeDataApiHttpPolicy(
                enabled=True,
                network_enabled=True,
                secret_resolution_enabled=True,
                timeout_seconds=policy.timeout_seconds,
                max_attempts=policy.max_attempts,
                retry_backoff_seconds=policy.retry_backoff_seconds,
            ),
        }
        if open_url is not None:
            client_kwargs["open_url"] = open_url
        if sleep is not None:
            client_kwargs["sleep"] = sleep
        client = YouTubeDataApiHttpClient(**client_kwargs)  # type: ignore[arg-type]
        provider = YouTubeDiscoveryProvider(
            client=client,
            policy=YouTubeDiscoveryPolicy(
                enabled=True,
                network_enabled=True,
                max_results=policy.max_results,
                region_code=policy.region_code,
                relevance_language=policy.relevance_language,
                video_duration=policy.video_duration,
                safe_search=policy.safe_search,
            ),
        )
        activation = activate_youtube_dashboard_library(
            provider=provider,
            query=normalized_query,
            dashboard_path=destination,
            catalog_path=catalog_path,
            discovered_at=discovered_at,
        )
    except (YouTubeDataApiHttpError, ValueError, OSError) as exc:
        return _write_report(
            report_destination,
            _report(
                status="BLOCKED",
                query=normalized_query,
                discovered_count=0,
                library_asset_count=0,
                dashboard_path=str(destination),
                blockers=(f"CONTROLLED_EXECUTION_FAILED:{type(exc).__name__}",),
                network_used=True,
                dashboard_written=False,
            ),
        )

    status = "SYNCHRONIZED" if activation.status == "ACTIVATED" else activation.status
    return _write_report(
        report_destination,
        _from_activation(activation, status=status),
    )


def _from_activation(
    activation: YouTubeDashboardActivationReport,
    *,
    status: str,
) -> YouTubeDiscoverySyncReport:
    return _report(
        status=status,
        query=activation.query,
        discovered_count=activation.discovered_count,
        library_asset_count=activation.library_asset_count,
        dashboard_path=activation.dashboard_path,
        blockers=activation.blockers,
        network_used=activation.network_used,
        dashboard_written=status == "SYNCHRONIZED",
    )


def _report(**values: object) -> YouTubeDiscoverySyncReport:
    import hashlib

    unsigned = {
        "schema": "football-shorts-ai.youtube-discovery-sync.v1",
        **values,
        "metadata_only": True,
        "download_enabled": False,
        "acquisition_enabled": False,
        "render_enabled": False,
        "publishing_enabled": False,
    }
    evidence = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    result = YouTubeDiscoverySyncReport(
        evidence_sha256=evidence,
        **unsigned,  # type: ignore[arg-type]
    )
    result.validate()
    return result


def _write_report(path: Path, report: YouTubeDiscoverySyncReport) -> YouTubeDiscoverySyncReport:
    payload = json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return report


__all__ = [
    "YouTubeDiscoverySyncError",
    "YouTubeDiscoverySyncPolicy",
    "YouTubeDiscoverySyncReport",
    "execute_youtube_discovery_sync",
]
