from __future__ import annotations

import pytest

from discovery.environment_secret_resolver import (
    EnvironmentSecretPolicy,
    EnvironmentSecretResolver,
)
from discovery.youtube_data_api_http_client import YouTubeDataApiHttpError


def test_disabled_resolver_does_not_read_secret() -> None:
    resolver = EnvironmentSecretResolver(
        policy=EnvironmentSecretPolicy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret"},
    )
    with pytest.raises(YouTubeDataApiHttpError, match="not activated"):
        resolver.resolve_text("YOUTUBE_DATA_API_KEY")


def test_resolves_only_allowlisted_secret() -> None:
    resolver = EnvironmentSecretResolver(
        policy=EnvironmentSecretPolicy(enabled=True),
        environment={"YOUTUBE_DATA_API_KEY": "secret-value", "OTHER": "no"},
    )
    assert resolver.resolve_text("YOUTUBE_DATA_API_KEY") == "secret-value"
    with pytest.raises(YouTubeDataApiHttpError, match="not allowlisted"):
        resolver.resolve_text("OTHER")


def test_missing_or_blank_secret_fails_closed() -> None:
    for environment in ({}, {"YOUTUBE_DATA_API_KEY": "   "}):
        resolver = EnvironmentSecretResolver(
            policy=EnvironmentSecretPolicy(enabled=True),
            environment=environment,
        )
        with pytest.raises(YouTubeDataApiHttpError, match="unavailable"):
            resolver.resolve_text("YOUTUBE_DATA_API_KEY")


def test_policy_rejects_duplicate_or_invalid_names() -> None:
    with pytest.raises(YouTubeDataApiHttpError, match="unique"):
        EnvironmentSecretPolicy(
            allowed_secret_names=("YOUTUBE_DATA_API_KEY", "YOUTUBE_DATA_API_KEY")
        ).validate()
    with pytest.raises(YouTubeDataApiHttpError, match="invalid"):
        EnvironmentSecretPolicy(allowed_secret_names=("youtube-key",)).validate()
