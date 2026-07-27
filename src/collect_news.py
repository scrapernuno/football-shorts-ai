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
}


def collect_feed(source: str, url: str) -> list[NewsItem]:
    feed = feedparser.parse(url)

    if getattr(feed, "bozo", False):
        print(f"[AVISO] Não foi possível ler corretamente: {source}")

    items: list[NewsItem] = []

    for entry in feed.entries[:20]:
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

    return items


def remove_duplicates(items: Iterable[NewsItem]) -> list[NewsItem]:
    unique_items: list[NewsItem] = []
    seen_titles: set[str] = set()

    for item in items:
        normalized_title = item.title.casefold()

        if normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        unique_items.append(item)

    return unique_items


def collect_all_news() -> list[NewsItem]:
    collected: list[NewsItem] = []

    for source, url in RSS_FEEDS.items():
        print(f"[INFO] A recolher notícias de: {source}")
        collected.extend(collect_feed(source, url))

    return remove_duplicates(collected)


def main() -> None:
    news = collect_all_news()

    print()
    print("=" * 70)
    print(f"TOTAL DE NOTÍCIAS RECOLHIDAS: {len(news)}")
    print("=" * 70)

    for index, item in enumerate(news[:15], start=1):
        print(f"{index}. [{item.source}] {item.title}")
        print(f"   Data: {item.published}")
        print(f"   Link: {item.link}")
        print()


if __name__ == "__main__":
    main()
