from __future__ import annotations

import json
from pathlib import Path

import pytest

from discovery.external_provider_contract import (
    ProviderCapabilities,
    build_external_video_asset,
    canonical_sha256,
)
from library.discovery_catalog_persistence import (
    DiscoveryCatalogPersistenceError,
    dump_catalog,
    export_dashboard_data,
    load_catalog,
    snapshot_library,
)
from library.football_library import FootballLibrary


DISCOVERED_AT = "2026-08-03T10:30:00Z"


def _capabilities(*, direct: bool = False) -> ProviderCapabilities:
    return ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=direct,
    )


def _asset(provider: str, provider_id: str, *, rights: str = "reference_only"):
    return build_external_video_asset(
        provider=provider,
        provider_asset_id=provider_id,
        provider_url=f"https://example.test/{provider}/{provider_id}",
        embed_url=f"https://example.test/embed/{provider_id}",
        thumbnail_url=f"https://example.test/thumb/{provider_id}.jpg",
        title=f"Football video {provider_id}",
        description="Discovery catalog persistence fixture",
        channel_name="Football Channel",
        capabilities=_capabilities(direct=rights != "reference_only"),
        discovered_at=DISCOVERED_AT,
        source_metadata={"provider": provider, "id": provider_id},
        duration_seconds=20,
        views=1000,
        likes=100,
        tags=("football", "goal"),
        score=90,
        rights_status=rights,
    )


def _library() -> FootballLibrary:
    return FootballLibrary(
        (
            _asset("youtube", "yt-0054c"),
            _asset("local_library", "owned-0054c", rights="owned"),
        )
    )


def test_snapshot_is_deterministic_and_fail_closed() -> None:
    first = snapshot_library(_library())
    second = snapshot_library(_library())
    assert first.to_dict() == second.to_dict()
    assert first.asset_count == 2
    assert first.auto_acquire is False
    assert first.auto_publish is False


def test_catalog_round_trip_preserves_canonical_library(tmp_path: Path) -> None:
    path = tmp_path / "discovery_catalog.json"
    before = _library().to_dashboard_dict()
    snapshot = dump_catalog(path, _library())
    restored = load_catalog(path)
    assert path.is_file()
    assert snapshot.asset_count == 2
    assert restored.to_dashboard_dict() == before


def test_rejects_tampered_catalog_checksum(tmp_path: Path) -> None:
    path = tmp_path / "discovery_catalog.json"
    dump_catalog(path, _library())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["assets"][0]["title"] = "Tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DiscoveryCatalogPersistenceError, match="checksum mismatch"):
        load_catalog(path)


def test_rejects_automatic_acquisition_flag(tmp_path: Path) -> None:
    path = tmp_path / "discovery_catalog.json"
    dump_catalog(path, _library())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["auto_acquire"] = True
    unsigned = {
        "schema": payload["schema"],
        "assets": payload["assets"],
        "asset_count": payload["asset_count"],
        "auto_acquire": False,
        "auto_publish": False,
    }
    payload["catalog_sha256"] = canonical_sha256(unsigned)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        DiscoveryCatalogPersistenceError,
        match="automatic acquisition",
    ):
        load_catalog(path)


def test_dashboard_export_has_expected_name_and_checksum(tmp_path: Path) -> None:
    path = tmp_path / "dashboard" / "data" / "football_library.json"
    payload = export_dashboard_data(path, _library())
    assert path.is_file()
    assert payload["asset_count"] == 2
    assert payload["auto_acquire"] is False
    assert payload["auto_publish"] is False
    unsigned = dict(payload)
    evidence = unsigned.pop("evidence_sha256")
    assert evidence == canonical_sha256(unsigned)


def test_rejects_wrong_dashboard_filename(tmp_path: Path) -> None:
    with pytest.raises(DiscoveryCatalogPersistenceError, match="football_library.json"):
        export_dashboard_data(tmp_path / "wrong.json", _library())


def test_rejects_invalid_json_and_missing_catalog(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(DiscoveryCatalogPersistenceError, match="does not exist"):
        load_catalog(missing)
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(DiscoveryCatalogPersistenceError, match="cannot be loaded"):
        load_catalog(broken)
