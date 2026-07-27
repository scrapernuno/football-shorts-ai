from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PACKAGE_VERSION = "1.0"


VALID_PLATFORMS = {
    "youtube_shorts",
}


VALID_STATUS = {
    "draft",
    "ready",
    "scheduled",
    "published",
}



@dataclass(frozen=True)
class PublishingMetadata:

    platform: str

    title: str

    description: str

    hashtags: tuple[str, ...]

    scheduled_window: str


    def __post_init__(self):

        if self.platform not in VALID_PLATFORMS:

            raise ValueError(
                "Publishing platform inválida."
            )


        if not self.title:

            raise ValueError(
                "Publishing title obrigatório."
            )


        if not self.description:

            raise ValueError(
                "Publishing description obrigatório."
            )


        if len(self.hashtags) == 0:

            raise ValueError(
                "Hashtags obrigatórias."
            )



@dataclass(frozen=True)
class ThumbnailBrief:

    text_overlay: str

    visual_direction: str

    emotion_target: str


    def __post_init__(self):

        required = [

            self.text_overlay,

            self.visual_direction,

            self.emotion_target,

        ]


        if any(
            not item
            for item in required
        ):

            raise ValueError(
                "Thumbnail brief incompleto."
            )



@dataclass(frozen=True)
class PublishingChecklist:

    title_valid: bool

    description_valid: bool

    hashtags_valid: bool

    thumbnail_ready: bool

    copyright_review_required: bool

    final_confirmation_required: bool



@dataclass(frozen=True)
class PublishingPackage:


    package_version: str

    generated_at: str


    source_content_id: str


    metadata: PublishingMetadata


    thumbnail: ThumbnailBrief


    checklist: PublishingChecklist


    status: str



    def __post_init__(self):

        if self.package_version != PACKAGE_VERSION:

            raise ValueError(
                "Publishing package version inválida."
            )


        if self.status not in VALID_STATUS:

            raise ValueError(
                "Publishing status inválido."
            )


        if not self.source_content_id:

            raise ValueError(
                "Source content obrigatório."
            )



def validate_publishing_payload(
    payload: dict[str, Any],
) -> None:


    required = {

        "package_version",

        "generated_at",

        "source_content_id",

        "metadata",

        "thumbnail",

        "checklist",

        "status",

    }


    missing = (

        required

        -

        payload.keys()

    )


    if missing:

        raise ValueError(
            f"Publishing package incompleto: {missing}"
        )



def validate_checklist(
    checklist: dict[str, Any],
) -> None:


    required = {

        "title_valid",

        "description_valid",

        "hashtags_valid",

        "thumbnail_ready",

        "copyright_review_required",

        "final_confirmation_required",

    }


    missing = (

        required

        -

        checklist.keys()

    )


    if missing:

        raise ValueError(
            f"Checklist inválida: {missing}"
        )



def build_default_publishing_package(
    content_package: dict[str, Any],
) -> dict[str, Any]:


    source = content_package.get(
        "source_topic",
        {},
    )


    title = source.get(
        "title",
        "Football Short",
    )


    return {


        "package_version":

            PACKAGE_VERSION,


        "generated_at":

            content_package.get(
                "generated_at",
                "",
            ),



        "source_content_id":

            title.lower()
            .replace(
                " ",
                "-",
            ),



        "metadata": {


            "platform":

                "youtube_shorts",



            "title":

                title,



            "description":

                "Football Shorts AI generated content.",



            "hashtags":

                [

                    "#football",

                    "#shorts",

                    "#soccer",

                ],



            "scheduled_window":

                "recommended",

        },



        "thumbnail": {


            "text_overlay":

                "O MOMENTO QUE TODOS FALAM",



            "visual_direction":

                "High emotion football frame",



            "emotion_target":

                "curiosity",

        },



        "checklist": {


            "title_valid":

                True,


            "description_valid":

                True,


            "hashtags_valid":

                True,


            "thumbnail_ready":

                False,


            "copyright_review_required":

                True,


            "final_confirmation_required":

                True,

        },


        "status":

            "draft",

    }
