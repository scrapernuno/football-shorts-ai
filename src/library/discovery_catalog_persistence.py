"""
FOOTBALL-SHORTS-AI-0054C
DISCOVERY CATALOG PERSISTENCE AND DASHBOARD DATA EXPORT

Deterministic JSON persistence boundary for the 0054A/0054B football library.
Provides fail-closed loading, canonical checksums, atomic local writes and a
stable dashboard export contract. No network, provider acquisition or publishing
operation is performed.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from discovery.external_provider_contract import (
    ExternalVideoAsset,
    ProviderCapabilities,
    canonical_sha256,
)
from library.football_library import FootballLibrary


CATALOG_SCHEMA = "football-shorts-ai.discovery-catalog.v1"
DASHBOARD_SCHEMA = "football-shorts-ai.dashboard-football-library.v1"


class DiscoveryCatalogPersistenceError(ValueError):
    """Raised when persisted discovery evidence is malformed or unsafe."""


@dataclass(frozen=True)
class DiscoveryCatalogSnapshot:
    schema: str
    assets: tuple[ExternalVideoAsset, ...]
    asset_count: int
    catalog_sha256: str
    auto_acquire: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != CATALOG_SCHEMA:
            raise DiscoveryCatalogPersistenceError("unsupported catalog schema")
        if self.asset_count != len(self.assets):
            raise DiscoveryCatalogPersistenceError("asset_count does not match assets")
        if len({asset.asset_id for asset in self.assets}) != len(self.assets):
            raise DiscoveryCatalogPersistenceError("duplicate asset_id in catalog")
        for asset in self.assets:
            asset.validate()
        expected = canonical_sha256(
            {
                "schema": self.schema,
                "assets": [asset.to_dict() for asset in self.assets],
                "asset_count": self.asset_count,
                "auto_acquire": False,
                "auto_publish": False,
            }
        )
        if self.catalog_sha256 != expected:
            raise DiscoveryCatalogPersistenceError("catalog checksum mismatch")
        if self.auto_acquire or self.auto_publish:
            raise DiscoveryCatalogPersistenceError(
                "automatic acquisition and publishing must remain disabled"
            )

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "assets": [asset.to_dict() for asset in self.assets],
            "asset_count": self.asset_count,
            "catalog_sha256": self.catalog_sha256,
            "auto_acquire": False,
            "auto_publish": False,
        }


def snapshot_library(library: FootballLibrary) -> DiscoveryCatalogSnapshot:
    assets = tuple(library.assets())
    unsigned = {
        "schema": CATALOG_SCHEMA,
        "assets": [asset.to_dict() for asset in assets],
        "asset_count": len(assets),
        "auto_acquire": False,
        "auto_publish": False,
    }
    result = DiscoveryCatalogSnapshot(
        schema=CATALOG_SCHEMA,
        assets=assets,
        asset_count=len(assets),
        catalog_sha256=canonical_sha256(unsigned),
        auto_acquire=False,
        auto_publish=False,
    )
    result.validate()
    return result


def dump_catalog(path: str | Path, library: FootballLibrary) -> DiscoveryCatalogSnapshot:
    """Atomically persist one canonical catalog JSON file."""

    destination = Path(path)
    if destination.suffix.lower() != ".json":
        raise DiscoveryCatalogPersistenceError("catalog path must end with .json")
    snapshot = snapshot_library(library)
    _atomic_write_json(destination, snapshot.to_dict())
    return snapshot


def load_catalog(path: str | Path) -> FootballLibrary:
    source = Path(path)
    if not source.is_file():
        raise DiscoveryCatalogPersistenceError("catalog file does not exist")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiscoveryCatalogPersistenceError("catalog JSON cannot be loaded") from exc
    snapshot = _snapshot_from_mapping(payload)
    snapshot.validate()
    return FootballLibrary(snapshot.assets)


def export_dashboard_data(
    path: str | Path,
    library: FootballLibrary,
) -> dict[str, object]:
    """Write dashboard/data/football_library.json compatible evidence."""

    destination = Path(path)
    if destination.name != "football_library.json":
        raise DiscoveryCatalogPersistenceError(
            "dashboard export must be named football_library.json"
        )
    library_payload = library.to_dashboard_dict()
    payload: dict[str, object] = {
        "schema": DASHBOARD_SCHEMA,
        "library": library_payload,
        "asset_count": len(library),
        "source_catalog_sha256": snapshot_library(library).catalog_sha256,
        "auto_acquire": False,
        "auto_publish": False,
    }
    payload["evidence_sha256"] = canonical_sha256(payload)
    _atomic_write_json(destination, payload)
    return payload


def _snapshot_from_mapping(payload: object) -> DiscoveryCatalogSnapshot:
    if not isinstance(payload, Mapping):
        raise DiscoveryCatalogPersistenceError("catalog root must be an object")
    assets_payload = payload.get("assets")
    if not isinstance(assets_payload, list):
        raise DiscoveryCatalogPersistenceError("catalog assets must be an array")
    assets = tuple(_asset_from_mapping(item) for item in assets_payload)
    result = DiscoveryCatalogSnapshot(
        schema=_required_text(payload, "schema"),
        assets=assets,
        asset_count=_required_int(payload, "asset_count"),
        catalog_sha256=_required_text(payload, "catalog_sha256"),
        auto_acquire=_required_bool(payload, "auto_acquire"),
        auto_publish=_required_bool(payload, "auto_publish"),
    )
    return result


def _asset_from_mapping(payload: object) -> ExternalVideoAsset:
    if not isinstance(payload, Mapping):
        raise DiscoveryCatalogPersistenceError("asset entry must be an object")
    capabilities_payload = payload.get("capabilities")
    if not isinstance(capabilities_payload, Mapping):
        raise DiscoveryCatalogPersistenceError("asset capabilities must be an object")
    capabilities = ProviderCapabilities(
        supports_embed=_required_bool(capabilities_payload, "supports_embed"),
        supports_thumbnail=_required_bool(capabilities_payload, "supports_thumbnail"),
        supports_metadata=_required_bool(capabilities_payload, "supports_metadata"),
        supports_preview=_required_bool(capabilities_payload, "supports_preview"),
        supports_manual_import=_required_bool(
            capabilities_payload, "supports_manual_import"
        ),
        supports_direct_acquisition=_required_bool(
            capabilities_payload, "supports_direct_acquisition"
        ),
    )
    asset = ExternalVideoAsset(
        schema=_required_text(payload, "schema"),
        asset_id=_required_text(payload, "asset_id"),
        provider=_required_text(payload, "provider"),
        provider_asset_id=_required_text(payload, "provider_asset_id"),
        provider_url=_required_text(payload, "provider_url"),
        embed_url=_optional_text(payload, "embed_url"),
        title=_required_text(payload, "title"),
        description=str(payload.get("description", "")),
        thumbnail_url=_optional_text(payload, "thumbnail_url"),
        duration_seconds=_optional_number(payload, "duration_seconds"),
        published_at=_optional_text(payload, "published_at"),
        channel_name=_required_text(payload, "channel_name"),
        channel_id=_optional_text(payload, "channel_id"),
        views=_optional_int(payload, "views"),
        likes=_optional_int(payload, "likes"),
        language=_optional_text(payload, "language"),
        competition=_optional_text(payload, "competition"),
        teams=_text_tuple(payload, "teams"),
        players=_text_tuple(payload, "players"),
        tags=_text_tuple(payload, "tags"),
        score=float(payload.get("score", 0)),
        rights_status=_required_text(payload, "rights_status"),
        library_state=_required_text(payload, "library_state"),
        capabilities=capabilities,
        discovered_at=_required_text(payload, "discovered_at"),
        source_metadata_sha256=_required_text(payload, "source_metadata_sha256"),
        render_allowed=_required_bool(payload, "render_allowed"),
        acquisition_allowed=_required_bool(payload, "acquisition_allowed"),
        preview_allowed=_required_bool(payload, "preview_allowed"),
        auto_acquire=_required_bool(payload, "auto_acquire"),
        auto_publish=_required_bool(payload, "auto_publish"),
    )
    asset.validate()
    return asset


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _required_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DiscoveryCatalogPersistenceError(f"{key} must be non-empty text")
    return value


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DiscoveryCatalogPersistenceError(f"{key} must be text or null")
    return value


def _required_bool(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise DiscoveryCatalogPersistenceError(f"{key} must be boolean")
    return value


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise DiscoveryCatalogPersistenceError(f"{key} must be integer")
    return value


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise DiscoveryCatalogPersistenceError(f"{key} must be integer or null")
    return value


def _optional_number(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise DiscoveryCatalogPersistenceError(f"{key} must be numeric or null")
    return float(value)


def _text_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise DiscoveryCatalogPersistenceError(f"{key} must be an array of text")
    return tuple(value)


__all__ = [
    "CATALOG_SCHEMA",
    "DASHBOARD_SCHEMA",
    "DiscoveryCatalogPersistenceError",
    "DiscoveryCatalogSnapshot",
    "dump_catalog",
    "export_dashboard_data",
    "load_catalog",
    "snapshot_library",
]
