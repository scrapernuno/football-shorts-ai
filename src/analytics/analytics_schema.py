from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ANALYTICS_VERSION = "1.0"


VALID_PLATFORMS = {
    "youtube_shorts",
}


VALID_PERFORMANCE_STATUS = {
    "pending",
    "collecting",
    "complete",
}



@dataclass(frozen=True)
class VideoPerformanceMetrics:


    views: int

    likes: int

    comments: int

    shares: int

    average_watch_time_seconds: float

    retention_percent: float

    subscribers_gained: int



    def __post_init__(self):

        values = [

            self.views,

            self.likes,

            self.comments,

            self.shares,

            self.subscribers_gained,

        ]


        if any(
            value < 0
            for value in values
        ):

            raise ValueError(
                "Métricas não podem ser negativas."
            )


        if self.retention_percent < 0:

            raise ValueError(
                "Retention inválida."
            )



@dataclass(frozen=True)
class GrowthSignals:


    hook_strength_score: int

    audience_match_score: int

    engagement_score: int

    virality_score: int



    def __post_init__(self):

        scores = [

            self.hook_strength_score,

            self.audience_match_score,

            self.engagement_score,

            self.virality_score,

        ]


        for score in scores:

            if score < 0 or score > 100:

                raise ValueError(
                    "Growth score deve estar entre 0 e 100."
                )



@dataclass(frozen=True)
class LearningRecommendation:


    next_topic_direction: str

    recommended_improvement: str

    confidence_score: int



    def __post_init__(self):

        if not self.next_topic_direction:

            raise ValueError(
                "Topic direction obrigatório."
            )


        if not self.recommended_improvement:

            raise ValueError(
                "Improvement obrigatório."
            )


        if (
            self.confidence_score < 0
            or self.confidence_score > 100
        ):

            raise ValueError(
                "Confidence inválida."
            )



@dataclass(frozen=True)
class AnalyticsPackage:


    analytics_version: str

    content_id: str

    platform: str

    status: str

    metrics: VideoPerformanceMetrics

    growth_signals: GrowthSignals

    recommendation: LearningRecommendation



    def __post_init__(self):

        if self.analytics_version != ANALYTICS_VERSION:

            raise ValueError(
                "Analytics version inválida."
            )


        if self.platform not in VALID_PLATFORMS:

            raise ValueError(
                "Platform inválida."
            )


        if self.status not in VALID_PERFORMANCE_STATUS:

            raise ValueError(
                "Analytics status inválido."
            )


        if not self.content_id:

            raise ValueError(
                "Content id obrigatório."
            )



def validate_analytics_payload(
    payload: dict[str, Any],
) -> None:


    required = {

        "analytics_version",

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



def build_initial_analytics_package(
    publishing_package: dict[str, Any],
) -> dict[str, Any]:


    return {


        "analytics_version":

            ANALYTICS_VERSION,


        "content_id":

            publishing_package.get(
                "source_content_id",
                "",
            ),



        "platform":

            "youtube_shorts",



        "status":

            "pending",



        "metrics": {


            "views":

                0,


            "likes":

                0,


            "comments":

                0,


            "shares":

                0,


            "average_watch_time_seconds":

                0,


            "retention_percent":

                0,


            "subscribers_gained":

                0,

        },



        "growth_signals": {


            "hook_strength_score":

                0,


            "audience_match_score":

                0,


            "engagement_score":

                0,


            "virality_score":

                0,

        },



        "recommendation": {


            "next_topic_direction":

                "Collect performance data",



            "recommended_improvement":

                "Await first publication metrics",



            "confidence_score":

                0,

        },

    }
