from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

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


def load_editorial_package() -> dict:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Ficheiro não encontrado: {INPUT_FILE}"
        )

    return json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )


def build_dashboard(
    package: dict,
) -> DashboardModel:

    topics = package["topics"]

    top = topics[0]

    editorial = top["editorial"]
    ranking = top["ranking"]
    analytics = top["analytics"]
    publishing = top["publishing"]
    storyboard = top["storyboard"]

    metrics = (
        DashboardMetric(
            label="Probabilidade Viral",
            value=f"{ranking['viral_probability']}%",
            score=ranking["viral_probability"],
        ),
        DashboardMetric(
            label="CTR Previsto",
            value=f"{analytics['predicted_ctr_percent']}%",
            score=int(
                analytics["predicted_ctr_percent"]
            ),
        ),
        DashboardMetric(
            label="Retenção Prevista",
            value=f"{analytics['predicted_retention_percent']}%",
            score=int(
                analytics["predicted_retention_percent"]
            ),
        ),
        DashboardMetric(
            label="Hora Publicação",
            value=publishing["best_publish_time"],
            score=90,
        ),
    )

    hooks = tuple(
        DashboardHook(
            text=item["text"],
            score=item["score"],
        )
        for item in editorial[
            "alternative_hooks"
        ]
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
                scene["asset"][
                    "search_queries"
                ]
            ),
        )
        for scene in storyboard["scenes"]
    )

    ranking_items = tuple(
        DashboardTopic(
            rank=index + 1,
            title=item["editorial"][
                "primary_title"
            ],
            viral_score=item[
                "ranking"
            ][
                "viral_probability"
            ],
            urgency=item[
                "publishing"
            ][
                "urgency"
            ],
        )
        for index, item in enumerate(topics)
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

    OUTPUT_FILE.write_text(
        json.dumps(
            model.to_dict(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
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
    print("DASHBOARD MODEL GENERATED")
    print("=" * 70)
    print(
        f"Título: {dashboard.top_title}"
    )
    print(
        f"Viral: {dashboard.viral_probability}%"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
