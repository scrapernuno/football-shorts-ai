from __future__ import annotations

import json
from typing import Any, TypeVar, cast

from editorial.schema import (
    AssetSuggestion,
    EditorialContent,
    EditorialPackage,
    EditorialTopicPackage,
    EditorChecklist,
    PredictedAnalytics,
    PublishingPlan,
    RankingAssessment,
    ScoredTextOption,
    SourceReference,
    Storyboard,
    StoryboardScene,
)


class EditorialPackageParseError(ValueError):
    """Resposta editorial ausente, inválida ou incompatível."""


T = TypeVar("T")


def require_mapping(
    value: object,
    field_name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EditorialPackageParseError(
            f"{field_name} deve ser um objeto JSON."
        )

    return cast(dict[str, Any], value)


def require_list(
    value: object,
    field_name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise EditorialPackageParseError(
            f"{field_name} deve ser uma lista JSON."
        )

    return cast(list[Any], value)


def require_string(
    value: object,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise EditorialPackageParseError(
            f"{field_name} deve ser uma string."
        )

    normalized = value.strip()

    if not normalized:
        raise EditorialPackageParseError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def require_integer(
    value: object,
    field_name: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
    ):
        raise EditorialPackageParseError(
            f"{field_name} deve ser um número inteiro."
        )

    return value


def require_number(
    value: object,
    field_name: str,
) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
    ):
        raise EditorialPackageParseError(
            f"{field_name} deve ser numérico."
        )

    return float(value)


def require_boolean(
    value: object,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise EditorialPackageParseError(
            f"{field_name} deve ser booleano."
        )

    return value


def require_exact_keys(
    payload: dict[str, Any],
    *,
    required: set[str],
    field_name: str,
) -> None:
    actual = set(payload)

    missing = required - actual
    unexpected = actual - required

    if missing:
        raise EditorialPackageParseError(
            f"{field_name} não contém os campos obrigatórios: "
            f"{sorted(missing)}"
        )

    if unexpected:
        raise EditorialPackageParseError(
            f"{field_name} contém campos inesperados: "
            f"{sorted(unexpected)}"
        )


def parse_scored_text_option(
    value: object,
    field_name: str,
) -> ScoredTextOption:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "text",
            "score",
        },
        field_name=field_name,
    )

    return ScoredTextOption(
        text=require_string(
            payload["text"],
            f"{field_name}.text",
        ),
        score=require_integer(
            payload["score"],
            f"{field_name}.score",
        ),
    )


def parse_scored_text_options(
    value: object,
    field_name: str,
) -> tuple[ScoredTextOption, ...]:
    items = require_list(value, field_name)

    return tuple(
        parse_scored_text_option(
            item,
            f"{field_name}[{index}]",
        )
        for index, item in enumerate(items)
    )


def parse_source_reference(
    value: object,
    field_name: str,
) -> SourceReference:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "title",
            "name",
            "url",
            "published",
            "confirmation_status",
        },
        field_name=field_name,
    )

    confirmation_status = require_string(
        payload["confirmation_status"],
        f"{field_name}.confirmation_status",
    )

    return SourceReference(
        title=require_string(
            payload["title"],
            f"{field_name}.title",
        ),
        name=require_string(
            payload["name"],
            f"{field_name}.name",
        ),
        url=require_string(
            payload["url"],
            f"{field_name}.url",
        ),
        published=require_string(
            payload["published"],
            f"{field_name}.published",
        ),
        confirmation_status=cast(
            Any,
            confirmation_status,
        ),
    )


def parse_ranking_assessment(
    value: object,
    field_name: str,
) -> RankingAssessment:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "priority",
            "viral_probability",
            "competition",
            "breaking",
            "publish_today",
            "reason",
        },
        field_name=field_name,
    )

    competition = require_string(
        payload["competition"],
        f"{field_name}.competition",
    )

    return RankingAssessment(
        priority=require_integer(
            payload["priority"],
            f"{field_name}.priority",
        ),
        viral_probability=require_integer(
            payload["viral_probability"],
            f"{field_name}.viral_probability",
        ),
        competition=cast(
            Any,
            competition,
        ),
        breaking=require_boolean(
            payload["breaking"],
            f"{field_name}.breaking",
        ),
        publish_today=require_boolean(
            payload["publish_today"],
            f"{field_name}.publish_today",
        ),
        reason=require_string(
            payload["reason"],
            f"{field_name}.reason",
        ),
    )


