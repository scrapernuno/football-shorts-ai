from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from collect_news import collect_all_news
from score_news import ScoredNewsItem, normalize_text, score_news


@dataclass(frozen=True)
class SelectedTopic:
    ranked_item: ScoredNewsItem
    topic_tokens: frozenset[str]


GENERIC_WORDS = {
    "a",
    "all",
    "an",
    "and",
    "approach",
    "as",
    "at",
    "battle",
    "deal",
    "for",
    "football",
    "from",
    "future",
    "in",
    "interest",
    "is",
    "it",
    "make",
    "move",
    "new",
    "of",
    "on",
    "out",
    "ready",
    "rumours",
    "rumor",
    "rumour",
    "seal",
    "sign",
    "the",
    "to",
    "transfer",
    "want",
    "what",
    "with",
}


DISTINCTIVE_TERMS = {
    "arsenal",
    "barcelona",
    "barcola",
    "chelsea",
    "chiesa",
    "cristiano",
    "diomande",
    "infantino",
    "liverpool",
    "madrid",
    "mbappe",
    "messi",
    "miura",
    "neymar",
    "palmer",
    "psg",
    "real",
    "rodri",
    "ronaldo",
    "scaloni",
    "vinicius",
    "yamal",
}


# Uma correspondência num destes tokens é suficiente para considerar
# que duas notícias representam a mesma história principal.
PRIMARY_ENTITY_TERMS = {
    "barcola",
    "chiesa",
    "cristiano",
    "diomande",
    "infantino",
    "mbappe",
    "messi",
    "miura",
    "neymar",
    "palmer",
    "rodri",
    "ronaldo",
    "scaloni",
    "vinicius",
    "yamal",
}


CONFLICTING_TOKEN_GROUPS = (
    frozenset({"men", "mens", "male"}),
    frozenset({"women", "womens", "female"}),
)


def extract_topic_tokens(title: str) -> frozenset[str]:
    normalized = normalize_text(title)

    words = {
        word
        for word in normalized.split()
        if len(word) >= 3 and word not in GENERIC_WORDS
    }

    distinctive = {
        word
        for word in words
        if word in DISTINCTIVE_TERMS
    }

    if distinctive:
        return frozenset(distinctive)

    return frozenset(words)


def has_conflicting_context(
    first_tokens: frozenset[str],
    second_tokens: frozenset[str],
) -> bool:
    for first_group in CONFLICTING_TOKEN_GROUPS:
        for second_group in CONFLICTING_TOKEN_GROUPS:
            if first_group == second_group:
                continue

            if (
                first_tokens & first_group
                and second_tokens & second_group
            ):
                return True

    return False


def overlap_coefficient(
    first_tokens: frozenset[str],
    second_tokens: frozenset[str],
) -> float:
    if not first_tokens or not second_tokens:
        return 0.0

    intersection = first_tokens & second_tokens
    denominator = min(len(first_tokens), len(second_tokens))

    return len(intersection) / denominator


def represents_same_topic(
    candidate: SelectedTopic,
    existing: SelectedTopic,
) -> tuple[bool, float]:
    if has_conflicting_context(
        candidate.topic_tokens,
        existing.topic_tokens,
    ):
        return False, 0.0

    common_tokens = (
        candidate.topic_tokens
        & existing.topic_tokens
    )

    overlap = overlap_coefficient(
        candidate.topic_tokens,
        existing.topic_tokens,
    )

    # Uma entidade principal igual, como Barcola, Vinícius ou Diomande,
    # é suficiente para considerar as notícias parte da mesma história.
    common_primary_entities = (
        common_tokens
        & PRIMARY_ENTITY_TERMS
    )

    if common_primary_entities:
        return True, overlap

    # Para clubes ou termos mais genéricos, exigimos pelo menos dois
    # tokens comuns para evitar remover histórias diferentes do mesmo clube.
    same_topic = (
        overlap >= 0.66
        and len(common_tokens) >= 2
    )

    return same_topic, overlap


def select_unique_topics(
    ranked_items: Iterable[ScoredNewsItem],
    limit: int = 10,
) -> list[SelectedTopic]:
    selected: list[SelectedTopic] = []

    for ranked_item in ranked_items:
        candidate = SelectedTopic(
            ranked_item=ranked_item,
            topic_tokens=extract_topic_tokens(
                ranked_item.item.title
            ),
        )

        duplicate_of: SelectedTopic | None = None
        duplicate_overlap = 0.0

        for existing in selected:
            is_duplicate, overlap = represents_same_topic(
                candidate,
                existing,
            )

            if is_duplicate:
                duplicate_of = existing
                duplicate_overlap = overlap
                break

        if duplicate_of is not None:
            print()
            print("[INFO] Tema repetido removido")
            print(
                "       Removido: "
                f"{candidate.ranked_item.item.title}"
            )
            print(
                "       Mantido: "
                f"{duplicate_of.ranked_item.item.title}"
            )
            print(
                "       Tokens comuns: "
                f"{sorted(candidate.topic_tokens & duplicate_of.topic_tokens)}"
            )
            print(
                f"       Sobreposição: {duplicate_overlap:.2f}"
            )
            continue

        selected.append(candidate)

        if len(selected) >= limit:
            break

    return selected


def main() -> None:
    news = collect_all_news()
    ranked = score_news(news)
    selected = select_unique_topics(ranked, limit=10)

    print()
    print("=" * 78)
    print("TOP 10 TEMAS ÚNICOS PARA YOUTUBE SHORTS")
    print("=" * 78)

    for position, topic in enumerate(selected, start=1):
        result = topic.ranked_item

        print()
        print(
            f"{position}. SCORE={result.score} "
            f"[{result.item.source}] {result.item.title}"
        )

        print(
            "   Tema: "
            f"{', '.join(sorted(topic.topic_tokens))}"
        )

        for reason in result.reasons:
            print(f"   - {reason}")

        print(f"   Link: {result.item.link}")


if __name__ == "__main__":
    main()
