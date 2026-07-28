from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIRECTORY = ROOT / "output"

DASHBOARD_DIRECTORY = ROOT / "dashboard"
DASHBOARD_DATA_DIRECTORY = DASHBOARD_DIRECTORY / "data"
DASHBOARD_ASSETS_DIRECTORY = DASHBOARD_DIRECTORY / "assets"

INDEX_FILE = DASHBOARD_DIRECTORY / "index.html"
CSS_FILE = DASHBOARD_ASSETS_DIRECTORY / "dashboard.css"
JAVASCRIPT_FILE = DASHBOARD_ASSETS_DIRECTORY / "dashboard.js"

OUTPUT_DASHBOARD_MODEL = (
    OUTPUT_DIRECTORY
    / "dashboard_model.json"
)

OUTPUT_CONTENT_PACKAGE = (
    OUTPUT_DIRECTORY
    / "content_package.json"
)

OUTPUT_PUBLISHING_PACKAGE = (
    OUTPUT_DIRECTORY
    / "publishing_package.json"
)

OUTPUT_ANALYTICS_PACKAGE = (
    OUTPUT_DIRECTORY
    / "analytics_package.json"
)

PUBLIC_DASHBOARD_MODEL = (
    DASHBOARD_DATA_DIRECTORY
    / "dashboard_model.json"
)

PUBLIC_CONTENT_PACKAGE = (
    DASHBOARD_DATA_DIRECTORY
    / "content_package.json"
)

PUBLIC_PUBLISHING_PACKAGE = (
    DASHBOARD_DATA_DIRECTORY
    / "publishing_package.json"
)

PUBLIC_ANALYTICS_PACKAGE = (
    DASHBOARD_DATA_DIRECTORY
    / "analytics_package.json"
)


REQUIRED_FILES = (
    INDEX_FILE,
    CSS_FILE,
    JAVASCRIPT_FILE,
    OUTPUT_DASHBOARD_MODEL,
    OUTPUT_CONTENT_PACKAGE,
    OUTPUT_PUBLISHING_PACKAGE,
    OUTPUT_ANALYTICS_PACKAGE,
    PUBLIC_DASHBOARD_MODEL,
    PUBLIC_CONTENT_PACKAGE,
    PUBLIC_PUBLISHING_PACKAGE,
    PUBLIC_ANALYTICS_PACKAGE,
)


REQUIRED_HTML_IDS = frozenset(
    {
        "application",
        "loading-screen",
        "generated-at",
        "overview",
        "top-title",
        "top-hook",
        "viral-probability",
        "ranking",
        "ranking-list",
        "script-studio",
        "script-hook",
        "script-introduction",
        "script-development",
        "script-climax",
        "script-ending",
        "script-call-to-action",
        "voice-style",
        "voice-segment-count",
        "storyboard",
        "storyboard-list",
        "assets",
        "assets-list",
        "publishing",
        "publishing-title",
        "publishing-description",
        "publishing-hashtags",
        "publishing-checklist-list",
        "analytics",
        "analytics-views",
        "analytics-likes",
        "analytics-comments",
        "analytics-shares",
        "analytics-watch-time",
        "analytics-retention",
        "analytics-subscribers",
        "growth-signals-list",
        "next-topic-direction",
        "recommended-improvement",
        "recommendation-confidence",
        "dashboard-error",
        "dashboard-error-message",
    }
)


REQUIRED_JAVASCRIPT_DATA_FILES = frozenset(
    {
        "data/dashboard_model.json",
        "data/content_package.json",
        "data/publishing_package.json",
        "data/analytics_package.json",
    }
)


REQUIRED_JAVASCRIPT_FUNCTIONS = frozenset(
    {
        "loadProductionStudioData",
        "renderProductionStudio",
        "renderOverview",
        "renderPipelineStatus",
        "renderScriptStudio",
        "renderStoryboard",
        "renderAssets",
        "renderPublishing",
        "renderAnalytics",
        "startProductionStudio",
    }
)


