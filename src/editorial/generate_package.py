from __future__ import annotations

import json
import logging
from pathlib import Path

from editorial.parser import parse_editorial_package_dict
from editorial.prompt_builder import build_editorial_prompt
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


SYSTEM_PROMPT = """
És o editor-chefe de um canal internacional de YouTube Shorts de futebol.

Não resumas notícias.

Transforma os melhores temas em pacotes editoriais prontos para produção.

Devolve exclusivamente JSON válido.

Nunca uses markdown.

Nunca uses blocos de código.

Cada tema precisa de:

- ranking
- fonte
- títulos alternativos
- hooks
- guião 45-60 segundos
- storyboard com cenas
- sugestões de vídeos
- thumbnail
- hashtags
- comentário fixado
- previsão de CTR
- previsão de retenção
- hora recomendada de publicação

O objetivo é maximizar retenção e comentários.
"""


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

    if len(topics) == 0:
        raise ValueError(
            "Nenhum tema encontrado"
        )

    return topics[:5]


def build_request(
    topics: list[dict],
) -> str:

    return build_editorial_prompt(
        topics
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
        "Temas enviados para editorial AI: %s",
        len(topics),
    )

    user_prompt = build_request(
        topics
    )

    logger.info(
        "A chamar GPT-5.5 editorial."
    )

    response = call_openai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    if isinstance(
        response,
        str,
    ):
        package = json.loads(
            response
        )
    else:
        package = response


    logger.info(
        "A validar contrato editorial."
    )

    validated = parse_editorial_package_dict(
        package
    )


    save_package(
        validated.to_dict()
    )


    logger.info(
        "Editorial package criado."
    )

    print("=" * 70)
    print("EDITORIAL PACKAGE GENERATED")
    print("=" * 70)
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        f"Temas: {len(validated.topics)}"
    )
    print(
        f"Top topic: {validated.top_topic_id}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
