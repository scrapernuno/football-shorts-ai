from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Literal

from knowledge.fixtures import OfflineFootballKnowledgeFixture
from knowledge.live_provider import LiveFootballRssKnowledgeProvider


KnowledgeMode = Literal["offline_fixture", "live"]
ProviderFactory = Callable[[], object]


@dataclass(frozen=True, slots=True)
class KnowledgeRuntimeConfig:
    """Fail-closed runtime selection for the governed knowledge provider."""

    mode: KnowledgeMode = "offline_fixture"
    allow_live_network: bool = False

    @classmethod
    def from_environment(cls) -> "KnowledgeRuntimeConfig":
        raw_mode = os.getenv(
            "FOOTBALL_SHORTS_KNOWLEDGE_MODE",
            "offline_fixture",
        ).strip()
        if raw_mode not in {"offline_fixture", "live"}:
            raise ValueError(
                "FOOTBALL_SHORTS_KNOWLEDGE_MODE must be "
                "'offline_fixture' or 'live'"
            )

        raw_allow = os.getenv(
            "FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK",
            "false",
        ).strip().lower()
        if raw_allow not in {"true", "false"}:
            raise ValueError(
                "FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK must be 'true' or 'false'"
            )

        return cls(
            mode=raw_mode,
            allow_live_network=raw_allow == "true",
        )


def select_knowledge_provider(
    config: KnowledgeRuntimeConfig | None = None,
    *,
    offline_factory: ProviderFactory = OfflineFootballKnowledgeFixture,
    live_factory: ProviderFactory = LiveFootballRssKnowledgeProvider,
) -> object:
    """Resolve exactly one provider without silently enabling network access."""

    resolved = config or KnowledgeRuntimeConfig.from_environment()

    if resolved.mode == "offline_fixture":
        return offline_factory()

    if resolved.mode == "live":
        if not resolved.allow_live_network:
            raise RuntimeError(
                "live knowledge mode requires "
                "FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK=true"
            )
        return live_factory()

    raise ValueError(f"unsupported knowledge mode: {resolved.mode}")