REQUIRED_CSS_CLASSES = frozenset(
    {
        "hero-card",
        "metric-grid",
        "metric-card",
        "panel",
        "script-studio-grid",
        "script-block",
        "voiceover-summary",
        "storyboard-list",
        "scene-card",
        "asset-grid",
        "asset-card",
        "publishing-grid",
        "publishing-main-card",
        "thumbnail-card",
        "thumbnail-preview",
        "checklist-grid",
        "analytics-metric-grid",
        "analytics-metric-card",
        "analytics-detail-card",
        "growth-signals-list",
        "growth-signal",
        "error-panel",
    }
)


REQUIRED_DASHBOARD_KEYS = frozenset(
    {
        "generated_at",
        "channel",
        "top_title",
        "top_hook",
        "viral_probability",
        "metrics",
        "hooks",
        "storyboard",
        "ranking",
    }
)


REQUIRED_CONTENT_KEYS = frozenset(
    {
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
)


REQUIRED_PUBLISHING_KEYS = frozenset(
    {
        "package_version",
        "generated_at",
        "source_content_id",
        "metadata",
        "thumbnail",
        "checklist",
        "status",
    }
)


REQUIRED_ANALYTICS_KEYS = frozenset(
    {
        "analytics_version",
        "generated_at",
        "content_id",
        "platform",
        "status",
        "metrics",
        "growth_signals",
        "recommendation",
    }
)


def require_file(
    path: Path,
) -> None:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro obrigatório em falta: {path}"
        )

    if path.stat().st_size <= 0:

        raise ValueError(
            f"Ficheiro vazio: {path}"
        )


def load_json(
    path: Path,
) -> dict[str, Any]:

    require_file(
        path
    )

    try:

        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"JSON inválido em {path}: {exc}"
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):

        raise ValueError(
            f"{path} deve conter um objeto JSON."
        )

    return payload


def require_mapping(
    value: Any,
    field_name: str,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):

        raise ValueError(
            f"{field_name} deve ser um objeto JSON."
        )

    return value


def require_list(
    value: Any,
    field_name: str,
) -> list[Any]:

    if not isinstance(
        value,
        list,
    ):

        raise ValueError(
            f"{field_name} deve ser uma lista JSON."
        )

    return value


def require_non_empty_string(
    value: Any,
    field_name: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):

        raise ValueError(
            f"{field_name} deve ser texto."
        )

    normalized = value.strip()

    if not normalized:

        raise ValueError(
            f"{field_name} não pode estar vazio."
        )

    return normalized


def validate_required_keys(
    payload: dict[str, Any],
    required: frozenset[str],
    name: str,
) -> None:

    missing = (
        required
        -
        payload.keys()
    )

    if missing:

        raise ValueError(
            f"{name} incompleto: {sorted(missing)}"
        )


def canonical_json_bytes(
    payload: dict[str, Any],
) -> bytes:

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def payload_sha256(
    payload: dict[str, Any],
) -> str:

    return hashlib.sha256(
        canonical_json_bytes(
            payload
        )
    ).hexdigest()


