from __future__ import annotations

import ast
import json

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DISCOVERY_REQUEST_PATH = (
    ROOT
    /
    "output"
    /
    "trend_discovery_request.json"
)

PUBLIC_DISCOVERY_REQUEST_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "trend_discovery_request.json"
)

DISCOVERY_RESULTS_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_discovery_results.json"
)

PUBLIC_DISCOVERY_RESULTS_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "tiktok_trend_discovery_results.json"
)

INTELLIGENCE_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_intelligence.json"
)

PUBLIC_INTELLIGENCE_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "tiktok_trend_intelligence.json"
)

VARIANTS_PATH = (
    ROOT
    /
    "output"
    /
    "platform_variants.json"
)

PUBLIC_VARIANTS_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "platform_variants.json"
)


SOURCE_FILES = (
    ROOT / "src" / "trends" / "build_trend_discovery_request.py",
    ROOT / "src" / "trends" / "discover_tiktok_trends.py",
    ROOT / "src" / "trends" / "build_tiktok_trend_intelligence.py",
    ROOT / "src" / "trends" / "build_platform_variants.py",
    ROOT / "src" / "trends" / "sync_trend_intelligence.py",
)


FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "urllib.request",
    "socket",
    "aiohttp",
    "selenium",
    "playwright",
}


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

    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            f"{path} deve conter "
            "um objeto JSON."
        )

    return payload


def certify_ast(
    path: Path,
) -> None:

    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        ),
        filename=str(
            path
        ),
    )

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if alias.name in FORBIDDEN_IMPORT_ROOTS:

                    raise ValueError(
                        "Import de rede proibido: "
                        f"{alias.name}"
                    )

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            module = node.module or ""

            if module in FORBIDDEN_IMPORT_ROOTS:

                raise ValueError(
                    "Import de rede proibido: "
                    f"{module}"
                )


def safe_mapping(
    value: object,
) -> dict[str, Any]:

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else
        {}
    )


