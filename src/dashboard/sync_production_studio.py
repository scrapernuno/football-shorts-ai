from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = ROOT / "output"

DASHBOARD_DATA_DIRECTORY = (
    ROOT
    / "dashboard"
    / "data"
)


@dataclass(frozen=True)
class PackageContract:

    name: str

    source: Path

    target: Path

    required_keys: frozenset[str]


CONTRACTS = (

    PackageContract(

        name=(
            "Content Production Package"
        ),

        source=(
            OUTPUT_DIRECTORY
            / "content_package.json"
        ),

        target=(
            DASHBOARD_DATA_DIRECTORY
            / "content_package.json"
        ),

        required_keys=frozenset(
            {
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
        ),

    ),

    PackageContract(

        name=(
            "Publishing Package"
        ),

        source=(
            OUTPUT_DIRECTORY
            / "publishing_package.json"
        ),

        target=(
            DASHBOARD_DATA_DIRECTORY
            / "publishing_package.json"
        ),

        required_keys=frozenset(
            {
                "package_version",
                "generated_at",
                "source_content_id",
                "metadata",
                "thumbnail",
                "checklist",
                "status",
            }
        ),

    ),

    PackageContract(

        name=(
            "Analytics Package"
        ),

        source=(
            OUTPUT_DIRECTORY
            / "analytics_package.json"
        ),

        target=(
            DASHBOARD_DATA_DIRECTORY
            / "analytics_package.json"
        ),

        required_keys=frozenset(
            {
                "analytics_version",
                "generated_at",
                "content_id",
                "platform",
                "status",
                "metrics",
                "growth_signals",
                "recommendation",
            }
        ),

    ),

)


def require_mapping(
    value: Any,
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
    value: Any,
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


def require_non_empty_string(
    value: Any,
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
            f"{field_name} não pode "
            "estar vazio."
        )

    return normalized


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

    return require_mapping(
        payload,
        str(path),
    )


def validate_exact_required_keys(
    payload: dict[str, Any],
    contract: PackageContract,
) -> None:

    missing = (
        contract.required_keys
        -
        payload.keys()
    )

    if missing:

        raise ValueError(
            f"{contract.name} incompleto: "
            f"{sorted(missing)}"
        )


def validate_content_package(
    payload: dict[str, Any],
) -> None:

    source_topic = require_mapping(
        payload.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    require_non_empty_string(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    require_non_empty_string(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )

    priority = source_topic.get(
        "priority"
    )

    if priority != 1:

        raise ValueError(
            "content.source_topic.priority "
            "deve ser 1."
        )

    script = require_mapping(
        payload.get(
            "script"
        ),
        "content.script",
    )

    for key in (
        "hook",
        "introduction",
        "development",
        "climax",
        "ending",
        "call_to_action",
    ):

        require_non_empty_string(
            script.get(
                key
            ),
            f"content.script.{key}",
        )

    voiceover = require_mapping(
        payload.get(
            "voiceover"
        ),
        "content.voiceover",
    )

    require_non_empty_string(
        voiceover.get(
            "language"
        ),
        "content.voiceover.language",
    )

    segments = require_list(
        voiceover.get(
            "segments"
        ),
        "content.voiceover.segments",
    )

    if not segments:

        raise ValueError(
            "content.voiceover.segments "
            "não pode estar vazio."
        )

    scenes = require_list(
        payload.get(
            "scenes"
        ),
        "content.scenes",
    )

    if not scenes:

        raise ValueError(
            "content.scenes não pode "
            "estar vazio."
        )

    expected_scene_numbers = list(
        range(
            1,
            len(scenes) + 1,
        )
    )

    observed_scene_numbers = []

    for index, value in enumerate(
        scenes,
        start=1,
    ):

        scene = require_mapping(
            value,
            f"content.scenes[{index - 1}]",
        )

        observed_scene_numbers.append(
            scene.get(
                "scene_number"
            )
        )

        duration = scene.get(
            "duration_seconds"
        )

        if (
            not isinstance(
                duration,
                int,
            )
            or isinstance(
                duration,
                bool,
            )
            or duration <= 0
        ):

            raise ValueError(
                "content.scenes"
                f"[{index - 1}]"
                ".duration_seconds "
                "deve ser inteiro positivo."
            )

    if (
        observed_scene_numbers
        != expected_scene_numbers
    ):

        raise ValueError(
            "content.scenes deve usar "
            "scene_number sequencial."
        )


def validate_publishing_package(
    payload: dict[str, Any],
) -> None:

    require_non_empty_string(
        payload.get(
            "source_content_id"
        ),
        "publishing.source_content_id",
    )

    metadata = require_mapping(
        payload.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    require_non_empty_string(
        metadata.get(
            "platform"
        ),
        "publishing.metadata.platform",
    )

    require_non_empty_string(
        metadata.get(
            "title"
        ),
        "publishing.metadata.title",
    )

    hashtags = require_list(
        metadata.get(
            "hashtags"
        ),
        "publishing.metadata.hashtags",
    )

    if not hashtags:

        raise ValueError(
            "publishing.metadata.hashtags "
            "não pode estar vazio."
        )

    thumbnail = require_mapping(
        payload.get(
            "thumbnail"
        ),
        "publishing.thumbnail",
    )

    require_non_empty_string(
        thumbnail.get(
            "text_overlay"
        ),
        "publishing.thumbnail.text_overlay",
    )

    require_mapping(
        payload.get(
            "checklist"
        ),
        "publishing.checklist",
    )

    status = require_non_empty_string(
        payload.get(
            "status"
        ),
        "publishing.status",
    )

    if status not in {
        "draft",
        "ready",
        "scheduled",
        "published",
    }:

        raise ValueError(
            "publishing.status inválido."
        )


def validate_analytics_package(
    payload: dict[str, Any],
) -> None:

    require_non_empty_string(
        payload.get(
            "content_id"
        ),
        "analytics.content_id",
    )

    require_non_empty_string(
        payload.get(
            "platform"
        ),
        "analytics.platform",
    )

    status = require_non_empty_string(
        payload.get(
            "status"
        ),
        "analytics.status",
    )

    if status not in {
        "pending",
        "collecting",
        "complete",
    }:

        raise ValueError(
            "analytics.status inválido."
        )

    metrics = require_mapping(
        payload.get(
            "metrics"
        ),
        "analytics.metrics",
    )

    required_metrics = {
        "views",
        "likes",
        "comments",
        "shares",
        "average_watch_time_seconds",
        "retention_percent",
        "subscribers_gained",
    }

    missing_metrics = (
        required_metrics
        -
        metrics.keys()
    )

    if missing_metrics:

        raise ValueError(
            "analytics.metrics incompleto: "
            f"{sorted(missing_metrics)}"
        )

    for key in required_metrics:

        value = metrics[key]

        if (
            not isinstance(
                value,
                (int, float),
            )
            or isinstance(
                value,
                bool,
            )
            or value < 0
        ):

            raise ValueError(
                f"analytics.metrics.{key} "
                "deve ser numérico não negativo."
            )

    require_mapping(
        payload.get(
            "growth_signals"
        ),
        "analytics.growth_signals",
    )

    require_mapping(
        payload.get(
            "recommendation"
        ),
        "analytics.recommendation",
    )


def validate_cross_package_identity(
    content: dict[str, Any],
    publishing: dict[str, Any],
    analytics: dict[str, Any],
) -> None:

    content_title = require_non_empty_string(
        require_mapping(
            content.get(
                "source_topic"
            ),
            "content.source_topic",
        ).get(
            "title"
        ),
        "content.source_topic.title",
    )

    publishing_title = require_non_empty_string(
        require_mapping(
            publishing.get(
                "metadata"
            ),
            "publishing.metadata",
        ).get(
            "title"
        ),
        "publishing.metadata.title",
    )

    if content_title != publishing_title:

        raise ValueError(
            "O título do Content Package "
            "não corresponde ao título "
            "do Publishing Package."
        )

    source_content_id = require_non_empty_string(
        publishing.get(
            "source_content_id"
        ),
        "publishing.source_content_id",
    )

    analytics_content_id = require_non_empty_string(
        analytics.get(
            "content_id"
        ),
        "analytics.content_id",
    )

    if (
        source_content_id
        != analytics_content_id
    ):

        raise ValueError(
            "analytics.content_id não "
            "corresponde a "
            "publishing.source_content_id."
        )


def canonical_json_bytes(
    payload: dict[str, Any],
) -> bytes:

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )
        .encode(
            "utf-8"
        )
    )


def sha256_payload(
    payload: dict[str, Any],
) -> str:

    return hashlib.sha256(
        canonical_json_bytes(
            payload
        )
    ).hexdigest()


def write_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.parent
        /
        f".{path.name}.tmp"
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


def verify_written_payload(
    contract: PackageContract,
    expected_payload: dict[str, Any],
) -> None:

    observed_payload = load_json(
        contract.target
    )

    expected_hash = sha256_payload(
        expected_payload
    )

    observed_hash = sha256_payload(
        observed_payload
    )

    if observed_hash != expected_hash:

        raise ValueError(
            f"Falha de integridade após "
            f"sincronização de "
            f"{contract.name}."
        )


def main() -> int:

    print("=" * 70)

    print(
        "FOOTBALL-SHORTS-AI-0030B"
    )

    print(
        "PRODUCTION STUDIO "
        "DATA SYNCHRONIZATION"
    )

    print(
        "VALIDATE BEFORE WRITE"
    )

    print(
        "ATOMIC TARGET REPLACEMENT"
    )

    print("=" * 70)

    loaded: dict[
        str,
        dict[str, Any],
    ] = {}

    for contract in CONTRACTS:

        print(
            f"LOAD={contract.source}"
        )

        payload = load_json(
            contract.source
        )

        validate_exact_required_keys(
            payload,
            contract,
        )

        loaded[
            contract.name
        ] = payload

    content = loaded[
        "Content Production Package"
    ]

    publishing = loaded[
        "Publishing Package"
    ]

    analytics = loaded[
        "Analytics Package"
    ]

    validate_content_package(
        content
    )

    validate_publishing_package(
        publishing
    )

    validate_analytics_package(
        analytics
    )

    validate_cross_package_identity(
        content,
        publishing,
        analytics,
    )

    print(
        "PRE_WRITE_VALIDATION=PASS"
    )

    for contract in CONTRACTS:

        payload = loaded[
            contract.name
        ]

        write_json_atomically(
            contract.target,
            payload,
        )

        verify_written_payload(
            contract,
            payload,
        )

        print(
            f"SYNCED={contract.target}"
        )

        print(
            f"SHA256={sha256_payload(payload)}"
        )

    print("=" * 70)

    print(
        "PRODUCTION_STUDIO_SYNC=PASS"
    )

    print(
        f"CONTENT_TITLE="
        f"{content['source_topic']['title']}"
    )

    print(
        f"PUBLISHING_STATUS="
        f"{publishing['status']}"
    )

    print(
        f"ANALYTICS_STATUS="
        f"{analytics['status']}"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
