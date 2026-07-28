from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Mapping, Any

from trends.providers.base import (
    TrendDiscoveryProvider,
    TrendProviderReadiness,
)
from trends.providers.openai_web_search import (
    OpenAIWebSearchProvider,
)
from trends.providers.tiktok_business_discovery import (
    TikTokBusinessDiscoveryProvider,
)


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = (
    ROOT
    / "config"
    / "tiktok_trend_provider_policy.json"
)

PROVIDER_TYPES: dict[
    str,
    type[TrendDiscoveryProvider],
] = {
    "tiktok_business_discovery":
        TikTokBusinessDiscoveryProvider,
    "openai_web_search":
        OpenAIWebSearchProvider,
}


def _require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} deve ser um objeto JSON."
        )

    return value


def load_provider_policy(
    path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Política de providers em falta: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return _require_mapping(
        payload,
        "tiktok_trend_provider_policy",
    )


def build_provider_registry(
    policy: Mapping[str, Any],
) -> tuple[TrendDiscoveryProvider, ...]:
    provider_order = policy.get("provider_order")

    if not isinstance(provider_order, list):
        raise ValueError(
            "provider_order deve ser uma lista."
        )

    providers = _require_mapping(
        policy.get("providers"),
        "policy.providers",
    )

    registry: list[TrendDiscoveryProvider] = []

    for position, raw_provider_id in enumerate(
        provider_order,
        start=1,
    ):
        if not isinstance(raw_provider_id, str):
            raise ValueError(
                "provider_order contém um valor inválido."
            )

        provider_id = raw_provider_id.strip()

        if provider_id not in PROVIDER_TYPES:
            raise ValueError(
                f"Provider sem adapter: {provider_id}"
            )

        config = _require_mapping(
            providers.get(provider_id),
            f"policy.providers.{provider_id}",
        )

        priority = config.get("priority")

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or priority != position
        ):
            raise ValueError(
                "Prioridade inválida para "
                f"{provider_id}: {priority!r}"
            )

        registry.append(
            PROVIDER_TYPES[provider_id](
                config
            )
        )

    return tuple(registry)


def resolve_provider_route(
    policy: Mapping[str, Any] | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    resolved_policy = (
        dict(policy)
        if policy is not None
        else load_provider_policy()
    )
    resolved_environment = (
        dict(environment)
        if environment is not None
        else dict(os.environ)
    )
    registry = build_provider_registry(
        resolved_policy
    )
    decisions: list[TrendProviderReadiness] = [
        provider.evaluate(
            resolved_environment
        )
        for provider in registry
    ]

    selected = next(
        (
            decision
            for decision in decisions
            if decision.executable
        ),
        None,
    )

    return {
        "policy_version": resolved_policy.get(
            "policy_version"
        ),
        "mode": resolved_policy.get("mode"),
        "provider_order": [
            provider.provider_id
            for provider in registry
        ],
        "selected_provider_id": (
            selected.provider_id
            if selected is not None
            else None
        ),
        "fallback_used": (
            selected is not None
            and selected.priority > 1
        ),
        "decisions": [
            decision.as_dict()
            for decision in decisions
        ],
        "governance": dict(
            _require_mapping(
                resolved_policy.get("governance"),
                "policy.governance",
            )
        ),
    }
