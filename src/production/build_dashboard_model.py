from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from production.dashboard_model import (
    DashboardHook,
    DashboardMetric,
    DashboardModel,
    DashboardScene,
    DashboardTopic,
)


ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "output"
    / "editorial_package.json"
)

OUTPUT_FILE = (
    ROOT
    / "output"
    / "dashboard_model.json"
)


def load_editorial_package() -> dict[str, Any]:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Ficheiro não encontrado: {INPUT_FILE}"
        )

    try:
        payload = json.loads(
            INPUT_FILE.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"JSON inválido em {INPUT_FILE}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Editorial Package deve ser "
            "um objeto JSON."
        )

    return payload


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


def build_dashboard(
    package: dict[str, Any],
) -> DashboardModel:
    topics = require_list(
        package.get(
            "topics"
        ),
        "editorial_package.topics",
    )

    if not topics:
        raise ValueError(
            "Editorial Package sem tópicos."
        )

    top = require_mapping(
        topics[0],
        "editorial_package.topics[0]",
    )

    editorial = require_mapping(
        top.get(
            "editorial"
        ),
        "top.editorial",
    )

    ranking = require_mapping(
        top.get(
            "ranking"
        ),
        "top.ranking",
    )

    analytics = require_mapping(
        top.get(
            "analytics"
        ),
        "top.analytics",
    )

    publishing = require_mapping(
        top.get(
            "publishing"
        ),
        "top.publishing",
    )

    storyboard = require_mapping(
        top.get(
            "storyboard"
        ),
        "top.storyboard",
    )

    metrics = (
        DashboardMetric(
            label="Probabilidade Viral",
            value=(
                f"{ranking['viral_probability']}%"
            ),
            score=ranking[
                "viral_probability"
            ],
        ),
        DashboardMetric(
            label="CTR Previsto",
            value=(
                f"{analytics['predicted_ctr_percent']}%"
            ),
            score=int(
                analytics[
                    "predicted_ctr_percent"
                ]
            ),
        ),
        DashboardMetric(
            label="Retenção Prevista",
            value=(
                f"{analytics['predicted_retention_percent']}%"
            ),
            score=int(
                analytics[
                    "predicted_retention_percent"
                ]
            ),
        ),
        DashboardMetric(
            label="Hora Publicação",
            value=publishing[
                "best_publish_time"
            ],
            score=90,
        ),
    )

    alternative_hooks = require_list(
        editorial.get(
            "alternative_hooks"
        ),
        "top.editorial.alternative_hooks",
    )

    hooks = tuple(
        DashboardHook(
            text=require_mapping(
                item,
                (
                    "top.editorial."
                    f"alternative_hooks[{index}]"
                ),
            )[
                "text"
            ],
            score=require_mapping(
                item,
                (
                    "top.editorial."
                    f"alternative_hooks[{index}]"
                ),
            )[
                "score"
            ],
        )
        for index, item in enumerate(
            alternative_hooks
        )
    )

    storyboard_scenes = require_list(
        storyboard.get(
            "scenes"
        ),
        "top.storyboard.scenes",
    )

    scenes = tuple(
        DashboardScene(
            time_range=(
                f"{scene['start_second']}s-"
                f"{scene['end_second']}s"
            ),
            visual=scene[
                "visual_description"
            ],
            voice=scene[
                "voiceover"
            ],
            search=", ".join(
                require_mapping(
                    scene.get(
                        "asset"
                    ),
                    (
                        "top.storyboard.scenes"
                        f"[{index}].asset"
                    ),
                )[
                    "search_queries"
                ]
            ),
        )
        for index, raw_scene in enumerate(
            storyboard_scenes
        )
        for scene in (
            require_mapping(
                raw_scene,
                (
                    "top.storyboard.scenes"
                    f"[{index}]"
                ),
            ),
        )
    )

    ranking_items = tuple(
        DashboardTopic(
            rank=index + 1,
            title=editorial_item[
                "primary_title"
            ],
            hook=editorial_item[
                "primary_hook"
            ],
            reason=ranking_item[
                "reason"
            ],
            viral_score=ranking_item[
                "viral_probability"
            ],
            urgency=publishing_item[
                "urgency"
            ],
        )
        for index, raw_item in enumerate(
            topics
        )
        for item in (
            require_mapping(
                raw_item,
                (
                    "editorial_package.topics"
                    f"[{index}]"
                ),
            ),
        )
        for editorial_item in (
            require_mapping(
                item.get(
                    "editorial"
                ),
                (
                    "editorial_package.topics"
                    f"[{index}].editorial"
                ),
            ),
        )
        for ranking_item in (
            require_mapping(
                item.get(
                    "ranking"
                ),
                (
                    "editorial_package.topics"
                    f"[{index}].ranking"
                ),
            ),
        )
        for publishing_item in (
            require_mapping(
                item.get(
                    "publishing"
                ),
                (
                    "editorial_package.topics"
                    f"[{index}].publishing"
                ),
            ),
        )
    )

    return DashboardModel(
        generated_at=package[
            "generated_at"
        ],
        channel=package[
            "channel"
        ],
        top_title=editorial[
            "primary_title"
        ],
        top_hook=editorial[
            "primary_hook"
        ],
        viral_probability=ranking[
            "viral_probability"
        ],
        predicted_views_low=analytics[
            "predicted_views_low"
        ],
        predicted_views_high=analytics[
            "predicted_views_high"
        ],
        confidence_score=analytics[
            "confidence_score"
        ],
        predicted_comment_rate_percent=analytics[
            "predicted_comment_rate_percent"
        ],
        prediction_basis=analytics[
            "prediction_basis"
        ],
        predicted_ctr=(
            f"{analytics['predicted_ctr_percent']}%"
        ),
        predicted_retention=(
            f"{analytics['predicted_retention_percent']}%"
        ),
        recommended_publish_time=publishing[
            "best_publish_time"
        ],
        metrics=metrics,
        hooks=hooks,
        storyboard=scenes,
        ranking=ranking_items,
    )


def save_dashboard_model(
    model: DashboardModel,
) -> None:
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        OUTPUT_FILE.with_suffix(
            OUTPUT_FILE.suffix
            + ".tmp"
        )
    )

    temporary_path.write_text(
        json.dumps(
            model.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        OUTPUT_FILE
    )


def main() -> int:
    package = load_editorial_package()

    dashboard = build_dashboard(
        package
    )

    save_dashboard_model(
        dashboard
    )

    print("=" * 70)
    print(
        "FOOTBALL-SHORTS-AI-0031C.1"
    )
    print(
        "FORECAST AND RANKING DATA "
        "CONTRACT COMPLETION"
    )
    print("=" * 70)
    print(
        f"Título: {dashboard.top_title}"
    )
    print(
        "Views previstas: "
        f"{dashboard.predicted_views_low}"
        " - "
        f"{dashboard.predicted_views_high}"
    )
    print(
        "Confiança: "
        f"{dashboard.confidence_score}%"
    )
    print(
        "Comment rate: "
        f"{dashboard.predicted_comment_rate_percent}%"
    )
    print(
        f"Hooks: {len(dashboard.hooks)}"
    )
    print(
        f"Cenas: {len(dashboard.storyboard)}"
    )
    print(
        f"Ranking: {len(dashboard.ranking)}"
    )
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
