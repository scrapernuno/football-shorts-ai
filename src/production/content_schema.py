from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PACKAGE_VERSION = "1.0"


VALID_ASSET_TYPES = {
    "video",
    "image",
    "graphic",
    "screenshot",
    "text",
}


VALID_CAPTION_STYLES = {
    "headline",
    "subtitle",
    "highlight",
    "cta",
}


@dataclass(frozen=True)
class SourceTopic:

    title: str
    hook: str
    viral_probability: int
    priority: int

    def __post_init__(self):

        if not self.title:
            raise ValueError(
                "SourceTopic.title obrigatório."
            )

        if not self.hook:
            raise ValueError(
                "SourceTopic.hook obrigatório."
            )

        if not (
            0 <= self.viral_probability <= 100
        ):
            raise ValueError(
                "viral_probability deve estar entre 0 e 100."
            )

        if self.priority != 1:
            raise ValueError(
                "Content production apenas aceita winner priority 1."
            )



@dataclass(frozen=True)
class ScriptPackage:

    hook: str
    introduction: str
    development: str
    climax: str
    ending: str
    call_to_action: str

    def __post_init__(self):

        fields = [

            self.hook,
            self.climax,
            self.call_to_action,

        ]

        if any(
            not value
            for value in fields
        ):

            raise ValueError(
                "Script necessita hook, climax e CTA."
            )



@dataclass(frozen=True)
class VoiceSegment:

    start_second: int
    end_second: int
    text: str

    def __post_init__(self):

        if self.start_second < 0:

            raise ValueError(
                "Voice start inválido."
            )


        if self.end_second <= self.start_second:

            raise ValueError(
                "Voice duration inválida."
            )


        if not self.text:

            raise ValueError(
                "Voice text obrigatório."
            )



@dataclass(frozen=True)
class VoicePackage:

    language: str
    style: str
    segments: tuple[VoiceSegment, ...]

    def __post_init__(self):

        if not self.language:

            raise ValueError(
                "Voice language obrigatório."
            )


        if len(self.segments) == 0:

            raise ValueError(
                "Voice necessita segmentos."
            )



@dataclass(frozen=True)
class ProductionScene:

    scene_number: int
    duration_seconds: int
    visual_instruction: str
    camera_direction: str
    voiceover_segment: str
    caption_text: str
    asset_reference: str


    def __post_init__(self):

        if self.scene_number <= 0:

            raise ValueError(
                "Scene number inválido."
            )


        if self.duration_seconds <= 0:

            raise ValueError(
                "Scene duration inválida."
            )


        required = [

            self.visual_instruction,
            self.voiceover_segment,
            self.caption_text,

        ]


        if any(
            not item
            for item in required
        ):

            raise ValueError(
                "Scene incompleta."
            )



@dataclass(frozen=True)
class Caption:

    text: str
    start_second: int
    end_second: int
    style: str


    def __post_init__(self):

        if self.style not in VALID_CAPTION_STYLES:

            raise ValueError(
                "Caption style inválido."
            )


        if self.end_second <= self.start_second:

            raise ValueError(
                "Caption timing inválido."
            )



@dataclass(frozen=True)
class AssetReference:

    asset_type: str
    description: str
    search_query: str
    copyright_status: str


    def __post_init__(self):

        if self.asset_type not in VALID_ASSET_TYPES:

            raise ValueError(
                "Asset type inválido."
            )


        if not self.description:

            raise ValueError(
                "Asset description obrigatório."
            )



@dataclass(frozen=True)
class PublishingPackage:

    platform: str
    title: str
    description: str
    hashtags: tuple[str, ...]
    scheduled_window: str



@dataclass(frozen=True)
class ContentProductionPackage:

    package_version: str
    generated_at: str

    source_topic: SourceTopic

    script: ScriptPackage

    voiceover: VoicePackage

    scenes: tuple[ProductionScene, ...]

    captions: tuple[Caption, ...]

    assets: tuple[AssetReference, ...]

    publishing: PublishingPackage


    def __post_init__(self):

        if self.package_version != PACKAGE_VERSION:

            raise ValueError(
                "Content package version inválida."
            )


        if len(self.scenes) == 0:

            raise ValueError(
                "Content package sem scenes."
            )


        expected = list(
            range(
                1,
                len(self.scenes) + 1,
            )
        )


        actual = [

            scene.scene_number

            for scene in self.scenes

        ]


        if actual != expected:

            raise ValueError(
                "Scenes devem ser sequenciais."
            )



def validate_content_package(
    payload: dict[str, Any],
) -> None:


    required = {

        "package_version",

        "generated_at",

        "source_topic",

        "script",

        "voiceover",

        "scenes",

        "captions",

        "assets",

        "publishing",

    }


    missing = (
        required
        -
        payload.keys()
    )


    if missing:

        raise ValueError(
            f"Content package incompleto: {sorted(missing)}"
        )
