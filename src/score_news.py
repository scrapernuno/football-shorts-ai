from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from collect_news import NewsItem, collect_all_news


@dataclass(frozen=True)
class ScoredNewsItem:
    item: NewsItem
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RuleGroup:
    name: str
    points: int
    reason: str
    keywords: tuple[str, ...]


POSITIVE_RULE_GROUPS: tuple[RuleGroup, ...] = (
    RuleGroup(
        name="cristiano_ronaldo",
        points=35,
        reason="Cristiano Ronaldo",
        keywords=(
            "cristiano ronaldo",
            "cristiano",
            "cr7",
        ),
    ),
    RuleGroup(
        name="lionel_messi",
        points=35,
        reason="Lionel Messi",
        keywords=(
            "lionel messi",
            "messi",
        ),
    ),
    RuleGroup(
        name="vinicius_junior",
        points=30,
        reason="Vinícius Júnior",
        keywords=(
            "vinicius junior",
            "vinicius jr",
            "vinicius",
            "vini jr",
        ),
    ),
    RuleGroup(
        name="lamine_yamal",
        points=30,
        reason="Lamine Yamal",
        keywords=(
            "lamine yamal",
            "yamal",
        ),
    ),
    RuleGroup(
        name="neymar",
        points=30,
        reason="Neymar",
        keywords=(
            "neymar",
        ),
    ),
    RuleGroup(
        name="mbappe",
        points=30,
        reason="Kylian Mbappé",
        keywords=(
            "kylian mbappe",
            "mbappe",
        ),
    ),
    RuleGroup(
        name="real_madrid",
        points=25,
        reason="Real Madrid",
        keywords=(
            "real madrid",
        ),
    ),
    RuleGroup(
        name="barcelona",
        points=25,
        reason="Barcelona",
        keywords=(
            "barcelona",
            "barca",
        ),
    ),
    RuleGroup(
        name="manchester_united",
        points=22,
        reason="Manchester United",
        keywords=(
            "manchester united",
            "man utd",
        ),
    ),
    RuleGroup(
        name="manchester_city",
        points=22,
        reason="Manchester City",
        keywords=(
            "manchester city",
            "man city",
        ),
    ),
    RuleGroup(
        name="liverpool",
        points=22,
        reason="Liverpool",
        keywords=(
            "liverpool",
        ),
    ),
    RuleGroup(
        name="arsenal",
        points=22,
        reason="Arsenal",
        keywords=(
            "arsenal",
        ),
    ),
    RuleGroup(
        name="chelsea",
        points=20,
        reason="Chelsea",
        keywords=(
            "chelsea",
        ),
    ),
    RuleGroup(
        name="psg",
        points=20,
        reason="PSG",
        keywords=(
            "paris saint germain",
            "paris saint-germain",
            "psg",
        ),
    ),
    RuleGroup(
        name="world_cup",
        points=25,
        reason="Mundial",
        keywords=(
            "world cup",
            "fifa world cup",
        ),
    ),
    RuleGroup(
        name="champions_league",
        points=25,
        reason="Liga dos Campeões",
        keywords=(
            "champions league",
        ),
    ),
    RuleGroup(
        name="final",
        points=20,
        reason="Final",
        keywords=(
            "final",
        ),
    ),
    RuleGroup(
        name="record",
        points=18,
        reason="Recorde",
        keywords=(
            "record",
            "historic",
            "history",
        ),
    ),
    RuleGroup(
        name="shock",
        points=18,
        reason="Surpresa",
        keywords=(
            "shock",
            "stunning",
            "surprise",
        ),
    ),
    RuleGroup(
        name="transfer_agreement",
        points=22,
        reason="Acordo de transferência",
        keywords=(
            "agrees terms",
            "agreed terms",
            "agreement",
            "seal deal",
        ),
    ),
    RuleGroup(
        name="contract_talks",
        points=18,
        reason="Negociação contratual",
        keywords=(
            "contract talks",
            "contract negotiation",
            "new contract",
        ),
    ),
    RuleGroup(
        name="transfer",
        points=20,
        reason="Transferência",
        keywords=(
            "transfer",
            "signing",
            "sign",
            "move",
        ),
    ),
    RuleGroup(
        name="gossip",
        points=8,
        reason="Rumor de mercado",
        keywords=(
            "gossip",
            "rumour",
            "rumor",
        ),
    ),
    RuleGroup(
        name="injury",
        points=15,
        reason="Lesão",
        keywords=(
            "injury",
            "injured",
        ),
    ),
    RuleGroup(
        name="goal",
        points=15,
        reason="Golo",
        keywords=(
            "scores",
            "scored",
            "goal",
            "goals",
        ),
    ),
    RuleGroup(
        name="legend",
        points=12,
        reason="Lenda do futebol",
        keywords=(
            "legend",
            "great",
        ),
    ),
    RuleGroup(
        name="emotion",
        points=15,
        reason="Momento emocional",
        keywords=(
            "tears",
            "crying",
            "emotional",
        ),
    ),
    RuleGroup(
        name="future",
        points=10,
        reason="Incerteza sobre o futuro",
        keywords=(
            "future",
            "uncertain",
        ),
    ),
    RuleGroup(
        name="high_value",
        points=10,
        reason="Valor financeiro elevado",
        keywords=(
            "£",
            "€",
            "$",
            "million",
            "m ",
        ),
    ),
)


