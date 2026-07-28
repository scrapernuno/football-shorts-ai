from __future__ import annotations

import ast
import json

from pathlib import Path
from typing import Any

from trends.providers.registry import (
    load_provider_policy,
    resolve_provider_route,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    ROOT
    / "config"
    / "tiktok_trend_provider_policy.json"
)
TIKTOK_PROVIDER_SOURCE = (
    ROOT
    / "src"
    / "trends"
    / "providers"
    / "tiktok_business_discovery.py"
)

EXPECTED_PROVIDER_ORDER = [
    "tiktok_business_discovery",
    "openai_web_search",
]

EXPECTED_ENDPOINTS = [
    "/discovery/trending_list/",
    "/discovery/detail/",
    "/discovery/video_list/",
    "/discovery/cml/trending_list/",
    "/discovery/cml/video_list/",
    "/discovery/trending/search/",
    "/discovery/trending/search/keyword/",
]

FORBIDDEN_IMPORTS = {
    "requests",
    "httpx",
    "urllib.request",
    "socket",
    "aiohttp",
    "selenium",
    "playwright",
}


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} deve ser um objeto."
        )

    return value


def certify_no_network_imports(
    path: Path,
) -> None:
    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        ),
        filename=str(path),
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS:
                    raise ValueError(
                        "Import de rede proibido no "
                        f"provider pré-ativação: {alias.name}"
                    )

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if module in FORBIDDEN_IMPORTS:
                raise ValueError(
                    "Import de rede proibido no "
                    f"provider pré-ativação: {module}"
                )


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.4E")
    print("OFFICIAL TIKTOK BUSINESS DISCOVERY PROVIDER")
    print("PRE-ACTIVATION CERTIFICATION")
    print("NO TIKTOK NETWORK - NO SECRET READ - NO PUBLICATION")
    print("=" * 70)

    policy = load_provider_policy(
        POLICY_PATH
    )

    if policy.get("mode") != "pre_activation_fail_closed":
        raise ValueError(
            "Modo de pre-activation inválido."
        )

    if policy.get("provider_order") != EXPECTED_PROVIDER_ORDER:
        raise ValueError(
            "Ordem de providers inválida."
        )

    providers = require_mapping(
        policy.get("providers"),
        "policy.providers",
    )
    tiktok = require_mapping(
        providers.get("tiktok_business_discovery"),
        "providers.tiktok_business_discovery",
    )

    if tiktok.get("activation_state") != "pending_approval":
        raise ValueError(
            "Aplicação TikTok não está marcada como pending_approval."
        )

    if tiktok.get("configured") is not False:
        raise ValueError(
            "Provider TikTok foi marcado como configurado prematuramente."
        )

    if tiktok.get("pre_activation_only") is not True:
        raise ValueError(
            "Provider TikTok perdeu o bloqueio de pre-activation."
        )

    if tiktok.get("network_execution_allowed") is not False:
        raise ValueError(
            "Rede TikTok foi ativada antes da aprovação."
        )

    if tiktok.get("discovery_endpoints") != EXPECTED_ENDPOINTS:
        raise ValueError(
            "Lista oficial de Discovery endpoints inválida."
        )

    governance = require_mapping(
        policy.get("governance"),
        "policy.governance",
    )

    for field_name in (
        "browser_api_calls_enabled",
        "public_secret_material_allowed",
        "automatic_candidate_selection_enabled",
        "direct_tiktok_api_calls_enabled_before_approval",
        "third_party_download_allowed",
        "watermark_removal_allowed",
        "publication_execution_enabled",
    ):
        if governance.get(field_name) is not False:
            raise ValueError(
                f"{field_name} deve permanecer false."
            )

    simulated_environment = {
        "OPENAI_API_KEY": "configured-for-readiness-test",
        "TIKTOK_BUSINESS_APP_ID": "",
        "TIKTOK_BUSINESS_APP_SECRET": "",
        "TIKTOK_BUSINESS_ACCESS_TOKEN": "",
    }
    route = resolve_provider_route(
        policy=policy,
        environment=simulated_environment,
    )

    if route.get("selected_provider_id") != "openai_web_search":
        raise ValueError(
            "OpenAI Web Search não foi preservado como fallback."
        )

    if route.get("fallback_used") is not True:
        raise ValueError(
            "Fallback não foi atribuído."
        )

    decisions = {
        decision["provider_id"]: decision
        for decision in route.get("decisions", [])
        if isinstance(decision, dict)
    }
    tiktok_decision = require_mapping(
        decisions.get("tiktok_business_discovery"),
        "route.tiktok_business_discovery",
    )

    if tiktok_decision.get("executable") is not False:
        raise ValueError(
            "Provider TikTok ficou executável antes da aprovação."
        )

    if tiktok_decision.get("reason") != "application_pending_approval":
        raise ValueError(
            "Atribuição do bloqueio pending incorreta."
        )

    serialized = json.dumps(
        route,
        ensure_ascii=False,
        sort_keys=True,
    )

    for secret_marker in (
        "configured-for-readiness-test",
        "TIKTOK_BUSINESS_APP_SECRET_VALUE",
        "TIKTOK_BUSINESS_ACCESS_TOKEN_VALUE",
    ):
        if secret_marker in serialized:
            raise ValueError(
                "Material secreto apareceu na decisão pública."
            )

    certify_no_network_imports(
        TIKTOK_PROVIDER_SOURCE
    )

    print("PROVIDER_ORDER=PASS")
    print("TIKTOK_APPLICATION_STATUS=PENDING_APPROVAL")
    print("TIKTOK_PROVIDER_EXECUTABLE=NO")
    print("TIKTOK_API_NETWORK_CALL=NO")
    print("OPENAI_WEB_SEARCH_FALLBACK=PASS")
    print("OFFICIAL_DISCOVERY_ENDPOINT_INVENTORY=PASS")
    print("SECRET_MATERIAL_EXPOSURE=NO")
    print("AUTOMATIC_SELECTION_ENABLED=NO")
    print("THIRD_PARTY_DOWNLOAD_ALLOWED=NO")
    print("WATERMARK_REMOVAL_ALLOWED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("PRE_ACTIVATION_CERTIFICATION=PASS")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
