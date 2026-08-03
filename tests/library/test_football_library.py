from __future__ import annotations

import pytest

from discovery.external_provider_contract import (
    ProviderCapabilities,
    build_external_video_asset,
)
from library.football_library import (
    FootballLibrary,
    FootballLibraryError,
    LibraryQuery,
    canonical_sha256,
)


DISCOVERED_AT = "2026-08-03T10:00:00Z"


def _capabilities(*, direct: bool = False) -> ProviderCapabilities:
    return ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=direct,
    )


def _asset(
    provider: str,
    provider_id: str,
    title: str,
    *,
    score: float,
    views: int,
    rights: str = "reference_only",
    player: str = "",
    team: str = "",
    competition: str = "Champions League",
):
    return build_external_video_asset(
        provider=provider,
        provider_asset_id=provider_id,
        provider_url=f"https://example.test/{provider}/{provider_id}",
        embed_url=f"https://example.test/embed/{provider_id}",
        thumbnail_url=f"https://example.test/thumb/{provider_id}.jpg",
        title=title,
        description="Football highlight and tactical analysis",
        channel_name="Football Channel",
        capabilities=_capabilities(direct=rights != "reference_only"),
        discovered_at=DISCOVERED_AT,
        published_at="2026-08-02T12:00:00Z",
        source_metadata={"provider": provider, "id": provider_id},
        views=views,
        likes=views // 10,
        competition=competition,
        teams=(team,) if team else (),
        players=(player,) if player else (),
        tags=("football", "goal"),
        score=score,
        rights_status=rights,
    )


def _library() -> FootballLibrary:
    return FootballLibrary(
        (
            _asset(
                "youtube",
                "yt-1",
                "Ronaldo decisive goal",
                score=98,
                views=3_000_000,
                player="Cristiano Ronaldo",
                team="Real Madrid",
            ),
            _asset(
                "tiktok",
                "tt-1",
                "Messi free kick",
                score=96,
                views=4_000_000,
                player="Lionel Messi",
                team="Barcelona",
            ),
            _asset(
                "local_library",
                "own-1",
                "Owned training footage",
                score=80,
                views=100,
                rights="owned",
                team="Football Shorts AI",
                competition="Training",
            ),
        )
    )


def test_indexes_and_deduplicates_identical_assets() -> None:
    asset = _asset("youtube", "same", "Same", score=50, views=10)
    library = FootballLibrary()
    library.index(asset)
    library.index(asset)
    assert len(library) == 1


def test_rejects_provider_identity_collision() -> None:
    first = _asset("youtube", "same", "Original", score=50, views=10)
    second = _asset("youtube", "same", "Changed", score=60, views=20)
    library = FootballLibrary((first,))
    with pytest.raises(FootballLibraryError, match="provider asset identity collision"):
        library.index(second)


def test_searches_text_without_accents_and_sorts_by_score() -> None:
    result = _library().search(LibraryQuery(text="cristiano ronaldo"))
    assert result.total_matches == 1
    assert result.assets[0].title == "Ronaldo decisive goal"


def test_filters_provider_rights_team_and_minimum_score() -> None:
    result = _library().search(
        LibraryQuery(
            providers=("local_library",),
            rights_statuses=("owned",),
            teams=("Football Shorts AI",),
            minimum_score=75,
            render_allowed=True,
        )
    )
    assert result.total_matches == 1
    assert result.assets[0].rights_status == "owned"


def test_orders_trending_assets_by_views() -> None:
    result = _library().search(LibraryQuery(sort="views_desc"))
    assert [asset.provider for asset in result.assets] == [
        "tiktok",
        "youtube",
        "local_library",
    ]


def test_applies_governed_state_transitions() -> None:
    library = _library()
    asset_id = library.search(LibraryQuery(providers=("youtube",))).assets[0].asset_id
    indexed = library.transition(asset_id, "indexed")
    selected = library.transition(asset_id, "selected")
    assert indexed.library_state == "indexed"
    assert selected.library_state == "selected"
    with pytest.raises(FootballLibraryError, match="invalid state transition"):
        library.transition(asset_id, "published")


def test_dashboard_export_is_deterministic_and_fail_closed() -> None:
    first = _library().to_dashboard_dict()
    second = _library().to_dashboard_dict()
    assert first == second
    assert first["summary"]["providers"] == {
        "local_library": 1,
        "tiktok": 1,
        "youtube": 1,
    }
    assert first["summary"]["renderable"] == 1
    assert first["summary"]["previewable"] == 3
    assert first["auto_acquire"] is False
    assert first["auto_publish"] is False
    evidence = first["evidence_sha256"]
    unsigned = dict(first)
    unsigned.pop("evidence_sha256")
    assert evidence == canonical_sha256(unsigned)


def test_query_pagination_and_query_identity_are_deterministic() -> None:
    query = LibraryQuery(limit=2, offset=1, sort="score_desc")
    first = _library().search(query)
    second = _library().search(query)
    assert first.query_sha256 == second.query_sha256
    assert first.to_dict() == second.to_dict()
    assert first.total_matches == 3
    assert len(first.assets) == 2


def test_rejects_invalid_query_contract() -> None:
    with pytest.raises(FootballLibraryError, match="unsupported sort"):
        _library().search(LibraryQuery(sort="random"))
    with pytest.raises(FootballLibraryError, match="limit"):
        _library().search(LibraryQuery(limit=0))