def parse_editorial_content(
    value: object,
    field_name: str,
) -> EditorialContent:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "primary_title",
            "alternative_titles",
            "primary_hook",
            "alternative_hooks",
            "script",
            "call_to_action",
            "pinned_comment",
            "description",
            "hashtags",
        },
        field_name=field_name,
    )

    hashtags_raw = require_list(
        payload["hashtags"],
        f"{field_name}.hashtags",
    )

    hashtags = tuple(
        require_string(
            hashtag,
            f"{field_name}.hashtags[{index}]",
        )
        for index, hashtag in enumerate(hashtags_raw)
    )

    return EditorialContent(
        primary_title=require_string(
            payload["primary_title"],
            f"{field_name}.primary_title",
        ),
        alternative_titles=parse_scored_text_options(
            payload["alternative_titles"],
            f"{field_name}.alternative_titles",
        ),
        primary_hook=require_string(
            payload["primary_hook"],
            f"{field_name}.primary_hook",
        ),
        alternative_hooks=parse_scored_text_options(
            payload["alternative_hooks"],
            f"{field_name}.alternative_hooks",
        ),
        script=require_string(
            payload["script"],
            f"{field_name}.script",
        ),
        call_to_action=require_string(
            payload["call_to_action"],
            f"{field_name}.call_to_action",
        ),
        pinned_comment=require_string(
            payload["pinned_comment"],
            f"{field_name}.pinned_comment",
        ),
        description=require_string(
            payload["description"],
            f"{field_name}.description",
        ),
        hashtags=hashtags,
    )


def parse_asset_suggestion(
    value: object,
    field_name: str,
) -> AssetSuggestion:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "asset_type",
            "description",
            "search_queries",
            "preferred_source",
            "fallback_description",
            "copyright_note",
        },
        field_name=field_name,
    )

    queries_raw = require_list(
        payload["search_queries"],
        f"{field_name}.search_queries",
    )

    queries = tuple(
        require_string(
            query,
            f"{field_name}.search_queries[{index}]",
        )
        for index, query in enumerate(queries_raw)
    )

    asset_type = require_string(
        payload["asset_type"],
        f"{field_name}.asset_type",
    )

    return AssetSuggestion(
        asset_type=cast(
            Any,
            asset_type,
        ),
        description=require_string(
            payload["description"],
            f"{field_name}.description",
        ),
        search_queries=queries,
        preferred_source=require_string(
            payload["preferred_source"],
            f"{field_name}.preferred_source",
        ),
        fallback_description=require_string(
            payload["fallback_description"],
            f"{field_name}.fallback_description",
        ),
        copyright_note=require_string(
            payload["copyright_note"],
            f"{field_name}.copyright_note",
        ),
    )


def parse_storyboard_scene(
    value: object,
    field_name: str,
) -> StoryboardScene:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "scene_number",
            "start_second",
            "end_second",
            "voiceover",
            "subtitle",
            "visual_type",
            "visual_description",
            "editing_pace",
            "transition",
            "subtitle_style",
            "camera_movement",
            "sound_effect",
            "asset",
        },
        field_name=field_name,
    )

    return StoryboardScene(
        scene_number=require_integer(
            payload["scene_number"],
            f"{field_name}.scene_number",
        ),
        start_second=require_integer(
            payload["start_second"],
            f"{field_name}.start_second",
        ),
        end_second=require_integer(
            payload["end_second"],
            f"{field_name}.end_second",
        ),
        voiceover=require_string(
            payload["voiceover"],
            f"{field_name}.voiceover",
        ),
        subtitle=require_string(
            payload["subtitle"],
            f"{field_name}.subtitle",
        ),
        visual_type=cast(
            Any,
            require_string(
                payload["visual_type"],
                f"{field_name}.visual_type",
            ),
        ),
        visual_description=require_string(
            payload["visual_description"],
            f"{field_name}.visual_description",
        ),
        editing_pace=cast(
            Any,
            require_string(
                payload["editing_pace"],
                f"{field_name}.editing_pace",
            ),
        ),
        transition=cast(
            Any,
            require_string(
                payload["transition"],
                f"{field_name}.transition",
            ),
        ),
        subtitle_style=cast(
            Any,
            require_string(
                payload["subtitle_style"],
                f"{field_name}.subtitle_style",
            ),
        ),
        camera_movement=cast(
            Any,
            require_string(
                payload["camera_movement"],
                f"{field_name}.camera_movement",
            ),
        ),
        sound_effect=require_string(
            payload["sound_effect"],
            f"{field_name}.sound_effect",
        ),
        asset=parse_asset_suggestion(
            payload["asset"],
            f"{field_name}.asset",
        ),
    )


