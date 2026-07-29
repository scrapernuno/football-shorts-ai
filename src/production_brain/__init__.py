"""Production Brain public contract foundation.

FOOTBALL-SHORTS-AI-0040C introduces contracts only. It does not provide
runtime orchestration, engine execution, workflow migration, publication,
or network authority.
"""

from .contracts import (
    ArtifactReference,
    EngineContract,
    EngineResult,
    EngineStatus,
    ProductionContext,
    ProductionStage,
)

__all__ = [
    "ArtifactReference",
    "EngineContract",
    "EngineResult",
    "EngineStatus",
    "ProductionContext",
    "ProductionStage",
]
