from __future__ import annotations

from typing import Any

from assets.contracts import (
    ProviderCapability,
    SceneAcquisitionRequest,
    SubjectScope,
)
from assets.providers.base import (
    MediaProviderAdapter,
)


class PexelsFallbackAdapter(
    MediaProviderAdapter
):

    def __init__(
        self,
        capability: ProviderCapability,
    ) -> None:

        super().__init__(
            capability
        )


    def supports(
        self,
        request: SceneAcquisitionRequest,
    ) -> bool:

        if (
            request.subject_scope
            !=
            SubjectScope.GENERIC_FOOTBALL
        ):

            return False

        return super().supports(
            request
        )


    def describe_acquisition(
        self,
        request: SceneAcquisitionRequest,
    ) -> dict[str, Any]:

        supported = self.supports(
            request
        )

        return {
            "provider_id":
                self.capability.provider_id,

            "supported":
                supported,

            "network_execution":
                False,

            "activation_required":
                (
                    supported
                    and
                    not self.capability.configured
                ),

            "generic_broll_only":
                True,

            "named_person_or_event_allowed":
                False,

            "search_intent":
                (
                    {
                        "terms":
                            list(
                                request.search_terms
                            ),

                        "media_types":
                            list(
                                request.media_type_preference
                            ),
                    }
                    if supported
                    else
                    None
                ),

            "required_rights_basis":
                "licensed",

            "reason":
                (
                    "Fallback permitido apenas "
                    "para B-roll genérico."
                    if supported
                    else
                    "Bloqueado para jogadores, "
                    "clubes ou eventos específicos."
                ),
        }
