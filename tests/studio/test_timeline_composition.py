from __future__ import annotations

import pytest

from discovery.external_provider_contract import ProviderCapabilities, build_external_video_asset
from studio.governed_clip_selection import build_governed_clip_selection
from studio.timeline_composition import (
    TimelineCompositionError,
    TimelineTrack,
    build_timeline_composition,
    canonical_sha256,
)


DISCOVERED_AT = "2026-08-03T10:30:00Z"


def _asset(provider_id: str, *, rights: str):
    renderable = rights != "reference_only"
    return build_external_video_asset(
        provider="local_library" if renderable else "youtube",
        provider_asset_id=provider_id,
        provider_url=f"https://example.test/video/{provider_id}",
        embed_url=f"https://example.test/embed/{provider_id}",
        title=f"Video {provider_id}",
        channel_name="Football Channel",
        capabilities=ProviderCapabilities(
            supports_embed=True,
            supports_thumbnail=True,
            supports_metadata=True,
            supports_preview=True,
            supports_manual_import=True,
            supports_direct_acquisition=renderable,
        ),
        discovered_at=DISCOVERED_AT,
        source_metadata={"id": provider_id},
        duration_seconds=60,
        rights_status=rights,
    )


def _clip(provider_id: str, start: float, end: float, *, rights: str = "owned"):
    return build_governed_clip_selection(
        asset=_asset(provider_id, rights=rights),
        start_seconds=start,
        end_seconds=end,
        editorial_intent="production_source" if rights != "reference_only" else "reference",
        clip_state="approved_for_project" if rights != "reference_only" else "proposed",
    )


def test_builds_ordered_vertical_timeline() -> None:
    timeline = build_timeline_composition(
        title="Final goal story",
        selections=(
            _clip("one", 1, 6),
            _clip("two", 10, 16),
        ),
        transitions=("cut", "crossfade"),
        timeline_state="ready_for_factory",
    )
    assert timeline.aspect_ratio == "9:16"
    assert timeline.resolution == "1080x1920"
    assert timeline.total_duration_seconds == 11
    assert [clip.order for clip in timeline.clips] == [1, 2]
    assert timeline.timeline_state == "ready_for_factory"
    assert timeline.blockers == ()
    assert timeline.render_enabled is False
    assert timeline.auto_render is False


def test_reference_only_clip_blocks_factory_readiness() -> None:
    timeline = build_timeline_composition(
        title="Reference analysis",
        selections=(
            _clip("owned", 0, 5),
            _clip("reference", 5, 10, rights="reference_only"),
        ),
        timeline_state="ready_for_factory",
    )
    assert timeline.timeline_state == "blocked"
    assert len(timeline.blockers) == 1
    assert "CLIP_NOT_RENDERABLE" in timeline.blockers[0]


def test_supports_voiceover_music_and_caption_tracks() -> None:
    tracks = (
        TimelineTrack("voiceover", "assets/voiceover.mp3", True, 0, 8, volume=1),
        TimelineTrack("music", "assets/music.mp3", True, 0, 8, volume=0.2),
        TimelineTrack("captions", "assets/captions.vtt", True, 0, 8, language="pt-PT"),
    )
    timeline = build_timeline_composition(
        title="Tracks",
        selections=(_clip("one", 0, 8),),
        tracks=tracks,
    )
    assert {track.track_type for track in timeline.tracks} == {
        "voiceover",
        "music",
        "captions",
    }


def test_rejects_track_outside_timeline() -> None:
    with pytest.raises(TimelineCompositionError, match="track exceeds"):
        build_timeline_composition(
            title="Invalid track",
            selections=(_clip("one", 0, 5),),
            tracks=(
                TimelineTrack("music", "assets/music.mp3", True, 0, 8, volume=0.2),
            ),
        )


def test_rejects_transition_count_mismatch() -> None:
    with pytest.raises(TimelineCompositionError, match="one transition"):
        build_timeline_composition(
            title="Mismatch",
            selections=(_clip("one", 0, 5), _clip("two", 0, 5)),
            transitions=("cut",),
        )


def test_rejects_duration_below_governed_minimum() -> None:
    with pytest.raises(TimelineCompositionError, match="duration is outside"):
        build_timeline_composition(
            title="Too short",
            selections=(_clip("one", 0, 1),),
        )


def test_identity_and_replay_are_deterministic() -> None:
    kwargs = {
        "title": "Deterministic timeline",
        "selections": (_clip("one", 0, 5), _clip("two", 2, 7)),
        "transitions": ("cut", "fade"),
        "timeline_state": "reviewed",
    }
    first = build_timeline_composition(**kwargs)
    second = build_timeline_composition(**kwargs)
    assert first.timeline_id == second.timeline_id
    assert first.to_dict() == second.to_dict()
    assert canonical_sha256(first.to_dict()) == canonical_sha256(second.to_dict())


def test_rejects_automatic_or_runtime_render_activation() -> None:
    timeline = build_timeline_composition(
        title="Safe",
        selections=(_clip("one", 0, 5),),
    )
    payload = timeline.to_dict()
    payload["render_enabled"] = True
    assert payload["auto_acquire"] is False
    assert payload["auto_render"] is False
    assert payload["auto_publish"] is False
