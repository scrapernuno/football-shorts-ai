from __future__ import annotations

from typing import Any

from assets.contracts import (
    ProviderCapability,
    SceneAcquisitionRequest,
)
from assets.providers.base import (
    MediaProviderAdapter,
)


class ReutersConnectAdapter(
    MediaProviderAdapter
):

    def __init__(
        self,
        capability: ProviderCapability,
    ) -> None:

        super().__init__(
            capability
        )


    def describe_acquisition(
        self,
        request: SceneAcquisitionRequest,
    ) -> dict[str, Any]:

        if not self.supports(
            request
        ):

            return {
                "provider_id":
                    self.capability.provider_id,

                "supported":
                    False,

                "reason":
                    "Pedido fora do âmbito "
                    "multimédia editorial.",
            }

        return {
            "provider_id":
                self.capability.provider_id,

            "supported":
                True,

            "network_execution":
                False,

            "activation_required":
                not self.capability.configured,

            "integration_kind":
                self.capability.integration_kind,

            "contract_schema_status":
                "subscription_documentation_required",

            "search_intent":
                {
                    "terms":
                        list(
                            request.search_terms
                        ),

                    "subject_scope":
                        request.subject_scope.value,

                    "media_types":
                        list(
                            request.media_type_preference
                        ),
                },

            "required_rights_basis":
                "licensed",
        }