def validate_public_copy(
    source: dict[str, Any],
    public: dict[str, Any],
    name: str,
) -> None:

    source_hash = payload_sha256(
        source
    )

    public_hash = payload_sha256(
        public
    )

    if source_hash == public_hash:

        print(
            f"{name.upper()}_SHA256={source_hash}"
        )

        print(
            f"{name.upper()}_PUBLIC_COPY=EXACT"
        )

        return

    if name != "dashboard_model":

        raise ValueError(
            f"{name} público não corresponde "
            "ao artefacto produzido."
        )

    required_root_keys = {
        "generated_at",
        "channel",
        "top_title",
        "top_hook",
        "viral_probability",
        "metrics",
        "hooks",
        "storyboard",
        "ranking",
    }

    source_missing = (
        required_root_keys
        -
        source.keys()
    )

    public_missing = (
        required_root_keys
        -
        public.keys()
    )

    if source_missing:

        raise ValueError(
            "dashboard_model produzido incompleto: "
            f"{sorted(source_missing)}"
        )

    if public_missing:

        raise ValueError(
            "dashboard_model público incompleto: "
            f"{sorted(public_missing)}"
        )

    invariant_fields = (
        "generated_at",
        "channel",
        "top_title",
        "top_hook",
        "viral_probability",
        "metrics",
        "hooks",
        "storyboard",
    )

    mismatched_fields = [
        field_name
        for field_name in invariant_fields
        if (
            source.get(field_name)
            != public.get(field_name)
        )
    ]

    if mismatched_fields:

        raise ValueError(
            "dashboard_model público alterou "
            "campos que deveriam permanecer invariantes: "
            f"{mismatched_fields}"
        )

    source_ranking = source.get(
        "ranking"
    )

    public_ranking = public.get(
        "ranking"
    )

    if not isinstance(
        source_ranking,
        list,
    ):

        raise ValueError(
            "dashboard_model produzido possui "
            "ranking inválido."
        )

    if not isinstance(
        public_ranking,
        list,
    ):

        raise ValueError(
            "dashboard_model público possui "
            "ranking inválido."
        )

    if len(source_ranking) != len(public_ranking):

        raise ValueError(
            "dashboard_model público alterou "
            "a quantidade de itens do ranking."
        )

    expected_priorities = list(
        range(
            1,
            len(public_ranking) + 1,
        )
    )

    observed_priorities = []

    for index, (
        source_item,
        public_item,
    ) in enumerate(
        zip(
            source_ranking,
            public_ranking,
            strict=True,
        ),
        start=1,
    ):

        if not isinstance(
            source_item,
            dict,
        ):

            raise ValueError(
                "Ranking produzido contém item "
                f"inválido na posição {index}."
            )

        if not isinstance(
            public_item,
            dict,
        ):

            raise ValueError(
                "Ranking público contém item "
                f"inválido na posição {index}."
            )

        source_without_priority = {
            key: value
            for key, value in source_item.items()
            if key != "priority"
        }

        public_without_priority = {
            key: value
            for key, value in public_item.items()
            if key != "priority"
        }

        if (
            source_without_priority
            != public_without_priority
        ):

            raise ValueError(
                "dashboard_model público alterou "
                "dados editoriais do ranking "
                f"na posição {index}."
            )

        observed_priorities.append(
            public_item.get(
                "priority"
            )
        )

    if observed_priorities != expected_priorities:

        raise ValueError(
            "dashboard_model público não possui "
            "prioridades sequenciais: "
            f"{observed_priorities}"
        )

    print(
        f"{name.upper()}_SOURCE_SHA256="
        f"{source_hash}"
    )

    print(
        f"{name.upper()}_PUBLIC_SHA256="
        f"{public_hash}"
    )

    print(
        f"{name.upper()}_PUBLIC_COPY="
        "CERTIFIED_NORMALIZED"
    )


def validate_dashboard(
    dashboard: dict[str, Any],
) -> None:

    validate_required_keys(
        dashboard,
        REQUIRED_DASHBOARD_KEYS,
        "Dashboard Model",
    )

    require_non_empty_string(
        dashboard.get(
            "top_title"
        ),
        "dashboard.top_title",
    )

    require_non_empty_string(
        dashboard.get(
            "top_hook"
        ),
        "dashboard.top_hook",
    )

    ranking = require_list(
        dashboard.get(
            "ranking"
        ),
        "dashboard.ranking",
    )

    if not ranking:

        raise ValueError(
            "dashboard.ranking não pode estar vazio."
        )


