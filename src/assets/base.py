from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from assets.contracts import (
    ProviderCapability,
    SceneAcquisitionRequest,
)


class ProviderActivationRequired(
    RuntimeError
):
    """Raised when a provider lacks configuration."""


class UnsupportedAcquisitionRequest(
    RuntimeError
):
    """Raised when a request violates provider policy."""


class MediaProviderAdapter(ABC):

    def __init__(
        self,
        capability: ProviderCapability,
    ) -> None:

        self._capability = capability


    @property
    def capability(
        self,
    ) -> ProviderCapability:

        return self._capability


    def supports(
        self,
        request: SceneAcquisitionRequest,
    ) -> bool:

        if (
            request.subject_scope
            not in
            self.capability.subject_scopes
        ):

            return False

        return any(
            media_type
            in
            self.capability.media_types
            for media_type
            in
            request.media_type_preference
        )


    def require_activation(
        self,
    ) -> None:

        if not self.capability.configured:

            raise ProviderActivationRequired(
                f"{self.capability.provider_id} "
                "não está configurado."
            )


    @abstractmethod
    def describe_acquisition(
        self,
        request: SceneAcquisitionRequest,
    ) -> dict[str, Any]:
        """Return a network-free acquisition descriptor."""
