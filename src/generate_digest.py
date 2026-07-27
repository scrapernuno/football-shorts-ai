from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_prompt import SYSTEM_PROMPT, build_user_prompt
from collect_news import collect_all_news
from openai_client import (
    OpenAIClientError,
    configure_logging,
    generate_json,
)
from score_news import score_news
from select_topics import select_unique_topics


LOGGER = logging.getLogger("football_shorts.generate_digest")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output"
DIGEST_FILE = OUTPUT_DIRECTORY / "digest.json"
PROMPT_FILE = OUTPUT_DIRECTORY / "last_prompt.txt"

TOPIC_LIMIT = 10


class DigestGenerationError(RuntimeError):
    """Erro na construção ou gravação do digest."""


def build_source_snapshot(
    selected_topics: list[Any],
) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []

    for position, selected_topic in enumerate(
        selected_topics,
        start=1,
    ):
        ranked_item = selected_topic.ranked_item
        item = ranked_item.item

        snapshot.append(
            {
                "position": position,
                "source_name": item.source,
                "source_title": item.title,
                "source_url": item.link,
                "published": item.published,
                "internal_score": ranked_item.score,
                "score_reasons": list(ranked_item.reasons),
                "topic_tokens": sorted(
                    selected_topic.topic_tokens
                ),
            }
        )

    return snapshot


def enrich_digest(
    digest: dict[str, Any],
    *,
    selected_topics: list[Any],
) -> dict[str, Any]:
    enriched = dict(digest)

    enriched["pipeline"] = {
        "generated_by": "football-shorts-ai",
        "model": "gpt-5.5",
        "collector_count": len(selected_topics),
        "selected_for_ai": len(selected_topics),
    }

    enriched["source_snapshot"] = build_source_snapshot(
        selected_topics
    )

    return enriched


def validate_source_traceability(
    digest: dict[str, Any],
    selected_topics: list[Any],
) -> None:
    allowed_urls = {
        topic.ranked_item.item.link
        for topic in selected_topics
    }

    topics = digest.get("topics")

    if not isinstance(topics, list):
        raise DigestGenerationError(
            "O digest não contém uma lista válida de temas."
        )

    for index, topic in enumerate(topics, start=1):
        if not isinstance(topic, dict):
            raise DigestGenerationError(
                f"O tema {index} não é um objeto JSON."
            )

        source_url = topic.get("source_url")

        if source_url not in allowed_urls:
            raise DigestGenerationError(
                "O GPT devolveu uma fonte que não estava entre "
                f"as notícias fornecidas. Tema={index}; "
                f"source_url={source_url!r}"
            )


def save_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp"
    )

    temporary_path.write_text(
        content,
        encoding="utf-8",
    )

    temporary_path.replace(path)


def save_json_file(
    path: Path,
    payload: dict[str, Any],
) -> None:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    )

    save_text_file(
        path,
        serialized + "\n",
    )


def print_digest_summary(
    digest: dict[str, Any],
) -> None:
    topics = digest.get("topics", [])

    print()
    print("=" * 78)
    print("DIGEST GERADO COM SUCESSO")
    print("=" * 78)
    print(f"Ficheiro: {DIGEST_FILE}")
    print(f"Temas: {len(topics)}")
    print()

    for position, topic in enumerate(topics, start=1):
        print(
            f"{position}. "
            f"[{topic.get('urgency', 'UNKNOWN')}] "
            f"VIRAL={topic.get('viral_score', '?')} — "
            f"{topic.get('title', 'Sem título')}"
        )

        print(
            f"   Hook: "
            f"{topic.get('hook', 'Sem hook')}"
        )

        print(
            f"   Fonte: "
            f"{topic.get('source_name', 'Sem fonte')}"
        )

        print(
            f"   Link: "
            f"{topic.get('source_url', 'Sem link')}"
        )

        print()


def generate_digest() -> dict[str, Any]:
    LOGGER.info("A iniciar recolha de notícias.")

    news = collect_all_news()

    if not news:
        raise DigestGenerationError(
            "Nenhuma notícia foi recolhida."
        )

    LOGGER.info(
        "Notícias recolhidas: %s",
        len(news),
    )

    ranked = score_news(news)

    if not ranked:
        raise DigestGenerationError(
            "Nenhuma notícia foi classificada."
        )

    selected_topics = select_unique_topics(
        ranked,
        limit=TOPIC_LIMIT,
    )

    if len(selected_topics) < 5:
        raise DigestGenerationError(
            "Foram selecionados menos de cinco temas. "
            f"Total selecionado: {len(selected_topics)}"
        )

    LOGGER.info(
        "Temas únicos enviados à IA: %s",
        len(selected_topics),
    )

    user_prompt = build_user_prompt(
        selected_topics
    )

    prompt_snapshot = (
        "SYSTEM PROMPT\n"
        + "=" * 80
        + "\n"
        + SYSTEM_PROMPT
        + "\n\n"
        + "USER PROMPT\n"
        + "=" * 80
        + "\n"
        + user_prompt
        + "\n"
    )

    save_text_file(
        PROMPT_FILE,
        prompt_snapshot,
    )

    LOGGER.info(
        "Snapshot do prompt gravado em %s",
        PROMPT_FILE,
    )

    digest = generate_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    validate_source_traceability(
        digest,
        selected_topics,
    )

    generated_at = digest.get(
        "generated_at",
        "",
    )

    if not generated_at:
        digest["generated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

    enriched_digest = enrich_digest(
        digest,
        selected_topics=selected_topics,
    )

    save_json_file(
        DIGEST_FILE,
        enriched_digest,
    )

    return enriched_digest


def main() -> int:
    configure_logging()

    try:
        digest = generate_digest()
    except OpenAIClientError as exc:
        LOGGER.exception(
            "Falha na integração com a OpenAI: %s",
            exc,
        )
        print(
            f"ERRO_OPENAI: {exc}",
            file=sys.stderr,
        )
        return 2
    except DigestGenerationError as exc:
        LOGGER.exception(
            "Falha na geração do digest: %s",
            exc,
        )
        print(
            f"ERRO_DIGEST: {exc}",
            file=sys.stderr,
        )
        return 3
    except Exception as exc:
        LOGGER.exception(
            "Erro inesperado: %s",
            exc,
        )
        print(
            f"ERRO_INESPERADO: {exc}",
            file=sys.stderr,
        )
        return 1

    print_digest_summary(digest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
