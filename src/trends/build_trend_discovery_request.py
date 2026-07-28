from __future__ import annotations

import hashlib
import json
import re

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CONTENT_PATH = (
    ROOT
    /
    "output"
    /
    "content_package.json"
)

INTAKE_PATH = (
    ROOT
    /
    "config"
    /
    "tiktok_trend_intake.json"
)

OUTPUT_PATH = (
    ROOT
    /
    "output"
    /
    "trend_discovery_request.json"
)


DISCOVERY_REQUEST_VERSION = "1.0"


SPACE_PATTERN = re.compile(r"\s+")


STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "por",
    "que",
    "um",
    "uma",
    "the",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "to",
    "with",
}


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

    normalized = SPACE_PATTERN.sub(
        " ",
        value.strip(),
    )

    if not normalized:

        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro em falta: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return require_mapping(
        payload,
        str(path),
    )


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


def canonical_sha256(
    value: object,
) -> str:

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def unique_texts(
    values: list[str],
) -> list[str]:

    output: list[str] = []
    observed: set[str] = set()

    for value in values:

        normalized = SPACE_PATTERN.sub(
            " ",
            value.strip(),
        )

        identity = normalized.casefold()

        if (
            normalized
            and
            identity not in observed
        ):

            output.append(
                normalized
            )

            observed.add(
                identity
            )

    return output


def extract_keyword_query(
    title: str,
) -> str | None:

    tokens = re.findall(
        r"[^\W_]+",
        title,
        flags=re.UNICODE,
    )

    keywords = [
        token
        for token in tokens
        if (
            len(token) >= 3
            and
            token.casefold() not in STOPWORDS
        )
    ]

    keywords = unique_texts(
        keywords
    )[
        :6
    ]

    if not keywords:

        return None

    return " ".join(
        keywords
    )


def build_search_queries(
    title: str,
    hook: str,
) -> list[str]:

    keyword_query = extract_keyword_query(
        title
    )

    raw_queries = [
        title,
    ]

    if re.search(
        r"\b(?:futebol|football)\b",
        title,
        flags=re.IGNORECASE,
    ) is None:

        raw_queries.append(
            f"{title} futebol"
        )

    if keyword_query is not None:

        raw_queries.append(
            keyword_query
        )

    if (
        hook.casefold()
        !=
        title.casefold()
    ):

        raw_queries.append(
            hook[
                :180
            ]
        )

    queries = unique_texts(
        raw_queries
    )[
        :4
    ]

    if not queries:

        raise ValueError(
            "Não foi possível gerar queries "
            "de discovery."
        )

    return queries


