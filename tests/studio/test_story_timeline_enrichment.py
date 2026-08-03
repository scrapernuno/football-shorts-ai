from __future__ import annotations

import pytest

from discovery.external_provider_contract import (
    ProviderCapabilities,
    build_external_video_asset,
)
from studio.governed_clip_selection import build_governed_clip_selection
from studio.story_timeline_enrichment import (
    StoryTimelineEnrichmentError,
    build_story_timeline_enrichment,
    canonical_sha256,
)
from studio.timeline_composition import build_timeline_composition


DISCOVERED_AT = "2026-08-03T10:30:00Z"


def _capabilities(*, direct: bool = True) -> ProviderCapabilities:
    return ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=direct,
    )


def _selection(provider_id: str, *, rights: str = "owned"):
    asset = build_external_video_asset(
        provider="local_library" if rights == "owned" else "youtube",
        provider_asset_id=provider_id,
        provider_url=f"https://example.test/{provider_id}",
        embed_url=f"https://example.test/embed/{provider_id}",
        thumbnail_url=f"https://example.test/{provider_id}.jpg",
        title=f"Football clip {provider_id}",
        channel_name="Football Shorts AI",
        capabilities=_capabilities(direct=rights != "reference_only"),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": provider_id},
        duration_seconds=30,
        rights_status=rights,
    )
    return build_governed_clip_selection(
        asset=asset,
        start_seconds=0,
        end_seconds=5,
        editorial_intent="production_source" if rights == "owned" else "reference",
    )


def _timeline(*, reference_only: bool = False):
    selections = (
        _selection("one"),
        _selection("two", rights="reference_only" if reference_only else "owned"),
    )
    return build_timeline_composition(
        title="The decisive football moment",
        selections=selections,
        transitions=("cut", "fade"),
        timeline_state="ready_for_factory",
    )


def _story() -> dict[str, object]:
    return {
        "script": {
            "hook": "This changed the entire match.",
            "introduction": "Everything started with one quick decision.",
            "development": "The defence moved, the space opened and the attack accelerated.",
            "climax": "Then came the decisive finish.",
            "ending": "One moment separated the teams.",
            "call_to_action": "Would you have made the same choice?",
        }
    }


def test_enriches_renderable_timeline_with_story_beats() -> None:
    timeline = _timeline()
    result = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        language="pt-PT",
        music_mood="cinematic tension",
        requested_state="ready_for_factory",
    )

    assert result.enrichment_state == "ready_for_factory"
    assert result.blockers == ()
    assert result.timeline_id == timeline.timeline_id
    assert len(result.beats) == 6
    assert [beat.beat_type for beat in result.beats] == [
        "hook",
        "introduction",
        "development",
        "climax",
        "ending",
        "call_to_action",
    ]
    assert result.beats[0].start_seconds == 0
    assert result.beats[-1].end_seconds == timeline.total_duration_seconds
    assert result.captions_required is True
    assert len(result.narration) == len(result.beats)


def test_nested_script_aliases_are_supported() -> None:
    result = build_story_timeline_enrichment(
        timeline=_timeline(),
        story={
            "script": {
                "top_hook": "Watch the movement.",
                "body": "The gap appears between the defenders.",
                "conclusion": "That movement wins the match.",
                "cta": "Did you spot it?",
            }
        },
    )
    assert [beat.beat_type for beat in result.beats] == [
        "hook",
        "development",
        "ending",
        "call_to_action",
    ]


def test_reference_only_timeline_remains_blocked() -> None:
    timeline = _timeline(reference_only=True)
    assert timeline.timeline_state == "blocked"

    result = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        requested_state="ready_for_factory",
    )

    assert result.enrichment_state == "blocked"
    assert "TIMELINE_BLOCKED" in result.blockers
    assert "NON_RENDERABLE_CLIPS_PRESENT" in result.blockers


def test_rejects_story_without_usable_sections() -> None:
    with pytest.raises(StoryTimelineEnrichmentError, match="no usable sections"):
        build_story_timeline_enrichment(
            timeline=_timeline(),
            story={"unrelated": "value"},
        )


def test_rejects_binding_to_different_timeline() -> None:
    timeline = _timeline()
    result = build_story_timeline_enrichment(timeline=timeline, story=_story())
    another = build_timeline_composition(
        title="Another timeline",
        selections=(_selection("three"),),
        timeline_state="draft",
    )

    with pytest.raises(StoryTimelineEnrichmentError, match="timeline identity mismatch"):
        result.validate(another)


def test_identity_and_replay_are_deterministic() -> None:
    timeline = _timeline()
    first = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        language="pt-PT",
        music_mood="cinematic tension",
    )
    second = build_story_timeline_enrichment(
        timeline=timeline,
        story=_story(),
        language="pt-PT",
        music_mood="cinematic tension",
    )

    assert first.enrichment_id == second.enrichment_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_automatic_execution_and_rendering_remain_disabled() -> None:
    result = build_story_timeline_enrichment(
        timeline=_timeline(),
        story=_story(),
        requested_state="reviewed",
    )
    payload = result.to_dict()
    assert payload["ai_execution_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_render"] is False
    assert payload["auto_publish"] is False
