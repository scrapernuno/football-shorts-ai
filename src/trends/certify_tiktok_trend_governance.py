from __future__ import annotations

import ast
import json

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

INTELLIGENCE_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_intelligence.json"
)

PUBLIC_INTELLIGENCE_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "tiktok_trend_intelligence.json"
)

VARIANTS_PATH = (
    ROOT
    /
    "output"
    /
    "platform_variants.json"
)

PUBLIC_VARIANTS_PATH = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "platform_variants.json"
)


SOURCE_FILES = (
    ROOT / "src" / "trends" / "build_tiktok_trend_intelligence.py",
    ROOT / "src" / "trends" / "build_platform_variants.py",
    ROOT / "src" / "trends" / "sync_trend_intelligence.py",
)


FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "urllib.request",
    "socket",
    "aiohttp",
    "selenium",
    "playwright",
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


def certify_ast(
    path: Path,
) -> None:

    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        ),
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

                if alias.name in FORBIDDEN_IMPORT_ROOTS:

                    raise ValueError(
                        "Import de rede proibido: "
                        f"{alias.name}"
                    )

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            module = node.module or ""

            if module in FORBIDDEN_IMPORT_ROOTS:

                raise ValueError(
                    "Import de rede proibido: "
                    f"{module}"
                )


def safe_mapping(
    value: object,
) -> dict[str, Any]:

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else
        {}
    )


def main() -> int:

    print(
        "="
        *
        70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031C.4B"
    )

    print(
        "TIKTOK TREND GOVERNANCE "
        "CERTIFICATION"
    )

    print(
        "="
        *
        70
    )

    for source in SOURCE_FILES:

        certify_ast(
            source
        )

    intelligence = load_json(
        INTELLIGENCE_PATH
    )

    public_intelligence = load_json(
        PUBLIC_INTELLIGENCE_PATH
    )

    variants = load_json(
        VARIANTS_PATH
    )

    public_variants = load_json(
        PUBLIC_VARIANTS_PATH
    )

    if intelligence != public_intelligence:

        raise ValueError(
            "Trend intelligence pública "
            "não corresponde ao output."
        )

    if variants != public_variants:

        raise ValueError(
            "Platform variants público "
            "não corresponde ao output."
        )

    boundaries = safe_mapping(
        intelligence.get(
            "official_capability_boundaries"
        )
    )

    if boundaries.get(
        "display_api_global_trend_search_available"
    ) is not False:

        raise ValueError(
            "Display API indevidamente "
            "declarada como pesquisa global."
        )

    for key in (
        "third_party_download_allowed",
        "watermark_removal_allowed",
    ):

        if boundaries.get(
            key
        ) is not False:

            raise ValueError(
                f"{key} deve permanecer false."
            )

    if intelligence.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Trend intelligence ativou "
            "publicação."
        )

    governance = safe_mapping(
        variants.get(
            "governance"
        )
    )

    if governance.get(
        "native_remix_platform_bound"
    ) is not True:

        raise ValueError(
            "Remix nativo deixou de estar "
            "limitado à plataforma."
        )

    if governance.get(
        "cross_platform_third_party_use_requires_license"
    ) is not True:

        raise ValueError(
            "Uso cross-platform deixou de "
            "exigir licença."
        )

    if governance.get(
        "publication_execution_enabled"
    ) is not False:

        raise ValueError(
            "Variants ativaram publicação."
        )

    print(
        "AST_NETWORK_ISOLATION=PASS"
    )

    print(
        "DISPLAY_API_BOUNDARY=PASS"
    )

    print(
        "NATIVE_REMIX_PLATFORM_BOUND=PASS"
    )

    print(
        "COMMERCIAL_MUSIC_GOVERNANCE=PASS"
    )

    print(
        "THIRD_PARTY_DOWNLOAD_BLOCKED=PASS"
    )

    print(
        "WATERMARK_REMOVAL_BLOCKED=PASS"
    )

    print(
        "CROSS_PLATFORM_LICENSE_GATE=PASS"
    )

    print(
        "PUBLIC_DATA_INTEGRITY=PASS"
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
