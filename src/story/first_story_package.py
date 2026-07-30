"""
FOOTBALL-SHORTS-AI-0050B
FIRST STORY PACKAGE GENERATION

Creates the first governed story package for VID-0001.
No publishing. No external execution.
"""

from dataclasses import dataclass, asdict
from typing import List


@dataclass(frozen=True)
class StoryScene:
    scene_id: str
    start_second: int
    end_second: int
    purpose: str
    text: str


@dataclass(frozen=True)
class StoryPackage:
    story_id: str
    video_id: str
    duration_seconds: int
    hook: str
    scenes: List[StoryScene]


def create_first_story_package() -> StoryPackage:
    return StoryPackage(
        story_id="STORY-0001",
        video_id="VID-0001",
        duration_seconds=45,
        hook="O momento que ficou para sempre na história do futebol.",
        scenes=[
            StoryScene(
                scene_id="scene_01",
                start_second=0,
                end_second=3,
                purpose="hook",
                text="O momento que ninguém esperava.",
            ),
            StoryScene(
                scene_id="scene_02",
                start_second=3,
                end_second=38,
                purpose="story",
                text="Contexto, acontecimento e impacto histórico.",
            ),
            StoryScene(
                scene_id="scene_03",
                start_second=38,
                end_second=45,
                purpose="ending",
                text="Porque este momento ficou na memória dos adeptos.",
            ),
        ],
    )


def validate_story_package(package: StoryPackage) -> bool:
    return (
        package.story_id == "STORY-0001"
        and package.video_id == "VID-0001"
        and package.duration_seconds > 0
        and len(package.scenes) == 3
    )


if __name__ == "__main__":
    package = create_first_story_package()
    print(asdict(package))
    print("VALID=" + str(validate_story_package(package)))
