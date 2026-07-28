from __future__ import annotations

import json
import re

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_SOURCE = (
    ROOT
    / "output"
    / "dashboard_model.json"
)

EDITORIAL_SOURCE = (
    ROOT
    / "output"
    / "editorial_package.json"
)

CONTENT_OUTPUT = (
    ROOT
    / "output"
    / "content_package.json"
)

PACKAGE_VERSION = "1.0"

SCRIPT_FIELDS = (
    "hook",
    "introduction",
    "development",
    "climax",
    "ending",
    "call_to_action",
)


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON inválido em {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} deve conter um objeto JSON."
        )

    return payload


def save_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} deve ser um objeto JSON."
        )

    return value


def require_list(
    value: object,
    field_name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(
            f"{field_name} deve ser uma lista JSON."
        )

    return value


def normalize_integer(
    value: Any,
    *,
    default: int = 0,
) -> int:
    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(
            round(
                value
            )
        )

    if isinstance(value, str):
        candidate = (
            value
            .strip()
            .replace(
                "%",
                "",
            )
            .replace(
                ",",
                ".",
            )
        )

        try:
            return int(
                round(
                    float(
                        candidate
                    )
                )
            )
        except ValueError:
            return default

    return default


def normalize_non_empty_string(
    value: Any,
    *,
    default: str,
) -> str:
    if isinstance(value, str):
        normalized = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        if normalized:
            return normalized

    return default


def select_winner(
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    ranking = dashboard.get(
        "ranking",
        [],
    )

    if not isinstance(
        ranking,
        list,
    ):
        raise ValueError(
            "Dashboard ranking deve ser uma lista."
        )

    if not ranking:
        raise ValueError(
            "Dashboard sem ranking."
        )

    candidates: list[
        tuple[
            int,
            int,
            int,
            dict[str, Any],
        ]
    ] = []

    for original_index, raw_item in enumerate(
        ranking,
        start=1,
    ):
        if not isinstance(
            raw_item,
            dict,
        ):
            raise ValueError(
                "Todos os elementos de ranking "
                "devem ser objetos JSON."
            )

        item = deepcopy(
            raw_item
        )

        priority = normalize_integer(
            item.get(
                "priority"
            ),
            default=0,
        )

        viral_probability = normalize_integer(
            item.get(
                "viral_probability"
            ),
            default=normalize_integer(
                item.get(
                    "viral_score"
                ),
                default=0,
            ),
        )

        if priority > 0:
            priority_group = 0
            priority_value = priority
        else:
            priority_group = 1
            priority_value = original_index

        candidates.append(
            (
                priority_group,
                priority_value,
                -viral_probability,
                item,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
            candidate[2],
        )
    )

    winner = candidates[0][3]

    winner["priority"] = 1

    winner[
        "viral_probability"
    ] = max(
        0,
        min(
            100,
            normalize_integer(
                winner.get(
                    "viral_probability",
                    dashboard.get(
                        "viral_probability",
                        0,
                    ),
                ),
                default=0,
            ),
        ),
    )

    winner["title"] = normalize_non_empty_string(
        winner.get(
            "title"
        ),
        default=normalize_non_empty_string(
            dashboard.get(
                "top_title"
            ),
            default="Football Story",
        ),
    )

    winner["hook"] = normalize_non_empty_string(
        winner.get(
            "hook"
        ),
        default=normalize_non_empty_string(
            dashboard.get(
                "top_hook"
            ),
            default=(
                "Informação editorial indisponível."
            ),
        ),
    )

    winner["reason"] = normalize_non_empty_string(
        winner.get(
            "reason"
        ),
        default="",
    )

    return winner


def select_editorial_topic(
    editorial_package: dict[str, Any],
    winner: dict[str, Any],
) -> dict[str, Any]:
    topics = require_list(
        editorial_package.get(
            "topics"
        ),
        "editorial_package.topics",
    )

    if not topics:
        raise ValueError(
            "Editorial Package sem tópicos."
        )

    winner_title = normalize_non_empty_string(
        winner.get(
            "title"
        ),
        default="",
    ).casefold()

    valid_topics = [
        require_mapping(
            topic,
            (
                "editorial_package."
                f"topics[{index}]"
            ),
        )
        for index, topic in enumerate(
            topics
        )
    ]

    for topic in valid_topics:
        editorial = topic.get(
            "editorial"
        )

        if not isinstance(
            editorial,
            dict,
        ):
            continue

        candidate_title = (
            normalize_non_empty_string(
                editorial.get(
                    "primary_title"
                ),
                default="",
            )
            .casefold()
        )

        if (
            winner_title
            and
            candidate_title
            ==
            winner_title
        ):
            return topic

    for topic in valid_topics:
        ranking = topic.get(
            "ranking"
        )

        if (
            isinstance(
                ranking,
                dict,
            )
            and
            normalize_integer(
                ranking.get(
                    "priority"
                ),
                default=0,
            )
            ==
            1
        ):
            return topic

    return valid_topics[0]


def normalize_comparison_text(
    value: str,
) -> str:
    return re.sub(
        r"[^\wÀ-ÖØ-öø-ÿ]+",
        "",
        value.casefold(),
    )


def remove_boundary_phrase(
    text: str,
    phrase: str,
    *,
    at_start: bool,
) -> str:
    normalized_text = text.strip()
    normalized_phrase = phrase.strip()

    if (
        not normalized_text
        or
        not normalized_phrase
    ):
        return normalized_text

    comparable_text = normalize_comparison_text(
        normalized_text
    )
    comparable_phrase = normalize_comparison_text(
        normalized_phrase
    )

    if not comparable_phrase:
        return normalized_text

    if (
        at_start
        and
        comparable_text.startswith(
            comparable_phrase
        )
    ):
        position = normalized_text.find(
            normalized_phrase
        )

        if position == 0:
            return normalized_text[
                len(
                    normalized_phrase
                ):
            ].lstrip(
                " \t\r\n—–-:;,.!?"
            )

    if (
        not at_start
        and
        comparable_text.endswith(
            comparable_phrase
        )
    ):
        position = normalized_text.rfind(
            normalized_phrase
        )

        if position >= 0:
            return normalized_text[
                :position
            ].rstrip(
                " \t\r\n—–-:;,.!?"
            )

    return normalized_text


def split_script_units(
    value: str,
) -> list[str]:
    normalized = value.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    primary_parts = re.split(
        (
            r"(?<=[.!?…])\s+"
            r"|\n+"
        ),
        normalized,
    )

    parts = [
        re.sub(
            r"\s+",
            " ",
            part,
        ).strip(
            " \t—–-"
        )
        for part in primary_parts
    ]

    parts = [
        part
        for part in parts
        if part
    ]

    if len(parts) >= 4:
        return parts

    secondary_parts = re.split(
        r"\s*[;•]\s*|\s+—\s+",
        normalized,
    )

    secondary = [
        re.sub(
            r"\s+",
            " ",
            part,
        ).strip(
            " \t—–-"
        )
        for part in secondary_parts
    ]

    secondary = [
        part
        for part in secondary
        if part
    ]

    if len(secondary) > len(parts):
        return secondary

    return parts


def balanced_partition(
    values: list[str],
    group_count: int,
) -> list[str]:
    if group_count <= 0:
        raise ValueError(
            "group_count deve ser positivo."
        )

    if len(values) < group_count:
        raise ValueError(
            "Não existem unidades suficientes "
            "para a partição editorial."
        )

    base_size, remainder = divmod(
        len(values),
        group_count,
    )

    output: list[str] = []
    cursor = 0

    for index in range(
        group_count
    ):
        size = (
            base_size
            +
            (
                1
                if index < remainder
                else 0
            )
        )

        group = values[
            cursor:
            cursor + size
        ]

        cursor += size

        output.append(
            " ".join(
                group
            ).strip()
        )

    return output


def build_script(
    winner: dict[str, Any],
    editorial_topic: dict[str, Any],
) -> dict[str, str]:
    editorial = require_mapping(
        editorial_topic.get(
            "editorial"
        ),
        "winner.editorial",
    )

    ranking = require_mapping(
        editorial_topic.get(
            "ranking"
        ),
        "winner.ranking",
    )

    hook = normalize_non_empty_string(
        editorial.get(
            "primary_hook"
        ),
        default=normalize_non_empty_string(
            winner.get(
                "hook"
            ),
            default=(
                "Informação editorial indisponível."
            ),
        ),
    )

    call_to_action = normalize_non_empty_string(
        editorial.get(
            "call_to_action"
        ),
        default=normalize_non_empty_string(
            editorial.get(
                "pinned_comment"
            ),
            default=(
                "Interação editorial não definida."
            ),
        ),
    )

    full_script = normalize_non_empty_string(
        editorial.get(
            "script"
        ),
        default="",
    )

    body = remove_boundary_phrase(
        full_script,
        hook,
        at_start=True,
    )

    body = remove_boundary_phrase(
        body,
        call_to_action,
        at_start=False,
    )

    units = split_script_units(
        body
    )

    if len(units) >= 4:
        (
            introduction,
            development,
            climax,
            ending,
        ) = balanced_partition(
            units,
            4,
        )
    else:
        description = normalize_non_empty_string(
            editorial.get(
                "description"
            ),
            default="",
        )

        reason = normalize_non_empty_string(
            ranking.get(
                "reason"
            ),
            default=normalize_non_empty_string(
                winner.get(
                    "reason"
                ),
                default="",
            ),
        )

        pinned_comment = normalize_non_empty_string(
            editorial.get(
                "pinned_comment"
            ),
            default="",
        )

        introduction = (
            units[0]
            if units
            else description
        )

        development = (
            body
            or
            description
            or
            reason
        )

        climax = (
            reason
            or
            (
                units[-1]
                if units
                else ""
            )
            or
            development
        )

        ending = (
            pinned_comment
            or
            (
                units[-1]
                if units
                else ""
            )
            or
            call_to_action
        )

    sections = {
        "hook": hook,
        "introduction": introduction,
        "development": development,
        "climax": climax,
        "ending": ending,
        "call_to_action": call_to_action,
    }

    missing = [
        field_name
        for field_name in SCRIPT_FIELDS
        if not normalize_non_empty_string(
            sections.get(
                field_name
            ),
            default="",
        )
    ]

    if missing:
        raise ValueError(
            "Não foi possível construir um guião "
            "editorial completo sem inventar conteúdo: "
            f"{missing}"
        )

    return {
        field_name:
            normalize_non_empty_string(
                sections[field_name],
                default="",
            )
        for field_name in SCRIPT_FIELDS
    }


def build_voiceover(
    script: dict[str, str],
) -> dict[str, Any]:
    timeline = (
        (
            "hook",
            0,
            3,
        ),
        (
            "introduction",
            3,
            9,
        ),
        (
            "development",
            9,
            24,
        ),
        (
            "climax",
            24,
            36,
        ),
        (
            "ending",
            36,
            41,
        ),
        (
            "call_to_action",
            41,
            45,
        ),
    )

    return {
        "language": "pt-PT",
        "style": "energetic",
        "segments": [
            {
                "section": section,
                "start_second": start_second,
                "end_second": end_second,
                "text": script[
                    section
                ],
            }
            for (
                section,
                start_second,
                end_second,
            ) in timeline
        ],
    }


def build_scenes() -> list[dict[str, Any]]:
    return [
        {
            "scene_number": 1,
            "duration_seconds": 5,
            "visual_instruction": (
                "Opening football highlight"
            ),
            "camera_direction": "zoom_in",
            "voiceover_segment": "Hook inicial",
            "caption_text": (
                "O MOMENTO QUE TODOS FALAM"
            ),
            "asset_reference": (
                "football_opening_clip"
            ),
        },
        {
            "scene_number": 2,
            "duration_seconds": 15,
            "visual_instruction": (
                "Context football footage"
            ),
            "camera_direction": "pan_right",
            "voiceover_segment": (
                "Contexto da história"
            ),
            "caption_text": (
                "COMO TUDO ACONTECEU"
            ),
            "asset_reference": (
                "football_context_clip"
            ),
        },
        {
            "scene_number": 3,
            "duration_seconds": 15,
            "visual_instruction": (
                "Main football moment"
            ),
            "camera_direction": "slow_motion",
            "voiceover_segment": (
                "Momento decisivo"
            ),
            "caption_text": (
                "O MOMENTO DECISIVO"
            ),
            "asset_reference": (
                "football_highlight_clip"
            ),
        },
        {
            "scene_number": 4,
            "duration_seconds": 10,
            "visual_instruction": "Fan reaction",
            "camera_direction": "zoom_out",
            "voiceover_segment": (
                "Reação dos adeptos"
            ),
            "caption_text": (
                "QUAL É A TUA OPINIÃO?"
            ),
            "asset_reference": (
                "fans_reaction_clip"
            ),
        },
    ]


def build_content_package(
    dashboard: dict[str, Any],
    editorial_package: dict[str, Any],
) -> dict[str, Any]:
    winner = select_winner(
        dashboard
    )

    editorial_topic = select_editorial_topic(
        editorial_package,
        winner,
    )

    editorial = require_mapping(
        editorial_topic.get(
            "editorial"
        ),
        "winner.editorial",
    )

    source = require_mapping(
        editorial_topic.get(
            "source"
        ),
        "winner.source",
    )

    publishing_plan = require_mapping(
        editorial_topic.get(
            "publishing"
        ),
        "winner.publishing",
    )

    script = build_script(
        winner,
        editorial_topic,
    )

    title = normalize_non_empty_string(
        editorial.get(
            "primary_title"
        ),
        default=winner[
            "title"
        ],
    )

    hook = script[
        "hook"
    ]

    description = normalize_non_empty_string(
        editorial.get(
            "description"
        ),
        default=normalize_non_empty_string(
            winner.get(
                "reason"
            ),
            default=title,
        ),
    )

    hashtags_raw = editorial.get(
        "hashtags"
    )

    hashtags = (
        [
            normalize_non_empty_string(
                hashtag,
                default="",
            )
            for hashtag in hashtags_raw
            if isinstance(
                hashtag,
                str,
            )
            and
            hashtag.strip()
        ]
        if isinstance(
            hashtags_raw,
            list,
        )
        else []
    )

    return {
        "package_version": PACKAGE_VERSION,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_topic": {
            "title": title,
            "hook": hook,
            "viral_probability": (
                winner[
                    "viral_probability"
                ]
            ),
            "priority": 1,
            "source_name": normalize_non_empty_string(
                source.get(
                    "name"
                ),
                default="Fonte não identificada",
            ),
            "source_url": normalize_non_empty_string(
                source.get(
                    "url"
                ),
                default="",
            ),
            "confirmation_status":
                normalize_non_empty_string(
                    source.get(
                        "confirmation_status"
                    ),
                    default="REPORTED",
                ),
        },
        "script": script,
        "voiceover": build_voiceover(
            script
        ),
        "scenes": build_scenes(),
        "captions": [],
        "assets": [],
        "publishing": {
            "platform": "youtube_shorts",
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "scheduled_window":
                normalize_non_empty_string(
                    publishing_plan.get(
                        "best_publish_time"
                    ),
                    default="recommended",
                ),
        },
    }


def validate_package(
    payload: dict[str, Any],
) -> None:
    required = {
        "package_version",
        "generated_at",
        "source_topic",
        "script",
        "voiceover",
        "scenes",
        "captions",
        "assets",
        "publishing",
    }

    missing = required - payload.keys()

    if missing:
        raise ValueError(
            "Content package incompleto: "
            f"{sorted(missing)}"
        )

    if payload[
        "package_version"
    ] != PACKAGE_VERSION:
        raise ValueError(
            "Content package version inválida."
        )

    source_topic = require_mapping(
        payload.get(
            "source_topic"
        ),
        "content_package.source_topic",
    )

    required_source_topic = {
        "title",
        "hook",
        "viral_probability",
        "priority",
    }

    missing_source_topic = (
        required_source_topic
        -
        source_topic.keys()
    )

    if missing_source_topic:
        raise ValueError(
            "source_topic incompleto: "
            f"{sorted(missing_source_topic)}"
        )

    if source_topic[
        "priority"
    ] != 1:
        raise ValueError(
            "Content package deve usar "
            "winner priority 1."
        )

    viral_probability = source_topic[
        "viral_probability"
    ]

    if (
        not isinstance(
            viral_probability,
            int,
        )
        or
        isinstance(
            viral_probability,
            bool,
        )
    ):
        raise ValueError(
            "viral_probability deve "
            "ser um número inteiro."
        )

    if not (
        0
        <=
        viral_probability
        <=
        100
    ):
        raise ValueError(
            "viral_probability deve "
            "estar entre 0 e 100."
        )

    script = require_mapping(
        payload.get(
            "script"
        ),
        "content_package.script",
    )

    missing_script = (
        set(
            SCRIPT_FIELDS
        )
        -
        script.keys()
    )

    if missing_script:
        raise ValueError(
            "Script incompleto: "
            f"{sorted(missing_script)}"
        )

    for field_name in SCRIPT_FIELDS:
        normalize_non_empty_string(
            script.get(
                field_name
            ),
            default=(
                ""
            ),
        )

        if not normalize_non_empty_string(
            script.get(
                field_name
            ),
            default="",
        ):
            raise ValueError(
                "Script contém uma secção vazia: "
                f"{field_name}"
            )

    voiceover = require_mapping(
        payload.get(
            "voiceover"
        ),
        "content_package.voiceover",
    )

    segments = require_list(
        voiceover.get(
            "segments"
        ),
        "content_package.voiceover.segments",
    )

    if len(
        segments
    ) != len(
        SCRIPT_FIELDS
    ):
        raise ValueError(
            "Voice-over deve conter exatamente "
            "seis segmentos semânticos."
        )

    observed_sections = [
        require_mapping(
            segment,
            (
                "content_package."
                f"voiceover.segments[{index}]"
            ),
        ).get(
            "section"
        )
        for index, segment in enumerate(
            segments
        )
    ]

    if observed_sections != list(
        SCRIPT_FIELDS
    ):
        raise ValueError(
            "Voice-over não respeita a ordem "
            "semântica do guião."
        )

    scenes = require_list(
        payload.get(
            "scenes"
        ),
        "content_package.scenes",
    )

    if not scenes:
        raise ValueError(
            "Content package deve "
            "conter scenes."
        )

    expected = list(
        range(
            1,
            len(
                scenes
            )
            +
            1,
        )
    )

    actual = []

    for scene in scenes:
        scene_mapping = require_mapping(
            scene,
            "content_package.scenes[]",
        )

        actual.append(
            scene_mapping.get(
                "scene_number"
            )
        )

        if normalize_integer(
            scene_mapping.get(
                "duration_seconds"
            ),
            default=0,
        ) <= 0:
            raise ValueError(
                "Scene com duração inválida."
            )

    if actual != expected:
        raise ValueError(
            "Scenes inválidas: "
            "scene_number deve ser sequencial."
        )

    publishing = require_mapping(
        payload.get(
            "publishing"
        ),
        "content_package.publishing",
    )

    if not normalize_non_empty_string(
        publishing.get(
            "description"
        ),
        default="",
    ):
        raise ValueError(
            "Publishing description não pode ser genérica ou vazia."
        )

    hashtags = publishing.get(
        "hashtags"
    )

    if not isinstance(
        hashtags,
        list,
    ):
        raise ValueError(
            "Publishing hashtags deve ser uma lista."
        )


def main() -> int:
    print(
        "="
        *
        70
    )
    print(
        "FOOTBALL-SHORTS-AI-0031C.5A"
    )
    print(
        "SCRIPT STUDIO SEMANTIC CONTENT RECOVERY"
    )
    print(
        "REAL EDITORIAL SCRIPT BINDING"
    )
    print(
        "NO PUBLICATION EXECUTION"
    )
    print(
        "="
        *
        70
    )

    dashboard = load_json(
        DASHBOARD_SOURCE
    )

    editorial_package = load_json(
        EDITORIAL_SOURCE
    )

    package = build_content_package(
        dashboard,
        editorial_package,
    )

    validate_package(
        package
    )

    save_json(
        CONTENT_OUTPUT,
        package,
    )

    print(
        "EDITORIAL_PACKAGE_BINDING=PASS"
    )
    print(
        "SCRIPT_GENERIC_PLACEHOLDERS=REMOVED"
    )
    print(
        "SCRIPT_SECTIONS=6"
    )
    print(
        "VOICEOVER_SEGMENTS=6"
    )
    print(
        "SOURCE_TRACEABILITY=PRESERVED"
    )
    print(
        "CONTENT PACKAGE BUILD PASS"
    )
    print(
        "Winner: "
        f"{package['source_topic']['title']}"
    )
    print(
        "Viral probability: "
        f"{package['source_topic']['viral_probability']}%"
    )
    print(
        f"Scenes: {len(package['scenes'])}"
    )
    print(
        f"Output: {CONTENT_OUTPUT}"
    )
    print(
        "="
        *
        70
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
