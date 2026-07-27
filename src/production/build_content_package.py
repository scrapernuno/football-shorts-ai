from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_SOURCE = ROOT / "output" / "dashboard_model.json"
CONTENT_OUTPUT = ROOT / "output" / "content_package.json"

PACKAGE_VERSION = "1.0"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON inválido em {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"{path} deve conter um objeto JSON."
        )

    return payload


def save_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(path)


def normalize_integer(
    value: Any,
    *,
    default: int = 0,
) -> int:
    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(round(value))

    if isinstance(value, str):
        candidate = (
            value.strip()
            .replace("%", "")
            .replace(",", ".")
        )

        try:
            return int(round(float(candidate)))
        except ValueError:
            return default

    return default


def normalize_non_empty_string(
    value: Any,
    *,
    default: str,
) -> str:
    if isinstance(value, str):
        normalized = value.strip()

        if normalized:
            return normalized

    return default


def select_winner(
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    ranking = dashboard.get(
        "ranking",
        [],
    )

    if not isinstance(ranking, list):
        raise ValueError(
            "Dashboard ranking deve ser uma lista."
        )

    if not ranking:
        raise ValueError(
            "Dashboard sem ranking."
        )

    candidates: list[
        tuple[int, int, int, dict[str, Any]]
    ] = []

    for original_index, raw_item in enumerate(
        ranking,
        start=1,
    ):
        if not isinstance(raw_item, dict):
            raise ValueError(
                "Todos os elementos de ranking "
                "devem ser objetos JSON."
            )

        item = deepcopy(raw_item)

        priority = normalize_integer(
            item.get("priority"),
            default=0,
        )

        viral_probability = normalize_integer(
            item.get("viral_probability"),
            default=0,
        )

        if priority > 0:
            priority_group = 0
            priority_value = priority
        else:
            priority_group = 1
            priority_value = original_index

        candidates.append(
            (
                priority_group,
                priority_value,
                -viral_probability,
                item,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
            candidate[2],
        )
    )

    winner = candidates[0][3]

    winner["priority"] = 1

    winner["viral_probability"] = max(
        0,
        min(
            100,
            normalize_integer(
                winner.get(
                    "viral_probability",
                    dashboard.get(
                        "viral_probability",
                        0,
                    ),
                ),
                default=0,
            ),
        ),
    )

    winner["title"] = normalize_non_empty_string(
        winner.get("title"),
        default=normalize_non_empty_string(
            dashboard.get("top_title"),
            default="Football Story",
        ),
    )

    winner["hook"] = normalize_non_empty_string(
        winner.get("hook"),
        default=normalize_non_empty_string(
            dashboard.get("top_hook"),
            default=(
                "O momento que está a gerar "
                "debate no futebol."
            ),
        ),
    )

    return winner


def build_script(
    winner: dict[str, Any],
) -> dict[str, str]:
    title = normalize_non_empty_string(
        winner.get("title"),
        default="Football Story",
    )

    source_hook = normalize_non_empty_string(
        winner.get("hook"),
        default=(
            f"O momento que todos estão "
            f"a comentar: {title}"
        ),
    )

    return {
        "hook": source_hook,
        "introduction": (
            "Vamos explicar rapidamente "
            "o que aconteceu."
        ),
        "development": (
            "Contexto, protagonistas "
            "e o momento principal."
        ),
        "climax": (
            "A jogada ou acontecimento "
            "que mudou tudo."
        ),
        "ending": (
            "Este momento ficará marcado "
            "na história."
        ),
        "call_to_action": (
            "Concordas? Comenta e segue "
            "para mais histórias."
        ),
    }


def build_voiceover(
    script: dict[str, str],
) -> dict[str, Any]:
    return {
        "language": "pt-PT",
        "style": "energetic",
        "segments": [
            {
                "start_second": 0,
                "end_second": 5,
                "text": script["hook"],
            },
            {
                "start_second": 5,
                "end_second": 20,
                "text": script["development"],
            },
            {
                "start_second": 20,
                "end_second": 40,
                "text": script["climax"],
            },
            {
                "start_second": 40,
                "end_second": 45,
                "text": script["call_to_action"],
            },
        ],
    }


def build_scenes() -> list[dict[str, Any]]:
    return [
        {
            "scene_number": 1,
            "duration_seconds": 5,
            "visual_instruction": (
                "Opening football highlight"
            ),
            "camera_direction": "zoom_in",
            "voiceover_segment": "Hook inicial",
            "caption_text": (
                "O MOMENTO QUE TODOS FALAM"
            ),
            "asset_reference": (
                "football_opening_clip"
            ),
        },
        {
            "scene_number": 2,
            "duration_seconds": 15,
            "visual_instruction": (
                "Context football footage"
            ),
            "camera_direction": "pan_right",
            "voiceover_segment": (
                "Contexto da história"
            ),
            "caption_text": (
                "COMO TUDO ACONTECEU"
            ),
            "asset_reference": (
                "football_context_clip"
            ),
        },
        {
            "scene_number": 3,
            "duration_seconds": 15,
            "visual_instruction": (
                "Main football moment"
            ),
            "camera_direction": "slow_motion",
            "voiceover_segment": (
                "Momento decisivo"
            ),
            "caption_text": (
                "O MOMENTO DECISIVO"
            ),
            "asset_reference": (
                "football_highlight_clip"
            ),
        },
        {
            "scene_number": 4,
            "duration_seconds": 10,
            "visual_instruction": "Fan reaction",
            "camera_direction": "zoom_out",
            "voiceover_segment": (
                "Reação dos adeptos"
            ),
            "caption_text": (
                "QUAL É A TUA OPINIÃO?"
            ),
            "asset_reference": (
                "fans_reaction_clip"
            ),
        },
    ]


def build_content_package(
    dashboard: dict[str, Any],
) -> dict[str, Any]:
    winner = select_winner(dashboard)
    script = build_script(winner)

    title = winner["title"]
    hook = winner["hook"]

    return {
        "package_version": PACKAGE_VERSION,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_topic": {
            "title": title,
            "hook": hook,
            "viral_probability": (
                winner["viral_probability"]
            ),
            "priority": 1,
        },
        "script": script,
        "voiceover": build_voiceover(script),
        "scenes": build_scenes(),
        "captions": [],
        "assets": [],
        "publishing": {
            "platform": "youtube_shorts",
            "title": title,
            "description": (
                "Generated by Football Shorts AI"
            ),
            "hashtags": [
                "#football",
                "#shorts",
            ],
            "scheduled_window": "recommended",
        },
    }


