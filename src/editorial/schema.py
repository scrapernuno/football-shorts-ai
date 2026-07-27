from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Urgency = Literal["LOW", "MEDIUM", "HIGH"]
Competition = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
ConfirmationStatus = Literal[
    "CONFIRMED",
    "REPORTED",
    "RUMOUR",
    "ANALYSIS",
]
VisualType = Literal[
    "video",
    "image",
    "graphic",
    "screenshot",
    "text",
]
EditingPace = Literal[
    "slow",
    "medium",
    "fast",
    "very_fast",
]
TransitionType = Literal[
    "cut",
    "flash",
    "zoom",
    "swipe",
    "fade",
    "none",
]
SubtitleStyle = Literal[
    "large_center",
    "large_bottom",
    "word_by_word",
    "headline",
]
CameraMovement = Literal[
    "static",
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "slow_motion",
]


def require_non_empty_string(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} deve ser uma string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def require_score(
    value: object,
    field_name: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise TypeError(
            f"{field_name} deve ser um número inteiro."
        )

    if not 0 <= value <= 100:
        raise ValueError(
            f"{field_name} deve estar entre 0 e 100."
        )

    return value


def require_positive_integer(
    value: object,
    field_name: str,
    *,
    allow_zero: bool = False,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise TypeError(
            f"{field_name} deve ser um número inteiro."
        )

    minimum = 0 if allow_zero else 1

    if value < minimum:
        raise ValueError(
            f"{field_name} deve ser igual ou superior a {minimum}."
        )

    return value


@dataclass(frozen=True)
class ScoredTextOption:
    text: str
    score: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            require_non_empty_string(
                self.text,
                "ScoredTextOption.text",
            ),
        )

        require_score(
            self.score,
            "ScoredTextOption.score",
        )


@dataclass(frozen=True)
class SourceReference:
    title: str
    name: str
    url: str
    published: str
    confirmation_status: ConfirmationStatus

    def __post_init__(self) -> None:
        for field_name in (
            "title",
            "name",
            "url",
            "published",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"SourceReference.{field_name}",
                ),
            )

        if self.confirmation_status not in {
            "CONFIRMED",
            "REPORTED",
            "RUMOUR",
            "ANALYSIS",
        }:
            raise ValueError(
                "SourceReference.confirmation_status inválido."
            )


@dataclass(frozen=True)
class RankingAssessment:
    priority: int
    viral_probability: int
    competition: Competition
    breaking: bool
    publish_today: bool
    reason: str

    def __post_init__(self) -> None:
        require_positive_integer(
            self.priority,
            "RankingAssessment.priority",
        )

        require_score(
            self.viral_probability,
            "RankingAssessment.viral_probability",
        )

        if self.competition not in {
            "LOW",
            "MEDIUM",
            "HIGH",
            "EXTREME",
        }:
            raise ValueError(
                "RankingAssessment.competition inválido."
            )

        object.__setattr__(
            self,
            "reason",
            require_non_empty_string(
                self.reason,
                "RankingAssessment.reason",
            ),
        )


@dataclass(frozen=True)
class EditorialContent:
    primary_title: str
    alternative_titles: tuple[ScoredTextOption, ...]
    primary_hook: str
    alternative_hooks: tuple[ScoredTextOption, ...]
    script: str
    call_to_action: str
    pinned_comment: str
    description: str
    hashtags: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "primary_title",
            "primary_hook",
            "script",
            "call_to_action",
            "pinned_comment",
            "description",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"EditorialContent.{field_name}",
                ),
            )

        if len(self.alternative_titles) != 3:
            raise ValueError(
                "EditorialContent.alternative_titles "
                "deve conter exatamente 3 opções."
            )

        if len(self.alternative_hooks) != 3:
            raise ValueError(
                "EditorialContent.alternative_hooks "
                "deve conter exatamente 3 opções."
            )

        if not 5 <= len(self.hashtags) <= 8:
            raise ValueError(
                "EditorialContent.hashtags deve conter "
                "entre 5 e 8 hashtags."
            )

        normalized_hashtags: list[str] = []

        for hashtag in self.hashtags:
            text = require_non_empty_string(
                hashtag,
                "EditorialContent.hashtags",
            )

            if not text.startswith("#"):
                text = f"#{text}"

            normalized_hashtags.append(text)

        object.__setattr__(
            self,
            "hashtags",
            tuple(normalized_hashtags),
        )