def parse_storyboard(
    value: object,
    field_name: str,
) -> Storyboard:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "estimated_duration_seconds",
            "required_clip_count",
            "scenes",
        },
        field_name=field_name,
    )

    scenes_raw = require_list(
        payload["scenes"],
        f"{field_name}.scenes",
    )

    scenes = tuple(
        parse_storyboard_scene(
            scene,
            f"{field_name}.scenes[{index}]",
        )
        for index, scene in enumerate(scenes_raw)
    )

    return Storyboard(
        estimated_duration_seconds=require_integer(
            payload["estimated_duration_seconds"],
            f"{field_name}.estimated_duration_seconds",
        ),
        required_clip_count=require_integer(
            payload["required_clip_count"],
            f"{field_name}.required_clip_count",
        ),
        scenes=scenes,
    )


def parse_publishing_plan(
    value: object,
    field_name: str,
) -> PublishingPlan:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "urgency",
            "best_publish_time",
            "publish_window_minutes",
            "relevance_lifetime_hours",
            "timezone",
            "publication_reason",
        },
        field_name=field_name,
    )

    return PublishingPlan(
        urgency=cast(
            Any,
            require_string(
                payload["urgency"],
                f"{field_name}.urgency",
            ),
        ),
        best_publish_time=require_string(
            payload["best_publish_time"],
            f"{field_name}.best_publish_time",
        ),
        publish_window_minutes=require_integer(
            payload["publish_window_minutes"],
            f"{field_name}.publish_window_minutes",
        ),
        relevance_lifetime_hours=require_integer(
            payload["relevance_lifetime_hours"],
            f"{field_name}.relevance_lifetime_hours",
        ),
        timezone=require_string(
            payload["timezone"],
            f"{field_name}.timezone",
        ),
        publication_reason=require_string(
            payload["publication_reason"],
            f"{field_name}.publication_reason",
        ),
    )


def parse_predicted_analytics(
    value: object,
    field_name: str,
) -> PredictedAnalytics:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "predicted_ctr_percent",
            "predicted_retention_percent",
            "predicted_views_low",
            "predicted_views_high",
            "predicted_comment_rate_percent",
            "confidence_score",
            "prediction_basis",
        },
        field_name=field_name,
    )

    return PredictedAnalytics(
        predicted_ctr_percent=require_number(
            payload["predicted_ctr_percent"],
            f"{field_name}.predicted_ctr_percent",
        ),
        predicted_retention_percent=require_number(
            payload["predicted_retention_percent"],
            f"{field_name}.predicted_retention_percent",
        ),
        predicted_views_low=require_integer(
            payload["predicted_views_low"],
            f"{field_name}.predicted_views_low",
        ),
        predicted_views_high=require_integer(
            payload["predicted_views_high"],
            f"{field_name}.predicted_views_high",
        ),
        predicted_comment_rate_percent=require_number(
            payload["predicted_comment_rate_percent"],
            f"{field_name}.predicted_comment_rate_percent",
        ),
        confidence_score=require_integer(
            payload["confidence_score"],
            f"{field_name}.confidence_score",
        ),
        prediction_basis=require_string(
            payload["prediction_basis"],
            f"{field_name}.prediction_basis",
        ),
    )


