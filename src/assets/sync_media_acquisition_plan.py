from __future__ import annotations

import hashlib
import json

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

SOURCE = (
    ROOT
    /
    "output"
    /
    "media_acquisition_plan.json"
)

TARGET = (
    ROOT
    /
    "dashboard"
    /
    "data"
    /
    "media_acquisition_plan.json"
)


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

    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            f"{path} deve conter "
            "um objeto JSON."
        )

    return payload


def canonical_bytes(
    payload: dict[str, Any],
) -> bytes:

    return json.dumps(
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


def sha256_payload(
    payload: dict[str, Any],
) -> str:

    return hashlib.sha256(
        canonical_bytes(
            payload
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

    payload = load_json(
        SOURCE
    )

    write_atomically(
        TARGET,
        payload,
    )

    observed = load_json(
        TARGET
    )

    if (
        sha256_payload(
            payload
        )
        !=
        sha256_payload(
            observed
        )
    ):

        raise ValueError(
            "Falha de integridade "
            "na sincronização."
        )

    print(
        "MEDIA_ACQUISITION_PLAN_SYNC=PASS"
    )

    print(
        f"TARGET={TARGET}"
    )

    print(
        f"SHA256="
        f"{sha256_payload(payload)}"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
