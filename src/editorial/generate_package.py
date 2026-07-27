from __future__ import annotations

import json
import logging
from pathlib import Path

from editorial.parser import parse_editorial_package_dict
from editorial.prompt_builder import build_prompt
from openai_client import call_openai


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
            "digest.json sem lista topics"
        )

    if not topics:
        raise ValueError(
            "Nenhum tema encontrado no digest"
        )

    return topics[:5]


def build_editorial_request(
    topics: list[dict],
) -> tuple[str, str]:

    return build_prompt(
        topics
    )


def parse_openai_response(
    response,
) -> dict:

    if isinstance(
        response,
        dict,
    ):
        return response

    if isinstance(
        response,
        str,
    ):
        return json.loads(
            response
        )

    raise TypeError(
        "Resposta OpenAI com formato inválido"
    )


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
        "Temas enviados para Editorial AI: %s",
        len(topics),
    )


    system_prompt, user_prompt = (
        build_editorial_request(
            topics
        )
    )


    logger.info(
        "A chamar GPT-5.5 Editorial."
    )


    response = call_openai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


    package = parse_openai_response(
        response
    )


    logger.info(
        "A validar contrato Editorial Package."
    )


    validated = parse_editorial_package_dict(
        package
    )


    save_package(
        validated.to_dict()
    )


    logger.info(
        "Editorial Package criado com sucesso."
    )


    print("=" * 70)
    print("EDITORIAL PACKAGE GENERATED")
    print("=" * 70)
    print(
        f"Ficheiro: {OUTPUT_FILE}"
    )

    try:
        print(
            f"Temas: {len(validated.topics)}"
        )
    except AttributeError:
        pass


    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