def parse_editor_checklist(
    value: object,
    field_name: str,
) -> EditorChecklist:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "hook_first_two_seconds",
            "duration_valid",
            "thumbnail_short",
            "call_to_action_present",
            "pinned_comment_present",
            "sources_require_confirmation",
            "missing_assets",
        },
        field_name=field_name,
    )

    missing_assets_raw = require_list(
        payload["missing_assets"],
        f"{field_name}.missing_assets",
    )

    missing_assets = tuple(
        require_string(
            item,
            f"{field_name}.missing_assets[{index}]",
        )
        for index, item in enumerate(missing_assets_raw)
    )

    return EditorChecklist(
        hook_first_two_seconds=require_boolean(
            payload["hook_first_two_seconds"],
            f"{field_name}.hook_first_two_seconds",
        ),
        duration_valid=require_boolean(
            payload["duration_valid"],
            f"{field_name}.duration_valid",
        ),
        thumbnail_short=require_boolean(
            payload["thumbnail_short"],
            f"{field_name}.thumbnail_short",
        ),
        call_to_action_present=require_boolean(
            payload["call_to_action_present"],
            f"{field_name}.call_to_action_present",
        ),
        pinned_comment_present=require_boolean(
            payload["pinned_comment_present"],
            f"{field_name}.pinned_comment_present",
        ),
        sources_require_confirmation=require_boolean(
            payload["sources_require_confirmation"],
            f"{field_name}.sources_require_confirmation",
        ),
        missing_assets=missing_assets,
    )


def parse_editorial_topic_package(
    value: object,
    field_name: str,
) -> EditorialTopicPackage:
    payload = require_mapping(value, field_name)

    require_exact_keys(
        payload,
        required={
            "topic_id",
            "ranking",
            "source",
            "editorial",
            "storyboard",
            "publishing",
            "analytics",
            "checklist",
        },
        field_name=field_name,
    )

    return EditorialTopicPackage(
        topic_id=require_string(
            payload["topic_id"],
            f"{field_name}.topic_id",
        ),
        ranking=parse_ranking_assessment(
            payload["ranking"],
            f"{field_name}.ranking",
        ),
        source=parse_source_reference(
            payload["source"],
            f"{field_name}.source",
        ),
        editorial=parse_editorial_content(
            payload["editorial"],
            f"{field_name}.editorial",
        ),
        storyboard=parse_storyboard(
            payload["storyboard"],
            f"{field_name}.storyboard",
        ),
        publishing=parse_publishing_plan(
            payload["publishing"],
            f"{field_name}.publishing",
        ),
        analytics=parse_predicted_analytics(
            payload["analytics"],
            f"{field_name}.analytics",
        ),
        checklist=parse_editor_checklist(
            payload["checklist"],
            f"{field_name}.checklist",
        ),
    )


def parse_editorial_package_dict(
    value: object,
) -> EditorialPackage:
    payload = require_mapping(
        value,
        "EditorialPackage",
    )

    require_exact_keys(
        payload,
        required={
            "schema_version",
            "generated_at",
            "channel",
            "language",
            "timezone",
            "top_topic_id",
            "topics",
        },
        field_name="EditorialPackage",
    )

    topics_raw = require_list(
        payload["topics"],
        "EditorialPackage.topics",
    )

    topics = tuple(
        parse_editorial_topic_package(
            topic,
            f"EditorialPackage.topics[{index}]",
        )
        for index, topic in enumerate(topics_raw)
    )

    try:
        return EditorialPackage(
            schema_version=require_string(
                payload["schema_version"],
                "EditorialPackage.schema_version",
            ),
            generated_at=require_string(
                payload["generated_at"],
                "EditorialPackage.generated_at",
            ),
            channel=require_string(
                payload["channel"],
                "EditorialPackage.channel",
            ),
            language=require_string(
                payload["language"],
                "EditorialPackage.language",
            ),
            timezone=require_string(
                payload["timezone"],
                "EditorialPackage.timezone",
            ),
            top_topic_id=require_string(
                payload["top_topic_id"],
                "EditorialPackage.top_topic_id",
            ),
            topics=topics,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise EditorialPackageParseError(
            f"Editorial Package inválido: {exc}"
        ) from exc


def parse_editorial_package_json(
    raw_json: str,
) -> EditorialPackage:
    if not isinstance(raw_json, str):
        raise TypeError(
            "raw_json deve ser uma string."
        )

    normalized = raw_json.strip()

    if not normalized:
        raise EditorialPackageParseError(
            "A resposta JSON está vazia."
        )

    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise EditorialPackageParseError(
            "A resposta não contém JSON válido. "
            f"Linha={exc.lineno}; "
            f"coluna={exc.colno}; "
            f"mensagem={exc.msg}"
        ) from exc

    return parse_editorial_package_dict(payload)


def serialize_editorial_package(
    package: EditorialPackage,
) -> str:
    return json.dumps(
        package.to_dict(),
        ensure_ascii=False,
        indent=2,
    )
