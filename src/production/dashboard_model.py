
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

    value = value.strip()

    if not value:
        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return value


def require_score(
    value: object,
    field_name: str,
) -> int:
    if not isinstance(value, int):
        raise TypeError(
            f"{field_name} deve ser inteiro."
        )

    if not 0 <= value <= 100:
        raise ValueError(
            f"{field_name} deve estar entre 0 e 100."
        )

    return value


@dataclass(frozen=True)
class DashboardMetric:
    label: str
    value: str
    score: int

    def __post_init__(self):
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

    def __post_init__(self):
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

    def __post_init__(self):
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
                    getattr(self, field_name),
                    f"DashboardScene.{field_name}",
                ),
            )


@dataclass(frozen=True)
class DashboardTopic:
    rank: int
    title: str
    viral_score: int
    urgency: str

    def __post_init__(self):

        if self.rank < 1:
            raise ValueError(
                "DashboardTopic.rank inválido."
            )

        object.__setattr__(
            self,
            "title",
            require_text(
                self.title,
                "DashboardTopic.title",
            ),
        )

        object.__setattr__(
            self,
            "urgency",
            require_text(
                self.urgency,
                "DashboardTopic.urgency",
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
    predicted_ctr: str
    predicted_retention: str
    recommended_publish_time: str

    metrics: tuple[DashboardMetric, ...]
    hooks: tuple[DashboardHook, ...]
    storyboard: tuple[DashboardScene, ...]
    ranking: tuple[DashboardTopic, ...]

    def __post_init__(self):

        for field_name in (
            "generated_at",
            "channel",
            "top_title",
            "top_hook",
            "predicted_ctr",
            "predicted_retention",
            "recommended_publish_time",
        ):
            object.__setattr__(
                self,
                field_name,
                require_text(
                    getattr(self, field_name),
                    f"DashboardModel.{field_name}",
                ),
            )

        require_score(
            self.viral_probability,
            "DashboardModel.viral_probability",
        )

        if len(self.hooks) != 3:
            raise ValueError(
                "Dashboard deve ter 3 hooks."
            )

        if len(self.ranking) == 0:
            raise ValueError(
                "Ranking não pode estar vazio."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