NEGATIVE_RULE_GROUPS: tuple[RuleGroup, ...] = (
    RuleGroup(
        name="quiz",
        points=-15,
        reason="Quiz genérico",
        keywords=(
            "quiz",
            "who am i",
            "guess",
        ),
    ),
    RuleGroup(
        name="limited_competition",
        points=-5,
        reason="Competição de interesse mais limitado",
        keywords=(
            "league cup",
        ),
    ),
    RuleGroup(
        name="limited_audience",
        points=-5,
        reason="Audiência potencial mais limitada",
        keywords=(
            "rangers",
            "st mirren",
        ),
    ),
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.casefold()
    value = re.sub(r"[^a-z0-9£€$]+", " ", value)

    return " ".join(value.split())


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = normalize_text(keyword)

    if not normalized_keyword:
        return False

    if len(normalized_keyword) <= 3 and normalized_keyword.isalpha():
        return bool(
            re.search(
                rf"\b{re.escape(normalized_keyword)}\b",
                text,
            )
        )

    return normalized_keyword in text


def score_item(item: NewsItem) -> ScoredNewsItem:
    text = normalize_text(item.title)

    score = 0
    reasons: list[str] = []

    for group in POSITIVE_RULE_GROUPS:
        if any(
            contains_keyword(text, keyword)
            for keyword in group.keywords
        ):
            score += group.points
            reasons.append(f"+{group.points}: {group.reason}")

    for group in NEGATIVE_RULE_GROUPS:
        if any(
            contains_keyword(text, keyword)
            for keyword in group.keywords
        ):
            score += group.points
            reasons.append(f"{group.points}: {group.reason}")

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


def title_tokens(title: str) -> set[str]:
    normalized = normalize_text(title)

    return {
        token
        for token in normalized.split()
        if len(token) >= 3 and token not in STOP_WORDS
    }


def title_similarity(first: str, second: str) -> float:
    first_normalized = normalize_text(first)
    second_normalized = normalize_text(second)

    sequence_score = SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio()

    first_tokens = title_tokens(first)
    second_tokens = title_tokens(second)

    if not first_tokens or not second_tokens:
        token_score = 0.0
    else:
        token_score = len(first_tokens & second_tokens) / len(
            first_tokens | second_tokens
        )

    return max(sequence_score, token_score)


def remove_similar_stories(
    items: Iterable[ScoredNewsItem],
    threshold: float = 0.56,
) -> list[ScoredNewsItem]:
    unique: list[ScoredNewsItem] = []

    for candidate in items:
        duplicate = False

        for existing in unique:
            similarity = title_similarity(
                candidate.item.title,
                existing.item.title,
            )

            if similarity >= threshold:
                duplicate = True

                print(
                    "[INFO] História semelhante removida: "
                    f"{candidate.item.title}"
                )
                print(
                    "       Mantida: "
                    f"{existing.item.title}"
                )
                print(
                    f"       Similaridade: {similarity:.2f}"
                )

                break

        if not duplicate:
            unique.append(candidate)

    return unique


def score_news(items: Iterable[NewsItem]) -> list[ScoredNewsItem]:
    scored = [score_item(item) for item in items]

    ranked = sorted(
        scored,
        key=lambda result: (
            result.score,
            result.item.published,
            result.item.title,
        ),
        reverse=True,
    )

    return remove_similar_stories(ranked)


def main() -> None:
    news = collect_all_news()
    ranked = score_news(news)

    print()
    print("=" * 78)
    print("TOP 15 NOTÍCIAS ÚNICAS POR POTENCIAL VIRAL")
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
