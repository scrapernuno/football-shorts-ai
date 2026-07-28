from __future__ import annotations

import hashlib
import json
import os
import re
import sys

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import openai

from openai_client import (
    OpenAIClientError,
    OpenAIClientSettings,
    OpenAIConfigurationError,
    OpenAIResponseError,
    create_client,
)
from trends.build_trend_discovery_request import (
    build_and_write_discovery_request,
    canonical_sha256,
    load_json,
    require_mapping,
    require_text,
    write_json_atomically,
)


ROOT = Path(__file__).resolve().parents[2]
CONTENT_PATH = ROOT / "output" / "content_package.json"
MANUAL_INTAKE_PATH = ROOT / "config" / "tiktok_trend_intake.json"
DISCOVERY_RESULTS_PATH = (
    ROOT / "output" / "tiktok_trend_discovery_results.json"
)
RUNTIME_INTAKE_PATH = (
    ROOT / "output" / "tiktok_trend_runtime_intake.json"
)

DISCOVERY_RESULTS_VERSION = "1.0"
RUNTIME_INTAKE_VERSION = "1.0"
MAX_VIDEO_REFERENCES = 5
MAX_SOUND_REFERENCES = 3
MAX_HASHTAGS = 8

ALLOWED_HOST_SUFFIXES = (
    "tiktok.com",
)
VIDEO_PATH_PATTERN = re.compile(
    r"^/@(?P<username>[^/]+)/video/(?P<video_id>[0-9]+)(?:/)?$",
    flags=re.IGNORECASE,
)

DISCOVERY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "video_references",
        "sound_references",
        "hashtags",
        "search_summary",
    ],
    "properties": {
        "video_references": {
            "type": "array",
            "maxItems": MAX_VIDEO_REFERENCES,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_url",
                    "caption",
                    "relevance_reason",
                ],
                "properties": {
                    "source_url": {
                        "type": "string",
                        "minLength": 20,
                        "maxLength": 2_000,
                    },
                    "caption": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                    },
                    "relevance_reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                    },
                },
            },
        },
        "sound_references": {
            "type": "array",
            "maxItems": MAX_SOUND_REFERENCES,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_url",
                    "sound_name",
                    "relevance_reason",
                ],
                "properties": {
                    "source_url": {
                        "type": "string",
                        "minLength": 15,
                        "maxLength": 2_000,
                    },
                    "sound_name": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "relevance_reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                    },
                },
            },
        },
        "hashtags": {
            "type": "array",
            "maxItems": MAX_HASHTAGS,
            "items": {
                "type": "string",
                "minLength": 2,
                "maxLength": 80,
            },
        },
        "search_summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1_000,
        },
    },
}

SYSTEM_PROMPT = """
És um motor de descoberta governada para Football Shorts AI.
Usa pesquisa web para encontrar referências públicas e atuais relacionadas
com a notícia vencedora. Só podes devolver URLs oficiais do TikTok ou do
TikTok Creative Center. Não inventes URLs, métricas, permissões, licenças,
disponibilidade de Duet/Stitch, direitos de reutilização ou disponibilidade
territorial. Um vídeo descoberto é apenas uma referência editorial. Um som
descoberto é apenas uma referência até existir confirmação separada na
Commercial Music Library para a região indicada. Não seleciones qualquer
candidato. Não proponhas download, remoção de watermark ou publicação.
""".strip()


