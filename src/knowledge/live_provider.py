from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from knowledge.adapters import MappingKnowledgeAdapter
from knowledge.contracts import ExternalKnowledgePackage


HttpGetter = Callable[[str, float], bytes]


@dataclass(frozen=True, slots=True)
class LiveProviderConfig:
    """Controlled configuration for an opt-in live RSS provider."""

    endpoint: str = "https://news.google.com/rss/search"
    language: str = "en"
    region: str = "US"
    edition: str = "US:en"
    timeout_seconds: float = 10.0
    maximum_items: int = 8

    def __post_init__(self) -> None:
        parsed = urlparse(self.endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("live provider endpoint must be an absolute HTTPS URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if not 1 <= self.maximum_items <= 25:
            raise ValueError("maximum_items must be between 1 and 25")
        if not self.language.strip() or not self.region.strip() or not self.edition.strip():
            raise ValueError("language, region and edition must not be empty")


class LiveFootballRssKnowledgeProvider:
    """Fetch current football headlines through a controlled RSS boundary.

    Live access is explicit: constructing this provider does not perform network
    access. Network access occurs only when ``fetch`` is called. Tests can inject
    a deterministic ``http_getter`` and therefore never require the network.
    """

    provider_name = "google_news_rss"
    provider_mode = "live"

    def __init__(
        self,
        config: LiveProviderConfig | None = None,
        *,
        http_getter: HttpGetter | None = None,
    ) -> None:
        self._config = config or LiveProviderConfig()
        self._http_getter = http_getter or self._default_http_getter
        self._adapter = MappingKnowledgeAdapter()

    def fetch(self, topic: str) -> ExternalKnowledgePackage:
        normalized_topic = str(topic).strip()
        if not normalized_topic:
            raise ValueError("topic must not be empty")

        request_url = self._build_request_url(normalized_topic)
        document = self._http_getter(request_url, self._config.timeout_seconds)
        payload = self._parse_feed(document)

        if not payload["sources"]:
            raise RuntimeError("live knowledge provider returned no usable RSS items")

        return self._adapter.build_package(
            normalized_topic,
            payload,
            provider_mode=self.provider_mode,
        )

    def _build_request_url(self, topic: str) -> str:
        query = f"{topic} football"
        parameters = urlencode(
            {
                "q": query,
                "hl": self._config.language,
                "gl": self._config.region,
                "ceid": self._config.edition,
            }
        )
        return f"{self._config.endpoint}?{parameters}"

    def _parse_feed(self, document: bytes) -> dict:
        try:
            root = ElementTree.fromstring(document)
        except ElementTree.ParseError as exc:
            raise RuntimeError("live knowledge provider returned invalid RSS XML") from exc

        retrieved_at = datetime.now(timezone.utc).isoformat()
        sources: list[dict] = []
        facts: list[dict] = []

        for item in root.findall("./channel/item")[: self._config.maximum_items]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            published_at = (item.findtext("pubDate") or "").strip() or None
            if not title or not link:
                continue

            parsed_link = urlparse(link)
            if parsed_link.scheme not in {"http", "https"} or not parsed_link.netloc:
                continue

            stable_key = sha256(f"{title}\n{link}".encode("utf-8")).hexdigest()[:16]
            source_id = f"live_source_{stable_key}"
            fact_id = f"live_fact_{stable_key}"

            sources.append(
                {
                    "source_id": source_id,
                    "provider": self.provider_name,
                    "title": title,
                    "source_type": "rss",
                    "reliability": "reputable_secondary",
                    "url": link,
                    "published_at": published_at,
                    "retrieved_at": retrieved_at,
                }
            )
            facts.append(
                {
                    "fact_id": fact_id,
                    "claim": title,
                    "source_ids": [source_id],
                    "verification_status": "supported",
                }
            )

        return {"sources": sources, "facts": facts}

    @staticmethod
    def _default_http_getter(url: str, timeout_seconds: float) -> bytes:
        request = Request(
            url,
            headers={
                "Accept": "application/rss+xml, application/xml;q=0.9",
                "User-Agent": "football-shorts-ai/1.0",
            },
            method="GET",
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise RuntimeError(f"live knowledge provider returned HTTP {status}")
            return response.read()
