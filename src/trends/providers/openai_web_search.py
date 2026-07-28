from __future__ import annotations

from typing import Mapping, Any

from trends.providers.base import (
    ProviderActivationRequired,
    TrendDiscoveryProvider,
    TrendProviderReadiness,
)


class OpenAIWebSearchProvider(TrendDiscoveryProvider):
    provider_id = "openai_web_search"

    def evaluate(
        self,
        environment: Mapping[str, str],
    ) -> TrendProviderReadiness:
        priority = int(self.config.get("priority", 99))
        enabled = self.config.get("enabled") is True
        network_allowed = (
            self.config.get("network_execution_allowed") is True
        )
        required_environment = tuple(
            str(name)
            for name in self.config.get(
                "required_environment",
                ["OPENAI_API_KEY"],
            )
        )
        missing = tuple(
            name
            for name in required_environment
            if not str(environment.get(name, "")).strip()
        )
        executable = enabled and network_allowed and not missing

        if not enabled:
            status = "disabled"
            reason = "provider_disabled"
        elif not network_allowed:
            status = "activation_blocked"
            reason = "network_execution_not_allowed"
        elif missing:
            status = "configuration_required"
            reason = "required_environment_missing"
        else:
            status = "ready"
            reason = "fallback_ready"

        return TrendProviderReadiness(
            provider_id=self.provider_id,
            priority=priority,
            status=status,
            executable=executable,
            network_execution_allowed=network_allowed,
            reason=reason,
            missing_environment=missing,
            metadata={
                "fallback_only": (
                    self.config.get("fallback_only") is True
                ),
                "activation_state": self.config.get(
                    "activation_state",
                    "unknown",
                ),
            },
        )

    def execute(
        self,
        request: Mapping[str, Any],
        environment: Mapping[str, str],
    ) -> dict[str, Any]:
        readiness = self.evaluate(environment)

        if not readiness.executable:
            raise ProviderActivationRequired(
                f"{self.provider_id}: {readiness.reason}"
            )

        raise ProviderActivationRequired(
            "OpenAI Web Search execution remains owned by "
            "src/trends/discover_tiktok_trends.py in phase 0031C.4E."
        )
