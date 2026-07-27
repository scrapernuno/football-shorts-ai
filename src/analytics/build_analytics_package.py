from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SOURCE = Path(
    "output/publishing_package.json"
)


OUTPUT = Path(
    "output/analytics_package.json"
)


ANALYTICS_VERSION = "1.0"



def load_json(
    path: Path,
) -> dict:

    if not path.exists():

        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
        )


    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )



def save_json(
    path: Path,
    payload: dict,
) -> None:


    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    path.write_text(

        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )



def validate_publishing_package(
    payload: dict,
) -> None:


    required = {

        "source_content_id",

        "metadata",

        "status",

    }


    missing = (

        required

        -

        payload.keys()

    )


    if missing:

        raise ValueError(
            f"Publishing package inválido: {missing}"
        )



def build_metrics() -> dict:


    return {

        "views": 0,

        "likes": 0,

        "comments": 0,

        "shares": 0,

        "average_watch_time_seconds": 0,

        "retention_percent": 0,

        "subscribers_gained": 0,

    }



def build_growth_signals() -> dict:


    return {

        "hook_strength_score": 0,

        "audience_match_score": 0,

        "engagement_score": 0,

        "virality_score": 0,

    }



def build_recommendation() -> dict:


    return {

        "next_topic_direction":

            "Collect initial performance data",


        "recommended_improvement":

            "Await publication metrics before optimization",


        "confidence_score":

            0,

    }



def build_analytics_package(
    publishing: dict,
) -> dict:


    validate_publishing_package(
        publishing
    )


    return {


        "analytics_version":

            ANALYTICS_VERSION,


        "generated_at":

            datetime.now(
                timezone.utc
            ).isoformat(),



        "content_id":

            publishing[
                "source_content_id"
            ],



        "platform":

            publishing[
                "metadata"
            ].get(
                "platform",
                "youtube_shorts",
            ),



        "status":

            "pending",



        "metrics":

            build_metrics(),



        "growth_signals":

            build_growth_signals(),



        "recommendation":

            build_recommendation(),

    }



def validate_analytics_package(
    payload: dict,
) -> None:


    required = {

        "analytics_version",

        "generated_at",

        "content_id",

        "platform",

        "status",

        "metrics",

        "growth_signals",

        "recommendation",

    }


    missing = (

        required

        -

        payload.keys()

    )


    if missing:

        raise ValueError(
            f"Analytics package incompleto: {missing}"
        )



    if payload["status"] != "pending":

        raise ValueError(
            "Analytics inicial deve estar pending."
        )



    metrics = payload["metrics"]


    required_metrics = {

        "views",

        "likes",

        "comments",

        "shares",

        "average_watch_time_seconds",

        "retention_percent",

        "subscribers_gained",

    }


    missing_metrics = (

        required_metrics

        -

        metrics.keys()

    )


    if missing_metrics:

        raise ValueError(
            f"Métricas incompletas: {missing_metrics}"
        )



def main() -> int:


    print("=" * 70)

    print(
        "FOOTBALL SHORTS AI"
    )

    print(
        "ANALYTICS & GROWTH INTELLIGENCE ENGINE"
    )

    print("=" * 70)



    publishing = load_json(
        SOURCE
    )


    analytics = build_analytics_package(
        publishing
    )


    validate_analytics_package(
        analytics
    )


    save_json(
        OUTPUT,
        analytics,
    )


    print(
        "ANALYTICS PACKAGE BUILD PASS"
    )


    print(
        f"Content ID: {analytics['content_id']}"
    )


    print(
        f"Status: {analytics['status']}"
    )


    print(
        f"Output: {OUTPUT}"
    )


    print("=" * 70)


    return 0



if __name__ == "__main__":

    raise SystemExit(
        main()
    )
