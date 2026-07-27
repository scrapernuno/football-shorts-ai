from __future__ import annotations

import json
import logging
from pathlib import Path

from editorial.parser import parse_editorial_package_dict
from editorial.prompt_builder import build_prompt
from openai_client import generate_json


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(
    "football_shorts.generate_package"
)


ROOT = Path(__file__).resolve().parents[2]

DIGEST_FILE = ROOT / "output" / "digest.json"

OUTPUT_FILE = (
    ROOT
    / "output"
    / "editorial_package.json"
)


CHANNEL = "@dinamegaz2014"

TIMEZONE = "Europe/Lisbon"

SCHEMA_VERSION = "2.0"


def load_digest() -> dict:

    return json.loads(
        DIGEST_FILE.read_text(
            encoding="utf-8"
        )
    )


def extract_topics(
    digest: dict,
) -> list[dict]:

    topics = digest.get(
        "topics",
    )

    if not isinstance(
        topics,
        list,
    ):
        raise ValueError(
            "digest sem topics"
        )

    return topics[:5]


def normalize_topics(
    topics: list[dict],
) -> list[dict]:

    result = []

    for topic in topics:

        item = dict(topic)

        if "score" not in item:

            item["score"] = item.get(
                "viral_score",
                0,
            )

        result.append(
            item
        )

    return result


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


    topics = normalized.get(
        "topics",
        [],
    )


    if topics:

        first = topics[0]


        topic_id = (
            first.get(
                "id"
            )
            or
            first.get(
                "slug"
            )
            or
            first.get(
                "title",
                "top-topic",
            )
            .lower()
            .replace(
                " ",
                "-",
            )
        )


        normalized.setdefault(
            "top_topic_id",
            topic_id,
        )


    return normalized


def save_package(
    package: dict,
):

    OUTPUT_FILE.write_text(
        json.dumps(
            package,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main():

    logger.info(
        "A carregar digest."
    )

    digest = load_digest()


    topics = normalize_topics(
        extract_topics(
            digest
        )
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
        OUTPUT_FILE
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
