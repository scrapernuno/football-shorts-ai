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

EVIDENCE_SOURCE = (
    ROOT
    / "output"
    / "publishing_evidence.json"
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
            +
            ".tmp"
        )
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


def validate_evidence(
    payload: dict[str, Any],
    *,
    expected_content_id: str,
) -> None:
    required = {
        "evidence_version",
        "generated_at",
        "content_identity",
        "thumbnail",
        "rights_review",
        "final_approval",
        "publication_execution_enabled",
    }

    missing = (
        required
        -
        payload.keys()
    )

    if missing:
        raise ValueError(
            "Publishing Evidence incompleto: "
            f"{sorted(missing)}"
        )

    identity = require_mapping(
        payload.get(
            "content_identity"
        ),
        "evidence.content_identity",
    )

    content_id = require_text(
        identity.get(
            "content_id"
        ),
        "evidence.content_identity.content_id",
    )

    if content_id != expected_content_id:
        raise ValueError(
            "Publishing Evidence pertence a "
            "outro conteúdo."
        )

    thumbnail = require_mapping(
        payload.get(
            "thumbnail"
        ),
        "evidence.thumbnail",
    )

    if thumbnail.get(
        "status"
    ) != "ready":
        raise ValueError(
            "A thumbnail de evidência não "
            "está ready."
        )

    artifact_path = (
        ROOT
        /
        require_text(
            thumbnail.get(
                "artifact_path"
            ),
            (
                "evidence.thumbnail."
                "artifact_path"
            ),
        )
    )

    public_path = (
        ROOT
        /
        "dashboard"
        /
        require_text(
            thumbnail.get(
                "public_path"
            ),
            (
                "evidence.thumbnail."
                "public_path"
            ),
        )
    )

    for path in (
        artifact_path,
        public_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(
                f"Thumbnail em falta: {path}"
            )

    require_mapping(
        payload.get(
            "rights_review"
        ),
        "evidence.rights_review",
    )

    final_approval = require_mapping(
        payload.get(
            "final_approval"
        ),
        "evidence.final_approval",
    )

    approval_content_id = require_text(
        final_approval.get(
            "content_id"
        ),
        "evidence.final_approval.content_id",
    )

    if approval_content_id != expected_content_id:
        raise ValueError(
            "A aprovação final está ligada "
            "a outro conteúdo."
        )

    if payload.get(
        "publication_execution_enabled"
    ) is not False:
        raise ValueError(
            "A execução de publicação deve "
            "permanecer desativada."
        )


def build_thumbnail(
    content: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
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

    evidence_thumbnail = require_mapping(
        evidence.get(
            "thumbnail"
        ),
        "evidence.thumbnail",
    )

    text_overlay = (
        title
        .upper()
        [:45]
    )

    return {
        "text_overlay":
            text_overlay,

        "visual_direction":
            (
                "Deterministic branded football "
                "thumbnail generated by pipeline"
            ),

        "emotion_target":
            "curiosity",

        "brief_ready":
            True,

        "asset_ready":
            (
                evidence_thumbnail.get(
                    "status"
                )
                ==
                "ready"
            ),

        "asset_status":
            require_text(
                evidence_thumbnail.get(
                    "status"
                ),
                "evidence.thumbnail.status",
            ),

        "asset_reference":
            require_text(
                evidence_thumbnail.get(
                    "artifact_path"
                ),
                (
                    "evidence.thumbnail."
                    "artifact_path"
                ),
            ),

        "asset_public_path":
            require_text(
                evidence_thumbnail.get(
                    "public_path"
                ),
                (
                    "evidence.thumbnail."
                    "public_path"
                ),
            ),

        "asset_sha256":
            require_text(
                evidence_thumbnail.get(
                    "sha256"
                ),
                "evidence.thumbnail.sha256",
            ),

        "width":
            evidence_thumbnail.get(
                "width"
            ),

        "height":
            evidence_thumbnail.get(
                "height"
            ),

        "mime_type":
            require_text(
                evidence_thumbnail.get(
                    "mime_type"
                ),
                "evidence.thumbnail.mime_type",
            ),

        "byte_size":
            evidence_thumbnail.get(
                "byte_size"
            ),
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
    metadata: dict[str, Any],
    thumbnail: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, dict[str, Any]]:
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

    rights_review = require_mapping(
        evidence.get(
            "rights_review"
        ),
        "evidence.rights_review",
    )

    final_approval = require_mapping(
        evidence.get(
            "final_approval"
        ),
        "evidence.final_approval",
    )

    rights_review_completed = (
        rights_review.get(
            "status"
        )
        ==
        "approved"
    )

    final_confirmation_completed = (
        final_approval.get(
            "status"
        )
        ==
        "approved"
        and
        final_approval.get(
            "approved"
        )
        is True
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
                completed=(
                    thumbnail.get(
                        "brief_ready"
                    )
                    is True
                ),
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
                completed=(
                    thumbnail.get(
                        "asset_ready"
                    )
                    is True
                ),
                detail=(
                    "A thumbnail PNG canónica "
                    "foi produzida e validada "
                    "por SHA256."
                ),
            ),

        "copyright_review_completed":
            checklist_entry(
                label=(
                    "Revisão de direitos concluída"
                ),
                completed=(
                    rights_review_completed
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
                    "humana ligada ao conteúdo."
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
    evidence: dict[str, Any],
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

    content_id = slugify(
        title
    )

    validate_dashboard_model(
        dashboard,
        expected_title=title,
    )

    validate_evidence(
        evidence,
        expected_content_id=content_id,
    )

    metadata = build_metadata(
        content,
        dashboard,
    )

    thumbnail = build_thumbnail(
        content,
        evidence,
    )

    checklist = build_checklist(
        metadata=metadata,
        thumbnail=thumbnail,
        evidence=evidence,
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
            content_id,

        "metadata":
            metadata,

        "thumbnail":
            thumbnail,

        "checklist":
            checklist,

        "readiness":
            readiness,

        "evidence":
            {
                "version":
                    evidence[
                        "evidence_version"
                    ],

                "content_identity_sha256":
                    evidence[
                        "content_identity"
                    ][
                        "sha256"
                    ],

                "thumbnail_sha256":
                    evidence[
                        "thumbnail"
                    ][
                        "sha256"
                    ],

                "rights_review_status":
                    evidence[
                        "rights_review"
                    ][
                        "status"
                    ],

                "final_approval_status":
                    evidence[
                        "final_approval"
                    ][
                        "status"
                    ],
            },

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
        "evidence",
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

    thumbnail = require_mapping(
        payload.get(
            "thumbnail"
        ),
        "publishing.thumbnail",
    )

    if thumbnail.get(
        "asset_ready"
    ) is not True:
        raise ValueError(
            "A thumbnail canónica deve "
            "estar pronta."
        )

    require_text(
        thumbnail.get(
            "asset_public_path"
        ),
        (
            "publishing.thumbnail."
            "asset_public_path"
        ),
    )

    checklist = require_mapping(
        payload.get(
            "checklist"
        ),
        "publishing.checklist",
    )

    if len(
        checklist
    ) != 8:
        raise ValueError(
            "Publishing checklist deve "
            "conter 8 controlos."
        )

    readiness = require_mapping(
        payload.get(
            "readiness"
        ),
        "publishing.readiness",
    )

    if readiness.get(
        "completion_percent"
    ) != 75:
        raise ValueError(
            "A prontidão esperada após "
            "thumbnail é 75%."
        )

    if readiness.get(
        "blocker_count"
    ) != 2:
        raise ValueError(
            "Devem permanecer exatamente "
            "2 bloqueios."
        )

    if readiness.get(
        "status"
    ) != "blocked":
        raise ValueError(
            "Publishing deve permanecer "
            "BLOCKED até revisão e aprovação."
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
        "FOOTBALL-SHORTS-AI-0031C.3"
    )

    print(
        "PUBLISHING EVIDENCE BINDING"
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

    evidence = load_json(
        EVIDENCE_SOURCE
    )

    publishing = (
        build_publishing_package(
            content,
            dashboard,
            evidence,
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
        "Thumbnail status: READY"
    )

    print(
        "Publication execution enabled: NO"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
