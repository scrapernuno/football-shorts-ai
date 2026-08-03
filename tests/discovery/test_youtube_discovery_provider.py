from __future__ import annotations

import dataclasses

import pytest

from discovery.youtube_discovery_provider import (
    YouTubeDiscoveryError,
    YouTubeDiscoveryPolicy,
    YouTubeDiscoveryProvider,
)
from library.football_library import FootballLibrary, LibraryQuery


class StaticYouTubeClient:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.list_calls: list[tuple[str, ...]] = []

    def search_videos(self, **kwargs):
        self.search_calls.append(dict(kwargs))
        return (
            {"id": {"videoId": "abc123"}},
            {"id": {"videoId": "def456"}},
        )

    def list_videos(self, *, video_ids):
        self.list_calls.append(tuple(video_ids))
        return tuple(_video(video_id, index) for index, video_id in enumerate(video_ids, start=1))


def _video(video_id: str, index: int) -> dict[str, object]:
    return {
        "id": video_id,
        "snippet": {
            "title": f"Football goal {index}",
            "description": "Tactical football highlight",
            "channelTitle": "Official Football Channel",
            "channelId": "CHANNEL-1",
            "publishedAt": "2026-08-02T12:00:00Z",
            "defaultLanguage": "en",
            "tags": ["football", "goal"],
            "thumbnails": {
                "high": {"url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"}
            },
        },
        "contentDetails": {"duration": "PT1M15S"},
        "statistics": {
            "viewCount": str(index * 1_000_000),
            "likeCount": str(index * 50_000),
        },
    }


def _enabled_policy() -> YouTubeDiscoveryPolicy:
    return YouTubeDiscoveryPolicy(
        enabled=True,
        network_enabled=True,
        max_results=12,
        region_code="PT",
        relevance_language="pt",
        video_duration="short",
        safe_search="moderate",
    )


def test_default_policy_is_not_activated_and_never_calls_client() -> None:
    client = StaticYouTubeClient()
    provider = YouTubeDiscoveryProvider(
        client=client,
        policy=YouTubeDiscoveryPolicy(),
    )

    result = provider.discover("Champions League")

    assert result.status == "NOT_ACTIVATED"
    assert result.network_used is False
    assert result.assets == ()
    assert client.search_calls == []
    assert client.list_calls == []


def test_discovers_and_normalizes_reference_only_youtube_assets() -> None:
    client = StaticYouTubeClient()
    provider = YouTubeDiscoveryProvider(client=client, policy=_enabled_policy())

    result = provider.discover(
        "Champions League goals",
        discovered_at="2026-08-03T10:50:00Z",
    )

    assert result.status == "DISCOVERED"
    assert result.network_used is True
    assert len(result.assets) == 2
    assert client.list_calls == [("abc123", "def456")]

    first = result.assets[0]
    assert first.provider == "youtube"
    assert first.provider_asset_id == "abc123"
    assert first.embed_url == "https://www.youtube.com/embed/abc123"
    assert first.duration_seconds == 75
    assert first.views == 1_000_000
    assert first.likes == 50_000
    assert first.rights_status == "reference_only"
    assert first.preview_allowed is True
    assert first.render_allowed is False
    assert first.acquisition_allowed is False
    assert first.auto_acquire is False
    assert first.auto_publish is False


def test_uses_governed_youtube_search_parameters() -> None:
    client = StaticYouTubeClient()
    provider = YouTubeDiscoveryProvider(client=client, policy=_enabled_policy())
    provider.discover("Cristiano Ronaldo", discovered_at="2026-08-03T10:50:00Z")

    assert client.search_calls == [
        {
            "query": "Cristiano Ronaldo",
            "max_results": 12,
            "region_code": "PT",
            "relevance_language": "pt",
            "video_duration": "short",
            "video_embeddable": True,
            "safe_search": "moderate",
        }
    ]


def test_discovered_assets_enter_library_and_dashboard_export() -> None:
    provider = YouTubeDiscoveryProvider(
        client=StaticYouTubeClient(),
        policy=_enabled_policy(),
    )
    result = provider.discover("football", discovered_at="2026-08-03T10:50:00Z")
    library = FootballLibrary(result.assets)

    search = library.search(LibraryQuery(providers=("youtube",), preview_allowed=True))
    dashboard = library.to_dashboard_dict()

    assert search.total_matches == 2
    assert dashboard["asset_count"] == 2
    assert dashboard["summary"]["providers"] == {"youtube": 2}
    assert dashboard["summary"]["previewable"] == 2
    assert dashboard["summary"]["renderable"] == 0
    assert dashboard["summary"]["acquirable"] == 0


def test_no_search_video_ids_is_fail_closed() -> None:
    class EmptyClient(StaticYouTubeClient):
        def search_videos(self, **kwargs):
            return ()

    provider = YouTubeDiscoveryProvider(client=EmptyClient(), policy=_enabled_policy())
    result = provider.discover("unknown")

    assert result.status == "BLOCKED"
    assert result.blockers == ("YOUTUBE_SEARCH_RETURNED_NO_VIDEO_IDS",)
    assert result.assets == ()


def test_invalid_duration_evidence_is_rejected() -> None:
    class InvalidClient(StaticYouTubeClient):
        def list_videos(self, *, video_ids):
            item = _video(video_ids[0], 1)
            item["contentDetails"] = {"duration": "invalid"}
            return (item,)

    provider = YouTubeDiscoveryProvider(client=InvalidClient(), policy=_enabled_policy())
    with pytest.raises(YouTubeDiscoveryError, match="ISO-8601"):
        provider.discover("football")


def test_network_cannot_be_enabled_implicitly() -> None:
    with pytest.raises(YouTubeDiscoveryError, match="network_enabled"):
        YouTubeDiscoveryProvider(
            client=StaticYouTubeClient(),
            policy=YouTubeDiscoveryPolicy(enabled=True, network_enabled=False),
        )


def test_media_operations_cannot_be_forged() -> None:
    provider = YouTubeDiscoveryProvider(client=StaticYouTubeClient(), policy=_enabled_policy())
    result = provider.discover("football", discovered_at="2026-08-03T10:50:00Z")

    with pytest.raises(YouTubeDiscoveryError, match="forbidden"):
        dataclasses.replace(result, download_enabled=True).validate()
    with pytest.raises(YouTubeDiscoveryError, match="forbidden"):
        dataclasses.replace(result, acquisition_enabled=True).validate()
    with pytest.raises(YouTubeDiscoveryError, match="forbidden"):
        dataclasses.replace(result, auto_publish=True).validate()


def test_replay_is_deterministic_with_fixed_discovery_time() -> None:
    first = YouTubeDiscoveryProvider(client=StaticYouTubeClient(), policy=_enabled_policy()).discover(
        "football",
        discovered_at="2026-08-03T10:50:00Z",
    )
    second = YouTubeDiscoveryProvider(client=StaticYouTubeClient(), policy=_enabled_policy()).discover(
        "football",
        discovered_at="2026-08-03T10:50:00Z",
    )

    assert [asset.to_dict() for asset in first.assets] == [asset.to_dict() for asset in second.assets]
