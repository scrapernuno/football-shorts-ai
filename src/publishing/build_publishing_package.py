from __future__ import annotations

import json
import re
import unicodedata

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CONTENT_SOURCE = (
    ROOT
    / "output"
    / "content_package.json"
)

DASHBOARD_SOURCE = (
    ROOT
    / "output"
    / "dashboard_model.json"
)

OUTPUT = (
    ROOT
    / "output"
    / "publishing_package.json"
)


PACKAGE_VERSION = "1.0"

READINESS_CONTRACT_VERSION = "1.0"

LIFECYCLE_STATUS = "draft"


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


def save_json(
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
            + ".tmp"
        )
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
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
            f"{field_name} deve ser "
            "um objeto JSON."
        )

    return value


def require_list(
    value: object,
    field_name: str,
) -> list[Any]:
    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{field_name} deve ser "
            "uma lista JSON."
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

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def optional_text(
    value: object,
    *,
    default: str,
) -> str:
    if isinstance(
        value,
        str,
    ):
        normalized = value.strip()

        if normalized:
            return normalized

    return default


def optional_boolean(
    value: object,
    *,
    default: bool = False,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return value

    return default


def slugify(
    value: str,
) -> str:
    normalized = (
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
        .lower()
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    ).strip("-")

    return (
        slug
        or
        "football-short"
    )


def validate_content_package(
    payload: dict[str, Any],
) -> None:
    required = {
        "package_version",
        "source_topic",
        "script",
        "publishing",
    }

    missing = (
        required
        -
        payload.keys()
    )

    if missing:
        raise ValueError(
            "Content Package inválido: "
            f"{sorted(missing)}"
        )

    source_topic = require_mapping(
        payload.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    require_text(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    require_mapping(
        payload.get(
            "script"
        ),
        "content.script",
    )

    require_mapping(
        payload.get(
            "publishing"
        ),
        "content.publishing",
    )


def validate_dashboard_model(
    payload: dict[str, Any],
    *,
    expected_title: str,
) -> None:
    dashboard_title = require_text(
        payload.get(
            "top_title"
        ),
        "dashboard.top_title",
    )

    if dashboard_title != expected_title:
        raise ValueError(
            "Dashboard Model e Content Package "
            "não usam o mesmo título."
        )

    publish_time = require_text(
        payload.get(
            "recommended_publish_time"
        ),
        (
            "dashboard."
            "recommended_publish_time"
        ),
    )

    if re.fullmatch(
        r"(?:[01]\d|2[0-3]):[0-5]\d",
        publish_time,
    ) is None:
        raise ValueError(
            "dashboard.recommended_publish_time "
            "deve usar HH:MM."
        )


def build_thumbnail(
    content: dict[str, Any],
) -> dict[str, Any]:
    source = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    publishing = require_mapping(
        content.get(
            "publishing"
        ),
        "content.publishing",
    )

    title = require_text(
        source.get(
            "title"
        ),
        "content.source_topic.title",
    )

    text_overlay = (
        title
        .upper()
        [:45]
    )

    visual_direction = (
        "High emotion football frame "
        "with player reaction"
    )

    emotion_target = "curiosity"

    brief_ready = all(
        (
            text_overlay,
            visual_direction,
            emotion_target,
        )
    )

    asset_ready = optional_boolean(
        publishing.get(
            "thumbnail_asset_ready"
        ),
        default=False,
    )

    asset_reference = optional_text(
        publishing.get(
            "thumbnail_asset_reference"
        ),
        default="",
    )

    if asset_ready and not asset_reference:
        raise ValueError(
            "thumbnail_asset_ready exige "
            "thumbnail_asset_reference."
        )

    return {
        "text_overlay":
            text_overlay,

        "visual_direction":
            visual_direction,

        "emotion_target":
            emotion_target,

        "brief_ready":
            brief_ready,

        "asset_ready":
            asset_ready,

        "asset_status":
            (
                "ready"
                if asset_ready
                else
                "not_generated"
            ),

        "asset_reference":
            asset_reference,
    }


def build_metadata(
    content: dict[str, Any],
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    source = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    publishing = require_mapping(
        content.get(
            "publishing"
        ),
        "content.publishing",
    )

    title = require_text(
        source.get(
            "title"
        ),
        "content.source_topic.title",
    )

    description = optional_text(
        publishing.get(
            "description"
        ),
        default=(
            f"{title}. "
            "História gerada pelo "
            "Football Shorts AI."
        ),
    )

    raw_hashtags = publishing.get(
        "hashtags"
    )

    hashtags: list[str] = []

    if isinstance(
        raw_hashtags,
        list,
    ):
        hashtags = [
            value.strip()
            for value in raw_hashtags
            if (
                isinstance(
                    value,
                    str,
                )
                and
                value.strip()
            )
        ]

    if not hashtags:
        hashtags = [
            "#football",
            "#soccer",
            "#shorts",
        ]

    scheduled_window = optional_text(
        publishing.get(
            "scheduled_window"
        ),
        default="recommended",
    )

    recommended_publish_time = require_text(
        dashboard.get(
            "recommended_publish_time"
        ),
        (
            "dashboard."
            "recommended_publish_time"
        ),
    )

    return {
        "platform":
            optional_text(
                publishing.get(
                    "platform"
                ),
                default="youtube_shorts",
            ),

        "title":
            title,

        "description":
            description,

        "hashtags":
            hashtags,

        "scheduled_window":
            scheduled_window,

        "recommended_publish_time":
            recommended_publish_time,
    }


def checklist_entry(
    *,
    label: str,
    completed: bool,
    detail: str,
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "label":
            label,

        "completed":
            completed,

        "blocking":
            blocking,

        "detail":
            detail,
    }


def build_checklist(
    *,
    content: dict[str, Any],
    metadata: dict[str, Any],
    thumbnail: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    publishing = require_mapping(
        content.get(
            "publishing"
        ),
        "content.publishing",
    )

    title_valid = bool(
        optional_text(
            metadata.get(
                "title"
            ),
            default="",
        )
    )

    description_valid = bool(
        optional_text(
            metadata.get(
                "description"
            ),
            default="",
        )
    )

    hashtags_valid = bool(
        require_list(
            metadata.get(
                "hashtags"
            ),
            "metadata.hashtags",
        )
    )

    scheduled_window = optional_text(
        metadata.get(
            "scheduled_window"
        ),
        default="",
    )

    recommended_publish_time = optional_text(
        metadata.get(
            "recommended_publish_time"
        ),
        default="",
    )

    schedule_defined = (
        bool(
            scheduled_window
        )
        and
        re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d",
            recommended_publish_time,
        )
        is not None
    )

    thumbnail_brief_ready = (
        thumbnail.get(
            "brief_ready"
        )
        is True
    )

    thumbnail_asset_ready = (
        thumbnail.get(
            "asset_ready"
        )
        is True
    )

    copyright_review_completed = (
        optional_boolean(
            publishing.get(
                "copyright_review_completed"
            ),
            default=False,
        )
    )

    final_confirmation_completed = (
        optional_boolean(
            publishing.get(
                "final_confirmation_completed"
            ),
            default=False,
        )
    )

    return {
        "title_valid":
            checklist_entry(
                label="Título validado",
                completed=title_valid,
                detail=(
                    "O título de publicação "
                    "está preenchido."
                ),
            ),

        "description_valid":
            checklist_entry(
                label="Descrição validada",
                completed=description_valid,
                detail=(
                    "A descrição de publicação "
                    "está preenchida."
                ),
            ),

        "hashtags_valid":
            checklist_entry(
                label="Hashtags validadas",
                completed=hashtags_valid,
                detail=(
                    "Existe pelo menos uma "
                    "hashtag de publicação."
                ),
            ),

        "schedule_defined":
            checklist_entry(
                label=(
                    "Horário recomendado definido"
                ),
                completed=schedule_defined,
                detail=(
                    f"Janela: {scheduled_window}; "
                    f"hora: "
                    f"{recommended_publish_time or '—'}."
                ),
            ),

        "thumbnail_brief_ready":
            checklist_entry(
                label=(
                    "Brief de thumbnail concluído"
                ),
                completed=thumbnail_brief_ready,
                detail=(
                    "Texto, direção visual e "
                    "emoção estão definidos."
                ),
            ),

        "thumbnail_asset_ready":
            checklist_entry(
                label=(
                    "Ficheiro de thumbnail pronto"
                ),
                completed=thumbnail_asset_ready,
                detail=(
                    "É necessário produzir ou "
                    "associar o ficheiro final."
                ),
            ),

        "copyright_review_completed":
            checklist_entry(
                label=(
                    "Revisão de direitos concluída"
                ),
                completed=(
                    copyright_review_completed
                ),
                detail=(
                    "Os clips e imagens devem "
                    "ser confirmados antes do "
                    "agendamento."
                ),
            ),

        "final_confirmation_completed":
            checklist_entry(
                label=(
                    "Confirmação final concluída"
                ),
                completed=(
                    final_confirmation_completed
                ),
                detail=(
                    "A publicação exige aprovação "
                    "humana final."
                ),
            ),
    }


def build_readiness(
    *,
    checklist: dict[
        str,
        dict[str, Any],
    ],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    total_items = len(
        checklist
    )

    completed_items = sum(
        1
        for item
        in checklist.values()
        if item.get(
            "completed"
        )
        is True
    )

    blockers = [
        {
            "code":
                key.upper(),

            "label":
                require_text(
                    item.get(
                        "label"
                    ),
                    (
                        "checklist."
                        f"{key}.label"
                    ),
                ),

            "detail":
                require_text(
                    item.get(
                        "detail"
                    ),
                    (
                        "checklist."
                        f"{key}.detail"
                    ),
                ),
        }
        for key, item
        in checklist.items()
        if (
            item.get(
                "blocking"
            )
            is True
            and
            item.get(
                "completed"
            )
            is not True
        )
    ]

    blocker_count = len(
        blockers
    )

    readiness_status = (
        "ready"
        if blocker_count == 0
        else
        "blocked"
    )

    completion_percent = (
        100
        if total_items == 0
        else
        (
            (
                completed_items
                *
                100
            )
            +
            (
                total_items
                //
                2
            )
        )
        //
        total_items
    )

    return {
        "contract_version":
            READINESS_CONTRACT_VERSION,

        "status":
            readiness_status,

        "lifecycle_status":
            LIFECYCLE_STATUS,

        "completion_percent":
            completion_percent,

        "completed_items":
            completed_items,

        "total_items":
            total_items,

        "blocker_count":
            blocker_count,

        "blockers":
            blockers,

        "recommended_publish_time":
            metadata[
                "recommended_publish_time"
            ],

        "scheduled_window":
            metadata[
                "scheduled_window"
            ],

        "ready_for_scheduling":
            blocker_count == 0,

        "publication_execution_enabled":
            False,

        "recommended_action":
            (
                "Concluir os controlos "
                "bloqueantes antes de agendar."
                if blocker_count
                else
                "Conteúdo pronto para "
                "agendamento manual."
            ),
    }


def build_publishing_package(
    content: dict[str, Any],
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    validate_content_package(
        content
    )

    source = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    title = require_text(
        source.get(
            "title"
        ),
        "content.source_topic.title",
    )

    validate_dashboard_model(
        dashboard,
        expected_title=title,
    )

    metadata = build_metadata(
        content,
        dashboard,
    )

    thumbnail = build_thumbnail(
        content
    )

    checklist = build_checklist(
        content=content,
        metadata=metadata,
        thumbnail=thumbnail,
    )

    readiness = build_readiness(
        checklist=checklist,
        metadata=metadata,
    )

    return {
        "package_version":
            PACKAGE_VERSION,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source_content_id":
            slugify(
                title
            ),

        "metadata":
            metadata,

        "thumbnail":
            thumbnail,

        "checklist":
            checklist,

        "readiness":
            readiness,

        "status":
            LIFECYCLE_STATUS,
    }


def validate_publishing_package(
    payload: dict[str, Any],
) -> None:
    required = {
        "package_version",
        "generated_at",
        "source_content_id",
        "metadata",
        "thumbnail",
        "checklist",
        "readiness",
        "status",
    }

    missing = (
        required
        -
        payload.keys()
    )

    if missing:
        raise ValueError(
            "Publishing Package incompleto: "
            f"{sorted(missing)}"
        )

    if payload.get(
        "status"
    ) != LIFECYCLE_STATUS:
        raise ValueError(
            "O ciclo de vida inicial deve "
            "permanecer draft."
        )

    metadata = require_mapping(
        payload.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    require_text(
        metadata.get(
            "recommended_publish_time"
        ),
        (
            "publishing.metadata."
            "recommended_publish_time"
        ),
    )

    checklist = require_mapping(
        payload.get(
            "checklist"
        ),
        "publishing.checklist",
    )

    if not checklist:
        raise ValueError(
            "publishing.checklist não pode "
            "estar vazio."
        )

    for key, raw_item in checklist.items():
        item = require_mapping(
            raw_item,
            (
                "publishing.checklist."
                f"{key}"
            ),
        )

        require_text(
            item.get(
                "label"
            ),
            (
                "publishing.checklist."
                f"{key}.label"
            ),
        )

        require_text(
            item.get(
                "detail"
            ),
            (
                "publishing.checklist."
                f"{key}.detail"
            ),
        )

        if not isinstance(
            item.get(
                "completed"
            ),
            bool,
        ):
            raise ValueError(
                "publishing.checklist."
                f"{key}.completed deve "
                "ser booleano."
            )

        if not isinstance(
            item.get(
                "blocking"
            ),
            bool,
        ):
            raise ValueError(
                "publishing.checklist."
                f"{key}.blocking deve "
                "ser booleano."
            )

    readiness = require_mapping(
        payload.get(
            "readiness"
        ),
        "publishing.readiness",
    )

    readiness_status = require_text(
        readiness.get(
            "status"
        ),
        "publishing.readiness.status",
    )

    if readiness_status not in {
        "blocked",
        "ready",
    }:
        raise ValueError(
            "publishing.readiness.status "
            "inválido."
        )

    blockers = require_list(
        readiness.get(
            "blockers"
        ),
        "publishing.readiness.blockers",
    )

    blocker_count = readiness.get(
        "blocker_count"
    )

    if (
        not isinstance(
            blocker_count,
            int,
        )
        or
        isinstance(
            blocker_count,
            bool,
        )
        or
        blocker_count < 0
    ):
        raise ValueError(
            "publishing.readiness."
            "blocker_count inválido."
        )

    if blocker_count != len(
        blockers
    ):
        raise ValueError(
            "publishing.readiness."
            "blocker_count inconsistente."
        )

    completed_items = sum(
        1
        for item
        in checklist.values()
        if item.get(
            "completed"
        )
        is True
    )

    if readiness.get(
        "completed_items"
    ) != completed_items:
        raise ValueError(
            "publishing.readiness."
            "completed_items inconsistente."
        )

    if readiness.get(
        "total_items"
    ) != len(
        checklist
    ):
        raise ValueError(
            "publishing.readiness."
            "total_items inconsistente."
        )

    if (
        readiness_status == "ready"
        and
        blocker_count != 0
    ):
        raise ValueError(
            "Readiness READY não pode "
            "conter bloqueios."
        )

    if (
        readiness_status == "blocked"
        and
        blocker_count == 0
    ):
        raise ValueError(
            "Readiness BLOCKED exige "
            "pelo menos um bloqueio."
        )

    if readiness.get(
        "publication_execution_enabled"
    ) is not False:
        raise ValueError(
            "A execução de publicação deve "
            "permanecer desativada."
        )


def main() -> int:
    print("=" * 70)

    print(
        "FOOTBALL-SHORTS-AI-0031C.2"
    )

    print(
        "PUBLISHING READINESS "
        "DATA CONTRACT COMPLETION"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print("=" * 70)

    content = load_json(
        CONTENT_SOURCE
    )

    dashboard = load_json(
        DASHBOARD_SOURCE
    )

    publishing = (
        build_publishing_package(
            content,
            dashboard,
        )
    )

    validate_publishing_package(
        publishing
    )

    save_json(
        OUTPUT,
        publishing,
    )

    readiness = publishing[
        "readiness"
    ]

    print(
        "PUBLISHING PACKAGE BUILD PASS"
    )

    print(
        f"Lifecycle status: "
        f"{publishing['status']}"
    )

    print(
        f"Readiness status: "
        f"{readiness['status']}"
    )

    print(
        f"Completion: "
        f"{readiness['completion_percent']}%"
    )

    print(
        f"Blocking actions: "
        f"{readiness['blocker_count']}"
    )

    print(
        "Recommended publish time: "
        f"{readiness['recommended_publish_time']}"
    )

    print(
        "Publication execution enabled: NO"
    )

    print(
        f"Output: {OUTPUT}"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
