from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


class ProductionStage(str, Enum):
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    EVIDENCE = "evidence"
    REFERENCES = "references"
    STORY = "story"
    EMOTION = "emotion"
    AUDIENCE = "audience"
    PRODUCTION = "production"
    QUALITY = "quality"
    PUBLISHING = "publishing"
    ANALYTICS = "analytics"
    LEARNING = "learning"


class EngineStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    artifact_id: str
    path: str
    media_type: str = "application/json"
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact_id must not be empty")
        if not self.path.strip():
            raise ValueError("path must not be empty")
        candidate = PurePosixPath(self.path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("path must be repository-relative")
        if self.sha256 is not None:
            normalized = self.sha256.lower()
            if len(normalized) != 64 or any(
                character not in "0123456789abcdef"
                for character in normalized
            ):
                raise ValueError("sha256 must be a 64-character hex digest")


@dataclass(frozen=True, slots=True)
class ProductionContext:
    execution_id: str
    correlation_id: str
    source_topic_id: str
    current_stage: ProductionStage
    artifacts: tuple[ArtifactReference, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in (
            "execution_id",
            "correlation_id",
            "source_topic_id",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        object.__setattr__(
            self,
            "metadata",
            _freeze_mapping(self.metadata),
        )

    def advance(
        self,
        stage: ProductionStage,
        *,
        artifacts: tuple[ArtifactReference, ...] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ProductionContext":
        return ProductionContext(
            execution_id=self.execution_id,
            correlation_id=self.correlation_id,
            source_topic_id=self.source_topic_id,
            current_stage=stage,
            artifacts=self.artifacts if artifacts is None else artifacts,
            metadata=self.metadata if metadata is None else metadata,
        )


@dataclass(frozen=True, slots=True)
class EngineResult:
    engine_id: str
    stage: ProductionStage
    status: EngineStatus
    context: ProductionContext
    produced_artifacts: tuple[ArtifactReference, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.engine_id.strip():
            raise ValueError("engine_id must not be empty")
        if self.stage is not self.context.current_stage:
            raise ValueError("result stage must match context current_stage")
        object.__setattr__(
            self,
            "evidence",
            _freeze_mapping(self.evidence),
        )
        if self.status is EngineStatus.FAILED:
            if not self.error_code or not self.error_message:
                raise ValueError(
                    "failed results require error_code and error_message"
                )
        elif self.error_code is not None or self.error_message is not None:
            raise ValueError(
                "non-failed results must not include error information"
            )


@runtime_checkable
class EngineContract(Protocol):
    @property
    def engine_id(self) -> str:
        """Return the stable engine identifier."""

    @property
    def stage(self) -> ProductionStage:
        """Return the single stage governed by this engine."""

    def execute(self, context: ProductionContext) -> EngineResult:
        """Execute deterministically for the supplied immutable context."""
