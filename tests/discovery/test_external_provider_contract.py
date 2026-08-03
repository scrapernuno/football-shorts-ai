from __future__ import annotations

import pytest

from discovery.external_provider_contract import (
    ExternalProviderContractError,
    ExternalVideoAsset,
    ProviderCapabilities,
    build_external_video_asset,
    canonical_sha256,
)


DISCOVERED_AT = "2026-08-03T09:30:00Z"


def _youtube_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=False,
    )


def _owned_capabilities() -> ProviderCapabilities:
    return ProviderCapabilities(
        supports_embed=False,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=True,
    )


def test_youtube_reference_asset_is_previewable_but_not_renderable() -> None:
    asset = build_external_video_asset(
        provider="youtube",
        provider_asset_id="abc123",
        provider_url="https://www.youtube.com/watch?v=abc123",
        embed_url="https://www.youtube.com/embed/abc123",
        thumbnail_url="https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        title="Football highlight",
        description="External reference video",
        channel_name="Football Channel",
        channel_id="UC123",
        capabilities=_youtube_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "abc123", "provider": "youtube"},
        duration_seconds=35.5,
        views=1_000_000,
        likes=50_000,
        language="en",
        competition="Champions League",
        teams=("Real Madrid", "Barcelona"),
        players=("Player A",),
        tags=("goal", "football"),
        score=98,
        rights_status="reference_only",
    )

    assert asset.preview_allowed is True
    assert asset.render_allowed is False
    assert asset.acquisition_allowed is False
    assert asset.auto_acquire is False
    assert asset.auto_publish is False
    assert asset.library_state == "discovered"


def test_owned_local_asset_is_renderable_and_acquirable() -> None:
    asset = build_external_video_asset(
        provider="local_library",
        provider_asset_id="VID-OWN-001",
        provider_url="https://library.example.test/videos/VID-OWN-001",
        thumbnail_url="https://library.example.test/thumbs/VID-OWN-001.jpg",
        title="Owned match footage",
        channel_name="Football Shorts AI",
        capabilities=_owned_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "VID-OWN-001", "ownership": "owned"},
        rights_status="owned",
        score=80,
    )

    assert asset.render_allowed is True
    assert asset.acquisition_allowed is True
    assert asset.preview_allowed is True


def test_asset_identity_and_serialization_are_deterministic() -> None:
    kwargs = dict(
        provider="tiktok",
        provider_asset_id="998877",
        provider_url="https://www.tiktok.com/@football/video/998877",
        embed_url="https://www.tiktok.com/player/v1/998877",
        thumbnail_url="https://cdn.example.test/998877.jpg",
        title="Short football reference",
        channel_name="Football Creator",
        capabilities=_youtube_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata={"provider": "tiktok", "id": "998877"},
        tags=("football", "short"),
        score=91,
    )

    first = build_external_video_asset(**kwargs)
    second = build_external_video_asset(**kwargs)

    assert first.asset_id == second.asset_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_rejects_invalid_provider_url() -> None:
    with pytest.raises(ExternalProviderContractError, match="absolute HTTP URL"):
        build_external_video_asset(
            provider="youtube",
            provider_asset_id="abc123",
            provider_url="javascript:alert(1)",
            title="Invalid URL",
            channel_name="Channel",
            capabilities=_youtube_capabilities(),
            discovered_at=DISCOVERED_AT,
            source_metadata={"id": "abc123"},
        )


def test_reference_only_asset_cannot_claim_acquisition_permission() -> None:
    valid = build_external_video_asset(
        provider="youtube",
        provider_asset_id="abc123",
        provider_url="https://www.youtube.com/watch?v=abc123",
        title="Reference",
        channel_name="Channel",
        capabilities=_youtube_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "abc123"},
    )
    payload = valid.to_dict()

    forged = ExternalVideoAsset(
        schema=str(payload["schema"]),
        asset_id=str(payload["asset_id"]),
        provider=str(payload["provider"]),
        provider_asset_id=str(payload["provider_asset_id"]),
        provider_url=str(payload["provider_url"]),
        embed_url=None,
        title=str(payload["title"]),
        description=str(payload["description"]),
        thumbnail_url=None,
        duration_seconds=None,
        published_at=None,
        channel_name=str(payload["channel_name"]),
        channel_id=None,
        views=None,
        likes=None,
        language=None,
        competition=None,
        teams=(),
        players=(),
        tags=(),
        score=0,
        rights_status="reference_only",
        library_state="discovered",
        capabilities=_youtube_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata_sha256=str(payload["source_metadata_sha256"]),
        render_allowed=False,
        acquisition_allowed=True,
        preview_allowed=True,
        auto_acquire=False,
        auto_publish=False,
    )

    with pytest.raises(ExternalProviderContractError, match="cannot be acquired"):
        forged.validate()


def test_rejects_automatic_acquisition_and_publication() -> None:
    asset = build_external_video_asset(
        provider="local_library",
        provider_asset_id="owned-1",
        provider_url="https://library.example.test/owned-1",
        title="Owned",
        channel_name="Library",
        capabilities=_owned_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "owned-1"},
        rights_status="owned",
    )
    payload = asset.to_dict()

    forged = ExternalVideoAsset(
        schema=str(payload["schema"]),
        asset_id=str(payload["asset_id"]),
        provider=str(payload["provider"]),
        provider_asset_id=str(payload["provider_asset_id"]),
        provider_url=str(payload["provider_url"]),
        embed_url=None,
        title=str(payload["title"]),
        description="",
        thumbnail_url=None,
        duration_seconds=None,
        published_at=None,
        channel_name="Library",
        channel_id=None,
        views=None,
        likes=None,
        language=None,
        competition=None,
        teams=(),
        players=(),
        tags=(),
        score=0,
        rights_status="owned",
        library_state="discovered",
        capabilities=_owned_capabilities(),
        discovered_at=DISCOVERED_AT,
        source_metadata_sha256=str(payload["source_metadata_sha256"]),
        render_allowed=True,
        acquisition_allowed=True,
        preview_allowed=True,
        auto_acquire=True,
        auto_publish=True,
    )

    with pytest.raises(ExternalProviderContractError, match="automatic acquisition"):
        forged.validate()
