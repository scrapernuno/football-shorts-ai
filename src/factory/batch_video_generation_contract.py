"""
FOOTBALL-SHORTS-AI-0051A
BATCH VIDEO GENERATION CONTRACT

First artifact for automated video factory scale.
Provider neutral and fail closed.
"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BatchVideoItem:
    video_id: str
    priority: str = "medium"
    status: str = "pending"


@dataclass(frozen=True)
class BatchVideoGenerationContract:
    batch_id: str
    videos: List[BatchVideoItem]
    auto_publish: bool = False

    def validate(self) -> bool:
        ids = [item.video_id for item in self.videos]
        return (
            bool(self.batch_id)
            and len(ids) == len(set(ids))
            and self.auto_publish is False
        )


__all__ = [
    "BatchVideoItem",
    "BatchVideoGenerationContract",
]
