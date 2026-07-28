from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from assets.contracts import (
    ProviderCapability,
    RightsBasis,
    SubjectScope,
    require_mapping,
    require_positive_integer,
    require_text,
)
from assets.providers.base import (
    MediaProviderAdapter,
)
from assets.providers.imago import (
    ImagoAdapter,
)
from assets.providers.owned_library import (
    OwnedLibraryAdapter,
)
from assets.providers.pexels import (
    PexelsFallbackAdapter,
)
from assets.providers.reuters_connect import (
    ReutersConnectAdapter,
)
from assets.providers.tiktok_licensed_ugc import (
    TikTokLicensedUGCAdapter,
)


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_POLICY_PATH = (
    ROOT
    /
    "config"
    /
    "media_provider_policy.json"
)


ADAPTER_TYPES = {
    "owned_library":
        OwnedLibraryAdapter,

    "imago":
        ImagoAdapter,

    "reuters_connect":
        ReutersConnectAdapter,

    "tiktok_licensed_ugc":
        TikTokLicensedUGCAdapter,

    "pexels":
        PexelsFallbackAdapter,
}


PROVIDER_DESCRIPTORS = {
    "owned_library":
        {
            "display_name":
                "Biblioteca própria",

            "integration_kind":
                "local_catalog",

            "documentation_url":
                "internal://owned-media-library",

            "license_url":
                None,

            "notes":
                "Primeira prioridade quando "
                "existe prova de propriedade.",
        },

    "imago":
        {
            "display_name":
                "IMAGO",

            "integration_kind":
                "commercial_api_or_ftp",

            "documentation_url":
                (
                    "https://www.imago-images.com/"
                    "ftp-push"
                ),

            "license_url":
                (
                    "https://www.imago-images.com/"
                    "license-info"
                ),

            "notes":
                "Fornecedor editorial de "
                "imagem e vídeo desportivo.",
        },

    "reuters_connect":
        {
            "display_name":
                "Reuters Connect",

            "integration_kind":
                "commercial_subscription_api",

            "documentation_url":
                (
                    "https://reutersagency.com/"
                    "content-delivery-platforms/"
                    "reuters-connect/"
                ),

            "license_url":
                None,

            "notes":
                "Conteúdo multimédia editorial "
                "e noticioso.",
        },

    "tiktok_licensed_ugc":
        {
            "display_name":
                "TikTok Licensed UGC",

            "integration_kind":
                "manual_native_remix_or_creator_license",

            "documentation_url":
                (
                    "https://developers.tiktok.com/"
                    "doc/embed-videos/"
                ),

            "license_url":
                None,

            "notes":
                "Dueto/Costura nativos no TikTok "
                "ou ficheiro original licenciado "
                "diretamente pelo creator.",
        },

    "pexels":
        {
            "display_name":
                "Pexels",

            "integration_kind":
                "public_api_fallback",

            "documentation_url":
                (
                    "https://www.pexels.com/"
                    "api/documentation/"
                ),

            "license_url":
                (
                    "https://www.pexels.com/"
                    "legal-pages/license/"
                ),

            "notes":
                "Fallback exclusivo para "
                "B-roll genérico.",
        },
}


def load_policy(
    path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Política em falta: {path}"
        )

    try:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"Política JSON inválida: {exc}"
        ) from exc

    return require_mapping(
        payload,
        "media_provider_policy",
    )


def parse_subject_scopes(
    values: object,
    field_name: str,
) -> tuple[
    SubjectScope,
    ...
]:

    if not isinstance(
        values,
        list,
    ):

        raise ValueError(
            f"{field_name} deve ser lista."
        )

    return tuple(
        SubjectScope(
            require_text(
                value,
                f"{field_name}[]",
            )
        )
        for value in values
    )


def parse_rights_bases(
    values: object,
    field_name: str,
) -> tuple[
    RightsBasis,
    ...
]:

    if not isinstance(
        values,
        list,
    ):

        raise ValueError(
            f"{field_name} deve ser lista."
        )

    return tuple(
        RightsBasis(
            require_text(
                value,
                f"{field_name}[]",
            )
        )
        for value in values
    )


def build_registry(
    policy: dict[str, Any],
) -> tuple[
    MediaProviderAdapter,
    ...
]:

    provider_order = policy.get(
        "provider_order"
    )

    if not isinstance(
        provider_order,
        list,
    ):

        raise ValueError(
            "provider_order deve ser lista."
        )

    provider_configs = require_mapping(
        policy.get(
            "providers"
        ),
        "policy.providers",
    )

    adapters: list[
        MediaProviderAdapter
    ] = []

    for position, raw_provider_id in enumerate(
        provider_order,
        start=1,
    ):

        provider_id = require_text(
            raw_provider_id,
            "provider_order[]",
        )

        if provider_id not in ADAPTER_TYPES:

            raise ValueError(
                "Provider sem adapter: "
                f"{provider_id}"
            )

        raw_config = require_mapping(
            provider_configs.get(
                provider_id
            ),
            f"policy.providers.{provider_id}",
        )

        if raw_config.get(
            "enabled"
        ) is not True:

            continue

        priority = require_positive_integer(
            raw_config.get(
                "priority"
            ),
            (
                "policy.providers."
                f"{provider_id}.priority"
            ),
        )

        if priority != position:

            raise ValueError(
                "Prioridade do provider "
                f"{provider_id} não corresponde "
                "à provider_order."
            )

        descriptor = PROVIDER_DESCRIPTORS[
            provider_id
        ]

        media_types = raw_config.get(
            "allowed_media_types"
        )

        if (
            not isinstance(
                media_types,
                list,
            )
            or
            not media_types
        ):

            raise ValueError(
                "allowed_media_types inválido "
                f"para {provider_id}."
            )

        capability = ProviderCapability(
            provider_id=provider_id,

            display_name=descriptor[
                "display_name"
            ],

            priority=priority,

            integration_kind=descriptor[
                "integration_kind"
            ],

            media_types=tuple(
                require_text(
                    value,
                    (
                        "allowed_media_types"
                        f"[{provider_id}]"
                    ),
                )
                for value in media_types
            ),

            subject_scopes=(
                parse_subject_scopes(
                    raw_config.get(
                        "allowed_subject_scope"
                    ),
                    (
                        "allowed_subject_scope."
                        f"{provider_id}"
                    ),
                )
            ),

            rights_bases=(
                parse_rights_bases(
                    raw_config.get(
                        "allowed_rights_basis"
                    ),
                    (
                        "allowed_rights_basis."
                        f"{provider_id}"
                    ),
                )
            ),

            configured=(
                raw_config.get(
                    "configured"
                )
                is True
            ),

            contract_required=(
                raw_config.get(
                    "contract_required"
                )
                is True
            ),

            documentation_url=descriptor[
                "documentation_url"
            ],

            license_url=descriptor[
                "license_url"
            ],

            notes=descriptor[
                "notes"
            ],
        )

        adapter_type = ADAPTER_TYPES[
            provider_id
        ]

        adapters.append(
            adapter_type(
                capability
            )
        )

    return tuple(
        adapters
    )
