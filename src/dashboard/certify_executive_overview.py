from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess

from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

DASHBOARD_DIRECTORY = ROOT / "dashboard"

DASHBOARD_DATA_DIRECTORY = (
    DASHBOARD_DIRECTORY
    / "data"
)

DASHBOARD_ASSETS_DIRECTORY = (
    DASHBOARD_DIRECTORY
    / "assets"
)


INDEX_FILE = (
    DASHBOARD_DIRECTORY
    / "index.html"
)

JAVASCRIPT_FILE = (
    DASHBOARD_ASSETS_DIRECTORY
    / "dashboard.js"
)

CSS_FILE = (
    DASHBOARD_ASSETS_DIRECTORY
    / "dashboard.css"
)


DASHBOARD_MODEL_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "dashboard_model.json"
)

CONTENT_PACKAGE_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "content_package.json"
)

PUBLISHING_PACKAGE_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "publishing_package.json"
)

ANALYTICS_PACKAGE_FILE = (
    DASHBOARD_DATA_DIRECTORY
    / "analytics_package.json"
)


REQUIRED_FILES = (
    INDEX_FILE,
    JAVASCRIPT_FILE,
    CSS_FILE,
    DASHBOARD_MODEL_FILE,
    CONTENT_PACKAGE_FILE,
    PUBLISHING_PACKAGE_FILE,
    ANALYTICS_PACKAGE_FILE,
)


REQUIRED_OVERVIEW_HTML_IDS = frozenset(
    {
        "application",
        "loading-screen",
        "overview",
        "generated-at",
        "channel-name",
        "winner-priority",
        "top-title",
        "top-hook",
        "content-platform",
        "content-language",
        "content-duration",
        "overview-production-status",
        "overview-generated-at",
        "viral-probability",
        "viral-progress",
        "dashboard-error",
        "dashboard-error-message",
    }
)


REQUIRED_OVERVIEW_JAVASCRIPT_BINDINGS = frozenset(
    {
        "generated-at",
        "channel-name",
        "winner-priority",
        "top-title",
        "top-hook",
        "content-platform",
        "content-language",
        "content-duration",
        "overview-production-status",
        "overview-generated-at",
        "viral-probability",
        "viral-progress",
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
        "fetchJson",
        "loadProductionStudioData",
        "renderHeader",
        "renderOverview",
        "renderPipelineStatus",
        "renderPerformanceSummary",
        "renderProductionStudio",
        "showApplication",
        "showError",
        "startProductionStudio",
    }
)


FORBIDDEN_JAVASCRIPT_PATTERNS = {
    "WEBSOCKET": r"\bWebSocket\s*\(",
    "LOCAL_STORAGE": r"\blocalStorage\b",
    "SESSION_STORAGE": r"\bsessionStorage\b",
    "INDEXED_DB": r"\bindexedDB\b",
    "DOCUMENT_COOKIE": r"\bdocument\.cookie\b",
}


ALLOWED_EXTERNAL_JAVASCRIPT_ORIGINS = frozenset(
    {
        "https://www.tiktok.com",
    }
)


ALLOWED_EXTERNAL_JAVASCRIPT_PREFIXES = (
    "https://www.tiktok.com/player/v1/",
)


REQUIRED_TIKTOK_PLAYER_MARKERS = frozenset(
    {
        "FOOTBALL-SHORTS-AI-0031C.5G",
        "renderTikTokViralReferenceReview",
        "activateTikTokReferenceButton",
        "handleTikTokReviewPlayerMessage",
        "https://www.tiktok.com/player/v1/",
    }
)


ALLOWED_PRODUCTION_STATUSES = {
    "draft",
    "ready",
    "scheduled",
    "published",
}


class CertificationError(
    RuntimeError
):
    """Executive Overview certification failure."""


