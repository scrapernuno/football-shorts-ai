from __future__ import annotations

from typing import Any

from assets.contracts import (
    ProviderCapability,
    SceneAcquisitionRequest,
)
from assets.providers.base import (
    MediaProviderAdapter,
)


class TikTokLicensedUGCAdapter(
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

            "integration_kind":
                self.capability.integration_kind,

            "intake_mode":
                "manual_governed_intake",

            "permitted_usage_modes":
                [
                    "native_duet",
                    "native_stitch",
                    "licensed_ugc",
                ],

            "native_remix_platform":
                "tiktok",

            "cross_platform_requires_creator_license":
                True,

            "cross_platform_requires_original_file":
                True,

            "third_party_download_allowed":
                False,

            "watermark_removal_allowed":
                False,

            "required_rights_basis":
                "licensed",

            "reason":
                (
                    "Pode ser usado como remix "
                    "nativo no TikTok ou como UGC "
                    "licenciado com prova do creator."
                    if supported
                    else
                    "Pedido não suportado pelo "
                    "adapter TikTok Licensed UGC."
                ),
        }