def main() -> int:

    print(
        "="
        *
        70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031C.4D"
    )

    print(
        "TIKTOK TREND GOVERNANCE "
        "CERTIFICATION"
    )

    print(
        "="
        *
        70
    )

    for source in SOURCE_FILES:

        certify_ast(
            source
        )

    discovery_request = load_json(
        DISCOVERY_REQUEST_PATH
    )

    public_discovery_request = load_json(
        PUBLIC_DISCOVERY_REQUEST_PATH
    )

    discovery_results = load_json(
        DISCOVERY_RESULTS_PATH
    )

    public_discovery_results = load_json(
        PUBLIC_DISCOVERY_RESULTS_PATH
    )

    intelligence = load_json(
        INTELLIGENCE_PATH
    )

    public_intelligence = load_json(
        PUBLIC_INTELLIGENCE_PATH
    )

    variants = load_json(
        VARIANTS_PATH
    )

    public_variants = load_json(
        PUBLIC_VARIANTS_PATH
    )

    if discovery_request != public_discovery_request:

        raise ValueError(
            "Discovery request público "
            "não corresponde ao output."
        )

    if discovery_results != public_discovery_results:

        raise ValueError(
            "Discovery results públicos "
            "não correspondem ao output."
        )

    if intelligence != public_intelligence:

        raise ValueError(
            "Trend intelligence pública "
            "não corresponde ao output."
        )

    if variants != public_variants:

        raise ValueError(
            "Platform variants público "
            "não corresponde ao output."
        )

    request_binding = safe_mapping(
        discovery_request.get(
            "topic_binding"
        )
    )

    intelligence_content = safe_mapping(
        intelligence.get(
            "content"
        )
    )

    intelligence_request = safe_mapping(
        intelligence.get(
            "discovery_request"
        )
    )

    if discovery_request.get(
        "source_mode"
    ) != "automatic_winning_topic_binding":

        raise ValueError(
            "Binding automático da notícia "
            "vencedora está ausente."
        )

    if discovery_request.get(
        "status"
    ) != "discovery_required":

        raise ValueError(
            "Estado do discovery request inválido."
        )

    if request_binding.get(
        "content_identity_sha256"
    ) != intelligence_content.get(
        "identity_sha256"
    ):

        raise ValueError(
            "Discovery request não corresponde "
            "à trend intelligence."
        )

    if intelligence_request.get(
        "content_identity_sha256"
    ) != request_binding.get(
        "content_identity_sha256"
    ):

        raise ValueError(
            "Trend intelligence perdeu o binding "
            "ao discovery request."
        )

    request_boundaries = safe_mapping(
        discovery_request.get(
            "capability_boundaries"
        )
    )

    if request_boundaries.get(
        "network_execution_enabled"
    ) is not True:

        raise ValueError(
            "Discovery server-side não foi ativada."
        )

    if request_boundaries.get(
        "network_execution_scope"
    ) != "github_actions_server_side_web_search":

        raise ValueError(
            "Âmbito server-side inválido."
        )

    if request_boundaries.get(
        "web_search_provider"
    ) != "openai_web_search":

        raise ValueError(
            "Provider de discovery inválido."
        )

    for key in (
        "browser_api_calls_enabled",
        "direct_tiktok_api_calls_enabled",
        "global_display_api_trend_search_assumed",
        "third_party_download_allowed",
        "watermark_removal_allowed",
    ):

        if request_boundaries.get(
            key
        ) is not False:

            raise ValueError(
                f"Discovery boundary inválida: {key}."
            )

    results_binding = safe_mapping(
        discovery_results.get(
            "topic_binding"
        )
    )

    results_provider = safe_mapping(
        discovery_results.get(
            "provider"
        )
    )

    results_execution = safe_mapping(
        discovery_results.get(
            "execution"
        )
    )

    results_governance = safe_mapping(
        discovery_results.get(
            "governance"
        )
    )

    if results_binding.get(
        "content_identity_sha256"
    ) != request_binding.get(
        "content_identity_sha256"
    ):

        raise ValueError(
            "Resultados de discovery perderam "
            "o binding à notícia atual."
        )

    if results_provider.get(
        "provider_id"
    ) != "openai_web_search":

        raise ValueError(
            "Resultados não foram produzidos "
            "pelo provider governado."
        )

    if results_execution.get(
        "server_side_network_execution_enabled"
    ) is not True:

        raise ValueError(
            "Execução server-side não foi evidenciada."
        )

    for key in (
        "browser_api_calls_enabled",
        "direct_tiktok_api_calls_enabled",
        "automatic_candidate_selection_enabled",
    ):

        if results_execution.get(key) is not False:

            raise ValueError(
                f"Execution boundary inválida: {key}."
            )

    for candidate in discovery_results.get(
        "video_candidates",
        [],
    ):

        if not isinstance(candidate, dict):

            raise ValueError(
                "Video candidate de discovery inválido."
            )

        if candidate.get(
            "intended_usage_mode"
        ) != "reference_only":

            raise ValueError(
                "Discovery atribuiu uso executável "
                "a um vídeo."
            )

        if candidate.get(
            "creator_license_status"
        ) != "none":

            raise ValueError(
                "Discovery inventou licença de creator."
            )

    for candidate in discovery_results.get(
        "sound_candidates",
        [],
    ):

        if not isinstance(candidate, dict):

            raise ValueError(
                "Sound candidate de discovery inválido."
            )

        if candidate.get(
            "rights_classification"
        ) != "reference_only":

            raise ValueError(
                "Discovery atribuiu direitos a um som."
            )

        if candidate.get(
            "commercial_library_confirmed"
        ) is not False:

            raise ValueError(
                "Discovery confirmou CML sem prova separada."
            )

    for key in (
        "third_party_download_allowed",
        "watermark_removal_allowed",
        "publication_execution_enabled",
    ):

        if results_governance.get(key) is not False:

            raise ValueError(
                f"Governance de discovery inválida: {key}."
            )

    if discovery_request.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Discovery request ativou publicação."
        )

    boundaries = safe_mapping(
        intelligence.get(
            "official_capability_boundaries"
        )
    )

    if boundaries.get(
        "display_api_global_trend_search_available"
    ) is not False:

        raise ValueError(
            "Display API indevidamente "
            "declarada como pesquisa global."
        )

    for key in (
        "third_party_download_allowed",
        "watermark_removal_allowed",
    ):

        if boundaries.get(
            key
        ) is not False:

            raise ValueError(
                f"{key} deve permanecer false."
            )

    if intelligence.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Trend intelligence ativou "
            "publicação."
        )

    governance = safe_mapping(
        variants.get(
            "governance"
        )
    )

    if governance.get(
        "native_remix_platform_bound"
    ) is not True:

        raise ValueError(
            "Remix nativo deixou de estar "
            "limitado à plataforma."
        )

    if governance.get(
        "cross_platform_third_party_use_requires_license"
    ) is not True:

        raise ValueError(
            "Uso cross-platform deixou de "
            "exigir licença."
        )

    if governance.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Variants ativaram publicação."
        )

    print(
        "AUTOMATIC_TOPIC_BINDING=PASS"
    )

    print(
        "TREND_DISCOVERY_REQUEST=PASS"
    )

    print(
        "DISCOVERY_REQUEST_PUBLIC_INTEGRITY=PASS"
    )

    print(
        "GOVERNED_SERVER_SIDE_WEB_SEARCH=PASS"
    )

    print(
        "DISCOVERED_REFERENCES_REFERENCE_ONLY=PASS"
    )

    print(
        "AST_NETWORK_ISOLATION=PASS"
    )

    print(
        "DISPLAY_API_BOUNDARY=PASS"
    )

    print(
        "NATIVE_REMIX_PLATFORM_BOUND=PASS"
    )

    print(
        "COMMERCIAL_MUSIC_GOVERNANCE=PASS"
    )

    print(
        "THIRD_PARTY_DOWNLOAD_BLOCKED=PASS"
    )

    print(
        "WATERMARK_REMOVAL_BLOCKED=PASS"
    )

    print(
        "CROSS_PLATFORM_LICENSE_GATE=PASS"
    )

    print(
        "PUBLIC_DATA_INTEGRITY=PASS"
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
