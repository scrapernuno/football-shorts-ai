from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from collect_news import NewsItem, collect_all_news


@dataclass(frozen=True)
class ScoredNewsItem:
    item: NewsItem
    score: int
    reasons: tuple[str, ...]


KEYWORD_RULES: tuple[tuple[str, int, str], ...] = (
    ("cristiano", 35, "Cristiano Ronaldo"),
    ("ronaldo", 30, "Ronaldo"),
    ("messi", 35, "Lionel Messi"),
    ("vinicius", 30, "Vinícius Júnior"),
    ("vinicius jr", 30, "Vinícius Júnior"),
    ("yamal", 30, "Lamine Yamal"),
    ("neymar", 30, "Neymar"),
    ("mbappe", 30, "Kylian Mbappé"),
    ("mbappé", 30, "Kylian Mbappé"),
    ("real madrid", 25, "Real Madrid"),
    ("barcelona", 25, "Barcelona"),
    ("manchester united", 22, "Manchester United"),
    ("manchester city", 22, "Manchester City"),
    ("liverpool", 22, "Liverpool"),
    ("arsenal", 22, "Arsenal"),
    ("chelsea", 20, "Chelsea"),
    ("psg", 20, "PSG"),
    ("world cup", 25, "Mundial"),
    ("champions league", 25, "Liga dos Campeões"),
    ("final", 20, "Final"),
    ("record", 18, "Recorde"),
    ("shock", 18, "Surpresa"),
    ("agrees terms", 22, "Acordo de transferência"),
    ("contract talks", 18, "Negociação contratual"),
    ("transfer", 20, "Transferência"),
    ("signing", 18, "Contratação"),
    ("gossip", 8, "Rumor de mercado"),
    ("injury", 15, "Lesão"),
    ("scores", 15, "Golo"),
    ("goal", 15, "Golo"),
    ("legend", 12, "Lenda do futebol"),
    ("tears", 15, "Momento emocional"),
    ("future", 10, "Incerteza sobre o futuro"),
    ("£", 10, "Valor financeiro elevado"),
    ("€", 10, "Valor financeiro elevado"),
)


LOW_VALUE_RULES: tuple[tuple[str, int, str], ...] = (
    ("quiz", -15, "Quiz genérico"),
    ("who am i", -15, "Conteúdo de adivinhação"),
    ("league cup", -5, "Competição de interesse mais limitado"),
    ("rangers", -5, "Audiência potencial mais limitada"),
    ("st mirren", -8, "Audiência potencial mais limitada"),
)


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def score_item(item: NewsItem) -> ScoredNewsItem:
    text = normalize_text(item.title)

    score = 0
    reasons: list[str] = []

    for keyword, points, reason in KEYWORD_RULES:
        if keyword in text:
            score += points
            reasons.append(f"+{points}: {reason}")

    for keyword, points, reason in LOW_VALUE_RULES:
        if keyword in text:
            score += points
            reasons.append(f"{points}: {reason}")

    if "?" in item.title:
        score += 5
        reasons.append("+5: Título gera curiosidade")

    if len(item.title) <= 90:
        score += 3
        reasons.append("+3: Título curto e adaptável a Short")

    return ScoredNewsItem(
        item=item,
        score=score,
        reasons=tuple(reasons),
    )


def score_news(items: Iterable[NewsItem]) -> list[ScoredNewsItem]:
    scored = [score_item(item) for item in items]

    return sorted(
        scored,
        key=lambda result: (
            result.score,
            result.item.published,
            result.item.title,
        ),
        reverse=True,
    )


def main() -> None:
    news = collect_all_news()
    ranked = score_news(news)

    print()
    print("=" * 78)
    print("TOP 15 NOTÍCIAS POR POTENCIAL VIRAL")
    print("=" * 78)

    for position, result in enumerate(ranked[:15], start=1):
        print()
        print(
            f"{position}. SCORE={result.score} "
            f"[{result.item.source}] {result.item.title}"
        )

        if result.reasons:
            for reason in result.reasons:
                print(f"   - {reason}")
        else:
            print("   - Sem sinais virais específicos")

        print(f"   Link: {result.item.link}")


if __name__ == "__main__":
    main()
