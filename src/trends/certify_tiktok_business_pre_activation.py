from __future__ import annotations

from typing import Mapping, Any

from trends.providers.base import (
    ProviderActivationRequired,
    TrendDiscoveryProvider,
    TrendProviderReadiness,
)


class TikTokBusinessDiscoveryProvider(TrendDiscoveryProvider):
    provider_id = "tiktok_business_discovery"

    def evaluate(
        self,
        environment: Mapping[str, str],
    ) -> TrendProviderReadiness:
        priority = int(self.config.get("priority", 99))
        enabled = self.config.get("enabled") is True
        activation_state = str(
            self.config.get("activation_state", "unknown")
        ).strip().lower()
        configured = self.config.get("configured") is True
        pre_activation_only = (
            self.config.get("pre_activation_only") is True
        )
        network_allowed = (
            self.config.get("network_execution_allowed") is True
        )
        required_environment = tuple(
            str(name)
            for name in self.config.get(
                "required_environment",
                (),
            )
        )
        missing = tuple(
            name
            for name in required_environment
            if not str(environment.get(name, "")).strip()
        )

        executable = (
            enabled
            and activation_state == "approved"
            and configured
            and not pre_activation_only
            and network_allowed
            and not missing
        )

        if not enabled:
            status = "disabled"
            reason = "provider_disabled"
        elif activation_state != "approved":
            status = "configuration_required"
            reason = "application_pending_approval"
        elif pre_activation_only:
            status = "activation_blocked"
            reason = "pre_activation_only"
        elif not configured:
            status = "configuration_required"
            reason = "provider_not_configured"
        elif not network_allowed:
            status = "activation_blocked"
            reason = "network_execution_not_allowed"
        elif missing:
            status = "configuration_required"
            reason = "required_environment_missing"
        else:
            status = "ready"
            reason = "official_provider_ready"

        return TrendProviderReadiness(
            provider_id=self.provider_id,
            priority=priority,
            status=status,
            executable=executable,
            network_execution_allowed=network_allowed,
            reason=reason,
            missing_environment=missing,
            metadata={
                "activation_state": activation_state,
                "configured": configured,
                "pre_activation_only": pre_activation_only,
                "required_permission": self.config.get(
                    "required_permission"
                ),
                "base_url": self.config.get("base_url"),
                "discovery_endpoints": list(
                    self.config.get("discovery_endpoints", [])
                ),
                "secret_values_exposed": False,
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
            "Real TikTok API execution is intentionally absent from "
            "FOOTBALL-SHORTS-AI-0031C.4E pre-activation."
        )
