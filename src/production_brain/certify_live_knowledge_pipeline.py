from __future__ import annotations

import json
import tempfile
from pathlib import Path

from knowledge.live_provider import LiveFootballRssKnowledgeProvider
from production_brain import brain


EXPECTED_PACKAGES = {
    "research_package.json": "research_status",
    "story_package.json": "story_status",
    "production_package.json": "production_status",
    "publishing_package.json": "publishing_status",
}

RSS_DOCUMENT = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<rss version=\"2.0\">
  <channel>
    <title>Controlled live certification feed</title>
    <item>
      <title>Controlled football headline one</title>
      <link>https://example.com/football/headline-one</link>
      <pubDate>Wed, 29 Jul 2026 18:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Controlled football headline two</title>
      <link>https://example.com/football/headline-two</link>
      <pubDate>Wed, 29 Jul 2026 18:05:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def _certify_live_research(research: dict) -> None:
    if research.get("research_status") != "completed":
        raise SystemExit("CERTIFICATION_FAILED: research package incomplete")
    if research.get("provider_mode") != "live":
        raise SystemExit("CERTIFICATION_FAILED: research provider mode is not live")

    knowledge = research.get("knowledge")
    if not isinstance(knowledge, dict) or knowledge.get("provider_mode") != "live":
        raise SystemExit("CERTIFICATION_FAILED: live knowledge package missing")

    sources = knowledge.get("sources")
    facts = knowledge.get("facts")
    if not isinstance(sources, list) or len(sources) != 2:
        raise SystemExit("CERTIFICATION_FAILED: controlled live sources missing")
    if not isinstance(facts, list) or len(facts) != 2:
        raise SystemExit("CERTIFICATION_FAILED: controlled live facts missing")

    source_ids = {source.get("source_id") for source in sources if isinstance(source, dict)}
    if None in source_ids or len(source_ids) != len(sources):
        raise SystemExit("CERTIFICATION_FAILED: invalid live source identifiers")

    for source in sources:
        if source.get("provider") != "google_news_rss":
            raise SystemExit("CERTIFICATION_FAILED: unexpected live source provider")
        if source.get("source_type") != "rss":
            raise SystemExit("CERTIFICATION_FAILED: live source is not RSS evidence")
        if not str(source.get("url", "")).startswith("https://"):
            raise SystemExit("CERTIFICATION_FAILED: live source URL is not HTTPS")

    for fact in facts:
        if fact.get("verification_status") != "supported":
            raise SystemExit("CERTIFICATION_FAILED: live fact is not supported")
        references = fact.get("source_ids")
        if not isinstance(references, list) or not set(references).issubset(source_ids):
            raise SystemExit("CERTIFICATION_FAILED: live fact evidence reference invalid")


def main() -> int:
    transport_calls: list[tuple[str, float]] = []

    def controlled_http_getter(url: str, timeout_seconds: float) -> bytes:
        transport_calls.append((url, timeout_seconds))
        return RSS_DOCUMENT

    provider = LiveFootballRssKnowledgeProvider(http_getter=controlled_http_getter)

    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0042a6d-") as tmp:
        output_dir = Path(tmp) / "output"
        original_output = brain.OUTPUT
        brain.OUTPUT = output_dir

        try:
            result = brain.execute(
                "controlled live football knowledge certification",
                knowledge_provider=provider,
            )
        finally:
            brain.OUTPUT = original_output

        if result.get("status") != "COMPLETED":
            raise SystemExit("CERTIFICATION_FAILED: live pipeline did not complete")
        if len(transport_calls) != 1:
            raise SystemExit("CERTIFICATION_FAILED: controlled transport call count drift")

        request_url, timeout_seconds = transport_calls[0]
        if not request_url.startswith("https://news.google.com/rss/search?"):
            raise SystemExit("CERTIFICATION_FAILED: unexpected live request boundary")
        if timeout_seconds <= 0:
            raise SystemExit("CERTIFICATION_FAILED: invalid live request timeout")

        persisted: dict[str, dict] = {}
        for package_name, status_key in EXPECTED_PACKAGES.items():
            package_path = output_dir / package_name
            if not package_path.is_file():
                raise SystemExit(f"CERTIFICATION_FAILED: missing package {package_name}")
            payload = json.loads(package_path.read_text(encoding="utf-8"))
            if payload.get(status_key) != "completed":
                raise SystemExit(
                    f"CERTIFICATION_FAILED: invalid status in {package_name}"
                )
            persisted[package_name] = payload

        research = result.get("research", {})
        _certify_live_research(research)
        if persisted["research_package.json"] != research:
            raise SystemExit("CERTIFICATION_FAILED: persisted live research drift")

        print("FOOTBALL-SHORTS-AI-0042A.6D: CERTIFIED")
        print("PIPELINE_STATUS: COMPLETED")
        print("KNOWLEDGE_PROVIDER_MODE: LIVE")
        print("CONTROLLED_TRANSPORT_CALLS: 1")
        print("REAL_EXTERNAL_NETWORK_ACCESS: NOT EXECUTED")
        print("GOVERNED_LIVE_SOURCES: 2")
        print("SUPPORTED_LIVE_FACTS: 2")
        print("PACKAGES_GENERATED: 4")
        print("REAL_PUBLICATION: NOT EXECUTED")
        print("NEXT_AUTHORISED_STEP: CONTROLLED_REAL_NETWORK_ACTIVATION")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
