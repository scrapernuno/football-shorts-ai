from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RightsBasis(str, Enum):

    OWNED = "owned"

    LICENSED = "licensed"

    EDITORIAL_EXCEPTION = (
        "editorial_exception"
    )

    UNLICENSED = "unlicensed"


class SubjectScope(str, Enum):

    SPECIFIC_FOOTBALL = (
        "specific_football"
    )

    GENERIC_FOOTBALL = (
        "generic_football"
    )


class AcquisitionStatus(str, Enum):

    PLANNED = "planned"

    CONFIGURATION_REQUIRED = (
        "configuration_required"
    )

    INVENTORY_REQUIRED = (
        "inventory_required"
    )

    BLOCKED = "blocked"

    DELIVERED = "delivered"


class RightsStatus(str, Enum):

    UNRESOLVED = "unresolved"

    REVIEW_REQUIRED = (
        "review_required"
    )

    APPROVED = "approved"

    BLOCKED = "blocked"


@dataclass(frozen=True)
class ProviderCapability:

    provider_id: str

    display_name: str

    priority: int

    integration_kind: str

    media_types: tuple[str, ...]

    subject_scopes: tuple[
        SubjectScope,
        ...
    ]

    rights_bases: tuple[
        RightsBasis,
        ...
    ]

    configured: bool

    contract_required: bool

    documentation_url: str

    license_url: str | None

    notes: str


@dataclass(frozen=True)
class ProviderRouteDecision:

    provider_id: str

    priority: int

    allowed: bool

    configured: bool

    activation_status: str

    allowed_rights_bases: tuple[
        RightsBasis,
        ...
    ]

    reason: str


@dataclass(frozen=True)
class SceneAcquisitionRequest:

    scene_number: int

    asset_role: str

    visual_instruction: str

    caption_text: str

    duration_seconds: int

    subject_scope: SubjectScope

    media_type_preference: tuple[
        str,
        ...
    ]

    search_terms: tuple[
        str,
        ...
    ]


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "um objeto JSON."
        )

    return value


def require_list(
    value: object,
    field_name: str,
) -> list[Any]:

    if not isinstance(
        value,
        list,
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "uma lista JSON."
        )

    return value


def require_text(
    value: object,
    field_name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):

        raise ValueError(
            f"{field_name} deve ser texto."
        )

    normalized = value.strip()

    if not normalized:

        raise ValueError(
            f"{field_name} não pode "
            "estar vazio."
        )

    return normalized


def require_positive_integer(
    value: object,
    field_name: str,
) -> int:

    if (
        not isinstance(
            value,
            int,
        )
        or
        isinstance(
            value,
            bool,
        )
        or
        value <= 0
    ):

        raise ValueError(
            f"{field_name} deve ser "
            "um inteiro positivo."
        )

    return value