@dataclass(frozen=True)
class AssetSuggestion:
    asset_type: VisualType
    description: str
    search_queries: tuple[str, ...]
    preferred_source: str
    fallback_description: str
    copyright_note: str

    def __post_init__(self) -> None:
        if self.asset_type not in {
            "video",
            "image",
            "graphic",
            "screenshot",
            "text",
        }:
            raise ValueError(
                "AssetSuggestion.asset_type inválido."
            )

        for field_name in (
            "description",
            "preferred_source",
            "fallback_description",
            "copyright_note",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"AssetSuggestion.{field_name}",
                ),
            )

        if not self.search_queries:
            raise ValueError(
                "AssetSuggestion.search_queries não pode estar vazio."
            )

        normalized_queries = tuple(
            require_non_empty_string(
                query,
                "AssetSuggestion.search_queries",
            )
            for query in self.search_queries
        )

        object.__setattr__(
            self,
            "search_queries",
            normalized_queries,
        )


@dataclass(frozen=True)
class StoryboardScene:
    scene_number: int
    start_second: int
    end_second: int
    voiceover: str
    subtitle: str
    visual_type: VisualType
    visual_description: str
    editing_pace: EditingPace
    transition: TransitionType
    subtitle_style: SubtitleStyle
    camera_movement: CameraMovement
    sound_effect: str
    asset: AssetSuggestion

    def __post_init__(self) -> None:
        require_positive_integer(
            self.scene_number,
            "StoryboardScene.scene_number",
        )

        require_positive_integer(
            self.start_second,
            "StoryboardScene.start_second",
            allow_zero=True,
        )

        require_positive_integer(
            self.end_second,
            "StoryboardScene.end_second",
        )

        if self.end_second <= self.start_second:
            raise ValueError(
                "StoryboardScene.end_second deve ser "
                "superior a start_second."
            )

        for field_name in (
            "voiceover",
            "subtitle",
            "visual_description",
            "sound_effect",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"StoryboardScene.{field_name}",
                ),
            )

        if self.visual_type not in {
            "video",
            "image",
            "graphic",
            "screenshot",
            "text",
        }:
            raise ValueError(
                "StoryboardScene.visual_type inválido."
            )

        if self.editing_pace not in {
            "slow",
            "medium",
            "fast",
            "very_fast",
        }:
            raise ValueError(
                "StoryboardScene.editing_pace inválido."
            )

        if self.transition not in {
            "cut",
            "flash",
            "zoom",
            "swipe",
            "fade",
            "none",
        }:
            raise ValueError(
                "StoryboardScene.transition inválido."
            )

        if self.subtitle_style not in {
            "large_center",
            "large_bottom",
            "word_by_word",
            "headline",
        }:
            raise ValueError(
                "StoryboardScene.subtitle_style inválido."
            )

        if self.camera_movement not in {
            "static",
            "zoom_in",
            "zoom_out",
            "pan_left",
            "pan_right",
            "slow_motion",
        }:
            raise ValueError(
                "StoryboardScene.camera_movement inválido."
            )


@dataclass(frozen=True)
class Storyboard:
    estimated_duration_seconds: int
    required_clip_count: int
    scenes: tuple[StoryboardScene, ...]

    def __post_init__(self) -> None:
        require_positive_integer(
            self.estimated_duration_seconds,
            "Storyboard.estimated_duration_seconds",
        )

        require_positive_integer(
            self.required_clip_count,
            "Storyboard.required_clip_count",
        )

        if not self.scenes:
            raise ValueError(
                "Storyboard.scenes não pode estar vazio."
            )

        expected_scene = 1
        previous_end = 0

        for scene in self.scenes:
            if scene.scene_number != expected_scene:
                raise ValueError(
                    "Storyboard.scenes deve ter numeração sequencial."
                )

            if scene.start_second != previous_end:
                raise ValueError(
                    "Storyboard.scenes deve formar uma timeline contínua."
                )

            previous_end = scene.end_second
            expected_scene += 1

        if (
            self.scenes[-1].end_second
            != self.estimated_duration_seconds
        ):
            raise ValueError(
                "A última cena deve terminar exatamente na duração "
                "estimada do storyboard."
            )


