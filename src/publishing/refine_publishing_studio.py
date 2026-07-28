
from __future__ import annotations

import json
import re
import unicodedata

from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CONTENT_SOURCE = (
    ROOT
    / "output"
    / "content_package.json"
)

PUBLISHING_SOURCE = (
    ROOT
    / "output"
    / "publishing_package.json"
)


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
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

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            f"{path} deve conter um objeto JSON."
        )

    return payload


def save_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.with_suffix(
            path.suffix
            +
            ".tmp"
        )
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
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
    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{field_name} deve ser um objeto JSON."
        )

    return value


def require_text(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"{field_name} deve ser texto."
        )

    normalized = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    if not normalized:
        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def optional_text(
    value: object,
    *,
    default: str = "",
) -> str:
    if isinstance(
        value,
        str,
    ):
        normalized = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        if normalized:
            return normalized

    return default


def normalize_ascii_upper(
    value: str,
) -> str:
    return (
        unicodedata.normalize(
            "NFKD",
            value,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii"
        )
        .upper()
    )


def infer_confirmation_status(
    content: dict[str, Any],
    publishing: dict[str, Any],
) -> str:
    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    direct_status = optional_text(
        source_topic.get(
            "confirmation_status"
        )
    ).upper()

    if direct_status in {
        "CONFIRMED",
        "REPORTED",
        "RUMOUR",
        "ANALYSIS",
    }:
        status = direct_status
    else:
        status = "REPORTED"

    metadata = require_mapping(
        publishing.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    title = optional_text(
        metadata.get(
            "title"
        )
    ).casefold()

    description = optional_text(
        metadata.get(
            "description"
        )
    ).casefold()

    combined = (
        title
        +
        " "
        +
        description
    )

    if (
        "rumor" in combined
        or
        "rumour" in combined
    ):
        return "RUMOUR"

    if (
        "análise" in combined
        or
        "analise" in combined
    ):
        return (
            "ANALYSIS"
            if status not in {
                "RUMOUR",
                "REPORTED",
            }
            else status
        )

    return status


def shorten_question_clause(
    title: str,
) -> str:
    normalized = re.sub(
        r"\s+",
        " ",
        title,
    ).strip()

    if "?" in normalized:
        clause = (
            normalized.split(
                "?",
                1,
            )[0].strip()
            +
            "?"
        )
    else:
        clause = normalized

    if len(
        clause
    ) <= 32:
        return clause

    match = re.match(
        (
            r"^(?P<subject>.+?)\s+"
            r"(?P<preposition>no|na|ao|à)\s+"
            r"(?P<destination>.+?)"
            r"(?P<question>\?)?$"
        ),
        clause,
        flags=re.IGNORECASE,
    )

    if match:
        subject_words = (
            match.group(
                "subject"
            )
            .strip()
            .split()
        )

        destination_words = (
            match.group(
                "destination"
            )
            .strip()
            .rstrip(
                "?"
            )
            .split()
        )

        if (
            subject_words
            and
            destination_words
        ):
            return (
                subject_words[-1]
                +
                " "
                +
                match.group(
                    "preposition"
                )
                +
                " "
                +
                destination_words[-1]
                +
                (
                    "?"
                    if (
                        match.group(
                            "question"
                        )
                        or
                        "?"
                        in
                        clause
                    )
                    else ""
                )
            )

    words = clause.split()

    shortened = " ".join(
        words[
            :5
        ]
    )

    if (
        "?"
        in
        clause
        and
        not shortened.endswith(
            "?"
        )
    ):
        shortened = (
            shortened.rstrip(
                ".,;:!"
            )
            +
            "?"
        )

    return shortened


def build_thumbnail_overlay(
    title: str,
) -> str:
    overlay = shorten_question_clause(
        title
    )

    return normalize_ascii_upper(
        overlay
    )[
        :40
    ].strip()


def build_visual_direction(
    *,
    overlay: str,
    confirmation_status: str,
) -> str:
    status_instruction = {
        "RUMOUR": (
            "Incluir marcador visível RUMOR e evitar "
            "qualquer grafismo que sugira uma transferência confirmada."
        ),
        "REPORTED": (
            "Incluir marcador INFORMAÇÃO REPORTADA e evitar "
            "apresentar o conteúdo como confirmação definitiva."
        ),
        "CONFIRMED": (
            "Apresentar a informação como confirmada, "
            "sem acrescentar factos não presentes na fonte."
        ),
        "ANALYSIS": (
            "Incluir marcador ANÁLISE e evitar apresentar "
            "conclusões editoriais como factos."
        ),
    }[
        confirmation_status
    ]

    return (
        f"Thumbnail editorial 16:9 para «{overlay}». "
        "Usar apenas material visual autorizado relacionado "
        "com os intervenientes do tema, alto contraste e leitura "
        f"imediata em ecrã móvel. {status_instruction}"
    )


def build_emotion_target(
    confirmation_status: str,
) -> str:
    return {
        "RUMOUR":
            "curiosidade e debate",
        "REPORTED":
            "curiosidade informada",
        "CONFIRMED":
            "impacto e clareza",
        "ANALYSIS":
            "debate e reflexão",
    }[
        confirmation_status
    ]


def normalize_schedule(
    metadata: dict[str, Any],
    readiness: dict[str, Any],
    checklist: dict[str, Any],
) -> None:
    recommended_time = require_text(
        metadata.get(
            "recommended_publish_time"
        ),
        (
            "publishing.metadata."
            "recommended_publish_time"
        ),
    )

    scheduled_window = optional_text(
        metadata.get(
            "scheduled_window"
        ),
        default="Hora recomendada",
    )

    if (
        scheduled_window.casefold()
        in {
            recommended_time.casefold(),
            "recommended",
            "hora recomendada",
        }
    ):
        normalized_window = (
            "Hora recomendada"
        )
    else:
        normalized_window = (
            scheduled_window
        )

    metadata[
        "scheduled_window"
    ] = normalized_window

    readiness[
        "scheduled_window"
    ] = normalized_window

    readiness[
        "recommended_publish_time"
    ] = recommended_time

    schedule_entry = checklist.get(
        "schedule_defined"
    )

    if isinstance(
        schedule_entry,
        dict,
    ):
        schedule_entry[
            "detail"
        ] = (
            "Hora recomendada: "
            f"{recommended_time}."
        )


def refine_publishing_package(
    content: dict[str, Any],
    publishing: dict[str, Any],
) -> dict[str, Any]:
    refined = deepcopy(
        publishing
    )

    metadata = require_mapping(
        refined.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    thumbnail = require_mapping(
        refined.get(
            "thumbnail"
        ),
        "publishing.thumbnail",
    )

    checklist = require_mapping(
        refined.get(
            "checklist"
        ),
        "publishing.checklist",
    )

    readiness = require_mapping(
        refined.get(
            "readiness"
        ),
        "publishing.readiness",
    )

    title = require_text(
        metadata.get(
            "title"
        ),
        "publishing.metadata.title",
    )

    status = infer_confirmation_status(
        content,
        refined,
    )

    overlay = build_thumbnail_overlay(
        title
    )

    thumbnail[
        "text_overlay"
    ] = overlay

    thumbnail[
        "visual_direction"
    ] = build_visual_direction(
        overlay=overlay,
        confirmation_status=status,
    )

    thumbnail[
        "emotion_target"
    ] = build_emotion_target(
        status
    )

    thumbnail[
        "confirmation_status"
    ] = status

    thumbnail[
        "brief_source"
    ] = (
        "governed_editorial_content"
    )

    thumbnail[
        "browser_text_overlay_enabled"
    ] = False

    normalize_schedule(
        metadata,
        readiness,
        checklist,
    )

    if refined.get(
        "status"
    ) != "draft":
        raise ValueError(
            "Publishing lifecycle deixou de estar draft."
        )

    if readiness.get(
        "status"
    ) != "blocked":
        raise ValueError(
            "Publishing readiness deixou de estar blocked."
        )

    if readiness.get(
        "publication_execution_enabled"
    ) is not False:
        raise ValueError(
            "A publicação foi ativada indevidamente."
        )

    if readiness.get(
        "blocker_count"
    ) != 2:
        raise ValueError(
            "O número de bloqueios deixou de ser 2."
        )

    return refined


def validate_invariance(
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    for field_name in (
        "package_version",
        "source_content_id",
        "evidence",
        "status",
    ):
        if (
            before.get(
                field_name
            )
            !=
            after.get(
                field_name
            )
        ):
            raise ValueError(
                "Campo governado alterado: "
                f"{field_name}"
            )

    before_metadata = require_mapping(
        before.get(
            "metadata"
        ),
        "before.metadata",
    )

    after_metadata = require_mapping(
        after.get(
            "metadata"
        ),
        "after.metadata",
    )

    for field_name in (
        "platform",
        "title",
        "description",
        "hashtags",
        "recommended_publish_time",
    ):
        if (
            before_metadata.get(
                field_name
            )
            !=
            after_metadata.get(
                field_name
            )
        ):
            raise ValueError(
                "Metadado editorial alterado: "
                f"{field_name}"
            )

    before_thumbnail = require_mapping(
        before.get(
            "thumbnail"
        ),
        "before.thumbnail",
    )

    after_thumbnail = require_mapping(
        after.get(
            "thumbnail"
        ),
        "after.thumbnail",
    )

    for field_name in (
        "asset_ready",
        "asset_status",
        "asset_reference",
        "asset_public_path",
        "asset_sha256",
        "width",
        "height",
        "mime_type",
        "byte_size",
    ):
        if (
            before_thumbnail.get(
                field_name
            )
            !=
            after_thumbnail.get(
                field_name
            )
        ):
            raise ValueError(
                "Evidência da thumbnail alterada: "
                f"{field_name}"
            )

    before_readiness = require_mapping(
        before.get(
            "readiness"
        ),
        "before.readiness",
    )

    after_readiness = require_mapping(
        after.get(
            "readiness"
        ),
        "after.readiness",
    )

    for field_name in (
        "status",
        "lifecycle_status",
        "completion_percent",
        "completed_items",
        "total_items",
        "blocker_count",
        "blockers",
        "ready_for_scheduling",
        "publication_execution_enabled",
        "recommended_action",
    ):
        if (
            before_readiness.get(
                field_name
            )
            !=
            after_readiness.get(
                field_name
            )
        ):
            raise ValueError(
                "Readiness governada alterada: "
                f"{field_name}"
            )


def main() -> int:
    print(
        "="
        *
        70
    )
    print(
        "FOOTBALL-SHORTS-AI-0031C.5D"
    )
    print(
        "PUBLISHING STUDIO SEMANTIC AND VISUAL RECOVERY"
    )
    print(
        "NO PUBLICATION EXECUTION"
    )
    print(
        "="
        *
        70
    )

    content = load_json(
        CONTENT_SOURCE
    )

    publishing = load_json(
        PUBLISHING_SOURCE
    )

    refined = refine_publishing_package(
        content,
        publishing,
    )

    validate_invariance(
        publishing,
        refined,
    )

    save_json_atomically(
        PUBLISHING_SOURCE,
        refined,
    )

    print(
        "THUMBNAIL_BRIEF_BINDING=PASS"
    )
    print(
        "DUPLICATE_BROWSER_OVERLAY=DISABLED"
    )
    print(
        "SCHEDULE_DUPLICATION=REMOVED"
    )
    print(
        "TITLE_DESCRIPTION_HASHTAGS_INVARIANCE=PASS"
    )
    print(
        "THUMBNAIL_ARTIFACT_INVARIANCE=PASS"
    )
    print(
        "READINESS_STATUS=BLOCKED"
    )
    print(
        "BLOCKER_COUNT=2"
    )
    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
    )
    print(
        "PUBLISHING_STUDIO_REFINEMENT=PASS"
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