def validate_content(
    content: dict[str, Any],
) -> None:

    validate_required_keys(
        content,
        REQUIRED_CONTENT_KEYS,
        "Content Package",
    )

    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    require_non_empty_string(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    require_non_empty_string(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )

    if source_topic.get(
        "priority"
    ) != 1:

        raise ValueError(
            "content.source_topic.priority deve ser 1."
        )

    script = require_mapping(
        content.get(
            "script"
        ),
        "content.script",
    )

    for field_name in (
        "hook",
        "introduction",
        "development",
        "climax",
        "ending",
        "call_to_action",
    ):

        require_non_empty_string(
            script.get(
                field_name
            ),
            f"content.script.{field_name}",
        )

    voiceover = require_mapping(
        content.get(
            "voiceover"
        ),
        "content.voiceover",
    )

    segments = require_list(
        voiceover.get(
            "segments"
        ),
        "content.voiceover.segments",
    )

    if not segments:

        raise ValueError(
            "content.voiceover.segments "
            "não pode estar vazio."
        )

    scenes = require_list(
        content.get(
            "scenes"
        ),
        "content.scenes",
    )

    if not scenes:

        raise ValueError(
            "content.scenes não pode estar vazio."
        )

    expected_numbers = list(
        range(
            1,
            len(scenes) + 1,
        )
    )

    observed_numbers = []

    for index, value in enumerate(
        scenes,
        start=1,
    ):

        scene = require_mapping(
            value,
            f"content.scenes[{index - 1}]",
        )

        observed_numbers.append(
            scene.get(
                "scene_number"
            )
        )

        duration = scene.get(
            "duration_seconds"
        )

        if (
            not isinstance(
                duration,
                int,
            )
            or isinstance(
                duration,
                bool,
            )
            or duration <= 0
        ):

            raise ValueError(
                f"content.scenes[{index - 1}]"
                ".duration_seconds inválido."
            )

    if observed_numbers != expected_numbers:

        raise ValueError(
            "content.scenes deve ser sequencial."
        )


def validate_publishing(
    publishing: dict[str, Any],
) -> None:

    validate_required_keys(
        publishing,
        REQUIRED_PUBLISHING_KEYS,
        "Publishing Package",
    )

    require_non_empty_string(
        publishing.get(
            "source_content_id"
        ),
        "publishing.source_content_id",
    )

    metadata = require_mapping(
        publishing.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    require_non_empty_string(
        metadata.get(
            "title"
        ),
        "publishing.metadata.title",
    )

    require_non_empty_string(
        metadata.get(
            "description"
        ),
        "publishing.metadata.description",
    )

    hashtags = require_list(
        metadata.get(
            "hashtags"
        ),
        "publishing.metadata.hashtags",
    )

    if not hashtags:

        raise ValueError(
            "publishing.metadata.hashtags "
            "não pode estar vazio."
        )

    require_mapping(
        publishing.get(
            "thumbnail"
        ),
        "publishing.thumbnail",
    )

    require_mapping(
        publishing.get(
            "checklist"
        ),
        "publishing.checklist",
    )

    status = require_non_empty_string(
        publishing.get(
            "status"
        ),
        "publishing.status",
    )

    if status not in {
        "draft",
        "ready",
        "scheduled",
        "published",
    }:

        raise ValueError(
            "publishing.status inválido."
        )


def validate_analytics(
    analytics: dict[str, Any],
) -> None:

    validate_required_keys(
        analytics,
        REQUIRED_ANALYTICS_KEYS,
        "Analytics Package",
    )

    require_non_empty_string(
        analytics.get(
            "content_id"
        ),
        "analytics.content_id",
    )

    require_non_empty_string(
        analytics.get(
            "platform"
        ),
        "analytics.platform",
    )

    metrics = require_mapping(
        analytics.get(
            "metrics"
        ),
        "analytics.metrics",
    )

    required_metrics = {
        "views",
        "likes",
        "comments",
        "shares",
        "average_watch_time_seconds",
        "retention_percent",
        "subscribers_gained",
    }

    missing_metrics = (
        required_metrics
        -
        metrics.keys()
    )

    if missing_metrics:

        raise ValueError(
            "analytics.metrics incompleto: "
            f"{sorted(missing_metrics)}"
        )

    for key in required_metrics:

        value = metrics[key]

        if (
            not isinstance(
                value,
                (int, float),
            )
            or isinstance(
                value,
                bool,
            )
            or value < 0
        ):

            raise ValueError(
                f"analytics.metrics.{key} inválido."
            )

    require_mapping(
        analytics.get(
            "growth_signals"
        ),
        "analytics.growth_signals",
    )

    require_mapping(
        analytics.get(
            "recommendation"
        ),
        "analytics.recommendation",
    )


def validate_cross_package_identity(
    dashboard: dict[str, Any],
    content: dict[str, Any],
    publishing: dict[str, Any],
    analytics: dict[str, Any],
) -> None:

    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )

    content_title = require_non_empty_string(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )

    dashboard_title = require_non_empty_string(
        dashboard.get(
            "top_title"
        ),
        "dashboard.top_title",
    )

    metadata = require_mapping(
        publishing.get(
            "metadata"
        ),
        "publishing.metadata",
    )

    publishing_title = require_non_empty_string(
        metadata.get(
            "title"
        ),
        "publishing.metadata.title",
    )

    if content_title != publishing_title:

        raise ValueError(
            "Content e Publishing usam "
            "títulos diferentes."
        )

    if dashboard_title != content_title:

        raise ValueError(
            "Dashboard e Content Package usam "
            "títulos diferentes."
        )

    publishing_id = require_non_empty_string(
        publishing.get(
            "source_content_id"
        ),
        "publishing.source_content_id",
    )

    analytics_id = require_non_empty_string(
        analytics.get(
            "content_id"
        ),
        "analytics.content_id",
    )

    if publishing_id != analytics_id:

        raise ValueError(
            "Publishing e Analytics usam "
            "content IDs diferentes."
        )


def extract_html_ids(
    source: str,
) -> set[str]:

    return set(
        re.findall(
            r'\bid=["\']([^"\']+)["\']',
            source,
        )
    )


def validate_html() -> None:

    source = INDEX_FILE.read_text(
        encoding="utf-8"
    )

    observed_ids = extract_html_ids(
        source
    )

    missing_ids = (
        REQUIRED_HTML_IDS
        -
        observed_ids
    )

    if missing_ids:

        raise ValueError(
            "Production Studio HTML incompleto. "
            f"IDs em falta: {sorted(missing_ids)}"
        )

    if (
        'href="assets/dashboard.css"'
        not in source
    ):

        raise ValueError(
            "index.html não referencia "
            "assets/dashboard.css."
        )

    if (
        'src="assets/dashboard.js"'
        not in source
    ):

        raise ValueError(
            "index.html não referencia "
            "assets/dashboard.js."
        )

    if re.search(
        r"\bundefined\b",
        source,
        flags=re.IGNORECASE,
    ):

        raise ValueError(
            "index.html contém o texto undefined."
        )

    print(
        f"HTML_ID_COUNT={len(observed_ids)}"
    )

    print(
        "HTML_CONTRACT=PASS"
    )


def validate_javascript() -> None:

    source = JAVASCRIPT_FILE.read_text(
        encoding="utf-8"
    )

    missing_data_files = {
        value
        for value
        in REQUIRED_JAVASCRIPT_DATA_FILES
        if value not in source
    }

    if missing_data_files:

        raise ValueError(
            "dashboard.js não carrega todos "
            "os ficheiros necessários: "
            f"{sorted(missing_data_files)}"
        )

    missing_functions = {
        function_name
        for function_name
        in REQUIRED_JAVASCRIPT_FUNCTIONS
        if not re.search(
            rf"\bfunction\s+{re.escape(function_name)}\s*\(",
            source,
        )
    }

    if missing_functions:

        raise ValueError(
            "dashboard.js não contém todas "
            "as funções necessárias: "
            f"{sorted(missing_functions)}"
        )

    if "Promise.all" not in source:

        raise ValueError(
            "dashboard.js não usa carregamento "
            "paralelo com Promise.all."
        )

    if "cache: \"no-store\"" not in source:

        raise ValueError(
            "dashboard.js não desativa cache "
            "durante o carregamento."
        )

    if "DOMContentLoaded" not in source:

        raise ValueError(
            "dashboard.js não inicializa "
            "no evento DOMContentLoaded."
        )

    print(
        "JAVASCRIPT_MULTI_PACKAGE_LOADER=PASS"
    )


def validate_css() -> None:

    source = CSS_FILE.read_text(
        encoding="utf-8"
    )

    missing_classes = {
        class_name
        for class_name
        in REQUIRED_CSS_CLASSES
        if not re.search(
            rf"\.{re.escape(class_name)}(?:\s|,|\{{|:)",
            source,
        )
    }

    if missing_classes:

        raise ValueError(
            "dashboard.css não contém todas "
            "as classes necessárias: "
            f"{sorted(missing_classes)}"
        )

    responsive_breakpoints = (
        "@media (max-width: 1250px)",
        "@media (max-width: 1050px)",
        "@media (max-width: 760px)",
        "@media (max-width: 520px)",
    )

    missing_breakpoints = {
        breakpoint
        for breakpoint
        in responsive_breakpoints
        if breakpoint not in source
    }

    if missing_breakpoints:

        raise ValueError(
            "dashboard.css não contém todos "
            "os breakpoints responsivos: "
            f"{sorted(missing_breakpoints)}"
        )

    print(
        "CSS_PRODUCTION_STUDIO=PASS"
    )


def main() -> int:

    print("=" * 70)

    print(
        "FOOTBALL-SHORTS-AI-0030C.4"
    )

    print(
        "PRODUCTION STUDIO "
        "INTEGRATION CERTIFICATION"
    )

    print(
        "READ-ONLY CERTIFICATION"
    )

    print(
        "NO EXTERNAL API"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print("=" * 70)

    for path in REQUIRED_FILES:

        require_file(
            path
        )

        print(
            f"FILE_PRESENT={path.relative_to(ROOT)}"
        )

    dashboard = load_json(
        OUTPUT_DASHBOARD_MODEL
    )

    content = load_json(
        OUTPUT_CONTENT_PACKAGE
    )

    publishing = load_json(
        OUTPUT_PUBLISHING_PACKAGE
    )

    analytics = load_json(
        OUTPUT_ANALYTICS_PACKAGE
    )

    public_dashboard = load_json(
        PUBLIC_DASHBOARD_MODEL
    )

    public_content = load_json(
        PUBLIC_CONTENT_PACKAGE
    )

    public_publishing = load_json(
        PUBLIC_PUBLISHING_PACKAGE
    )

    public_analytics = load_json(
        PUBLIC_ANALYTICS_PACKAGE
    )

    validate_dashboard(
        dashboard
    )

    validate_content(
        content
    )

    validate_publishing(
        publishing
    )

    validate_analytics(
        analytics
    )

    print(
        "PACKAGE_CONTRACTS=PASS"
    )

    validate_cross_package_identity(
        dashboard,
        content,
        publishing,
        analytics,
    )

    print(
        "CROSS_PACKAGE_IDENTITY=PASS"
    )

    validate_public_copy(
        dashboard,
        public_dashboard,
        "dashboard_model",
    )

    validate_public_copy(
        content,
        public_content,
        "content_package",
    )

    validate_public_copy(
        publishing,
        public_publishing,
        "publishing_package",
    )

    validate_public_copy(
        analytics,
        public_analytics,
        "analytics_package",
    )

    print(
        "PUBLIC_DATA_SYNCHRONIZATION=PASS"
    )

    validate_html()

    validate_javascript()

    validate_css()

    print("=" * 70)

    print(
        "PRODUCTION_STUDIO_INTEGRATION=PASS"
    )

    print(
        "CERTIFICATION_STATUS=CERTIFIED"
    )

    print(
        f"TOP_TITLE={dashboard['top_title']}"
    )

    print(
        f"SCENE_COUNT={len(content['scenes'])}"
    )

    print(
        f"PUBLISHING_STATUS={publishing['status']}"
    )

    print(
        f"ANALYTICS_STATUS={analytics['status']}"
    )

    print("=" * 70)

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
