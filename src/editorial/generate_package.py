from __future__ import annotations

import json
import logging
from pathlib import Path

from editorial.parser import parse_editorial_package_dict
from editorial.prompt_builder import build_prompt
from openai_client import generate_json


logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(
    "football_shorts.generate_package"
)


ROOT = Path(__file__).resolve().parents[2]


DIGEST_FILE = (
    ROOT
    / "output"
    / "digest.json"
)


OUTPUT_FILE = (
    ROOT
    / "output"
    / "editorial_package.json"
)


CHANNEL = "@dinamegaz2014"

TIMEZONE = "Europe/Lisbon"

SCHEMA_VERSION = "2.0"


def load_digest() -> dict:

    if not DIGEST_FILE.exists():

        raise FileNotFoundError(
            f"Digest inexistente: {DIGEST_FILE}"
        )

    return json.loads(
        DIGEST_FILE.read_text(
            encoding="utf-8"
        )
    )


def extract_topics(
    digest: dict,
) -> list[dict]:

    topics = digest.get(
        "topics"
    )

    if not isinstance(
        topics,
        list,
    ):

        raise ValueError(
            "digest.json sem topics"
        )


    return topics[:5]


def normalize_topics(
    topics: list[dict],
) -> list[dict]:

    normalized = []

    for topic in topics:

        item = dict(topic)

        if "score" not in item:

            item["score"] = item.get(
                "viral_score",
                0,
            )

        normalized.append(
            item
        )


    return normalized


def normalize_topic_package(
    topics: list[dict],
) -> list[dict]:

    normalized = []


    for index, topic in enumerate(
        topics,
        start=1,
    ):

        item = dict(topic)


        title = item.get(
            "title",
            f"topic-{index}",
        )


        topic_id = (

            item.get(
                "topic_id"
            )

            or

            item.get(
                "id"
            )

            or

            title.lower()
            .replace(
                " ",
                "-",
            )

        )


        item.setdefault(
            "topic_id",
            topic_id,
        )


        item.setdefault(
            "source",
            {
                "title": item.get(
                    "source_title",
                    title,
                ),
                "name": item.get(
                    "source_name",
                    "Unknown",
                ),
                "url": item.get(
                    "source_url",
                    "",
                ),
            },
        )


        item.setdefault(
            "ranking",
            {
                "viral_probability": item.get(
                    "viral_score",
                    0,
                ),
            },
        )


        item.setdefault(
            "editorial",
            {
                "primary_title": title,
                "primary_hook": item.get(
                    "hook",
                    "",
                ),
            },
        )


        item.setdefault(
            "storyboard",
            [],
        )


        item.setdefault(
            "publishing",
            {
                "urgency": item.get(
                    "urgency",
                    "MEDIUM",
                ),
                "best_publish_time": "18:30",
                "recommended_window": "18:00-20:00",
            },
        )


        item.setdefault(
            "analytics",
            {
                "predicted_ctr_percent": 0,
                "predicted_retention_percent": 0,
            },
        )


        item.setdefault(
            "checklist",
            [],
        )


        normalized.append(
            item
        )


    return normalized


def normalize_editorial_package(
    package: dict,
) -> dict:

    normalized = dict(package)


    normalized.setdefault(
        "schema_version",
        SCHEMA_VERSION,
    )


    normalized.setdefault(
        "channel",
        CHANNEL,
    )


    normalized.setdefault(
        "timezone",
        TIMEZONE,
    )


    topics = normalize_topic_package(
        normalized.get(
            "topics",
            [],
        )
    )


    normalized["topics"] = topics


    if topics:

        first_topic = topics[0]


        normalized.setdefault(
            "top_topic_id",
            first_topic[
                "topic_id"
            ],
        )


    return normalized


def save_package(
    package: dict,
) -> None:


    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    OUTPUT_FILE.write_text(
        json.dumps(
            package,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:


    logger.info(
        "A carregar digest."
    )


    digest = load_digest()


    topics = extract_topics(
        digest
    )


    topics = normalize_topics(
        topics
    )


    logger.info(
        "Temas enviados para Editorial AI: %s",
        len(topics),
    )


    logger.info(
        "A construir prompt editorial."
    )


    system_prompt, user_prompt = build_prompt(
        topics
    )


    logger.info(
        "A chamar OpenAI generate_json."
    )


    response = generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


    logger.info(
        "Normalizar Editorial Package."
    )


    response = normalize_editorial_package(
        response
    )


    logger.info(
        "Validar Editorial Package."
    )


    validated = parse_editorial_package_dict(
        response
    )


    save_package(
        validated.to_dict()
    )


    print("=" * 70)
    print("EDITORIAL PACKAGE GENERATED")
    print("=" * 70)
    print(
        f"Output: {OUTPUT_FILE}"
    )


    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
