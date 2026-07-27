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
    ROOT /
    "output" /
    "digest.json"
)

OUTPUT_FILE = (
    ROOT /
    "output" /
    "editorial_package.json"
)


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
        "A validar Editorial Package."
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