def build_discovery_request(
    content: dict[str, Any],
    intake: dict[str, Any],
) -> dict[str, Any]:

    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    title = require_text(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    hook = require_text(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )

    content_generated_at = require_text(
        content.get(
            "generated_at"
        ),
        "content.generated_at",
    )

    region = require_text(
        intake.get(
            "region"
        ),
        "intake.region",
    ).upper()

    content_identity = canonical_sha256(
        {
            "title":
                title,

            "hook":
                hook,

            "generated_at":
                content_generated_at,
        }
    )

    return {
        "discovery_request_version":
            DISCOVERY_REQUEST_VERSION,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source_mode":
            "automatic_winning_topic_binding",

        "platform":
            "tiktok",

        "region":
            region,

        "topic_binding":
            {
                "content_title":
                    title,

                "content_hook":
                    hook,

                "content_generated_at":
                    content_generated_at,

                "content_identity_sha256":
                    content_identity,
            },

        "search_queries":
            build_search_queries(
                title,
                hook,
            ),

        "requested_assets":
            [
                "trend_video_reference",
                "trend_sound_reference",
                "hashtag_reference",
            ],

        "candidate_intake":
            {
                "path":
                    "config/tiktok_trend_intake.json",

                "mode":
                    "manual_governed_intake",

                "automatic_candidate_selection":
                    False,

                "rights_evidence_required":
                    True,
            },

        "capability_boundaries":
            {
                "network_execution_enabled":
                    False,

                "browser_api_calls_enabled":
                    False,

                "global_display_api_trend_search_assumed":
                    False,

                "third_party_download_allowed":
                    False,

                "watermark_removal_allowed":
                    False,
            },

        "status":
            "discovery_required",

        "publication_execution_enabled":
            False,
    }


def validate_discovery_request(
    payload: dict[str, Any],
) -> None:

    if payload.get(
        "source_mode"
    ) != "automatic_winning_topic_binding":

        raise ValueError(
            "Binding automático da notícia "
            "vencedora está ausente."
        )

    topic_binding = require_mapping(
        payload.get(
            "topic_binding"
        ),
        "request.topic_binding",
    )

    for field_name in (
        "content_title",
        "content_hook",
        "content_generated_at",
        "content_identity_sha256",
    ):

        require_text(
            topic_binding.get(
                field_name
            ),
            f"request.topic_binding.{field_name}",
        )

    queries = require_list(
        payload.get(
            "search_queries"
        ),
        "request.search_queries",
    )

    normalized_queries = [
        require_text(
            query,
            "request.search_queries[]",
        )
        for query in queries
    ]

    if not normalized_queries:

        raise ValueError(
            "Discovery request sem queries."
        )

    if len(
        normalized_queries
    ) != len(
        {
            query.casefold()
            for query in normalized_queries
        }
    ):

        raise ValueError(
            "Discovery request contém "
            "queries duplicadas."
        )

    boundaries = require_mapping(
        payload.get(
            "capability_boundaries"
        ),
        "request.capability_boundaries",
    )

    for field_name in (
        "network_execution_enabled",
        "browser_api_calls_enabled",
        "global_display_api_trend_search_assumed",
        "third_party_download_allowed",
        "watermark_removal_allowed",
    ):

        if boundaries.get(
            field_name
        ) is not False:

            raise ValueError(
                f"{field_name} deve permanecer false."
            )

    candidate_intake = require_mapping(
        payload.get(
            "candidate_intake"
        ),
        "request.candidate_intake",
    )

    if candidate_intake.get(
        "automatic_candidate_selection"
    ) is not False:

        raise ValueError(
            "Seleção automática de candidatos "
            "deve permanecer desativada."
        )

    if candidate_intake.get(
        "rights_evidence_required"
    ) is not True:

        raise ValueError(
            "Evidência de direitos deve "
            "permanecer obrigatória."
        )

    if payload.get(
        "status"
    ) != "discovery_required":

        raise ValueError(
            "Estado do discovery request inválido."
        )

    if payload.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Publicação deve permanecer "
            "desativada."
        )


def build_and_write_discovery_request(
    content: dict[str, Any],
    intake: dict[str, Any],
) -> dict[str, Any]:

    payload = build_discovery_request(
        content,
        intake,
    )

    validate_discovery_request(
        payload
    )

    write_json_atomically(
        OUTPUT_PATH,
        payload,
    )

    return payload


def main() -> int:

    print(
        "="
        *
        70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031C.4C"
    )

    print(
        "AUTOMATIC WINNING-TOPIC BINDING"
    )

    print(
        "TREND DISCOVERY REQUEST"
    )

    print(
        "NO NETWORK - NO BROWSER API"
    )

    print(
        "NO AUTOMATIC SELECTION"
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
        CONTENT_PATH
    )

    intake = load_json(
        INTAKE_PATH
    )

    payload = build_and_write_discovery_request(
        content,
        intake,
    )

    topic_binding = require_mapping(
        payload.get(
            "topic_binding"
        ),
        "request.topic_binding",
    )

    print(
        "TREND_DISCOVERY_REQUEST=PASS"
    )

    print(
        "TOPIC_BINDING=AUTOMATIC"
    )

    print(
        "CONTENT_TITLE="
        f"{topic_binding['content_title']}"
    )

    print(
        "CONTENT_IDENTITY_SHA256="
        f"{topic_binding['content_identity_sha256']}"
    )

    print(
        "SEARCH_QUERY_COUNT="
        f"{len(payload['search_queries'])}"
    )

    print(
        "STATUS=DISCOVERY_REQUIRED"
    )

    print(
        "NETWORK_EXECUTION_ENABLED=NO"
    )

    print(
        "AUTOMATIC_CANDIDATE_SELECTION=NO"
    )

    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
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
