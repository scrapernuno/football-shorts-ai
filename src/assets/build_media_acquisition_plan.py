from __future__ import annotations

import hashlib
import json
import re
import unicodedata

from pathlib import Path
from typing import Any

from assets.contracts import (
    AcquisitionStatus,
    RightsStatus,
    SceneAcquisitionRequest,
    SubjectScope,
    require_list,
    require_mapping,
    require_positive_integer,
    require_text,
)
from assets.provider_registry import (
    build_registry,
    load_policy,
)


ROOT = Path(__file__).resolve().parents[2]

CONTENT_SOURCE = (
    ROOT
    /
    "output"
    /
    "content_package.json"
)

POLICY_SOURCE = (
    ROOT
    /
    "config"
    /
    "media_provider_policy.json"
)

OUTPUT = (
    ROOT
    /
    "output"
    /
    "media_acquisition_plan.json"
)


PLAN_VERSION = "1.0"


GENERIC_VISUAL_MARKERS = {
    "stadium",
    "crowd",
    "fans",
    "fan reaction",
    "football ball",
    "soccer ball",
    "training equipment",
    "boots",
    "tunnel",
    "empty pitch",
    "generic",
}


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro em falta: {path}"
        )

    try:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"JSON inválido em {path}: {exc}"
        ) from exc

    return require_mapping(
        payload,
        str(
            path
        ),
    )


