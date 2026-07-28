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
    """
    Divide apenas em fronteiras reais de frase.

    Ponto e vírgula, dois pontos e travessões permanecem dentro
    da mesma frase para evitar cortar perguntas ou raciocínios.
    """

    normalized = value.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    raw_parts = re.split(
        (
            r"(?<=[.!?…])\s+"
            r"(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9«“\"]|$)"
            r"|\n+"
        ),
        normalized,
    )

    return [
        re.sub(
            r"\s+",
            " ",
            part,
        ).strip(
            " \t—–-"
        )
        for part in raw_parts
        if re.sub(
            r"\s+",
            " ",
            part,
        ).strip(
            " \t—–-"
        )
    ]


def text_signature(
    value: str,
) -> str:
    return normalize_comparison_text(
        value
    )


def is_distinct_text(
    candidate: str,
    used_values: list[str],
) -> bool:
    candidate_signature = text_signature(
        candidate
    )

    if not candidate_signature:
        return False

    for used_value in used_values:
        used_signature = text_signature(
            used_value
        )

        if not used_signature:
            continue

        if candidate_signature == used_signature:
            return False

        if (
            len(
                candidate_signature
            )
            >=
            32
            and
            candidate_signature
            in
            used_signature
        ):
            return False

        if (
            len(
                used_signature
            )
            >=
            32
            and
            used_signature
            in
            candidate_signature
        ):
            return False

    return True


def first_distinct_text(
    candidates: list[str],
    *,
    used_values: list[str],
) -> str:
    for candidate in candidates:
        normalized = normalize_non_empty_string(
            candidate,
            default="",
        )

        if is_distinct_text(
            normalized,
            used_values,
        ):
            return normalized

    return ""


def build_confirmation_ending(
    source: dict[str, Any],
) -> str:
    status = normalize_non_empty_string(
        source.get(
            "confirmation_status"
        ),
        default="REPORTED",
    ).upper()

    endings = {
        "CONFIRMED": (
            "A informação principal está classificada "
            "como confirmada pela fonte editorial indicada."
        ),
        "REPORTED": (
            "A informação permanece reportada, mas sem "
            "confirmação definitiva no momento da produção."
        ),
        "RUMOUR": (
            "A informação permanece classificada como rumor "
            "e não como transferência confirmada."
        ),
        "ANALYSIS": (
            "Este conteúdo deve ser apresentado como análise "
            "editorial baseada na informação disponível."
        ),
    }

    return endings.get(
        status,
        endings[
            "REPORTED"
        ],
    )


