"""
FOOTBALL-SHORTS-AI-0050C
FIRST PRODUCTION PACKAGE GENERATION

Creates the governed production handoff for VID-0001.
No rendering. No publishing.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ProductionPackage:
    production_id: str
    video_id: str
    story_id: str
    format: str
    resolution: str
    duration_seconds: int
    subtitle_enabled: bool
    render_ready: bool


def create_first_production_package() -> dict:
    package = ProductionPackage(
        production_id="PRODUCTION-0001",
        video_id="VID-0001",
        story_id="STORY-0001",
        format="vertical_9_16",
        resolution="1080x1920",
        duration_seconds=45,
        subtitle_enabled=True,
        render_ready=True,
    )

    return asdict(package)


if __name__ == "__main__":
    print(create_first_production_package())