def write_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.parent
        /
        f".{path.name}.tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        +
        "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def slugify(
    value: str,
) -> str:

    normalized = (
        unicodedata.normalize(
            "NFKD",
            value,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode(
            "ascii"
        )
        .lower()
    )

    return (
        re.sub(
            r"[^a-z0-9]+",
            "-",
            normalized,
        )
        .strip(
            "-"
        )
        or
        "football-short"
    )


def canonical_sha256(
    payload: object,
) -> str:

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def classify_asset_role(
    scene_number: int,
) -> str:

    roles = {
        1:
            "opening_hook",

        2:
            "editorial_context",

        3:
            "main_moment",

        4:
            "audience_reaction",
    }

    return roles.get(
        scene_number,
        "supporting_broll",
    )


def classify_subject_scope(
    *,
    visual_instruction: str,
    asset_role: str,
) -> SubjectScope:

    normalized = (
        visual_instruction
        .strip()
        .lower()
    )

    generic_marker = any(
        marker in normalized
        for marker in GENERIC_VISUAL_MARKERS
    )

    if (
        asset_role
        in {
            "audience_reaction",
            "supporting_broll",
        }
        and
        generic_marker
    ):

        return (
            SubjectScope
            .GENERIC_FOOTBALL
        )

    return (
        SubjectScope
        .SPECIFIC_FOOTBALL
    )


def build_search_terms(
    *,
    title: str,
    hook: str,
    visual_instruction: str,
    caption_text: str,
    subject_scope: SubjectScope,
) -> tuple[
    str,
    ...
]:

    terms = [
        title,
        hook,
        visual_instruction,
        caption_text,
    ]

    if (
        subject_scope
        ==
        SubjectScope.GENERIC_FOOTBALL
    ):

        terms.append(
            "generic football b-roll"
        )

    observed: set[
        str
    ] = set()

    result: list[
        str
    ] = []

    for value in terms:

        normalized = " ".join(
            value.split()
        ).strip()

        key = normalized.lower()

        if (
            not normalized
            or
            key in observed
        ):

            continue

        observed.add(
            key
        )

        result.append(
            normalized
        )

    return tuple(
        result
    )


def build_request(
    *,
    title: str,
    hook: str,
    scene: dict[str, Any],
) -> SceneAcquisitionRequest:

    scene_number = (
        require_positive_integer(
            scene.get(
                "scene_number"
            ),
            "scene.scene_number",
        )
    )

    duration_seconds = (
        require_positive_integer(
            scene.get(
                "duration_seconds"
            ),
            "scene.duration_seconds",
        )
    )

    visual_instruction = require_text(
        scene.get(
            "visual_instruction"
        ),
        "scene.visual_instruction",
    )

    caption_text = require_text(
        scene.get(
            "caption_text"
        ),
        "scene.caption_text",
    )

    asset_role = classify_asset_role(
        scene_number
    )

    subject_scope = (
        classify_subject_scope(
            visual_instruction=(
                visual_instruction
            ),
            asset_role=asset_role,
        )
    )

    return SceneAcquisitionRequest(
        scene_number=scene_number,

        asset_role=asset_role,

        visual_instruction=(
            visual_instruction
        ),

        caption_text=caption_text,

        duration_seconds=duration_seconds,

        subject_scope=subject_scope,

        media_type_preference=(
            "video",
            "image",
        ),

        search_terms=build_search_terms(
            title=title,
            hook=hook,
            visual_instruction=(
                visual_instruction
            ),
            caption_text=caption_text,
            subject_scope=subject_scope,
        ),
    )


def route_status(
    *,
    configured: bool,
    provider_id: str,
    inventory_ready: bool,
) -> str:

    if provider_id == "owned_library":

        return (
            AcquisitionStatus.PLANNED.value
            if inventory_ready
            else
            AcquisitionStatus
            .INVENTORY_REQUIRED
            .value
        )

    return (
        AcquisitionStatus.PLANNED.value
        if configured
        else
        AcquisitionStatus
        .CONFIGURATION_REQUIRED
        .value
    )


def build_plan(
    *,
    content: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:

    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    title = require_text(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    hook = require_text(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )

    scenes = require_list(
        content.get(
            "scenes"
        ),
        "content.scenes",
    )

    if not scenes:

        raise ValueError(
            "Content Package sem cenas."
        )

    adapters = build_registry(
        policy
    )

    provider_configs = require_mapping(
        policy.get(
            "providers"
        ),
        "policy.providers",
    )

    provider_registry = []

    for adapter in adapters:

        capability = adapter.capability

        provider_config = require_mapping(
            provider_configs.get(
                capability.provider_id
            ),
            (
                "policy.providers."
                f"{capability.provider_id}"
            ),
        )

        provider_registry.append(
            {
                "provider_id":
                    capability.provider_id,

                "display_name":
                    capability.display_name,

                "priority":
                    capability.priority,

                "integration_kind":
                    capability.integration_kind,

                "configured":
                    capability.configured,

                "contract_required":
                    capability.contract_required,

                "inventory_ready":
                    (
                        provider_config.get(
                            "inventory_ready"
                        )
                        is True
                    ),

                "media_types":
                    list(
                        capability.media_types
                    ),

                "subject_scopes":
                    [
                        scope.value
                        for scope
                        in capability.subject_scopes
                    ],

                "rights_bases":
                    [
                        basis.value
                        for basis
                        in capability.rights_bases
                    ],

                "documentation_url":
                    capability.documentation_url,

                "license_url":
                    capability.license_url,

                "notes":
                    capability.notes,
            }
        )

    scene_plans = []

    global_blockers: set[
        str
    ] = set()

    for index, raw_scene in enumerate(
        scenes
    ):

        scene = require_mapping(
            raw_scene,
            f"content.scenes[{index}]",
        )

        request = build_request(
            title=title,
            hook=hook,
            scene=scene,
        )

        routes = []

        viable_configured_route = False

        for adapter in adapters:

            capability = adapter.capability

            provider_config = (
                require_mapping(
                    provider_configs.get(
                        capability.provider_id
                    ),
                    (
                        "policy.providers."
                        f"{capability.provider_id}"
                    ),
                )
            )

            allowed = adapter.supports(
                request
            )

            inventory_ready = (
                provider_config.get(
                    "inventory_ready"
                )
                is True
            )

            activation_status = (
                route_status(
                    configured=(
                        capability.configured
                    ),
                    provider_id=(
                        capability.provider_id
                    ),
                    inventory_ready=(
                        inventory_ready
                    ),
                )
                if allowed
                else
                AcquisitionStatus
                .BLOCKED
                .value
            )

            descriptor = (
                adapter.describe_acquisition(
                    request
                )
            )

            route_ready = (
                inventory_ready
                if capability.provider_id
                ==
                "owned_library"
                else
                capability.configured
            )

            if (
                allowed
                and
                route_ready
            ):

                viable_configured_route = True

            if (
                allowed
                and
                activation_status
                !=
                AcquisitionStatus
                .PLANNED
                .value
            ):

                global_blockers.add(
                    (
                        capability.provider_id
                        +
                        ":"
                        +
                        activation_status
                    )
                )

            routes.append(
                {
                    "provider_id":
                        capability.provider_id,

                    "priority":
                        capability.priority,

                    "allowed":
                        allowed,

                    "configured":
                        capability.configured,

                    "activation_status":
                        activation_status,

                    "allowed_rights_bases":
                        [
                            basis.value
                            for basis
                            in capability.rights_bases
                        ],

                    "descriptor":
                        descriptor,

                    "reason":
                        (
                            descriptor.get(
                                "reason"
                            )
                            if isinstance(
                                descriptor,
                                dict,
                            )
                            else
                            None
                        ),
                }
            )

        scene_plans.append(
            {
                "scene_number":
                    request.scene_number,

                "asset_role":
                    request.asset_role,

                "duration_seconds":
                    request.duration_seconds,

                "visual_instruction":
                    request.visual_instruction,

                "caption_text":
                    request.caption_text,

                "subject_scope":
                    request.subject_scope.value,

                "media_type_preference":
                    list(
                        request
                        .media_type_preference
                    ),

                "search_terms":
                    list(
                        request.search_terms
                    ),

                "provider_route":
                    routes,

                "selected_asset":
                    None,

                "acquisition_status":
                    (
                        AcquisitionStatus
                        .PLANNED
                        .value
                        if viable_configured_route
                        else
                        AcquisitionStatus
                        .CONFIGURATION_REQUIRED
                        .value
                    ),

                "rights_status":
                    RightsStatus
                    .UNRESOLVED
                    .value,

                "blocked_when_no_permitted_asset":
                    True,
            }
        )

    content_id = slugify(
        title
    )

    generated_at = require_text(
        content.get(
            "generated_at"
        ),
        "content.generated_at",
    )

    ready_for_acquisition = all(
        scene[
            "acquisition_status"
        ]
        ==
        AcquisitionStatus.PLANNED.value
        for scene in scene_plans
    )

    return {
        "plan_version":
            PLAN_VERSION,

        "generated_at":
            generated_at,

        "content_id":
            content_id,

        "content_title":
            title,

        "content_identity_sha256":
            canonical_sha256(
                {
                    "title":
                        title,

                    "hook":
                        hook,

                    "generated_at":
                        generated_at,

                    "scene_count":
                        len(
                            scenes
                        ),
                }
            ),

        "policy":
            {
                "policy_id":
                    policy[
                        "policy_id"
                    ],

                "mode":
                    policy[
                        "mode"
                    ],

                "publication_execution_enabled":
                    policy[
                        "publication_execution_enabled"
                    ],

                "automatic_license_purchase_enabled":
                    policy[
                        "automatic_license_purchase_enabled"
                    ],

                "unlicensed_media_allowed":
                    policy[
                        "unlicensed_media_allowed"
                    ],

                "editorial_exception_requires_manual_review":
                    policy[
                        "editorial_exception_requires_manual_review"
                    ],
            },

        "provider_registry":
            provider_registry,

        "scene_plans":
            scene_plans,

        "activation_blockers":
            sorted(
                global_blockers
            ),

        "ready_for_acquisition":
            ready_for_acquisition,

        "status":
            (
                AcquisitionStatus.PLANNED.value
                if ready_for_acquisition
                else
                AcquisitionStatus
                .CONFIGURATION_REQUIRED
                .value
            ),

        "publication_execution_enabled":
            False,
    }


def validate_plan(
    payload: dict[str, Any],
) -> None:

    required = {
        "plan_version",
        "generated_at",
        "content_id",
        "content_title",
        "content_identity_sha256",
        "policy",
        "provider_registry",
        "scene_plans",
        "activation_blockers",
        "ready_for_acquisition",
        "status",
        "publication_execution_enabled",
    }

    missing = required - payload.keys()

    if missing:

        raise ValueError(
            "Media Acquisition Plan "
            f"incompleto: {sorted(missing)}"
        )

    policy = require_mapping(
        payload.get(
            "policy"
        ),
        "plan.policy",
    )

    if policy.get(
        "mode"
    ) != "copyright_aware_fail_closed":

        raise ValueError(
            "Modo de direitos inválido."
        )

    if policy.get(
        "unlicensed_media_allowed"
    ) is not False:

        raise ValueError(
            "Media sem licença deve "
            "permanecer bloqueada."
        )

    if policy.get(
        "editorial_exception_requires_manual_review"
    ) is not True:

        raise ValueError(
            "Exceção editorial exige "
            "revisão manual."
        )

    if payload.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Publicação deve permanecer "
            "desativada."
        )

    providers = require_list(
        payload.get(
            "provider_registry"
        ),
        "plan.provider_registry",
    )

    provider_ids = [
        require_mapping(
            value,
            "plan.provider_registry[]",
        ).get(
            "provider_id"
        )
        for value in providers
    ]

    if provider_ids != [
        "owned_library",
        "imago",
        "reuters_connect",
        "tiktok_licensed_ugc",
        "pexels",
    ]:

        raise ValueError(
            "Ordem de providers inválida."
        )

    scenes = require_list(
        payload.get(
            "scene_plans"
        ),
        "plan.scene_plans",
    )

    if not scenes:

        raise ValueError(
            "Plano sem cenas."
        )

    for index, raw_scene in enumerate(
        scenes
    ):

        scene = require_mapping(
            raw_scene,
            f"plan.scene_plans[{index}]",
        )

        routes = require_list(
            scene.get(
                "provider_route"
            ),
            (
                "plan.scene_plans"
                f"[{index}].provider_route"
            ),
        )

        pexels_route = next(
            (
                require_mapping(
                    route,
                    "provider_route[]",
                )
                for route in routes
                if (
                    isinstance(
                        route,
                        dict,
                    )
                    and
                    route.get(
                        "provider_id"
                    )
                    ==
                    "pexels"
                )
            ),
            None,
        )

        if pexels_route is None:

            raise ValueError(
                "Rota Pexels em falta."
            )

        if (
            scene.get(
                "subject_scope"
            )
            ==
            "specific_football"
            and
            pexels_route.get(
                "allowed"
            )
            is not False
        ):

            raise ValueError(
                "Pexels não pode representar "
                "pessoa ou evento específico."
            )

        if scene.get(
            "selected_asset"
        ) is not None:

            raise ValueError(
                "Nenhum asset pode ser "
                "selecionado nesta fase."
            )

        if scene.get(
            "rights_status"
        ) != "unresolved":

            raise ValueError(
                "Direitos devem permanecer "
                "não resolvidos."
            )


def main() -> int:

    print(
        "="
        *
        70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031C.4A"
    )

    print(
        "MULTI-PROVIDER FOOTBALL "
        "MEDIA ACQUISITION PLAN"
    )

    print(
        "COPYRIGHT-AWARE FAIL-CLOSED"
    )

    print(
        "NO NETWORK - NO SECRET READ"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print(
        "="
        *
        70
    )

    content = load_json(
        CONTENT_SOURCE
    )

    policy = load_policy(
        POLICY_SOURCE
    )

    plan = build_plan(
        content=content,
        policy=policy,
    )

    validate_plan(
        plan
    )

    write_json_atomically(
        OUTPUT,
        plan,
    )

    print(
        "MEDIA_ACQUISITION_PLAN=PASS"
    )

    print(
        f"CONTENT_ID={plan['content_id']}"
    )

    print(
        f"SCENE_COUNT="
        f"{len(plan['scene_plans'])}"
    )

    print(
        "PROVIDER_ORDER="
        +
        ",".join(
            provider[
                "provider_id"
            ]
            for provider
            in plan[
                "provider_registry"
            ]
        )
    )

    print(
        f"STATUS={plan['status'].upper()}"
    )

    print(
        f"ACTIVATION_BLOCKERS="
        f"{len(plan['activation_blockers'])}"
    )

    print(
        "UNLICENSED_MEDIA_ALLOWED=NO"
    )

    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
    )

    print(
        "="
        *
        70
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
