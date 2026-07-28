from __future__ import annotations

import json

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CONTENT_PATH = (
    ROOT
    /
    "output"
    /
    "content_package.json"
)

INTELLIGENCE_PATH = (
    ROOT
    /
    "output"
    /
    "tiktok_trend_intelligence.json"
)

OUTPUT_PATH = (
    ROOT
    /
    "output"
    /
    "platform_variants.json"
)


VARIANTS_VERSION = "1.0"


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro em falta: {path}"
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            f"{path} deve conter "
            "um objeto JSON."
        )

    return payload


def write_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        path.parent
        /
        f".{path.name}.tmp"
    )

    temporary_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        +
        "\n",
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def safe_mapping(
    value: object,
) -> dict[str, Any]:

    return (
        value
        if isinstance(
            value,
            dict,
        )
        else
        {}
    )


def build_variants(
    content: dict[str, Any],
    intelligence: dict[str, Any],
) -> dict[str, Any]:

    source_topic = safe_mapping(
        content.get(
            "source_topic"
        )
    )

    publishing = safe_mapping(
        content.get(
            "publishing"
        )
    )

    selected_video = intelligence.get(
        "selected_video"
    )

    if not isinstance(
        selected_video,
        dict,
    ):

        selected_video = None

    selected_sound = intelligence.get(
        "selected_sound"
    )

    if not isinstance(
        selected_sound,
        dict,
    ):

        selected_sound = None

    readiness = safe_mapping(
        intelligence.get(
            "readiness"
        )
    )

    tiktok_ready = (
        readiness.get(
            "tiktok_variant_ready"
        )
        is True
    )

    cross_platform_ugc_ready = (
        readiness.get(
            "cross_platform_ugc_ready"
        )
        is True
    )

    base_title = str(
        source_topic.get(
            "title",
            publishing.get(
                "title",
                "Football Short",
            ),
        )
    )

    base_hook = str(
        source_topic.get(
            "hook",
            "",
        )
    )

    tiktok_usage_mode = (
        selected_video.get(
            "usage_mode"
        )
        if selected_video
        else
        None
    )

    tiktok_sound_mode = (
        selected_sound.get(
            "rights_classification"
        )
        if selected_sound
        else
        None
    )

    return {
        "platform_variants_version":
            VARIANTS_VERSION,

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "content_title":
            base_title,

        "clean_master":
            {
                "format":
                    "vertical_9_16",

                "third_party_tiktok_video_embedded":
                    False,

                "platform_music_embedded":
                    False,

                "watermark_present":
                    False,

                "status":
                    "planned",
            },

        "variants":
            {
                "tiktok":
                    {
                        "hook":
                            base_hook,

                        "video_strategy":
                            (
                                tiktok_usage_mode
                                or
                                "original_clean_master"
                            ),

                        "trend_source_url":
                            (
                                selected_video.get(
                                    "source_url"
                                )
                                if selected_video
                                else
                                None
                            ),

                        "creator_username":
                            (
                                selected_video.get(
                                    "creator_username"
                                )
                                if selected_video
                                else
                                None
                            ),

                        "sound_strategy":
                            (
                                tiktok_sound_mode
                                or
                                "commercial_music_library_selection_required"
                            ),

                        "sound_source_url":
                            (
                                selected_sound.get(
                                    "source_url"
                                )
                                if selected_sound
                                else
                                None
                            ),

                        "execution_status":
                            (
                                "manual_native_action_required"
                                if tiktok_ready
                                else
                                "blocked"
                            ),

                        "platform_native_execution":
                            True,

                        "automatic_publication":
                            False,
                    },

                "instagram_reels":
                    {
                        "hook":
                            base_hook,

                        "video_strategy":
                            (
                                "licensed_ugc_or_clean_master"
                                if cross_platform_ugc_ready
                                else
                                "clean_master_only"
                            ),

                        "tiktok_native_remix_imported":
                            False,

                        "audio_strategy":
                            "instagram_native_audio_selection_required",

                        "execution_status":
                            "adaptation_required",

                        "automatic_publication":
                            False,
                    },

                "youtube_shorts":
                    {
                        "title":
                            base_title,

                        "hook":
                            base_hook,

                        "video_strategy":
                            (
                                "licensed_ugc_or_clean_master"
                                if cross_platform_ugc_ready
                                else
                                "clean_master_only"
                            ),

                        "tiktok_native_remix_imported":
                            False,

                        "audio_strategy":
                            "youtube_native_audio_or_external_license",

                        "execution_status":
                            "adaptation_required",

                        "automatic_publication":
                            False,
                    },
            },

        "governance":
            {
                "same_news":
                    True,

                "same_concept":
                    True,

                "same_clean_master_permitted":
                    True,

                "same_final_file_required":
                    False,

                "third_party_download_allowed":
                    False,

                "watermark_removal_allowed":
                    False,

                "native_remix_platform_bound":
                    True,

                "cross_platform_third_party_use_requires_license":
                    True,

                "publication_execution_enabled":
                    False,
            },
    }


def validate_variants(
    payload: dict[str, Any],
) -> None:

    clean_master = safe_mapping(
        payload.get(
            "clean_master"
        )
    )

    if clean_master.get(
        "third_party_tiktok_video_embedded"
    ) is not False:

        raise ValueError(
            "TikTok de terceiro não pode "
            "ser embebido no clean master."
        )

    if clean_master.get(
        "platform_music_embedded"
    ) is not False:

        raise ValueError(
            "Música de plataforma não pode "
            "ser embebida no clean master."
        )

    governance = safe_mapping(
        payload.get(
            "governance"
        )
    )

    for key in (
        "third_party_download_allowed",
        "watermark_removal_allowed",
        "publication_execution_enabled",
    ):

        if governance.get(
            key
        ) is not False:

            raise ValueError(
                f"{key} deve permanecer false."
            )

    variants = safe_mapping(
        payload.get(
            "variants"
        )
    )

    for platform in (
        "tiktok",
        "instagram_reels",
        "youtube_shorts",
    ):

        variant = safe_mapping(
            variants.get(
                platform
            )
        )

        if variant.get(
            "automatic_publication"
        ) is not False:

            raise ValueError(
                "Publicação automática ativada "
                f"em {platform}."
            )


def main() -> int:

    content = load_json(
        CONTENT_PATH
    )

    intelligence = load_json(
        INTELLIGENCE_PATH
    )

    variants = build_variants(
        content,
        intelligence,
    )

    validate_variants(
        variants
    )

    write_json_atomically(
        OUTPUT_PATH,
        variants,
    )

    print(
        "PLATFORM_VARIANTS_BUILD=PASS"
    )

    print(
        "TIKTOK_NATIVE_VARIANT=PLANNED"
    )

    print(
        "INSTAGRAM_NATIVE_VARIANT=PLANNED"
    )

    print(
        "YOUTUBE_NATIVE_VARIANT=PLANNED"
    )

    print(
        "PUBLICATION_EXECUTION_ENABLED=NO"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
