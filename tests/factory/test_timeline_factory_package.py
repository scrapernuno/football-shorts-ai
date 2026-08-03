from __future__ import annotations

import dataclasses

import pytest

from discovery.external_provider_contract import ProviderCapabilities, build_external_video_asset
from factory.timeline_factory_package import (
    TimelineFactoryPackageError,
    build_timeline_factory_package,
    canonical_sha256,
)
from studio.governed_clip_selection import build_governed_clip_selection
from studio.story_timeline_enrichment import build_story_timeline_enrichment
from studio.timeline_composition import build_timeline_composition


DISCOVERED_AT = "2026-08-03T10:40:00Z"


def _selection(provider_id: str, *, rights: str = "owned"):
    capabilities = ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=rights != "reference_only",
    )
    asset = build_external_video_asset(
        provider="local_library" if rights == "owned" else "youtube",
        provider_asset_id=provider_id,
        provider_url=f"https://example.test/{provider_id}",
        embed_url=f"https://example.test/embed/{provider_id}",
        thumbnail_url=f"https://example.test/{provider_id}.jpg",
        title=f"Football source {provider_id}",
        channel_name="Football Shorts AI",
        capabilities=capabilities,
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": provider_id},
        duration_seconds=30,
        rights_status=rights,
    )
    return build_governed_clip_selection(
        asset=asset,
        start_seconds=2,
        end_seconds=7,
        editorial_intent="production_source" if rights == "owned" else "reference",
    )


def _story():
    return {
        "script": {
            "hook": "Tudo mudou neste instante.",
            "development": "O espaço apareceu e a jogada acelerou.",
            "climax": "O remate decidiu o jogo.",
            "call_to_action": "Teria feito o mesmo?",
        }
    }


def _ready_evidence():
    timeline = build_timeline_composition(
        title="Momento decisivo",
        selections=(_selection("one"), _selection("two")),
        transitions=("cut", "fade"),
        timeline_state="ready_for_factory",
        fps=30,
    )
    enrichment = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        language="pt-PT",
        music_mood="cinematic tension",
        requested_state="ready_for_factory",
    )
    return timeline, enrichment


def test_builds_ready_vertical_factory_package() -> None:
    timeline, enrichment = _ready_evidence()
    package = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)

    assert package.package_state == "ready_for_factory"
    assert package.blockers == ()
    assert package.timeline_id == timeline.timeline_id
    assert package.enrichment_id == enrichment.enrichment_id
    assert package.aspect_ratio == "9:16"
    assert package.resolution == "1080x1920"
    assert package.total_duration_seconds == 10
    assert len(package.scenes) == 2
    assert [scene.scene_order for scene in package.scenes] == [1, 2]
    assert all(scene.render_allowed for scene in package.scenes)


def test_scene_contract_preserves_source_timestamps_and_transitions() -> None:
    timeline, enrichment = _ready_evidence()
    package = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)

    assert package.scenes[0].source_start_seconds == 2
    assert package.scenes[0].source_end_seconds == 7
    assert package.scenes[0].transition == "cut"
    assert package.scenes[1].transition == "fade"
    assert package.scenes[0].narrative_beat == "hook"


def test_blocked_reference_timeline_cannot_become_ready_package() -> None:
    timeline = build_timeline_composition(
        title="Reference timeline",
        selections=(_selection("owned"), _selection("external", rights="reference_only")),
        transitions=("cut", "cut"),
        timeline_state="ready_for_factory",
    )
    enrichment = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        requested_state="ready_for_factory",
    )
    package = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)

    assert package.package_state == "blocked"
    assert "TIMELINE_NOT_READY" in package.blockers
    assert "ENRICHMENT_NOT_READY" in package.blockers
    assert any(item.startswith("CLIP_NOT_RENDERABLE:") for item in package.blockers)
    assert len(package.scenes) == 1


def test_rejects_enrichment_bound_to_another_timeline() -> None:
    timeline, _ = _ready_evidence()
    another = build_timeline_composition(
        title="Another",
        selections=(_selection("three"),),
        timeline_state="ready_for_factory",
    )
    enrichment = build_story_timeline_enrichment(
        timeline=another,
        story=_story(),
        requested_state="ready_for_factory",
    )

    with pytest.raises(Exception, match="timeline identity mismatch|identities differ"):
        build_timeline_factory_package(timeline=timeline, enrichment=enrichment)


def test_identity_and_replay_are_deterministic() -> None:
    timeline, enrichment = _ready_evidence()
    first = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)
    second = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)

    assert first.package_id == second.package_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_execution_rendering_and_publication_remain_disabled() -> None:
    timeline, enrichment = _ready_evidence()
    package = build_timeline_factory_package(timeline=timeline, enrichment=enrichment)
    payload = package.to_dict()

    assert payload["execution_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_render"] is False
    assert payload["auto_publish"] is False

    forged = dataclasses.replace(package, render_enabled=True)
    with pytest.raises(TimelineFactoryPackageError, match="cannot execute"):
        forged.validate()
