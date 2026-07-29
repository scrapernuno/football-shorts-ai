from __future__ import annotations

import pytest

from knowledge.fixtures import OfflineFootballKnowledgeFixture
from knowledge.runtime import KnowledgeRuntimeConfig, select_knowledge_provider


class StubLiveProvider:
    pass


def test_default_selection_is_offline_and_network_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FOOTBALL_SHORTS_KNOWLEDGE_MODE", raising=False)
    monkeypatch.delenv("FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK", raising=False)

    provider = select_knowledge_provider()

    assert isinstance(provider, OfflineFootballKnowledgeFixture)


def test_live_mode_requires_explicit_network_authority() -> None:
    config = KnowledgeRuntimeConfig(mode="live", allow_live_network=False)

    with pytest.raises(RuntimeError, match="requires"):
        select_knowledge_provider(
            config,
            live_factory=StubLiveProvider,
        )


def test_live_mode_selects_injected_provider_when_authorised() -> None:
    config = KnowledgeRuntimeConfig(mode="live", allow_live_network=True)

    provider = select_knowledge_provider(
        config,
        live_factory=StubLiveProvider,
    )

    assert isinstance(provider, StubLiveProvider)


def test_environment_selection_accepts_only_governed_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOTBALL_SHORTS_KNOWLEDGE_MODE", "unknown")

    with pytest.raises(ValueError, match="KNOWLEDGE_MODE"):
        KnowledgeRuntimeConfig.from_environment()

    monkeypatch.setenv("FOOTBALL_SHORTS_KNOWLEDGE_MODE", "offline_fixture")
    monkeypatch.setenv("FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK", "yes")

    with pytest.raises(ValueError, match="ALLOW_LIVE_NETWORK"):
        KnowledgeRuntimeConfig.from_environment()


def test_environment_live_authority_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FOOTBALL_SHORTS_KNOWLEDGE_MODE", "live")
    monkeypatch.setenv("FOOTBALL_SHORTS_ALLOW_LIVE_NETWORK", "true")

    config = KnowledgeRuntimeConfig.from_environment()

    assert config.mode == "live"
    assert config.allow_live_network is True
