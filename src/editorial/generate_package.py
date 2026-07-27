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

OUTPUT_FILE = ROOT / "output" / "editorial_package.json"


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
        []
    )

    if not topics:
        raise ValueError(
            "Sem temas"
        )

    return topics[:5]


def normalize_topics(
    topics: list[dict],
) -> list[dict]:

    result = []

    for topic in topics:

        item = dict(topic)

        item.setdefault(
            "score",
            item.get(
                "viral_score",
                0,
            )
        )

        result.append(item)

    return result


def scored_options(
    values: list[str],
) -> list[dict]:

    return [

        {
            "text": value,
            "score": 90 - (index * 5),
        }

        for index, value in enumerate(values)

    ]


def normalize_storyboard() -> dict:

    return {

        "duration_seconds": 45,

        "scenes": [

            {
                "start_second": 0,
                "end_second": 3,
                "voice": "Hook inicial forte",
                "caption": "Atenção máxima nos primeiros segundos",
                "visual": "Vídeo principal do tema",
                "transition": "Fast cut",
            },

            {
                "start_second": 3,
                "end_second": 35,
                "voice": "Desenvolvimento da história",
                "caption": "Informação principal",
                "visual": "Clips relacionados",
                "transition": "Dynamic",
            },

            {
                "start_second": 35,
                "end_second": 45,
                "voice": "Conclusão e chamada à ação",
                "caption": "Comenta a tua opinião",
                "visual": "Momento final forte",
                "transition": "Zoom out",
            },

        ],

    }


def normalize_topic_package(
    topics: list[dict],
) -> list[dict]:

    result = []


    for index, topic in enumerate(
        topics,
        start=1,
    ):

        title = topic.get(
            "title",
            f"topic-{index}",
        )


        viral_score = topic.get(
            "viral_score",
            0,
        )


        topic_id = (
            title.lower()
            .replace(
                " ",
                "-"
            )
        )


        result.append(

            {

            "topic_id": topic_id,


            "source": {

                "title": topic.get(
                    "source_title",
                    title,
                ),

                "name": topic.get(
                    "source_name",
                    "Unknown",
                ),

                "url": topic.get(
                    "source_url",
                    "",
                ),

                "confirmation_status": "CONFIRMED",

                "published": "YES",

            },


            "ranking": {

                "viral_probability": viral_score,

                "breaking": (
                    topic.get(
                        "urgency"
                    )
                    ==
                    "HIGH"
                ),

                "competition": "HIGH",

                "priority": viral_score,

                "publish_today": True,

                "reason": topic.get(
                    "reason",
                    "",
                ),

            },


            "editorial": {

                "primary_title": title,

                "primary_hook": topic.get(
                    "hook",
                    "",
                ),

                "alternative_titles": scored_options(
                    [
                        title,
                        f"{title} - A história que ninguém esperava",
                        "O momento que está a incendiar o futebol",
                    ]
                ),

                "alternative_hooks": scored_options(
                    [
                        topic.get(
                            "hook",
                            ""
                        ),
                        "Espera até veres o que aconteceu...",
                        "O futebol acabou de mudar tudo...",
                    ]
                ),

                "description": topic.get(
                    "reason",
                    "",
                ),

                "script": topic.get(
                    "script",
                    "",
                ),

                "hashtags": topic.get(
                    "hashtags",
                    [],
                ),

                "pinned_comment": (
                    "Qual é a tua opinião?"
                ),

                "call_to_action": (
                    "Segue o canal para mais histórias."
                ),

            },


            "storyboard": normalize_storyboard(),


            "publishing": {

                "urgency": topic.get(
                    "urgency",
                    "MEDIUM",
                ),

                "best_publish_time": "18:30",

                "recommended_window": "18:00-20:00",

            },


            "analytics": {

                "predicted_ctr_percent": 0,

                "predicted_retention_percent": 0,

            },


            "checklist": [],


            }

        )


    return result


def normalize_editorial_package(
    package: dict,
) -> dict:

    result = dict(package)


    result.setdefault(
        "schema_version",
        SCHEMA_VERSION,
    )

    result.setdefault(
        "channel",
        CHANNEL,
    )

    result.setdefault(
        "timezone",
        TIMEZONE,
    )


    result["topics"] = normalize_topic_package(
        result.get(
            "topics",
            [],
        )
    )


    if result["topics"]:

        result.setdefault(
            "top_topic_id",
            result["topics"][0]["topic_id"],
        )


    return result


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


def main() -> int:


    digest = load_digest()


    topics = normalize_topics(
        extract_topics(
            digest
        )
    )


    system_prompt, user_prompt = build_prompt(
        topics
    )


    response = generate_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )


    response = normalize_editorial_package(
        response
    )


    validated = parse_editorial_package_dict(
        response
    )


    save_package(
        validated.to_dict()
    )


    print(
        "EDITORIAL PACKAGE GENERATED"
    )


    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
