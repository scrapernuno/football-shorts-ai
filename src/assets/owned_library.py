from __future__ import annotations

from typing import Any

from assets.contracts import (
    ProviderCapability,
    SceneAcquisitionRequest,
)
from assets.providers.base import (
    MediaProviderAdapter,
)


class OwnedLibraryAdapter(
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
                    "da biblioteca própria.",
            }

        return {
            "provider_id":
                self.capability.provider_id,

            "supported":
                True,

            "network_execution":
                False,

            "inventory_required":
                True,

            "lookup_fields":
                [
                    "content_id",
                    "scene_number",
                    "search_terms",
                    "media_type",
                    "rights_owner",
                    "ownership_evidence",
                ],

            "required_rights_basis":
                "owned",
        }