@dataclass(frozen=True)
class PublishingPlan:
    urgency: Urgency
    best_publish_time: str
    publish_window_minutes: int
    relevance_lifetime_hours: int
    timezone: str
    publication_reason: str

    def __post_init__(self) -> None:
        if self.urgency not in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            raise ValueError(
                "PublishingPlan.urgency inválido."
            )

        for field_name in (
            "best_publish_time",
            "timezone",
            "publication_reason",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"PublishingPlan.{field_name}",
                ),
            )

        require_positive_integer(
            self.publish_window_minutes,
            "PublishingPlan.publish_window_minutes",
        )

        require_positive_integer(
            self.relevance_lifetime_hours,
            "PublishingPlan.relevance_lifetime_hours",
        )


@dataclass(frozen=True)
class PredictedAnalytics:
    predicted_ctr_percent: float
    predicted_retention_percent: float
    predicted_views_low: int
    predicted_views_high: int
    predicted_comment_rate_percent: float
    confidence_score: int
    prediction_basis: str

    def __post_init__(self) -> None:
        percentage_fields = (
            "predicted_ctr_percent",
            "predicted_retention_percent",
            "predicted_comment_rate_percent",
        )

        for field_name in percentage_fields:
            value = getattr(self, field_name)

            if not isinstance(value, (int, float)):
                raise TypeError(
                    f"PredictedAnalytics.{field_name} "
                    "deve ser numérico."
                )

            if not 0 <= float(value) <= 100:
                raise ValueError(
                    f"PredictedAnalytics.{field_name} "
                    "deve estar entre 0 e 100."
                )

        require_positive_integer(
            self.predicted_views_low,
            "PredictedAnalytics.predicted_views_low",
            allow_zero=True,
        )

        require_positive_integer(
            self.predicted_views_high,
            "PredictedAnalytics.predicted_views_high",
            allow_zero=True,
        )

        if (
            self.predicted_views_high
            < self.predicted_views_low
        ):
            raise ValueError(
                "predicted_views_high não pode ser inferior "
                "a predicted_views_low."
            )

        require_score(
            self.confidence_score,
            "PredictedAnalytics.confidence_score",
        )

        object.__setattr__(
            self,
            "prediction_basis",
            require_non_empty_string(
                self.prediction_basis,
                "PredictedAnalytics.prediction_basis",
            ),
        )


@dataclass(frozen=True)
class EditorChecklist:
    hook_first_two_seconds: bool
    duration_valid: bool
    thumbnail_short: bool
    call_to_action_present: bool
    pinned_comment_present: bool
    sources_require_confirmation: bool
    missing_assets: tuple[str, ...] = field(
        default_factory=tuple
    )


@dataclass(frozen=True)
class EditorialTopicPackage:
    topic_id: str
    ranking: RankingAssessment
    source: SourceReference
    editorial: EditorialContent
    storyboard: Storyboard
    publishing: PublishingPlan
    analytics: PredictedAnalytics
    checklist: EditorChecklist

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "topic_id",
            require_non_empty_string(
                self.topic_id,
                "EditorialTopicPackage.topic_id",
            ),
        )


@dataclass(frozen=True)
class EditorialPackage:
    schema_version: str
    generated_at: str
    channel: str
    language: str
    timezone: str
    top_topic_id: str
    topics: tuple[EditorialTopicPackage, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "schema_version",
            "generated_at",
            "channel",
            "language",
            "timezone",
            "top_topic_id",
        ):
            object.__setattr__(
                self,
                field_name,
                require_non_empty_string(
                    getattr(self, field_name),
                    f"EditorialPackage.{field_name}",
                ),
            )

        if self.language != "pt-PT":
            raise ValueError(
                "EditorialPackage.language deve ser pt-PT."
            )

        if not self.topics:
            raise ValueError(
                "EditorialPackage.topics não pode estar vazio."
            )

        topic_ids = [
            topic.topic_id
            for topic in self.topics
        ]

        if len(topic_ids) != len(set(topic_ids)):
            raise ValueError(
                "EditorialPackage contém topic_id duplicado."
            )

        if self.top_topic_id not in set(topic_ids):
            raise ValueError(
                "EditorialPackage.top_topic_id não corresponde "
                "a nenhum tópico."
            )

        priorities = [
            topic.ranking.priority
            for topic in self.topics
        ]

        if priorities != list(
            range(1, len(self.topics) + 1)
        ):
            raise ValueError(
                "As prioridades devem ser sequenciais "
                "e começar em 1."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
