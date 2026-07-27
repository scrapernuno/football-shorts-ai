from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

CERTIFICATION_SCRIPT = (
    ROOT
    / "src"
    / "dashboard"
    / "certify_production_studio.py"
)

OUTPUT_DIRECTORY = ROOT / "output"

DASHBOARD_DIRECTORY = ROOT / "dashboard"

DASHBOARD_DATA_DIRECTORY = (
    DASHBOARD_DIRECTORY
    / "data"
)

DASHBOARD_ASSETS_DIRECTORY = (
    DASHBOARD_DIRECTORY
    / "assets"
)

GOVERNANCE_JSON = (
    OUTPUT_DIRECTORY
    / "production_studio_governance_closure.json"
)

GOVERNANCE_DOCUMENT = (
    ROOT
    / "docs"
    / (
        "FOOTBALL-SHORTS-AI-0030C-"
        "PRODUCTION-STUDIO-INTERFACE-"
        "GOVERNANCE-CLOSURE.md"
    )
)


CANONICAL_FILES = (
    CERTIFICATION_SCRIPT,

    ROOT
    / "src"
    / "dashboard"
    / "sync_production_studio.py",

    DASHBOARD_DIRECTORY
    / "index.html",

    DASHBOARD_ASSETS_DIRECTORY
    / "dashboard.css",

    DASHBOARD_ASSETS_DIRECTORY
    / "dashboard.js",

    DASHBOARD_DATA_DIRECTORY
    / "dashboard_model.json",

    DASHBOARD_DATA_DIRECTORY
    / "content_package.json",

    DASHBOARD_DATA_DIRECTORY
    / "publishing_package.json",

    DASHBOARD_DATA_DIRECTORY
    / "analytics_package.json",

    OUTPUT_DIRECTORY
    / "dashboard_model.json",

    OUTPUT_DIRECTORY
    / "content_package.json",

    OUTPUT_DIRECTORY
    / "publishing_package.json",

    OUTPUT_DIRECTORY
    / "analytics_package.json",
)


REQUIRED_CERTIFICATION_MARKERS = (
    "PACKAGE_CONTRACTS=PASS",
    "CROSS_PACKAGE_IDENTITY=PASS",
    "PUBLIC_DATA_SYNCHRONIZATION=PASS",
    "HTML_CONTRACT=PASS",
    "JAVASCRIPT_MULTI_PACKAGE_LOADER=PASS",
    "CSS_PRODUCTION_STUDIO=PASS",
    "PRODUCTION_STUDIO_INTEGRATION=PASS",
    "CERTIFICATION_STATUS=CERTIFIED",
)


REQUIRED_PUBLIC_PACKAGES = {
    "dashboard_model": {
        "path":
            DASHBOARD_DATA_DIRECTORY
            / "dashboard_model.json",

        "required_keys": {
            "generated_at",
            "channel",
            "top_title",
            "top_hook",
            "viral_probability",
            "metrics",
            "hooks",
            "storyboard",
            "ranking",
        },
    },

    "content_package": {
        "path":
            DASHBOARD_DATA_DIRECTORY
            / "content_package.json",

        "required_keys": {
            "package_version",
            "generated_at",
            "source_topic",
            "script",
            "voiceover",
            "scenes",
            "captions",
            "assets",
            "publishing",
        },
    },

    "publishing_package": {
        "path":
            DASHBOARD_DATA_DIRECTORY
            / "publishing_package.json",

        "required_keys": {
            "package_version",
            "generated_at",
            "source_content_id",
            "metadata",
            "thumbnail",
            "checklist",
            "status",
        },
    },

    "analytics_package": {
        "path":
            DASHBOARD_DATA_DIRECTORY
            / "analytics_package.json",

        "required_keys": {
            "analytics_version",
            "generated_at",
            "content_id",
            "platform",
            "status",
            "metrics",
            "growth_signals",
            "recommendation",
        },
    },
}