class TrendDiscoveryError(RuntimeError):
    """Falha controlada na descoberta governada."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _host_allowed(host: str) -> bool:
    normalized = host.lower().rstrip(".")
    return any(
        normalized == suffix
        or normalized.endswith(f".{suffix}")
        for suffix in ALLOWED_HOST_SUFFIXES
    )


def _normalize_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()

    if parts.scheme != "https" or not _host_allowed(host):
        return None

    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit(("https", parts.netloc.lower(), path, parts.query, ""))


def _url_identity(value: str) -> str:
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    path = re.sub(r"/{2,}", "/", parts.path or "/").rstrip("/")
    return f"https://{host}{path}".casefold()


def _collect_cited_urls(response: object) -> set[str]:
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    elif isinstance(response, dict):
        payload = response
    else:
        return set()

    output: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            annotation_type = value.get("type")
            url = value.get("url")
            if annotation_type == "url_citation" and isinstance(url, str):
                normalized = _normalize_url(url)
                if normalized is not None:
                    output.add(normalized)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return output


def _parse_response_json(response: object) -> dict[str, Any]:
    output_text = getattr(response, "output_text", "")
    if not isinstance(output_text, str) or not output_text.strip():
        raise OpenAIResponseError(
            "A pesquisa web não devolveu conteúdo estruturado."
        )

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise OpenAIResponseError(
            "A pesquisa web não devolveu JSON válido."
        ) from exc

    return require_mapping(payload, "web_search_response")


def _make_candidate_id(prefix: str, source_url: str) -> str:
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


def _build_user_prompt(request: dict[str, Any]) -> str:
    binding = require_mapping(
        request.get("topic_binding"),
        "request.topic_binding",
    )
    queries = request.get("search_queries")
    if not isinstance(queries, list):
        queries = []

    return json.dumps(
        {
            "task": "discover_current_tiktok_references",
            "region": request.get("region", "PT"),
            "content_title": binding.get("content_title"),
            "content_hook": binding.get("content_hook"),
            "search_queries": queries,
            "limits": {
                "video_references": MAX_VIDEO_REFERENCES,
                "sound_references": MAX_SOUND_REFERENCES,
                "hashtags": MAX_HASHTAGS,
            },
            "rules": {
                "official_tiktok_urls_only": True,
                "rights_assumptions_allowed": False,
                "metrics_assumptions_allowed": False,
                "automatic_selection_allowed": False,
                "third_party_download_allowed": False,
                "watermark_removal_allowed": False,
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _perform_web_search(
    request: dict[str, Any],
) -> tuple[dict[str, Any], set[str], str, str]:
    fixture_path = os.environ.get(
        "TREND_DISCOVERY_OFFLINE_FIXTURE",
        "",
    ).strip()

    if fixture_path:
        fixture = load_json(Path(fixture_path))
        payload = require_mapping(
            fixture.get("payload"),
            "fixture.payload",
        )
        cited_urls = {
            normalized
            for raw_url in fixture.get("cited_urls", [])
            if (normalized := _normalize_url(raw_url)) is not None
        }
        return (
            payload,
            cited_urls,
            "offline-fixture",
            "offline-fixture",
        )

    base_settings = OpenAIClientSettings.from_environment()
    model = (
        os.environ.get("TREND_DISCOVERY_MODEL", "").strip()
        or base_settings.model
    )
    settings = replace(
        base_settings,
        model=model,
        max_output_tokens=min(base_settings.max_output_tokens, 6_000),
    )
    client = create_client(settings)

    response = client.responses.create(
        model=settings.model,
        instructions=SYSTEM_PROMPT,
        input=_build_user_prompt(request),
        tools=[
            {
                "type": "web_search",
                "filters": {
                    "allowed_domains": [
                        "tiktok.com",
                        "ads.tiktok.com",
                    ],
                },
                "search_context_size": "high",
                "user_location": {
                    "type": "approximate",
                    "country": "PT",
                    "timezone": "Europe/Lisbon",
                },
            }
        ],
        reasoning={"effort": "low"},
        max_output_tokens=settings.max_output_tokens,
        text={
            "format": {
                "type": "json_schema",
                "name": "football_shorts_tiktok_discovery",
                "description": (
                    "Referências públicas TikTok ligadas à notícia vencedora."
                ),
                "strict": True,
                "schema": DISCOVERY_JSON_SCHEMA,
            }
        },
    )

    status = getattr(response, "status", None)
    if status == "incomplete":
        raise OpenAIResponseError(
            "A pesquisa web ficou incompleta."
        )
    if status == "failed":
        raise OpenAIResponseError(
            f"A pesquisa web falhou: {getattr(response, 'error', None)}"
        )

    payload = _parse_response_json(response)
    cited_urls = _collect_cited_urls(response)
    request_id = str(getattr(response, "_request_id", "indisponível"))
    return payload, cited_urls, request_id, settings.model


def _video_candidates(
    raw_items: object,
    cited_urls: set[str],
    observed_at: str,
) -> list[dict[str, Any]]:
    items = raw_items if isinstance(raw_items, list) else []
    cited_identities = {_url_identity(url) for url in cited_urls}
    candidates: list[dict[str, Any]] = []
    observed: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            continue
        source_url = _normalize_url(raw.get("source_url"))
        if source_url is None:
            continue
        identity = _url_identity(source_url)
        if identity not in cited_identities or identity in observed:
            continue

        path = urlsplit(source_url).path.rstrip("/")
        match = VIDEO_PATH_PATTERN.fullmatch(path)
        if match is None:
            continue

        caption = str(raw.get("caption", "")).strip()
        if not caption:
            caption = "Referência pública TikTok relacionada com a notícia."

        candidates.append(
            {
                "candidate_id": _make_candidate_id("web_video", source_url),
                "source_url": source_url,
                "creator_username": f"@{match.group('username')}",
                "caption": caption[:500],
                "observed_at": observed_at,
                "trend_status": "discovered_reference",
                "metrics": {},
                "intended_usage_mode": "reference_only",
                "reuse_availability": {
                    "duet_enabled": False,
                    "stitch_enabled": False,
                    "embed_allowed": False,
                },
                "creator_license_status": "none",
                "creator_license_reference": None,
                "original_file_received": False,
                "original_file_reference": None,
                "music_review_status": "pending",
                "cross_platform_requested": False,
            }
        )
        observed.add(identity)

        if len(candidates) >= MAX_VIDEO_REFERENCES:
            break

    return candidates


def _sound_candidates(
    raw_items: object,
    cited_urls: set[str],
    region: str,
) -> list[dict[str, Any]]:
    items = raw_items if isinstance(raw_items, list) else []
    cited_identities = {_url_identity(url) for url in cited_urls}
    candidates: list[dict[str, Any]] = []
    observed: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            continue
        source_url = _normalize_url(raw.get("source_url"))
        if source_url is None:
            continue
        identity = _url_identity(source_url)
        if identity not in cited_identities or identity in observed:
            continue

        path = urlsplit(source_url).path.casefold()
        host = (urlsplit(source_url).hostname or "").casefold()
        is_sound_reference = (
            "/music/" in path
            or (
                host.endswith("ads.tiktok.com")
                and "/creativecenter/music/" in path
            )
        )
        if not is_sound_reference:
            continue

        sound_name = str(raw.get("sound_name", "")).strip()
        if not sound_name:
            sound_name = "TikTok sound reference"

        candidates.append(
            {
                "sound_id": _make_candidate_id("web_sound", source_url),
                "sound_name": sound_name[:200],
                "source_url": source_url,
                "trend_status": "discovered_reference",
                "rights_classification": "reference_only",
                "region": region,
                "commercial_library_confirmed": False,
                "external_license_reference": None,
                "allowed_platforms": [],
            }
        )
        observed.add(identity)

        if len(candidates) >= MAX_SOUND_REFERENCES:
            break

    return candidates


def _hashtags(raw_items: object) -> list[str]:
    items = raw_items if isinstance(raw_items, list) else []
    output: list[str] = []
    observed: set[str] = set()

    for value in items:
        if not isinstance(value, str):
            continue
        normalized = value.strip().replace(" ", "")
        if not normalized:
            continue
        if not normalized.startswith("#"):
            normalized = f"#{normalized}"
        identity = normalized.casefold()
        if identity in observed:
            continue
        if not re.fullmatch(r"#[\wÀ-ÖØ-öø-ÿ.]{1,79}", normalized):
            continue
        output.append(normalized)
        observed.add(identity)
        if len(output) >= MAX_HASHTAGS:
            break

    return output


def _manual_overlay(
    manual_intake: dict[str, Any],
    current_title: str,
    current_identity: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, str | None, bool]:
    binding = manual_intake.get("topic_binding")
    if not isinstance(binding, dict):
        binding = {}

    title = binding.get("content_title")
    identity = binding.get("content_identity_sha256")
    video_candidates = manual_intake.get("video_candidates")
    sound_candidates = manual_intake.get("sound_candidates")

    videos = video_candidates if isinstance(video_candidates, list) else []
    sounds = sound_candidates if isinstance(sound_candidates, list) else []
    selected_video = manual_intake.get("selected_video_candidate_id")
    selected_sound = manual_intake.get("selected_sound_candidate_id")

    has_material = bool(videos or sounds or selected_video or selected_sound)
    current = title == current_title and identity == current_identity

    if has_material and not current:
        return [], [], None, None, True

    return (
        [item for item in videos if isinstance(item, dict)],
        [item for item in sounds if isinstance(item, dict)],
        selected_video if isinstance(selected_video, str) else None,
        selected_sound if isinstance(selected_sound, str) else None,
        False,
    )


def _merge_candidates(
    manual: list[dict[str, Any]],
    discovered: list[dict[str, Any]],
    identifier: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    observed: set[str] = set()

    for item in [*manual, *discovered]:
        value = item.get(identifier)
        if not isinstance(value, str) or not value.strip():
            continue
        if value in observed:
            continue
        output.append(item)
        observed.add(value)

    return output


def _build_runtime_intake(
    manual_intake: dict[str, Any],
    request: dict[str, Any],
    discovered_videos: list[dict[str, Any]],
    discovered_sounds: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    binding = require_mapping(
        request.get("topic_binding"),
        "request.topic_binding",
    )
    title = require_text(binding.get("content_title"), "content_title")
    identity = require_text(
        binding.get("content_identity_sha256"),
        "content_identity_sha256",
    )

    (
        manual_videos,
        manual_sounds,
        selected_video,
        selected_sound,
        stale_ignored,
    ) = _manual_overlay(manual_intake, title, identity)

    policy = manual_intake.get("policy")
    if not isinstance(policy, dict):
        policy = {}

    payload = {
        "intake_version": RUNTIME_INTAKE_VERSION,
        "source_mode": (
            "automatic_governed_web_discovery_with_manual_evidence_overlay"
        ),
        "region": request.get("region", "PT"),
        "topic_binding": {
            "content_title": title,
            "content_identity_sha256": identity,
        },
        "selected_video_candidate_id": selected_video,
        "selected_sound_candidate_id": selected_sound,
        "video_candidates": _merge_candidates(
            manual_videos,
            discovered_videos,
            "candidate_id",
        ),
        "sound_candidates": _merge_candidates(
            manual_sounds,
            discovered_sounds,
            "sound_id",
        ),
        "policy": policy,
    }
    return payload, stale_ignored


def discover_and_write() -> dict[str, Any]:
    content = load_json(CONTENT_PATH)
    manual_intake = load_json(MANUAL_INTAKE_PATH)
    request = build_and_write_discovery_request(content, manual_intake)
    observed_at = _now()

    raw_result, cited_urls, request_id, model = _perform_web_search(request)

    region = require_text(request.get("region"), "request.region").upper()
    videos = _video_candidates(
        raw_result.get("video_references"),
        cited_urls,
        observed_at,
    )
    sounds = _sound_candidates(
        raw_result.get("sound_references"),
        cited_urls,
        region,
    )
    hashtags = _hashtags(raw_result.get("hashtags"))

    runtime_intake, stale_ignored = _build_runtime_intake(
        manual_intake,
        request,
        videos,
        sounds,
    )
    write_json_atomically(RUNTIME_INTAKE_PATH, runtime_intake)

    binding = require_mapping(
        request.get("topic_binding"),
        "request.topic_binding",
    )
    result = {
        "discovery_results_version": DISCOVERY_RESULTS_VERSION,
        "generated_at": observed_at,
        "provider": {
            "provider_id": "openai_web_search",
            "model": model,
            "request_id": request_id,
        },
        "topic_binding": {
            "content_title": binding.get("content_title"),
            "content_identity_sha256": binding.get(
                "content_identity_sha256"
            ),
        },
        "execution": {
            "status": (
                "completed"
                if videos or sounds or hashtags
                else "completed_no_verified_references"
            ),
            "server_side_network_execution_enabled": True,
            "browser_api_calls_enabled": False,
            "direct_tiktok_api_calls_enabled": False,
            "automatic_candidate_selection_enabled": False,
        },
        "evidence": {
            "cited_urls": sorted(cited_urls),
            "citation_count": len(cited_urls),
        },
        "video_candidates": videos,
        "sound_candidates": sounds,
        "hashtags": hashtags,
        "search_summary": str(raw_result.get("search_summary", "")).strip(),
        "manual_intake": {
            "stale_material_ignored": stale_ignored,
            "runtime_intake_path": str(
                RUNTIME_INTAKE_PATH.relative_to(ROOT)
            ),
        },
        "governance": {
            "all_discovered_videos_reference_only": True,
            "all_discovered_sounds_reference_only": True,
            "rights_evidence_required": True,
            "third_party_download_allowed": False,
            "watermark_removal_allowed": False,
            "publication_execution_enabled": False,
        },
        "result_identity_sha256": "",
    }
    result["result_identity_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in result.items()
            if key != "result_identity_sha256"
        }
    )
    write_json_atomically(DISCOVERY_RESULTS_PATH, result)
    return result


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.4D")
    print("GOVERNED SERVER-SIDE TIKTOK TREND DISCOVERY")
    print("OPENAI WEB SEARCH - OFFICIAL TIKTOK DOMAINS")
    print("NO AUTOMATIC SELECTION - NO DOWNLOAD - NO PUBLICATION")
    print("=" * 70)

    try:
        result = discover_and_write()
    except OpenAIConfigurationError as exc:
        print(f"TREND_DISCOVERY_CONFIGURATION_ERROR={exc}", file=sys.stderr)
        return 2
    except (
        OpenAIResponseError,
        OpenAIClientError,
        openai.OpenAIError,
        TrendDiscoveryError,
    ) as exc:
        print(f"TREND_DISCOVERY_ERROR={exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"TREND_DISCOVERY_UNEXPECTED_ERROR={exc}", file=sys.stderr)
        return 1

    print("TREND_DISCOVERY_EXECUTION=PASS")
    print("PROVIDER=OPENAI_WEB_SEARCH")
    print(
        "VIDEO_REFERENCE_COUNT="
        f"{len(result['video_candidates'])}"
    )
    print(
        "SOUND_REFERENCE_COUNT="
        f"{len(result['sound_candidates'])}"
    )
    print(f"HASHTAG_COUNT={len(result['hashtags'])}")
    print("AUTOMATIC_SELECTION_ENABLED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
