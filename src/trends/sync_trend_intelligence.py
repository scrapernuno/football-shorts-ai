from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

MAPPINGS = (
    (
        ROOT
        /
        "output"
        /
        "tiktok_trend_discovery_results.json",

        ROOT
        /
        "dashboard"
        /
        "data"
        /
        "tiktok_trend_discovery_results.json",
    ),
    (
        ROOT
        /
        "output"
        /
        "trend_discovery_request.json",

        ROOT
        /
        "dashboard"
        /
        "data"
        /
        "trend_discovery_request.json",
    ),
    (
        ROOT
        /
        "output"
        /
        "tiktok_trend_intelligence.json",

        ROOT
        /
        "dashboard"
        /
        "data"
        /
        "tiktok_trend_intelligence.json",
    ),
    (
        ROOT
        /
        "output"
        /
        "platform_variants.json",

        ROOT
        /
        "dashboard"
        /
        "data"
        /
        "platform_variants.json",
    ),
)


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


def digest(
    payload: dict[str, Any],
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


def write_atomically(
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


def main() -> int:

    for source, target in MAPPINGS:

        payload = load_json(
            source
        )

        write_atomically(
            target,
            payload,
        )

        observed = load_json(
            target
        )

        if digest(
            payload
        ) != digest(
            observed
        ):

            raise ValueError(
                "Falha de integridade em "
                f"{target}."
            )

        print(
            "TREND_SYNC=PASS"
            f"|target={target}"
            f"|sha256={digest(payload)}"
        )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
