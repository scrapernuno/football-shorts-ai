from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SOURCE = Path(
    "output/content_package.json"
)


OUTPUT = Path(
    "output/publishing_package.json"
)


PACKAGE_VERSION = "1.0"



def load_json(
    path: Path,
) -> dict:

    if not path.exists():

        raise FileNotFoundError(
            f"Ficheiro não encontrado: {path}"
        )


    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )



def save_json(
    path: Path,
    payload: dict,
) -> None:


    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    path.write_text(

        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),

        encoding="utf-8",
    )



def validate_content_package(
    payload: dict,
) -> None:


    required = {

        "package_version",

        "source_topic",

        "script",

        "publishing",

    }


    missing = (

        required

        -

        payload.keys()

    )


    if missing:

        raise ValueError(
            f"Content package inválido: {missing}"
        )



def build_thumbnail(
    content: dict,
) -> dict:


    title = content["source_topic"].get(
        "title",
        "",
    )


    return {

        "text_overlay":
            title.upper()[:45],


        "visual_direction":
            "High emotion football frame with player reaction",


        "emotion_target":
            "curiosity",

    }



def build_metadata(
    content: dict,
) -> dict:


    source = content["source_topic"]


    title = source.get(
        "title",
        "Football Short",
    )


    return {

        "platform":
            "youtube_shorts",


        "title":
            title,


        "description":
            (
                f"{title}. "
                "História gerada pelo Football Shorts AI."
            ),


        "hashtags":
            [

                "#football",

                "#soccer",

                "#shorts",

            ],


        "scheduled_window":
            "recommended",

    }



def build_checklist() -> dict:


    return {

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

    }



def build_publishing_package(
    content: dict,
) -> dict:


    validate_content_package(
        content
    )


    source = content["source_topic"]


    content_id = (

        source.get(
            "title",
            "football-short",
        )

        .lower()

        .replace(
            " ",
            "-",
        )

    )


    return {


        "package_version":

            PACKAGE_VERSION,


        "generated_at":

            datetime.now(
                timezone.utc
            ).isoformat(),



        "source_content_id":

            content_id,



        "metadata":

            build_metadata(
                content
            ),



        "thumbnail":

            build_thumbnail(
                content
            ),



        "checklist":

            build_checklist(),



        "status":

            "draft",

    }



def validate_publishing_package(
    payload: dict,
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


    if payload["status"] != "draft":

        raise ValueError(
            "Estado inicial deve ser draft."
        )



def main() -> int:


    print("=" * 70)

    print(
        "FOOTBALL SHORTS AI"
    )

    print(
        "PUBLISHING AUTOMATION ENGINE"
    )

    print("=" * 70)



    content = load_json(
        SOURCE
    )


    publishing = build_publishing_package(
        content
    )


    validate_publishing_package(
        publishing
    )


    save_json(
        OUTPUT,
        publishing,
    )


    print(
        "PUBLISHING PACKAGE BUILD PASS"
    )


    print(
        f"Source: {SOURCE}"
    )


    print(
        f"Output: {OUTPUT}"
    )


    print(
        f"Status: {publishing['status']}"
    )


    print("=" * 70)


    return 0



if __name__ == "__main__":

    raise SystemExit(
        main()
    )
