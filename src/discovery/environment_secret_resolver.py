"""
FOOTBALL-SHORTS-AI-0055B
CONTROLLED ENVIRONMENT SECRET RESOLVER

Minimal allowlisted resolver for deployment environments such as GitHub Actions.
It reads one configured environment variable on demand and never logs, hashes,
serializes or persists the secret value.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from discovery.youtube_data_api_http_client import YouTubeDataApiHttpError


@dataclass(frozen=True)
class EnvironmentSecretPolicy:
    enabled: bool = False
    allowed_secret_names: tuple[str, ...] = ("YOUTUBE_DATA_API_KEY",)

    def validate(self) -> None:
        if not self.allowed_secret_names:
            raise YouTubeDataApiHttpError("at least one allowed secret name is required")
        if len(set(self.allowed_secret_names)) != len(self.allowed_secret_names):
            raise YouTubeDataApiHttpError("allowed secret names must be unique")
        for name in self.allowed_secret_names:
            if not name or not name.replace("_", "").isalnum() or name.upper() != name:
                raise YouTubeDataApiHttpError("invalid allowed environment secret name")


class EnvironmentSecretResolver:
    def __init__(
        self,
        *,
        policy: EnvironmentSecretPolicy,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        policy.validate()
        self._policy = policy
        self._environment = environment if environment is not None else os.environ

    def resolve_text(self, secret_name: str) -> str:
        if not self._policy.enabled:
            raise YouTubeDataApiHttpError("environment secret resolution is not activated")
        if secret_name not in self._policy.allowed_secret_names:
            raise YouTubeDataApiHttpError("secret name is not allowlisted")
        value = self._environment.get(secret_name)
        if not isinstance(value, str) or not value.strip():
            raise YouTubeDataApiHttpError("required environment secret is unavailable")
        return value


__all__ = ["EnvironmentSecretPolicy", "EnvironmentSecretResolver"]
