from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

MODEL_FILE = (
    ROOT
    / "dashboard"
    / "data"
    / "dashboard_model.json"
)

JAVASCRIPT_FILE = (
    ROOT
    / "dashboard"
    / "assets"
    / "dashboard.js"
)


EXPECTED_ROOT_KEYS = {
    "generated_at",
    "channel",
    "top_title",
    "top_hook",
    "viral_probability",
    "metrics",
    "hooks",
    "storyboard",
    "ranking",
}


EXPECTED_METRIC_KEYS = {
    "predicted_views_low",
    "predicted_views_high",
    "confidence_score",
    "predicted_comment_rate_percent",
}


EXPECTED_HOOK_KEYS = {
    "primary",
    "alternatives",
}


EXPECTED_RANKING_KEYS = {
    "priority",
    "title",
    "viral_probability",
}


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
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
            "Dashboard model deve ser "
            "um objeto JSON."
        )

    return payload


def print_mapping(
    title: str,
    value: Any,
) -> None:

    print()
    print("-" * 70)
    print(title)
    print("-" * 70)

    if isinstance(
        value,
        dict,
    ):

        if not value:

            print("<objeto vazio>")
            return

        for key in sorted(
            value.keys()
        ):

            item = value[key]

            print(
                f"{key}: "
                f"{type(item).__name__} "
                f"= {item!r}"
            )

        return

    print(
        f"Tipo observado: "
        f"{type(value).__name__}"
    )

    print(
        f"Valor observado: "
        f"{value!r}"
    )


def validate_root(
    payload: dict[str, Any],
) -> None:

    missing = (
        EXPECTED_ROOT_KEYS
        -
        payload.keys()
    )

    unexpected = (
        payload.keys()
        -
        EXPECTED_ROOT_KEYS
    )

    print()
    print("ROOT CONTRACT")

    print(
        "Missing:",
        sorted(
            missing
        ),
    )

    print(
        "Unexpected:",
        sorted(
            unexpected
        ),
    )


def validate_metrics(
    payload: dict[str, Any],
) -> None:

    metrics = payload.get(
        "metrics"
    )

    print_mapping(
        "METRICS OBSERVED",
        metrics,
    )

    if not isinstance(
        metrics,
        dict,
    ):

        print(
            "METRICS_STATUS=INVALID_TYPE"
        )

        return

    missing = (
        EXPECTED_METRIC_KEYS
        -
        metrics.keys()
    )

    unexpected = (
        metrics.keys()
        -
        EXPECTED_METRIC_KEYS
    )

    print(
        "METRICS_MISSING:",
        sorted(
            missing
        ),
    )

    print(
        "METRICS_UNEXPECTED:",
        sorted(
            unexpected
        ),
    )


def validate_hooks(
    payload: dict[str, Any],
) -> None:

    hooks = payload.get(
        "hooks"
    )

    print_mapping(
        "HOOKS OBSERVED",
        hooks,
    )

    if not isinstance(
        hooks,
        dict,
    ):

        print(
            "HOOKS_STATUS=INVALID_TYPE"
        )

        return

    missing = (
        EXPECTED_HOOK_KEYS
        -
        hooks.keys()
    )

    unexpected = (
        hooks.keys()
        -
        EXPECTED_HOOK_KEYS
    )

    print(
        "HOOKS_MISSING:",
        sorted(
            missing
        ),
    )

    print(
        "HOOKS_UNEXPECTED:",
        sorted(
            unexpected
        ),
    )


def validate_ranking(
    payload: dict[str, Any],
) -> None:

    ranking = payload.get(
        "ranking"
    )

    print()
    print("-" * 70)
    print("RANKING OBSERVED")
    print("-" * 70)

    if not isinstance(
        ranking,
        list,
    ):

        print(
            "RANKING_STATUS=INVALID_TYPE"
        )

        print(
            "Observed:",
            type(
                ranking
            ).__name__,
        )

        return

    print(
        f"Ranking items: {len(ranking)}"
    )

    for index, item in enumerate(
        ranking,
        start=1,
    ):

        print()
        print(
            f"Item {index}:"
        )

        if not isinstance(
            item,
            dict,
        ):

            print(
                "INVALID_ITEM_TYPE:",
                type(
                    item
                ).__name__,
            )

            continue

        missing = (
            EXPECTED_RANKING_KEYS
            -
            item.keys()
        )

        unexpected = (
            item.keys()
            -
            EXPECTED_RANKING_KEYS
        )

        print(
            "Keys:",
            sorted(
                item.keys()
            ),
        )

        print(
            "Missing:",
            sorted(
                missing
            ),
        )

        print(
            "Unexpected:",
            sorted(
                unexpected
            ),
        )

        print(
            "Value:",
            json.dumps(
                item,
                ensure_ascii=False,
                indent=2,
            ),
        )


def inspect_javascript() -> None:

    print()
    print("-" * 70)
    print("DASHBOARD JAVASCRIPT INSPECTION")
    print("-" * 70)

    if not JAVASCRIPT_FILE.is_file():

        print(
            f"Ficheiro não encontrado: "
            f"{JAVASCRIPT_FILE}"
        )

        return

    source = JAVASCRIPT_FILE.read_text(
        encoding="utf-8"
    )

    tokens = [
        "predicted_views_low",
        "predicted_views_high",
        "confidence_score",
        "predicted_comment_rate_percent",
        "hooks.primary",
        "hooks.alternatives",
        "ranking",
        "storyboard",
    ]

    for token in tokens:

        status = (
            "FOUND"
            if token in source
            else "NOT_FOUND"
        )

        print(
            f"{token}: {status}"
        )


def main() -> int:

    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-002E")
    print("DASHBOARD UI V2 CONTRACT READINESS AUDIT")
    print("READ ONLY")
    print("=" * 70)

    payload = load_json(
        MODEL_FILE
    )

    print(
        f"MODEL_FILE={MODEL_FILE}"
    )

    print(
        "ROOT_KEYS="
        + ",".join(
            sorted(
                payload.keys()
            )
        )
    )

    validate_root(
        payload
    )

    validate_metrics(
        payload
    )

    validate_hooks(
        payload
    )

    validate_ranking(
        payload
    )

    inspect_javascript()

    print()
    print("=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
