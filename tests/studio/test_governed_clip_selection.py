from __future__ import annotations

import pytest

from discovery.external_provider_contract import ProviderCapabilities, build_external_video_asset
from studio.governed_clip_selection import (
    GovernedClipSelectionError,
    build_governed_clip_selection,
)


DISCOVERED_AT = "2026-08-03T10:30:00Z"


def _asset(*, rights: str = "reference_only", duration: float = 40.0):
    capabilities = ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=rights != "reference_only",
    )
    return build_external_video_asset(
        provider="youtube" if rights == "reference_only" else "local_library",
        provider_asset_id="asset-1",
        provider_url="https://example.test/watch/asset-1",
        embed_url="https://example.test/embed/asset-1",
        title="Football moment",
        channel_name="Football Channel",
        capabilities=capabilities,
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": "asset-1", "rights": rights},
        duration_seconds=duration,
        rights_status=rights,
    )


def test_reference_clip_is_preview_only_and_not_renderable() -> None:
    clip = build_governed_clip_selection(
        asset=_asset(),
        start_seconds=10,
        end_seconds=15,
        editorial_intent="analysis",
    )
    assert clip.preview_allowed is True
    assert clip.render_allowed is False
    assert clip.acquisition_allowed is False
    assert clip.auto_acquire is False
    assert clip.auto_render is False
    assert clip.auto_publish is False


def test_owned_clip_can_be_production_source() -> None:
    clip = build_governed_clip_selection(
        asset=_asset(rights="owned"),
        start_seconds=2.5,
        end_seconds=9.0,
        editorial_intent="production_source",
        clip_state="approved_for_project",
    )
    assert clip.render_allowed is True
    assert clip.acquisition_allowed is True
    assert clip.clip_state == "approved_for_project"


def test_rejects_reference_clip_as_production_source() -> None:
    with pytest.raises(GovernedClipSelectionError, match="production source"):
        build_governed_clip_selection(
            asset=_asset(),
            start_seconds=0,
            end_seconds=5,
            editorial_intent="production_source",
        )


def test_rejects_clip_longer_than_governed_maximum() -> None:
    with pytest.raises(GovernedClipSelectionError, match="outside governed limits"):
        build_governed_clip_selection(
            asset=_asset(),
            start_seconds=0,
            end_seconds=16,
        )


def test_rejects_end_beyond_source_duration() -> None:
    with pytest.raises(GovernedClipSelectionError, match="exceeds source duration"):
        build_governed_clip_selection(
            asset=_asset(duration=8),
            start_seconds=5,
            end_seconds=9,
        )


def test_clip_identity_is_deterministic() -> None:
    first = build_governed_clip_selection(
        asset=_asset(rights="owned"),
        start_seconds=1.2,
        end_seconds=7.4,
        editorial_intent="commentary",
        note="Goal analysis",
    )
    second = build_governed_clip_selection(
        asset=_asset(rights="owned"),
        start_seconds=1.2,
        end_seconds=7.4,
        editorial_intent="commentary",
        note="Goal analysis",
    )
    assert first.clip_id == second.clip_id
    assert first.to_dict() == second.to_dict()
