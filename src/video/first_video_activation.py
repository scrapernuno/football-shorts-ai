"""
FOOTBALL-SHORTS-AI-0050A
FIRST VIDEO PRODUCTION ACTIVATION

Controlled activation contract for the first real video pipeline.
No publishing execution.
No external provider calls.
Deterministic state generation only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class VideoActivation:
    video_id: str
    activation: str
    status: str
    auto_publish: bool
    stages: dict[str, str]
    created_at: str


def create_first_video_activation() -> dict:
    """Create the controlled VID-0001 activation contract."""

    activation = VideoActivation(
        video_id="VID-0001",
        activation="FIRST_VIDEO",
        status="READY",
        auto_publish=False,
        stages={
            "topic": "pending",
            "story": "pending",
            "production": "pending",
            "render": "pending",
            "dashboard": "pending",
        },
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    return asdict(activation)


if __name__ == "__main__":
    print(create_first_video_activation())
