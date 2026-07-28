from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def require_text(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} deve ser texto."
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
            f"{field_name} deve ser inteiro."
        )

    if not 0 <= value <= 100:
        raise ValueError(
            f"{field_name} deve estar entre 0 e 100."
        )

    return value


def require_percentage(
    value: object,
    field_name: str,
) -> float:
    if (
        not isinstance(
            value,
            (
                int,
                float,
            ),
        )
        or isinstance(
            value,
            bool,
        )
    ):
        raise TypeError(
            f"{field_name} deve ser numérico."
        )

    normalized = float(
        value
    )

    if not 0 <= normalized <= 100:
        raise ValueError(
            f"{field_name} deve estar entre 0 e 100."
        )

    return normalized


def require_non_negative_integer(
    value: object,
    field_name: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise TypeError(
            f"{field_name} deve ser inteiro."
        )

    if value < 0:
        raise ValueError(
            f"{field_name} não pode ser negativo."
        )

    return value


@dataclass(frozen=True)
class DashboardMetric:
    label: str
    value: str
    score: int

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "label",
            require_text(
                self.label,
                "DashboardMetric.label",
            ),
        )

        object.__setattr__(
            self,
            "value",
            require_text(
                self.value,
                "DashboardMetric.value",
            ),
        )

        require_score(
            self.score,
            "DashboardMetric.score",
        )


@dataclass(frozen=True)
class DashboardHook:
    text: str
    score: int

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "text",
            require_text(
                self.text,
                "DashboardHook.text",
            ),
        )

        require_score(
            self.score,
            "DashboardHook.score",
        )


@dataclass(frozen=True)
class DashboardScene:
    time_range: str
    visual: str
    voice: str
    search: str

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "time_range",
            "visual",
            "voice",
            "search",
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    (
                        "DashboardScene."
                        f"{field_name}"
                    ),
                ),
            )


@dataclass(frozen=True)
class DashboardTopic:
    rank: int
    title: str
    hook: str
    reason: str
    viral_score: int
    urgency: str

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.rank,
                int,
            )
            or isinstance(
                self.rank,
                bool,
            )
            or self.rank < 1
        ):
            raise ValueError(
                "DashboardTopic.rank inválido."
            )

        for field_name in (
            "title",
            "hook",
            "reason",
            "urgency",
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    (
                        "DashboardTopic."
                        f"{field_name}"
                    ),
                ),
            )

        require_score(
            self.viral_score,
            "DashboardTopic.viral_score",
        )


@dataclass(frozen=True)
class DashboardModel:
    generated_at: str
    channel: str

    top_title: str
    top_hook: str

    viral_probability: int

    predicted_views_low: int
    predicted_views_high: int
    confidence_score: int
    predicted_comment_rate_percent: float
    prediction_basis: str

    predicted_ctr: str
    predicted_retention: str
    recommended_publish_time: str

    metrics: tuple[
        DashboardMetric,
        ...,
    ]

    hooks: tuple[
        DashboardHook,
        ...,
    ]

    storyboard: tuple[
        DashboardScene,
        ...,
    ]

    ranking: tuple[
        DashboardTopic,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "generated_at",
            "channel",
            "top_title",
            "top_hook",
            "prediction_basis",
            "predicted_ctr",
            "predicted_retention",
            "recommended_publish_time",
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(
                    getattr(
                        self,
                        field_name,
                    ),
                    (
                        "DashboardModel."
                        f"{field_name}"
                    ),
                ),
            )

        require_score(
            self.viral_probability,
            (
                "DashboardModel."
                "viral_probability"
            ),
        )

        require_non_negative_integer(
            self.predicted_views_low,
            (
                "DashboardModel."
                "predicted_views_low"
            ),
        )

        require_non_negative_integer(
            self.predicted_views_high,
            (
                "DashboardModel."
                "predicted_views_high"
            ),
        )

        if (
            self.predicted_views_high
            <
            self.predicted_views_low
        ):
            raise ValueError(
                "DashboardModel.predicted_views_high "
                "não pode ser inferior a "
                "predicted_views_low."
            )

        require_score(
            self.confidence_score,
            (
                "DashboardModel."
                "confidence_score"
            ),
        )

        normalized_comment_rate = (
            require_percentage(
                (
                    self
                    .predicted_comment_rate_percent
                ),
                (
                    "DashboardModel."
                    "predicted_comment_rate_percent"
                ),
            )
        )

        object.__setattr__(
            self,
            (
                "predicted_comment_rate_percent"
            ),
            normalized_comment_rate,
        )

        if len(
            self.hooks
        ) != 3:
            raise ValueError(
                "Dashboard deve ter 3 hooks."
            )

        if len(
            self.ranking
        ) == 0:
            raise ValueError(
                "Ranking não pode estar vazio."
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )
