from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Any


class ProviderActivationRequired(RuntimeError):
    """Raised when a trend provider is not authorised for execution."""


@dataclass(frozen=True)
class TrendProviderReadiness:
    provider_id: str
    priority: int
    status: str
    executable: bool
    network_execution_allowed: bool
    reason: str
    missing_environment: tuple[str, ...]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "priority": self.priority,
            "status": self.status,
            "executable": self.executable,
            "network_execution_allowed": self.network_execution_allowed,
            "reason": self.reason,
            "missing_environment": list(self.missing_environment),
            "metadata": dict(self.metadata),
        }


class TrendDiscoveryProvider(ABC):
    provider_id: str

    def __init__(
        self,
        config: Mapping[str, Any],
    ) -> None:
        self._config = dict(config)

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @abstractmethod
    def evaluate(
        self,
        environment: Mapping[str, str],
    ) -> TrendProviderReadiness:
        """Return a secret-free readiness decision."""

    @abstractmethod
    def execute(
        self,
        request: Mapping[str, Any],
        environment: Mapping[str, str],
    ) -> dict[str, Any]:
        """Execute discovery only when explicitly activated."""