def build_specific_call_to_action(
    editorial: dict[str, Any],
    *,
    hook: str,
) -> str:
    pinned_comment = normalize_non_empty_string(
        editorial.get(
            "pinned_comment"
        ),
        default="",
    )

    editorial_cta = normalize_non_empty_string(
        editorial.get(
            "call_to_action"
        ),
        default="",
    )

    hook_question = ""

    for unit in split_script_units(
        hook
    ):
        if "?" in unit:
            hook_question = unit
            break

    primary = first_distinct_text(
        [
            pinned_comment,
            hook_question,
        ],
        used_values=[],
    )

    secondary = first_distinct_text(
        [
            editorial_cta,
        ],
        used_values=[
            primary
        ],
    )

    parts = [
        part
        for part in (
            primary,
            secondary,
        )
        if part
    ]

    if not parts:
        raise ValueError(
            "Call to action editorial indisponível."
        )

    return " ".join(
        parts
    )


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

    source = require_mapping(
        editorial_topic.get(
            "source"
        ),
        "winner.source",
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

    original_call_to_action = (
        normalize_non_empty_string(
            editorial.get(
                "call_to_action"
            ),
            default="",
        )
    )

    pinned_comment = normalize_non_empty_string(
        editorial.get(
            "pinned_comment"
        ),
        default="",
    )

    call_to_action = (
        build_specific_call_to_action(
            editorial,
            hook=hook,
        )
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

    for boundary in (
        original_call_to_action,
        pinned_comment,
    ):
        body = remove_boundary_phrase(
            body,
            boundary,
            at_start=False,
        )

    units = split_script_units(
        body
    )

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

    confirmation_ending = (
        build_confirmation_ending(
            source
        )
    )

    question_indexes = [
        index
        for index, unit in enumerate(
            units
        )
        if "?" in unit
    ]

    if question_indexes:
        climax_index = (
            question_indexes[-1]
        )
    elif len(
        units
    ) >= 3:
        climax_index = (
            len(
                units
            )
            -
            2
        )
    elif len(
        units
    ) >= 2:
        climax_index = 1
    else:
        climax_index = 0

    introduction = (
        units[0]
        if units
        else first_distinct_text(
            [
                description,
                reason,
            ],
            used_values=[
                hook
            ],
        )
    )

    if units:
        development_units = units[
            1:
            climax_index
        ]

        climax = units[
            climax_index
        ]

        ending_units = units[
            climax_index
            +
            1:
        ]
    else:
        development_units = []
        climax = ""
        ending_units = []

    development = " ".join(
        development_units
    ).strip()

    if not development:
        development = first_distinct_text(
            [
                description,
                reason,
                body,
            ],
            used_values=[
                hook,
                introduction,
                climax,
            ],
        )

    if not climax:
        climax = first_distinct_text(
            [
                reason,
                body,
                description,
            ],
            used_values=[
                hook,
                introduction,
                development,
            ],
        )

    ending = " ".join(
        ending_units
    ).strip()

    if not ending:
        ending = first_distinct_text(
            [
                reason,
                description,
                confirmation_ending,
            ],
            used_values=[
                hook,
                introduction,
                development,
                climax,
            ],
        )

    if not ending:
        ending = confirmation_ending

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


GENERIC_STORYBOARD_ASSET_MARKERS = {
    "opening football clip",
    "player team footage",
    "main highlight clip",
    "reaction statistics footage",
    "final football celebration video",
    "football opening clip",
    "football context clip",
    "football highlight clip",
    "fans reaction clip",
    "fan reaction",
}


def normalize_label(
    value: Any,
) -> str:
    return normalize_non_empty_string(
        value,
        default="",
    ).replace(
        "_",
        " ",
    )


def compact_caption(
    value: str,
    *,
    maximum_words: int = 8,
) -> str:
    normalized = normalize_non_empty_string(
        value,
        default="",
    )

    if not normalized:
        raise ValueError(
            "Não é possível criar uma legenda "
            "a partir de texto vazio."
        )

    first_sentence = split_script_units(
        normalized
    )[0]

    words = first_sentence.split()

    if len(
        words
    ) > maximum_words:
        first_sentence = (
            " ".join(
                words[
                    :maximum_words
                ]
            )
            +
            "…"
        )

    return first_sentence.upper()


def resolve_storyboard_status(
    source: dict[str, Any],
    script: dict[str, str],
) -> str:
    combined_script = " ".join(
        script.values()
    ).casefold()

    if "rumor" in combined_script:
        return "RUMOUR"

    if (
        "não é contratação confirmada"
        in
        combined_script
        or
        "não existe uma transferência confirmada"
        in
        combined_script
        or
        "sem confirmação definitiva"
        in
        combined_script
    ):
        return "REPORTED"

    return normalize_non_empty_string(
        source.get(
            "confirmation_status"
        ),
        default="REPORTED",
    ).upper()


def build_status_instruction(
    status: str,
) -> str:
    instructions = {
        "CONFIRMED": (
            "Apresentar como informação confirmada, "
            "sem acrescentar factos não presentes na fonte."
        ),
        "REPORTED": (
            "Apresentar como informação reportada, "
            "sem grafismo de contratação confirmada."
        ),
        "RUMOUR": (
            "Identificar claramente como rumor, "
            "sem grafismo de contratação confirmada."
        ),
        "ANALYSIS": (
            "Identificar claramente como análise editorial."
        ),
    }

    return instructions.get(
        status,
        instructions[
            "REPORTED"
        ],
    )


def extract_storyboard_scenes(
    editorial_topic: dict[str, Any],
) -> list[dict[str, Any]]:
    storyboard = require_mapping(
        editorial_topic.get(
            "storyboard"
        ),
        "winner.storyboard",
    )

    raw_scenes = require_list(
        storyboard.get(
            "scenes"
        ),
        "winner.storyboard.scenes",
    )

    scenes = [
        require_mapping(
            raw_scene,
            (
                "winner.storyboard."
                f"scenes[{index}]"
            ),
        )
        for index, raw_scene in enumerate(
            raw_scenes
        )
    ]

    if len(
        scenes
    ) < 4:
        raise ValueError(
            "O storyboard editorial deve conter "
            "pelo menos quatro cenas."
        )

    return scenes


def storyboard_groups(
    source_scenes: list[dict[str, Any]],
) -> tuple[
    tuple[dict[str, Any], ...],
    ...,
]:
    if len(
        source_scenes
    ) == 4:
        return tuple(
            (
                scene,
            )
            for scene in source_scenes
        )

    return (
        (
            source_scenes[0],
        ),
        (
            source_scenes[1],
        ),
        tuple(
            source_scenes[
                2:
                -1
            ]
        ),
        (
            source_scenes[-1],
        ),
    )


def select_group_value(
    group: tuple[dict[str, Any], ...],
    field_name: str,
    *,
    use_last: bool = False,
    default: str,
) -> str:
    ordered = (
        tuple(
            reversed(
                group
            )
        )
        if use_last
        else group
    )

    for scene in ordered:
        value = normalize_label(
            scene.get(
                field_name
            )
        )

        if value:
            return value

    return default


def asset_reference_from_group(
    group: tuple[dict[str, Any], ...],
) -> str:
    for scene in group:
        asset = scene.get(
            "asset"
        )

        if not isinstance(
            asset,
            dict,
        ):
            continue

        description = normalize_non_empty_string(
            asset.get(
                "description"
            ),
            default="",
        )

        if not description:
            continue

        if (
            description.casefold()
            in
            GENERIC_STORYBOARD_ASSET_MARKERS
        ):
            continue

        return description

    return "asset específico requerido"


def build_visual_instruction(
    *,
    title: str,
    narrative_text: str,
    source_visuals: list[str],
    status_instruction: str,
    stage: str,
) -> str:
    observed: set[str] = set()
    visuals: list[str] = []

    for value in source_visuals:
        normalized = normalize_non_empty_string(
            value,
            default="",
        )

        key = normalized.casefold()

        if (
            not normalized
            or
            key in observed
            or
            key in {
                "momento inicial mais forte do tema",
                "clips que explicam a situação",
                "a jogada ou momento principal",
                "reações, comentários e dados",
                "fecho do short com chamada à interação",
            }
        ):
            continue

        observed.add(
            key
        )
        visuals.append(
            normalized
        )

    source_hint = (
        " ".join(
            visuals
        )
        if visuals
        else
        (
            f"Usar imagens licenciadas diretamente "
            f"relacionadas com «{title}»."
        )
    )

    return (
        f"{stage}: {source_hint} "
        f"Conteúdo editorial a ilustrar: {narrative_text} "
        f"{status_instruction}"
    )


def build_scenes(
    editorial_topic: dict[str, Any],
    script: dict[str, str],
    title: str,
) -> list[dict[str, Any]]:
    source = require_mapping(
        editorial_topic.get(
            "source"
        ),
        "winner.source",
    )

    source_scenes = extract_storyboard_scenes(
        editorial_topic
    )

    groups = storyboard_groups(
        source_scenes
    )

    status = resolve_storyboard_status(
        source,
        script,
    )

    status_instruction = (
        build_status_instruction(
            status
        )
    )

    narrative = (
        {
            "caption_source": script[
                "hook"
            ],
            "voiceover": script[
                "hook"
            ],
            "stage": "Abertura",
            "duration": 5,
        },
        {
            "caption_source": script[
                "introduction"
            ],
            "voiceover": (
                script[
                    "introduction"
                ]
                +
                " "
                +
                script[
                    "development"
                ]
            ),
            "stage": "Contexto",
            "duration": 15,
        },
        {
            "caption_source": script[
                "climax"
            ],
            "voiceover": (
                script[
                    "climax"
                ]
                +
                " "
                +
                script[
                    "ending"
                ]
            ),
            "stage": "Ponto decisivo",
            "duration": 15,
        },
        {
            "caption_source": script[
                "call_to_action"
            ],
            "voiceover": script[
                "call_to_action"
            ],
            "stage": "Fecho",
            "duration": 10,
        },
    )

    scenes: list[
        dict[str, Any]
    ] = []

    for index, (
        group,
        narrative_item,
    ) in enumerate(
        zip(
            groups,
            narrative,
            strict=True,
        ),
        start=1,
    ):
        source_visuals = [
            normalize_non_empty_string(
                scene.get(
                    "visual_description"
                ),
                default="",
            )
            for scene in group
        ]

        camera_direction = (
            select_group_value(
                group,
                "camera_movement",
                default="static",
            )
        )

        editing_pace = select_group_value(
            group,
            "editing_pace",
            default="medium",
        )

        transition = select_group_value(
            group,
            "transition",
            use_last=True,
            default="cut",
        )

        sound_effect = select_group_value(
            group,
            "sound_effect",
            default="som editorial",
        )

        voiceover_text = (
            normalize_non_empty_string(
                narrative_item[
                    "voiceover"
                ],
                default="",
            )
        )

        scenes.append(
            {
                "scene_number": index,
                "duration_seconds": (
                    narrative_item[
                        "duration"
                    ]
                ),
                "visual_instruction":
                    build_visual_instruction(
                        title=title,
                        narrative_text=(
                            voiceover_text
                        ),
                        source_visuals=(
                            source_visuals
                        ),
                        status_instruction=(
                            status_instruction
                        ),
                        stage=(
                            narrative_item[
                                "stage"
                            ]
                        ),
                    ),
                "camera_direction":
                    camera_direction,
                "editing_pace":
                    editing_pace,
                "transition":
                    transition,
                "sound_effect":
                    sound_effect,
                "voiceover_segment":
                    voiceover_text,
                "caption_text":
                    compact_caption(
                        narrative_item[
                            "caption_source"
                        ]
                    ),
                "asset_reference":
                    asset_reference_from_group(
                        group
                    ),
                "confirmation_status":
                    status,
                "source_scene_numbers": [
                    normalize_integer(
                        scene.get(
                            "scene_number"
                        ),
                        default=position,
                    )
                    for position, scene in enumerate(
                        group,
                        start=1,
                    )
                ],
            }
        )

    if sum(
        scene[
            "duration_seconds"
        ]
        for scene in scenes
    ) != 45:
        raise ValueError(
            "O storyboard consolidado deve "
            "ter exatamente 45 segundos."
        )

    return scenes


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
        "scenes": build_scenes(
            editorial_topic,
            script,
            title,
        ),
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
