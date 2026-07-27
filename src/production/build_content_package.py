from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


DASHBOARD_SOURCE = Path(
    "output/dashboard_model.json"
)


CONTENT_OUTPUT = Path(
    "output/content_package.json"
)


PACKAGE_VERSION = "1.0"



def load_json(path: Path) -> dict:

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



def select_winner(
    dashboard: dict,
) -> dict:


    ranking = dashboard.get(
        "ranking",
        [],
    )


    if not ranking:

        raise ValueError(
            "Dashboard sem ranking."
        )


    winners = [

        item

        for item in ranking

        if item.get(
            "priority"
        ) == 1

    ]


    if len(winners) != 1:

        raise ValueError(
            "Deve existir exatamente um winner."
        )


    return winners[0]



def build_script(
    winner: dict,
) -> dict:


    title = winner.get(
        "title",
        "Football Story",
    )


    return {

        "hook":
            f"O momento que todos estão a falar: {title}",


        "introduction":
            "Vamos explicar rapidamente o que aconteceu.",


        "development":
            "Contexto, protagonistas e o momento principal.",


        "climax":
            "A jogada ou acontecimento que mudou tudo.",


        "ending":
            "Este momento ficará marcado na história.",


        "call_to_action":
            "Concordas? Comenta e segue para mais histórias.",

    }



def build_voiceover(
    script: dict,
) -> dict:


    return {

        "language": "pt-PT",

        "style": "energetic",

        "segments": [

            {
                "start_second": 0,

                "end_second": 5,

                "text": script["hook"],
            },


            {
                "start_second": 5,

                "end_second": 20,

                "text": script["development"],
            },


            {
                "start_second": 20,

                "end_second": 40,

                "text": script["climax"],
            },


            {
                "start_second": 40,

                "end_second": 45,

                "text": script["call_to_action"],
            },

        ],

    }



def build_scenes() -> list[dict]:


    return [

        {

            "scene_number": 1,

            "duration_seconds": 5,

            "visual_instruction":
                "Opening football highlight",

            "camera_direction":
                "zoom_in",

            "voiceover_segment":
                "Hook inicial",

            "caption_text":
                "O MOMENTO QUE TODOS FALAM",

            "asset_reference":
                "football_opening_clip",

        },


        {

            "scene_number": 2,

            "duration_seconds": 15,

            "visual_instruction":
                "Context football footage",

            "camera_direction":
                "pan_right",

            "voiceover_segment":
                "Contexto da história",

            "caption_text":
                "COMO TUDO ACONTECEU",

            "asset_reference":
                "football_context_clip",

        },


        {

            "scene_number": 3,

            "duration_seconds": 15,

            "visual_instruction":
                "Main football moment",

            "camera_direction":
                "slow_motion",

            "voiceover_segment":
                "Momento decisivo",

            "caption_text":
                "O MOMENTO DECISIVO",

            "asset_reference":
                "football_highlight_clip",

        },


        {

            "scene_number": 4,

            "duration_seconds": 10,

            "visual_instruction":
                "Fan reaction",

            "camera_direction":
                "zoom_out",

            "voiceover_segment":
                "Reação dos adeptos",

            "caption_text":
                "QUAL É A TUA OPINIÃO?",

            "asset_reference":
                "fans_reaction_clip",

        },

    ]



def build_content_package(
    dashboard: dict,
) -> dict:


    winner = select_winner(
        dashboard
    )


    script = build_script(
        winner
    )


    return {

        "package_version":
            PACKAGE_VERSION,


        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),


        "source_topic": {

            "title":
                winner.get(
                    "title",
                    ""
                ),

            "hook":
                winner.get(
                    "hook",
                    ""
                ),

            "viral_probability":
                int(
                    winner.get(
                        "viral_probability",
                        0
                    )
                ),

            "priority":
                1,

        },


        "script":
            script,


        "voiceover":
            build_voiceover(
                script
            ),


        "scenes":
            build_scenes(),


        "captions": [],


        "assets": [],


        "publishing": {

            "platform":
                "youtube_shorts",

            "title":
                winner.get(
                    "title",
                    ""
                ),

            "description":
                "Generated by Football Shorts AI",

            "hashtags":
                [
                    "#football",
                    "#shorts",
                ],

            "scheduled_window":
                "recommended",

        },

    }



def validate_package(
    payload: dict,
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
            f"Content package incompleto: {missing}"
        )


    scenes = payload["scenes"]


    expected = list(
        range(
            1,
            len(scenes) + 1,
        )
    )


    actual = [

        scene["scene_number"]

        for scene in scenes

    ]


    if actual != expected:

        raise ValueError(
            "Scenes inválidas."
        )



def main() -> int:


    print("=" * 70)

    print(
        "FOOTBALL SHORTS AI"
    )

    print(
        "CONTENT PRODUCTION ENGINE"
    )

    print("=" * 70)


    dashboard = load_json(
        DASHBOARD_SOURCE
    )


    package = build_content_package(
        dashboard
    )


    validate_package(
        package
    )


    save_json(
        CONTENT_OUTPUT,
        package,
    )


    print(
        "CONTENT PACKAGE BUILD PASS"
    )


    print(
        f"Winner: {package['source_topic']['title']}"
    )


    print(
        f"Scenes: {len(package['scenes'])}"
    )


    print(
        f"Output: {CONTENT_OUTPUT}"
    )


    print("=" * 70)


    return 0



if __name__ == "__main__":

    raise SystemExit(
        main()
    )