class DashboardHtmlParser(
    HTMLParser
):

    def __init__(
        self,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.ids: list[str] = []

        self.stylesheets: list[str] = []

        self.scripts: list[str] = []

        self.html_languages: list[str] = []


    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:

        attributes = dict(
            attrs
        )

        element_id = attributes.get(
            "id"
        )

        if element_id:

            self.ids.append(
                element_id
            )


        if tag == "html":

            language = attributes.get(
                "lang"
            )

            if language:

                self.html_languages.append(
                    language
                )


        if (
            tag == "link"
            and attributes.get(
                "rel"
            )
            == "stylesheet"
        ):

            href = attributes.get(
                "href"
            )

            if href:

                self.stylesheets.append(
                    href
                )


        if tag == "script":

            source = attributes.get(
                "src"
            )

            if source:

                self.scripts.append(
                    source
                )


def require(
    condition: bool,
    message: str,
) -> None:

    if not condition:

        raise CertificationError(
            message
        )


def require_file(
    path: Path,
) -> None:

    require(
        path.is_file(),
        (
            "Ficheiro obrigatório em falta: "
            f"{path.relative_to(ROOT)}"
        ),
    )

    require(
        path.stat().st_size > 0,
        (
            "Ficheiro obrigatório vazio: "
            f"{path.relative_to(ROOT)}"
        ),
    )


def read_text(
    path: Path,
) -> str:

    require_file(
        path
    )

    return path.read_text(
        encoding="utf-8"
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

        raise CertificationError(
            "JSON inválido em "
            f"{path.relative_to(ROOT)}: "
            f"{exc}"
        ) from exc


    require(
        isinstance(
            payload,
            dict,
        ),
        (
            f"{path.relative_to(ROOT)} "
            "deve conter um objeto JSON."
        ),
    )

    return payload


def require_mapping(
    value: Any,
    field_name: str,
) -> dict[str, Any]:

    require(
        isinstance(
            value,
            dict,
        ),
        (
            f"{field_name} deve ser "
            "um objeto JSON."
        ),
    )

    return value


def require_list(
    value: Any,
    field_name: str,
) -> list[Any]:

    require(
        isinstance(
            value,
            list,
        ),
        (
            f"{field_name} deve ser "
            "uma lista JSON."
        ),
    )

    return value


def require_text(
    value: Any,
    field_name: str,
) -> str:

    require(
        isinstance(
            value,
            str,
        ),
        f"{field_name} deve ser texto.",
    )

    normalized = value.strip()

    require(
        bool(
            normalized
        ),
        (
            f"{field_name} não pode "
            "estar vazio."
        ),
    )

    return normalized


def require_number(
    value: Any,
    field_name: str,
) -> float:

    require(
        isinstance(
            value,
            (
                int,
                float,
            ),
        )
        and not isinstance(
            value,
            bool,
        ),
        (
            f"{field_name} deve ser "
            "numérico."
        ),
    )

    return float(
        value
    )


def first_non_empty_text(
    *values: Any,
) -> str | None:

    for value in values:

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):

            return value.strip()


    return None


def sha256_file(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def build_manifest(
    paths: tuple[
        Path,
        ...,
    ],
) -> tuple[
    tuple[
        str,
        str,
    ],
    ...,
]:

    return tuple(
        sorted(
            (
                str(
                    path.relative_to(
                        ROOT
                    )
                ),
                sha256_file(
                    path
                ),
            )
            for path in paths
        )
    )


def validate_html(
    *,
    source: str,
) -> tuple[
    int,
    int,
]:

    parser = DashboardHtmlParser()

    parser.feed(
        source
    )

    observed_ids = set(
        parser.ids
    )


    duplicate_ids = sorted(
        element_id
        for element_id
        in observed_ids
        if parser.ids.count(
            element_id
        )
        > 1
    )


    require(
        not duplicate_ids,
        (
            "dashboard/index.html contém "
            "IDs duplicados: "
            f"{duplicate_ids}"
        ),
    )


    missing_ids = sorted(
        REQUIRED_OVERVIEW_HTML_IDS
        -
        observed_ids
    )


    require(
        not missing_ids,
        (
            "Executive Overview HTML "
            "incompleto. IDs em falta: "
            f"{missing_ids}"
        ),
    )


    require(
        "pt-PT"
        in parser.html_languages,
        (
            "dashboard/index.html deve "
            'declarar lang="pt-PT".'
        ),
    )


    require(
        "assets/dashboard.css"
        in parser.stylesheets,
        (
            "dashboard/index.html não "
            "referencia assets/dashboard.css."
        ),
    )


    require(
        "assets/dashboard.js"
        in parser.scripts,
        (
            "dashboard/index.html não "
            "referencia assets/dashboard.js."
        ),
    )


    overview_section = re.search(
        (
            r"<section\b"
            r"[^>]*"
            r"\bid=[\"']overview[\"']"
        ),
        source,
    )


    require(
        overview_section
        is not None,
        (
            "O Executive Overview deve "
            "permanecer num elemento "
            "section#overview."
        ),
    )


    require(
        re.search(
            r"\bundefined\b",
            source,
            flags=re.IGNORECASE,
        )
        is None,
        (
            "dashboard/index.html contém "
            "o texto undefined."
        ),
    )


    print(
        f"HTML_ID_COUNT="
        f"{len(observed_ids)}"
    )

    print(
        "EXECUTIVE_OVERVIEW_"
        "HTML_BINDING_COUNT="
        f"{len(REQUIRED_OVERVIEW_HTML_IDS)}"
    )

    print(
        "EXECUTIVE_OVERVIEW_"
        "HTML_CONTRACT=PASS"
    )


    return (
        len(
            observed_ids
        ),
        len(
            REQUIRED_OVERVIEW_HTML_IDS
        ),
    )


def validate_javascript(
    *,
    source: str,
) -> tuple[
    int,
    int,
]:

    node = shutil.which(
        "node"
    )


    require(
        node
        is not None,
        (
            "Node.js não encontrado "
            "para validar dashboard.js."
        ),
    )


    result = subprocess.run(
        [
            node,
            "--check",
            str(
                JAVASCRIPT_FILE
            ),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


    require(
        result.returncode
        == 0,
        (
            "dashboard.js falhou "
            "node --check: "
            f"{result.stderr.strip() or result.stdout.strip()}"
        ),
    )


    missing_data_files = sorted(
        value
        for value
        in REQUIRED_JAVASCRIPT_DATA_FILES
        if value
        not in source
    )


    require(
        not missing_data_files,
        (
            "dashboard.js não carrega "
            "todos os pacotes locais: "
            f"{missing_data_files}"
        ),
    )


    missing_functions = sorted(
        function_name
        for function_name
        in REQUIRED_JAVASCRIPT_FUNCTIONS
        if re.search(
            (
                rf"\bfunction\s+"
                rf"{re.escape(function_name)}"
                rf"\s*\("
            ),
            source,
        )
        is None
    )


    require(
        not missing_functions,
        (
            "dashboard.js não contém "
            "todas as funções obrigatórias: "
            f"{missing_functions}"
        ),
    )


    missing_bindings = sorted(
        element_id
        for element_id
        in REQUIRED_OVERVIEW_JAVASCRIPT_BINDINGS
        if re.search(
            (
                rf"[\"']"
                rf"{re.escape(element_id)}"
                rf"[\"']"
            ),
            source,
        )
        is None
    )


    require(
        not missing_bindings,
        (
            "dashboard.js não faz binding "
            "de todos os elementos do "
            "Executive Overview: "
            f"{missing_bindings}"
        ),
    )


    required_markers = {
        "PROMISE_ALL": (
            "Promise.all"
        ),

        "NO_STORE_CACHE": (
            'cache: "no-store"'
        ),

        "DOM_CONTENT_LOADED": (
            "DOMContentLoaded"
        ),

        "SCORE_RING": (
            ".score-ring"
        ),

        "SCORE_ANGLE": (
            "--score-angle"
        ),
    }


    missing_markers = sorted(
        name
        for name, marker
        in required_markers.items()
        if marker
        not in source
    )


    require(
        not missing_markers,
        (
            "dashboard.js perdeu "
            "marcadores obrigatórios: "
            f"{missing_markers}"
        ),
    )


    render_production_studio = re.search(
        (
            r"function\s+"
            r"renderProductionStudio\s*"
            r"\([^)]*\)"
            r"\s*\{"
            r"(?P<body>.*?)"
            r"\n\}"
        ),
        source,
        flags=re.DOTALL,
    )


    require(
        render_production_studio
        is not None,
        (
            "Não foi possível localizar "
            "renderProductionStudio."
        ),
    )


    render_body = (
        render_production_studio
        .group(
            "body"
        )
    )


    require(
        re.search(
            r"\brenderOverview\s*\(",
            render_body,
        )
        is not None,
        (
            "renderProductionStudio não "
            "invoca renderOverview."
        ),
    )


    external_urls = sorted(
        set(
            re.findall(
                r"https?://[^\\s\"'`<>)}]+",
                source,
                flags=re.IGNORECASE,
            )
        )
    )


    unauthorized_external_urls = sorted(
        url
        for url in external_urls
        if (
            url
            not in
            ALLOWED_EXTERNAL_JAVASCRIPT_ORIGINS
            and
            not any(
                url.startswith(
                    prefix
                )
                for prefix
                in ALLOWED_EXTERNAL_JAVASCRIPT_PREFIXES
            )
        )
    )


    require(
        not unauthorized_external_urls,
        (
            "dashboard.js contém URLs "
            "externos não autorizados: "
            f"{unauthorized_external_urls}"
        ),
    )


    tiktok_player_present = any(
        url.startswith(
            "https://www.tiktok.com/player/v1/"
        )
        for url in external_urls
    )


    if tiktok_player_present:

        missing_tiktok_markers = sorted(
            marker
            for marker
            in REQUIRED_TIKTOK_PLAYER_MARKERS
            if marker
            not in source
        )


        require(
            not missing_tiktok_markers,
            (
                "O player oficial TikTok perdeu "
                "marcadores governados: "
                f"{missing_tiktok_markers}"
            ),
        )


        require(
            "fullscreen; autoplay;"
            not in source,
            (
                "O iframe oficial TikTok não pode "
                "receber permissão de autoplay."
            ),
        )


        require(
            re.search(
                (
                    r"iframe\.allow\s*=\s*"
                    r"\([^)]*"
                    r"fullscreen;"
                ),
                source,
                flags=re.DOTALL,
            )
            is not None,
            (
                "Não foi possível confirmar "
                "a política de permissões "
                "do iframe TikTok."
            ),
        )


        require(
            "iframe.loading = \"lazy\""
            in source,
            (
                "O player TikTok deve "
                "permanecer lazy-loaded."
            ),
        )


        require(
            re.search(
                (
                    r"function\s+"
                    r"activateTikTokReferenceButton"
                    r"\s*\("
                ),
                source,
            )
            is not None,
            (
                "O player TikTok deve ser "
                "ativado por ação explícita."
            ),
        )


        print(
            "TIKTOK_IFRAME_AUTOPLAY_PERMISSION=BLOCKED"
        )


        print(
            "TIKTOK_PLAYER_LAZY_LOAD=PASS"
        )


    forbidden_matches = sorted(
        name
        for name, pattern
        in FORBIDDEN_JAVASCRIPT_PATTERNS.items()
        if re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        )
        is not None
    )


    require(
        not forbidden_matches,
        (
            "dashboard.js contém capacidades "
            "persistentes ou canais externos "
            "proibidos: "
            f"{forbidden_matches}"
        ),
    )


    print(
        "EXTERNAL_URL_COUNT="
        f"{len(external_urls)}"
    )


    print(
        "UNAUTHORIZED_EXTERNAL_URL_COUNT="
        f"{len(unauthorized_external_urls)}"
    )


    print(
        "OFFICIAL_TIKTOK_PLAYER_ALLOWED="
        f"{'YES' if tiktok_player_present else 'NOT_PRESENT'}"
    )


    print(
        "NODE_JAVASCRIPT_SYNTAX=PASS"
    )

    print(
        "JAVASCRIPT_LOCAL_DATA_"
        "FILE_COUNT="
        f"{len(REQUIRED_JAVASCRIPT_DATA_FILES)}"
    )

    print(
        "EXECUTIVE_OVERVIEW_"
        "JAVASCRIPT_BINDING_COUNT="
        f"{len(REQUIRED_OVERVIEW_JAVASCRIPT_BINDINGS)}"
    )

    print(
        "EXECUTIVE_OVERVIEW_"
        "JAVASCRIPT_CONTRACT=PASS"
    )


    return (
        len(
            REQUIRED_JAVASCRIPT_FUNCTIONS
        ),
        len(
            REQUIRED_OVERVIEW_JAVASCRIPT_BINDINGS
        ),
    )


def validate_overview_data(
    *,
    dashboard: dict[str, Any],
    content: dict[str, Any],
    publishing: dict[str, Any],
    analytics: dict[str, Any],
) -> dict[str, Any]:

    dashboard_title = require_text(
        dashboard.get(
            "top_title"
        ),
        "dashboard.top_title",
    )


    dashboard_hook = require_text(
        dashboard.get(
            "top_hook"
        ),
        "dashboard.top_hook",
    )


    dashboard_channel = require_text(
        dashboard.get(
            "channel"
        ),
        "dashboard.channel",
    )


    dashboard_generated_at = require_text(
        dashboard.get(
            "generated_at"
        ),
        "dashboard.generated_at",
    )


    dashboard_viral_probability = (
        require_number(
            dashboard.get(
                "viral_probability"
            ),
            "dashboard.viral_probability",
        )
    )


    require(
        (
            0
            <= dashboard_viral_probability
            <= 100
        ),
        (
            "dashboard.viral_probability "
            "deve estar entre 0 e 100."
        ),
    )


    source_topic = require_mapping(
        content.get(
            "source_topic"
        ),
        "content.source_topic",
    )


    content_title = require_text(
        source_topic.get(
            "title"
        ),
        "content.source_topic.title",
    )


    content_hook = require_text(
        source_topic.get(
            "hook"
        ),
        "content.source_topic.hook",
    )


    require(
        source_topic.get(
            "priority"
        )
        == 1,
        (
            "content.source_topic.priority "
            "deve ser 1."
        ),
    )


    source_viral_probability = (
        require_number(
            source_topic.get(
                "viral_probability"
            ),
            (
                "content.source_topic."
                "viral_probability"
            ),
        )
    )


    require(
        (
            0
            <= source_viral_probability
            <= 100
        ),
        (
            "content.source_topic."
            "viral_probability deve "
            "estar entre 0 e 100."
        ),
    )


    require(
        dashboard_title
        == content_title,
        (
            "Dashboard e Content Package "
            "usam títulos diferentes."
        ),
    )


    require(
        dashboard_hook
        == content_hook,
        (
            "Dashboard e Content Package "
            "usam hooks diferentes."
        ),
    )


    require(
        dashboard_viral_probability
        == source_viral_probability,
        (
            "Dashboard e Content Package "
            "usam probabilidades virais "
            "diferentes."
        ),
    )


    voiceover = require_mapping(
        content.get(
            "voiceover"
        ),
        "content.voiceover",
    )


    language = require_text(
        voiceover.get(
            "language"
        ),
        "content.voiceover.language",
    )


    scenes = require_list(
        content.get(
            "scenes"
        ),
        "content.scenes",
    )


    require(
        bool(
            scenes
        ),
        (
            "content.scenes não pode "
            "estar vazio."
        ),
    )


    total_duration = 0


    for index, value in enumerate(
        scenes,
        start=1,
    ):

        scene = require_mapping(
            value,
            (
                "content.scenes"
                f"[{index - 1}]"
            ),
        )


        duration = scene.get(
            "duration_seconds"
        )


        require(
            isinstance(
                duration,
                int,
            )
            and not isinstance(
                duration,
                bool,
            )
            and duration > 0,
            (
                "content.scenes"
                f"[{index - 1}]"
                ".duration_seconds inválido."
            ),
        )


        total_duration += duration


    publishing_metadata = require_mapping(
        publishing.get(
            "metadata"
        ),
        "publishing.metadata",
    )


    content_publishing = require_mapping(
        content.get(
            "publishing"
        ),
        "content.publishing",
    )


    platform = first_non_empty_text(
        publishing_metadata.get(
            "platform"
        ),
        content_publishing.get(
            "platform"
        ),
        analytics.get(
            "platform"
        ),
    )


    require(
        platform
        is not None,
        (
            "Não foi possível resolver "
            "a plataforma do "
            "Executive Overview."
        ),
    )


    production_status = require_text(
        publishing.get(
            "status"
        ),
        "publishing.status",
    )


    require(
        production_status
        in ALLOWED_PRODUCTION_STATUSES,
        (
            "publishing.status inválido: "
            f"{production_status}"
        ),
    )


    analytics_status = require_text(
        analytics.get(
            "status"
        ),
        "analytics.status",
    )


    result = {
        "title": dashboard_title,
        "hook": dashboard_hook,
        "channel": dashboard_channel,
        "generated_at": (
            dashboard_generated_at
        ),
        "priority": 1,
        "viral_probability": (
            dashboard_viral_probability
        ),
        "platform": platform,
        "language": language,
        "production_status": (
            production_status
        ),
        "analytics_status": (
            analytics_status
        ),
        "scene_count": len(
            scenes
        ),
        "total_duration_seconds": (
            total_duration
        ),
    }


    print(
        "EXECUTIVE_OVERVIEW_"
        "DATA_CONTRACT=PASS"
    )

    print(
        f"OVERVIEW_TITLE="
        f"{result['title']}"
    )

    print(
        f"OVERVIEW_PRIORITY="
        f"{result['priority']}"
    )

    print(
        "OVERVIEW_VIRAL_PROBABILITY="
        f"{result['viral_probability']}"
    )

    print(
        f"OVERVIEW_PLATFORM="
        f"{result['platform']}"
    )

    print(
        f"OVERVIEW_LANGUAGE="
        f"{result['language']}"
    )

    print(
        "OVERVIEW_PRODUCTION_STATUS="
        f"{result['production_status']}"
    )

    print(
        "OVERVIEW_ANALYTICS_STATUS="
        f"{result['analytics_status']}"
    )

    print(
        f"OVERVIEW_SCENE_COUNT="
        f"{result['scene_count']}"
    )

    print(
        "OVERVIEW_TOTAL_DURATION_SECONDS="
        f"{result['total_duration_seconds']}"
    )


    return result


def validate_read_only(
    *,
    before_manifest: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ],
) -> str:

    after_manifest = build_manifest(
        REQUIRED_FILES
    )


    require(
        before_manifest
        == after_manifest,
        (
            "A certificação modificou "
            "ficheiros do projeto."
        ),
    )


    canonical_payload = "\n".join(
        (
            f"{path}\t{digest}"
        )
        for path, digest
        in after_manifest
    ).encode(
        "utf-8"
    )


    manifest_sha256 = hashlib.sha256(
        canonical_payload
    ).hexdigest()


    print(
        "READ_ONLY_INVARIANCE=PASS"
    )

    print(
        f"CERTIFIED_FILE_COUNT="
        f"{len(after_manifest)}"
    )

    print(
        "CERTIFIED_MANIFEST_SHA256="
        f"{manifest_sha256}"
    )


    for path, digest in after_manifest:

        print(
            f"CERTIFIED_FILE={path}"
        )

        print(
            f"CERTIFIED_FILE_SHA256={digest}"
        )


    return manifest_sha256


def main() -> int:

    print(
        "=" * 70
    )

    print(
        "FOOTBALL-SHORTS-AI-0031B.2"
    )

    print(
        "EXECUTIVE OVERVIEW "
        "POST-IMPLEMENTATION CERTIFICATION"
    )

    print(
        "READ-ONLY HTML/JAVASCRIPT/"
        "DATA CONTRACT CERTIFICATION"
    )

    print(
        "NO PROJECT PATCH"
    )

    print(
        "NO EXTERNAL API"
    )

    print(
        "OFFICIAL TIKTOK PLAYER "
        "ALLOWLISTED FOR INTERNAL REVIEW ONLY"
    )

    print(
        "NO PUBLICATION EXECUTION"
    )

    print(
        "NO DATABASE"
    )

    print(
        "NO PERSISTENT BROWSER STORAGE"
    )

    print(
        "=" * 70
    )


    for path in REQUIRED_FILES:

        require_file(
            path
        )

        print(
            "FILE_PRESENT="
            f"{path.relative_to(ROOT)}"
        )


    before_manifest = build_manifest(
        REQUIRED_FILES
    )


    html_source = read_text(
        INDEX_FILE
    )

    javascript_source = read_text(
        JAVASCRIPT_FILE
    )


    dashboard = load_json(
        DASHBOARD_MODEL_FILE
    )

    content = load_json(
        CONTENT_PACKAGE_FILE
    )

    publishing = load_json(
        PUBLISHING_PACKAGE_FILE
    )

    analytics = load_json(
        ANALYTICS_PACKAGE_FILE
    )


    (
        html_id_count,
        html_binding_count,
    ) = validate_html(
        source=html_source
    )


    (
        javascript_function_count,
        javascript_binding_count,
    ) = validate_javascript(
        source=javascript_source
    )


    overview = validate_overview_data(
        dashboard=dashboard,
        content=content,
        publishing=publishing,
        analytics=analytics,
    )


    manifest_sha256 = validate_read_only(
        before_manifest=before_manifest
    )


    print(
        "=" * 70
    )

    print(
        "EXECUTIVE_OVERVIEW_IMPLEMENTATION=PASS"
    )

    print(
        "CERTIFICATION_STATUS=CERTIFIED"
    )

    print(
        "READ_ONLY=YES"
    )

    print(
        f"HTML_ID_COUNT="
        f"{html_id_count}"
    )

    print(
        f"HTML_BINDING_COUNT="
        f"{html_binding_count}"
    )

    print(
        "JAVASCRIPT_FUNCTION_COUNT="
        f"{javascript_function_count}"
    )

    print(
        "JAVASCRIPT_BINDING_COUNT="
        f"{javascript_binding_count}"
    )

    print(
        f"SCENE_COUNT="
        f"{overview['scene_count']}"
    )

    print(
        "TOTAL_DURATION_SECONDS="
        f"{overview['total_duration_seconds']}"
    )

    print(
        "CANONICAL_MANIFEST_SHA256="
        f"{manifest_sha256}"
    )

    print(
        "NEXT_PHASE_AUTHORIZED=YES"
    )

    print(
        "=" * 70
    )


    return 0


if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except CertificationError as exc:

        print(
            "=" * 70
        )

        print(
            "CERTIFICATION_STATUS=FAILED"
        )

        print(
            f"CERTIFICATION_ERROR={exc}"
        )

        print(
            "NEXT_PHASE_AUTHORIZED=NO"
        )

        print(
            "=" * 70
        )

        raise SystemExit(
            1
        ) from exc
