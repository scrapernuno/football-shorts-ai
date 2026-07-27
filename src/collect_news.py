from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import feedparser


@dataclass(frozen=True)
class NewsItem:
    source: str
    title: str
    link: str
    published: str


RSS_FEEDS = {
    "BBC Sport Football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "ESPN FC": "https://www.espn.com/espn/rss/soccer/news",
    "The Guardian Football": "https://www.theguardian.com/football/rss",
}


def collect_feed(source: str, url: str) -> list[NewsItem]:
    print(f"[INFO] A recolher notícias de: {source}")

    feed = feedparser.parse(
        url,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 FootballShortsAI/1.0 "
                "(GitHub Actions; news aggregation)"
            )
        },
    )

    status = getattr(feed, "status", "desconhecido")
    entries = list(getattr(feed, "entries", []))

    print(f"[INFO] {source}: HTTP={status}, entradas={len(entries)}")

    if getattr(feed, "bozo", False):
        error = getattr(feed, "bozo_exception", "erro desconhecido")
        print(f"[AVISO] Feed com erro em {source}: {error}")

    items: list[NewsItem] = []

    for entry in entries[:20]:
        title = str(entry.get("title", "")).strip()
        link = str(entry.get("link", "")).strip()
        published = str(
            entry.get("published", entry.get("updated", "Sem data"))
        ).strip()

        if not title or not link:
            continue

        items.append(
            NewsItem(
                source=source,
                title=title,
                link=link,
                published=published,
            )
        )

    print(f"[INFO] {source}: notícias válidas={len(items)}")

    return items


def normalize_title(title: str) -> str:
    return " ".join(title.casefold().split())


def remove_duplicates(items: Iterable[NewsItem]) -> list[NewsItem]:
    unique_items: list[NewsItem] = []
    seen_titles: set[str] = set()

    for item in items:
        normalized_title = normalize_title(item.title)

        if normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        unique_items.append(item)

    return unique_items


def collect_all_news() -> list[NewsItem]:
    collected: list[NewsItem] = []

    for source, url in RSS_FEEDS.items():
        try:
            collected.extend(collect_feed(source, url))
        except Exception as exc:
            print(f"[ERRO] Falha inesperada em {source}: {exc}")

    return remove_duplicates(collected)


def main() -> None:
    news = collect_all_news()

    print()
    print("=" * 70)
    print(f"TOTAL DE NOTÍCIAS RECOLHIDAS: {len(news)}")
    print("=" * 70)

    if not news:
        raise SystemExit("Nenhuma notícia foi recolhida.")

    source_totals: dict[str, int] = {}

    for item in news:
        source_totals[item.source] = source_totals.get(item.source, 0) + 1

    print("NOTÍCIAS POR FONTE")

    for source, total in sorted(source_totals.items()):
        print(f"- {source}: {total}")

    print()
    print("PRIMEIRAS 20 NOTÍCIAS")
    print()

    for index, item in enumerate(news[:20], start=1):
        print(f"{index}. [{item.source}] {item.title}")
        print(f"   Data: {item.published}")
        print(f"   Link: {item.link}")
        print()


if __name__ == "__main__":
    main()
