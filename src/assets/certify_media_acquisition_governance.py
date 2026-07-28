from __future__ import annotations

import ast
import json

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

PLAN_PATH = (
    ROOT
    /
    "output"
    /
    "media_acquisition_plan.json"
)

PUBLIC_PLAN_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "media_acquisition_plan.json"
)

POLICY_PATH = (
    ROOT
    /
    "config"
    /
    "media_provider_policy.json"
)


SOURCE_FILES = (
    ROOT / "src" / "assets" / "contracts.py",
    ROOT / "src" / "assets" / "provider_registry.py",
    ROOT / "src" / "assets" / "build_media_acquisition_plan.py",
    ROOT / "src" / "assets" / "sync_media_acquisition_plan.py",
    ROOT / "src" / "assets" / "providers" / "base.py",
    ROOT / "src" / "assets" / "providers" / "owned_library.py",
    ROOT / "src" / "assets" / "providers" / "imago.py",
    ROOT / "src" / "assets" / "providers" / "reuters_connect.py",
    ROOT / "src" / "assets" / "providers" / "tiktok_licensed_ugc.py",
    ROOT / "src" / "assets" / "providers" / "pexels.py",
)


FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "urllib",
    "socket",
    "aiohttp",
    "ftplib",
}


FORBIDDEN_SECRET_MARKERS = {
    "api_key",
    "access_token",
    "client_secret",
    "password",
    "authorization",
    "bearer",
}


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro em falta: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            f"{path} deve conter "
            "um objeto JSON."
        )

    return payload


def certify_source_file(
    path: Path,
) -> None:

    if not path.is_file():

        raise FileNotFoundError(
            f"Source em falta: {path}"
        )

    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source,
        filename=str(
            path
        ),
    )

    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                root = alias.name.split(
                    ".",
                    1,
                )[
                    0
                ]

                if root in FORBIDDEN_IMPORT_ROOTS:

                    raise ValueError(
                        "Import de rede proibido "
                        f"em {path}: {root}"
                    )

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            module = node.module or ""

            root = module.split(
                ".",
                1,
            )[
                0
            ]

            if root in FORBIDDEN_IMPORT_ROOTS:

                raise ValueError(
                    "Import de rede proibido "
                    f"em {path}: {root}"
                )


def walk_values(
    value: object,
):

    if isinstance(
        value,
        dict,
    ):

        for key, child in value.items():

            yield str(
                key
            )

            yield from walk_values(
                child
            )

    elif isinstance(
        value,
        list,
    ):

        for child in value:

            yield from walk_values(
                child
            )

    elif isinstance(
        value,
        str,
    ):

        yield value


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
        "MEDIA ACQUISITION "
        "GOVERNANCE CERTIFICATION"
    )

    print(
        "AST ONLY - NO NETWORK"
    )

    print(
        "="
        *
        70
    )

    for path in SOURCE_FILES:

        certify_source_file(
            path
        )

    plan = load_json(
        PLAN_PATH
    )

    public_plan = load_json(
        PUBLIC_PLAN_PATH
    )

    policy = load_json(
        POLICY_PATH
    )

    if plan != public_plan:

        raise ValueError(
            "Plano público não corresponde "
            "ao plano produzido."
        )

    if policy.get(
        "mode"
    ) != "copyright_aware_fail_closed":

        raise ValueError(
            "Política fail-closed ausente."
        )

    if policy.get(
        "unlicensed_media_allowed"
    ) is not False:

        raise ValueError(
            "Media sem licença não pode "
            "ser permitida."
        )

    if policy.get(
        "editorial_exception_requires_manual_review"
    ) is not True:

        raise ValueError(
            "Exceção editorial deve exigir "
            "revisão manual."
        )

    if plan.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Publicação não pode ser ativada."
        )

    provider_ids = [
        provider.get(
            "provider_id"
        )
        for provider in plan.get(
            "provider_registry",
            [],
        )
        if isinstance(
            provider,
            dict,
        )
    ]

    if provider_ids != [
        "owned_library",
        "imago",
        "reuters_connect",
        "tiktok_licensed_ugc",
        "pexels",
    ]:

        raise ValueError(
            "Provider order inválida."
        )

    for scene in plan.get(
        "scene_plans",
        [],
    ):

        if not isinstance(
            scene,
            dict,
        ):

            raise ValueError(
                "Cena inválida no plano."
            )

        if scene.get(
            "selected_asset"
        ) is not None:

            raise ValueError(
                "Asset selecionado sem "
                "ativação governada."
            )

        if scene.get(
            "rights_status"
        ) != "unresolved":

            raise ValueError(
                "Direitos resolvidos sem "
                "evidência."
            )

        for route in scene.get(
            "provider_route",
            [],
        ):

            if not isinstance(
                route,
                dict,
            ):

                continue

            if (
                route.get(
                    "provider_id"
                )
                ==
                "pexels"
                and
                scene.get(
                    "subject_scope"
                )
                ==
                "specific_football"
                and
                route.get(
                    "allowed"
                )
                is not False
            ):

                raise ValueError(
                    "Pexels indevidamente "
                    "permitido para conteúdo "
                    "específico."
                )

    searchable = "\n".join(
        walk_values(
            plan
        )
    ).lower()

    for marker in FORBIDDEN_SECRET_MARKERS:

        if marker in searchable:

            raise ValueError(
                "Marcador potencialmente "
                f"secreto no plano: {marker}"
            )

    print(
        "SOURCE_AST_NETWORK_ISOLATION=PASS"
    )

    print(
        "COPYRIGHT_POLICY=PASS"
    )

    print(
        "PROVIDER_ORDER=PASS"
    )

    print(
        "PEXELS_GENERIC_ONLY=PASS"
    )

    print(
        "UNLICENSED_MEDIA_BLOCKED=PASS"
    )

    print(
        "EDITORIAL_EXCEPTION_MANUAL_REVIEW=PASS"
    )

    print(
        "SECRET_MATERIAL_ABSENT=PASS"
    )

    print(
        "PUBLIC_PLAN_INTEGRITY=PASS"
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