def validate_package(
    payload: dict[str, Any],
) -> None:
    required = {
        "package_version",
        "generated_at",
        "source_topic",
        "script",
        "voiceover",
        "scenes",
        "captions",
        "assets",
        "publishing",
    }

    missing = required - payload.keys()

    if missing:
        raise ValueError(
            "Content package incompleto: "
            f"{sorted(missing)}"
        )

    if payload["package_version"] != PACKAGE_VERSION:
        raise ValueError(
            "Content package version inválida."
        )

    source_topic = payload["source_topic"]

    if not isinstance(source_topic, dict):
        raise ValueError(
            "source_topic deve ser "
            "um objeto JSON."
        )

    required_source_topic = {
        "title",
        "hook",
        "viral_probability",
        "priority",
    }

    missing_source_topic = (
        required_source_topic
        - source_topic.keys()
    )

    if missing_source_topic:
        raise ValueError(
            "source_topic incompleto: "
            f"{sorted(missing_source_topic)}"
        )

    if source_topic["priority"] != 1:
        raise ValueError(
            "Content package deve usar "
            "winner priority 1."
        )

    viral_probability = source_topic[
        "viral_probability"
    ]

    if not isinstance(viral_probability, int):
        raise ValueError(
            "viral_probability deve "
            "ser um número inteiro."
        )

    if not 0 <= viral_probability <= 100:
        raise ValueError(
            "viral_probability deve "
            "estar entre 0 e 100."
        )

    scenes = payload["scenes"]

    if not isinstance(scenes, list) or not scenes:
        raise ValueError(
            "Content package deve "
            "conter scenes."
        )

    expected = list(
        range(
            1,
            len(scenes) + 1,
        )
    )

    actual = []

    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError(
                "Cada scene deve ser "
                "um objeto JSON."
            )

        actual.append(
            scene.get("scene_number")
        )

        if normalize_integer(
            scene.get("duration_seconds"),
            default=0,
        ) <= 0:
            raise ValueError(
                "Scene com duração inválida."
            )

    if actual != expected:
        raise ValueError(
            "Scenes inválidas: "
            "scene_number deve ser sequencial."
        )


def main() -> int:
    print("=" * 70)
    print("FOOTBALL SHORTS AI")
    print("CONTENT PRODUCTION ENGINE")
    print("=" * 70)

    dashboard = load_json(
        DASHBOARD_SOURCE
    )

    package = build_content_package(
        dashboard
    )

    validate_package(
        package
    )

    save_json(
        CONTENT_OUTPUT,
        package,
    )

    print("CONTENT PACKAGE BUILD PASS")
    print(
        "Winner: "
        f"{package['source_topic']['title']}"
    )
    print(
        "Viral probability: "
        f"{package['source_topic']['viral_probability']}%"
    )
    print(
        f"Scenes: {len(package['scenes'])}"
    )
    print(
        f"Output: {CONTENT_OUTPUT}"
    )
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