def require_file(
    path: Path,
) -> None:

    if not path.is_file():

        raise FileNotFoundError(
            f"Ficheiro obrigatório em falta: {path}"
        )

    if path.stat().st_size <= 0:

        raise ValueError(
            f"Ficheiro obrigatório vazio: {path}"
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


def sha256_file(
    path: Path,
) -> str:

    require_file(
        path
    )

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:

                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def canonical_json_sha256(
    payload: dict[str, Any],
) -> str:

    encoded = json.dumps(
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

    return hashlib.sha256(
        encoded
    ).hexdigest()


def write_text_atomically(
    path: Path,
    content: str,
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
        content,
        encoding="utf-8",
    )

    temporary_path.replace(
        path
    )


def write_json_atomically(
    path: Path,
    payload: dict[str, Any],
) -> None:

    content = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        +
        "\n"
    )

    write_text_atomically(
        path,
        content,
    )


def execute_certification() -> str:

    require_file(
        CERTIFICATION_SCRIPT
    )

    environment = os.environ.copy()

    existing_pythonpath = environment.get(
        "PYTHONPATH",
        "",
    )

    source_path = str(
        ROOT / "src"
    )

    environment["PYTHONPATH"] = (
        source_path
        if not existing_pythonpath
        else (
            source_path
            +
            os.pathsep
            +
            existing_pythonpath
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(
                CERTIFICATION_SCRIPT
            ),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    output = (
        result.stdout
        +
        result.stderr
    )

    print(
        output,
        end="",
    )

    if result.returncode != 0:

        raise RuntimeError(
            "A certificação 0030C.4 falhou. "
            f"Return code: {result.returncode}"
        )

    missing_markers = [
        marker
        for marker
        in REQUIRED_CERTIFICATION_MARKERS
        if marker not in output
    ]

    if missing_markers:

        raise ValueError(
            "A certificação não apresentou todos "
            "os marcadores obrigatórios: "
            f"{missing_markers}"
        )

    return output


def validate_public_packages(
) -> dict[str, dict[str, Any]]:

    packages: dict[
        str,
        dict[str, Any],
    ] = {}

    for (
        package_name,
        contract,
    ) in REQUIRED_PUBLIC_PACKAGES.items():

        path = contract[
            "path"
        ]

        required_keys = contract[
            "required_keys"
        ]

        payload = load_json(
            path
        )

        missing = (
            required_keys
            -
            payload.keys()
        )

        if missing:

            raise ValueError(
                f"{package_name} incompleto: "
                f"{sorted(missing)}"
            )

        packages[
            package_name
        ] = payload

        print(
            f"PUBLIC_PACKAGE={package_name}"
        )

        print(
            f"PUBLIC_PACKAGE_SHA256="
            f"{canonical_json_sha256(payload)}"
        )

    return packages


def validate_cross_package_closure(
    packages: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    dashboard = packages[
        "dashboard_model"
    ]

    content = packages[
        "content_package"
    ]

    publishing = packages[
        "publishing_package"
    ]

    analytics = packages[
        "analytics_package"
    ]

    source_topic = content.get(
        "source_topic"
    )

    if not isinstance(
        source_topic,
        dict,
    ):

        raise ValueError(
            "content_package.source_topic inválido."
        )

    metadata = publishing.get(
        "metadata"
    )

    if not isinstance(
        metadata,
        dict,
    ):

        raise ValueError(
            "publishing_package.metadata inválido."
        )

    dashboard_title = dashboard.get(
        "top_title"
    )

    content_title = source_topic.get(
        "title"
    )

    publishing_title = metadata.get(
        "title"
    )

    if not all(
        isinstance(
            title,
            str,
        )
        and title.strip()
        for title
        in (
            dashboard_title,
            content_title,
            publishing_title,
        )
    ):

        raise ValueError(
            "Os títulos canónicos são inválidos."
        )

    if not (
        dashboard_title
        ==
        content_title
        ==
        publishing_title
    ):

        raise ValueError(
            "Dashboard, Content e Publishing "
            "não partilham o mesmo título."
        )

    publishing_content_id = publishing.get(
        "source_content_id"
    )

    analytics_content_id = analytics.get(
        "content_id"
    )

    if (
        not isinstance(
            publishing_content_id,
            str,
        )
        or not publishing_content_id.strip()
    ):

        raise ValueError(
            "publishing.source_content_id inválido."
        )

    if (
        publishing_content_id
        != analytics_content_id
    ):

        raise ValueError(
            "Publishing e Analytics não partilham "
            "o mesmo content ID."
        )

    scenes = content.get(
        "scenes"
    )

    if (
        not isinstance(
            scenes,
            list,
        )
        or not scenes
    ):

        raise ValueError(
            "Content Package sem cenas."
        )

    publishing_status = publishing.get(
        "status"
    )

    analytics_status = analytics.get(
        "status"
    )

    print(
        "CLOSURE_CROSS_PACKAGE_IDENTITY=PASS"
    )

    return {
        "top_title":
            dashboard_title,

        "viral_probability":
            dashboard.get(
                "viral_probability"
            ),

        "scene_count":
            len(
                scenes
            ),

        "publishing_status":
            publishing_status,

        "analytics_status":
            analytics_status,

        "content_id":
            publishing_content_id,
    }


def build_file_manifest(
) -> list[dict[str, Any]]:

    manifest = []

    for path in CANONICAL_FILES:

        require_file(
            path
        )

        relative_path = str(
            path.relative_to(
                ROOT
            )
        )

        entry = {
            "path":
                relative_path,

            "size_bytes":
                path.stat().st_size,

            "sha256":
                sha256_file(
                    path
                ),
        }

        manifest.append(
            entry
        )

        print(
            f"MANIFEST_FILE={relative_path}"
        )

        print(
            f"MANIFEST_SHA256={entry['sha256']}"
        )

    return manifest


def manifest_sha256(
    manifest: list[dict[str, Any]],
) -> str:

    encoded = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def build_governance_payload(
    *,
    closed_at: str,
    manifest: list[dict[str, Any]],
    package_summary: dict[str, Any],
) -> dict[str, Any]:

    return {
        "closure_id":
            "FOOTBALL-SHORTS-AI-0030C",

        "closure_name":
            (
                "Production Studio Interface "
                "Governance Closure"
            ),

        "closure_version":
            "1.0",

        "closed_at":
            closed_at,

        "status":
            "CLOSED",

        "certification_status":
            "CERTIFIED",

        "certification_authority":
            (
                "FOOTBALL-SHORTS-AI-0030C.4"
            ),

        "scope": {
            "interface":
                "dashboard/index.html",

            "stylesheet":
                (
                    "dashboard/assets/"
                    "dashboard.css"
                ),

            "javascript":
                (
                    "dashboard/assets/"
                    "dashboard.js"
                ),

            "public_data": [
                (
                    "dashboard/data/"
                    "dashboard_model.json"
                ),
                (
                    "dashboard/data/"
                    "content_package.json"
                ),
                (
                    "dashboard/data/"
                    "publishing_package.json"
                ),
                (
                    "dashboard/data/"
                    "analytics_package.json"
                ),
            ],
        },

        "governance_constraints": {
            "read_only_interface":
                True,

            "no_external_api":
                True,

            "no_browser_openai_call":
                True,

            "no_publication_execution":
                True,

            "no_database":
                True,

            "no_persistent_editing":
                True,

            "provider_neutral":
                True,
        },

        "certified_capabilities": [
            "multi_package_loading",
            "overview_rendering",
            "editorial_ranking",
            "script_studio",
            "storyboard_timeline",
            "asset_planner",
            "publishing_readiness",
            "analytics_preview",
            "responsive_layout",
            "github_pages_delivery",
        ],

        "package_summary":
            package_summary,

        "canonical_file_count":
            len(
                manifest
            ),

        "canonical_manifest_sha256":
            manifest_sha256(
                manifest
            ),

        "canonical_files":
            manifest,

        "decision": {
            "production_studio_interface":
                "ACCEPTED",

            "integration":
                "CERTIFIED",

            "governance":
                "CLOSED",

            "next_phase_authorized":
                True,

            "unauthorized_runtime_activation":
                False,
        },
    }


def build_governance_document(
    payload: dict[str, Any],
) -> str:

    summary = payload[
        "package_summary"
    ]

    manifest_hash = payload[
        "canonical_manifest_sha256"
    ]

    return f"""# FOOTBALL-SHORTS-AI-0030C

# Production Studio Interface Governance Closure

## Status

**CLOSED**

## Certification status

**CERTIFIED**

## Closure date

`{payload["closed_at"]}`

---

## Scope

This governance closure formally closes the implementation,
integration and certification of the Football Shorts AI
Production Studio interface.

The closed scope includes:

- `dashboard/index.html`
- `dashboard/assets/dashboard.css`
- `dashboard/assets/dashboard.js`
- `dashboard/data/dashboard_model.json`
- `dashboard/data/content_package.json`
- `dashboard/data/publishing_package.json`
- `dashboard/data/analytics_package.json`
- `src/dashboard/sync_production_studio.py`
- `src/dashboard/certify_production_studio.py`

---

## Certified architecture

```text
Dashboard Model
Content Package
Publishing Package
Analytics Package
        |
        v
Production Studio Multi-Package Loader
        |
        v
Overview
Ranking
Script Studio
Storyboard Timeline
Asset Planner
Publishing Readiness
Analytics Preview
        |
        v
GitHub Pages
