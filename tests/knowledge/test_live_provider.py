from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from knowledge.contracts import ExternalKnowledgePackage
from knowledge.live_provider import (
    LiveFootballRssKnowledgeProvider,
    LiveProviderConfig,
)


VALID_RSS = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
  <channel>
    <title>Controlled Football Feed</title>
    <item>
      <title>Player reaches a new football milestone</title>
      <link>https://example.com/news/player-milestone</link>
      <pubDate>Wed, 29 Jul 2026 18:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Club confirms an official squad update</title>
      <link>https://example.org/football/squad-update</link>
      <pubDate>Wed, 29 Jul 2026 17:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_live_provider_builds_governed_package_without_real_network() -> None:
    calls: list[tuple[str, float]] = []

    def controlled_getter(url: str, timeout_seconds: float) -> bytes:
        calls.append((url, timeout_seconds))
        return VALID_RSS

    provider = LiveFootballRssKnowledgeProvider(
        LiveProviderConfig(
            language="pt-PT",
            region="PT",
            edition="PT:pt-150",
            timeout_seconds=3.5,
            maximum_items=2,
        ),
        http_getter=controlled_getter,
    )

    package = provider.fetch("Cristiano Ronaldo recordes")

    assert isinstance(package, ExternalKnowledgePackage)
    assert package.provider_mode == "live"
    assert package.topic == "Cristiano Ronaldo recordes"
    assert len(package.sources) == 2
    assert len(package.facts) == 2
    assert calls and calls[0][1] == 3.5

    parsed = urlparse(calls[0][0])
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert query["q"] == ["Cristiano Ronaldo recordes football"]
    assert query["hl"] == ["pt-PT"]
    assert query["gl"] == ["PT"]
    assert query["ceid"] == ["PT:pt-150"]

    source_ids = {source.source_id for source in package.sources}
    assert len(source_ids) == 2
    for fact in package.facts:
        assert fact.verification_status == "supported"
        assert set(fact.source_ids) <= source_ids


def test_live_provider_respects_maximum_items() -> None:
    provider = LiveFootballRssKnowledgeProvider(
        LiveProviderConfig(maximum_items=1),
        http_getter=lambda _url, _timeout: VALID_RSS,
    )

    package = provider.fetch("football transfer")

    assert len(package.sources) == 1
    assert len(package.facts) == 1


def test_live_provider_rejects_empty_topic_before_transport() -> None:
    transport_called = False

    def controlled_getter(_url: str, _timeout: float) -> bytes:
        nonlocal transport_called
        transport_called = True
        return VALID_RSS

    provider = LiveFootballRssKnowledgeProvider(http_getter=controlled_getter)

    with pytest.raises(ValueError, match="topic must not be empty"):
        provider.fetch("   ")

    assert transport_called is False


def test_live_provider_rejects_invalid_xml() -> None:
    provider = LiveFootballRssKnowledgeProvider(
        http_getter=lambda _url, _timeout: b"not-xml",
    )

    with pytest.raises(RuntimeError, match="invalid RSS XML"):
        provider.fetch("football")


def test_live_provider_rejects_feed_without_usable_items() -> None:
    empty_feed = b"""<rss version=\"2.0\"><channel><item>
    <title></title><link>javascript:alert(1)</link>
    </item></channel></rss>"""
    provider = LiveFootballRssKnowledgeProvider(
        http_getter=lambda _url, _timeout: empty_feed,
    )

    with pytest.raises(RuntimeError, match="no usable RSS items"):
        provider.fetch("football")


@pytest.mark.parametrize(
    ("config_kwargs", "message"),
    [
        ({"endpoint": "http://example.com/rss"}, "absolute HTTPS URL"),
        ({"timeout_seconds": 0}, "greater than zero"),
        ({"maximum_items": 0}, "between 1 and 25"),
        ({"maximum_items": 26}, "between 1 and 25"),
        ({"language": " "}, "must not be empty"),
    ],
)
def test_live_provider_config_fails_closed(
    config_kwargs: dict,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        LiveProviderConfig(**config_kwargs)
