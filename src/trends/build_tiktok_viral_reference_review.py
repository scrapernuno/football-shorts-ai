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


ROOT = Path(__file__).resolve().parents[2]

CONTENT_PATH = ROOT / "output" / "content_package.json"
DISCOVERY_REQUEST_PATH = ROOT / "output" / "trend_discovery_request.json"
DISCOVERY_RESULTS_PATH = ROOT / "output" / "tiktok_trend_discovery_results.json"
TREND_INTELLIGENCE_PATH = ROOT / "output" / "tiktok_trend_intelligence.json"
OUTPUT_PATH = ROOT / "output" / "tiktok_viral_reference_review.json"

REVIEW_VERSION = "1.0"
MAX_SEARCH_REFERENCES = 8
MAX_SELECTED_REFERENCES = 3
REFERENCE_WINDOW_SECONDS = 3
MIN_RELEVANCE_SCORE = 65
MIN_TREND_CONFIDENCE = 60
MIN_VIRAL_CONFIDENCE = 60
MIN_TOTAL_SCORE = 70

TIKTOK_VIDEO_PATTERN = re.compile(
    r"^/@(?P<username>[^/]+)/video/(?P<video_id>[0-9]+)(?:/)?$",
    flags=re.IGNORECASE,
)

OFFICIAL_HOST_SUFFIXES = (
    "tiktok.com",
)

STOPWORDS = {
    "a", "ao", "aos", "as", "com", "da", "das", "de", "do", "dos",
    "e", "em", "na", "nas", "no", "nos", "o", "os", "para", "por",
    "que", "um", "uma", "the", "and", "for", "from", "in", "of",
    "on", "to", "with",
}

REVIEW_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "references",
        "search_summary",
    ],
    "properties": {
        "references": {
            "type": "array",
            "maxItems": MAX_SEARCH_REFERENCES,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_url",
                    "creator_username",
                    "caption",
                    "relevance_reason",
                    "trend_signal_status",
                    "trend_evidence",
                    "viral_signal_status",
                    "viral_evidence",
                    "published_at",
                    "metrics",
                    "engagement_peak_start_seconds",
                    "relevance_score",
                    "trend_confidence_score",
                    "viral_confidence_score",
                    "evidence_urls",
                ],
                "properties": {
                    "source_url": {
                        "type": "string",
                        "minLength": 30,
                        "maxLength": 2_000,
                    },
                    "creator_username": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 120,
                    },
                    "caption": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                    },
                    "relevance_reason": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 600,
                    },
                    "trend_signal_status": {
                        "type": "string",
                        "enum": ["verified", "insufficient"],
                    },
                    "trend_evidence": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 700,
                    },
                    "viral_signal_status": {
                        "type": "string",
                        "enum": ["verified", "insufficient"],
                    },
                    "viral_evidence": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 700,
                    },
                    "published_at": {
                        "type": ["string", "null"],
                    },
                    "metrics": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "view_count",
                            "like_count",
                            "comment_count",
                            "share_count",
                        ],
                        "properties": {
                            "view_count": {
                                "type": ["integer", "null"],
                                "minimum": 0,
                            },
                            "like_count": {
                                "type": ["integer", "null"],
                                "minimum": 0,
                            },
                            "comment_count": {
                                "type": ["integer", "null"],
                                "minimum": 0,
                            },
                            "share_count": {
                                "type": ["integer", "null"],
                                "minimum": 0,
                            },
                        },
                    },
                    "engagement_peak_start_seconds": {
                        "type": ["integer", "null"],
                        "minimum": 0,
                        "maximum": 3_600,
                    },
                    "relevance_score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "trend_confidence_score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "viral_confidence_score": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "evidence_urls": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "string",
                            "minLength": 20,
                            "maxLength": 2_000,
                        },
                    },
                },
            },
        },
        "search_summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": 1_200,
        },
    },
}

SYSTEM_PROMPT = """
És o motor governado de TikTok Viral Reference Review do Football Shorts AI.

Objetivo:
Encontrar referências de vídeos TikTok atuais, diretamente relacionadas com a
notícia vencedora, que tenham sinais explícitos de tendência e viralidade.

Regras obrigatórias:
- Só devolver URLs oficiais e diretos de posts TikTok no formato
  https://www.tiktok.com/@creator/video/ID.
- Usar apenas evidência pública oficial do TikTok ou TikTok Creative Center.
- Um candidato só pode ter trend_signal_status=verified quando a evidência
  oficial demonstrar atualidade/tendência de forma explícita.
- Um candidato só pode ter viral_signal_status=verified quando existirem
  métricas oficiais visíveis, classificação oficial de alto desempenho, ou
  outra evidência pública oficial inequívoca de forte tração.
- Não inventar métricas, datas, engagement peaks, permissões ou direitos.
- Quando um valor não estiver visível, usar null.
- Quando a evidência for insuficiente, usar status=insufficient e explicar.
- relevance_score, trend_confidence_score e viral_confidence_score são
  avaliações editoriais de 0 a 100, não métricas do TikTok.
- Não sugerir download, scraping, remoção de watermark ou publicação.
- Todos os vídeos são apenas referências para revisão interna.
- Dar prioridade aos vídeos mais recentes, mais diretamente relacionados com o
  tema e com maior evidência oficial de tração.
""".strip()


class ViralReferenceReviewError(RuntimeError):
    """Falha controlada na construção do review viral."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido em {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")

    return payload


def write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def require_mapping(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} deve ser um objeto.")
    return value


def require_list(value: object, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} deve ser uma lista.")
    return value


def require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} deve ser texto.")

    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        raise ValueError(f"{field_name} não pode estar vazio.")
    return normalized


def clamp_score(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, numeric))


def optional_nonnegative_integer(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    return numeric if numeric >= 0 else None


def host_allowed(hostname: str) -> bool:
    normalized = hostname.lower().rstrip(".")
    return any(
        normalized == suffix or normalized.endswith(f".{suffix}")
        for suffix in OFFICIAL_HOST_SUFFIXES
    )


def normalize_official_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()

    if parts.scheme != "https" or not host_allowed(host):
        return None

    path = re.sub(r"/{2,}", "/", parts.path or "/")
    return urlunsplit(("https", parts.netloc.lower(), path, parts.query, ""))


def url_identity(value: str) -> str:
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    path = re.sub(r"/{2,}", "/", parts.path or "/").rstrip("/")
    return f"https://{host}{path}".casefold()


def parse_video_url(value: object) -> tuple[str, str, str] | None:
    normalized = normalize_official_url(value)
    if normalized is None:
        return None

    parts = urlsplit(normalized)
    if (parts.hostname or "").lower() not in {"www.tiktok.com", "tiktok.com"}:
        return None

    match = TIKTOK_VIDEO_PATTERN.fullmatch(parts.path.rstrip("/"))
    if match is None:
        return None

    username = match.group("username")
    video_id = match.group("video_id")
    canonical = f"https://www.tiktok.com/@{username}/video/{video_id}"
    return canonical, username, video_id


def collect_cited_urls(response: object) -> set[str]:
    if hasattr(response, "model_dump"):
        payload = response.model_dump()
    elif isinstance(response, dict):
        payload = response
    else:
        return set()

    output: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if (
                value.get("type") == "url_citation"
                and isinstance(value.get("url"), str)
            ):
                normalized = normalize_official_url(value.get("url"))
                if normalized is not None:
                    output.add(normalized)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return output


def parse_response_json(response: object) -> dict[str, Any]:
    output_text = getattr(response, "output_text", "")
    if not isinstance(output_text, str) or not output_text.strip():
        raise OpenAIResponseError(
            "A pesquisa viral não devolveu conteúdo estruturado."
        )

    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise OpenAIResponseError(
            "A pesquisa viral não devolveu JSON válido."
        ) from exc

    return require_mapping(payload, "viral_review_response")


def content_tokens(*values: str) -> list[str]:
    output: list[str] = []
    observed: set[str] = set()

    for value in values:
        for token in re.findall(r"[^\W_]+", value, flags=re.UNICODE):
            normalized = token.casefold()
            if (
                len(normalized) < 3
                or normalized in STOPWORDS
                or normalized in observed
            ):
                continue
            output.append(token)
            observed.add(normalized)

    return output[:10]


def seed_candidates(
    discovery_results: dict[str, Any],
    intelligence: dict[str, Any],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    observed: set[str] = set()

    for source in (
        discovery_results.get("video_candidates"),
        intelligence.get("video_candidates"),
    ):
        if not isinstance(source, list):
            continue

        for raw in source:
            if not isinstance(raw, dict):
                continue

            parsed = parse_video_url(raw.get("source_url"))
            if parsed is None:
                continue

            canonical, username, _ = parsed
            identity = url_identity(canonical)
            if identity in observed:
                continue

            output.append(
                {
                    "source_url": canonical,
                    "creator_username": (
                        str(raw.get("creator_username", f"@{username}")).strip()
                        or f"@{username}"
                    ),
                    "caption": str(raw.get("caption", "")).strip()[:500],
                }
            )
            observed.add(identity)

    return output[:MAX_SEARCH_REFERENCES]


def build_user_prompt(
    content: dict[str, Any],
    discovery_request: dict[str, Any],
    discovery_results: dict[str, Any],
    intelligence: dict[str, Any],
) -> str:
    source_topic = require_mapping(
        content.get("source_topic"),
        "content.source_topic",
    )
    title = require_text(
        source_topic.get("title"),
        "content.source_topic.title",
    )
    hook = require_text(
        source_topic.get("hook"),
        "content.source_topic.hook",
    )

    existing_queries = discovery_request.get("search_queries")
    if not isinstance(existing_queries, list):
        existing_queries = []

    keywords = content_tokens(title, hook)
    viral_queries = [
        f"{title} TikTok viral",
        f"{title} TikTok trend",
        (" ".join(keywords[:6]) + " TikTok").strip(),
        f"{hook[:160]} TikTok",
    ]

    query_output: list[str] = []
    observed: set[str] = set()

    for raw in [*existing_queries, *viral_queries]:
        if not isinstance(raw, str):
            continue
        normalized = re.sub(r"\s+", " ", raw).strip()
        identity = normalized.casefold()
        if normalized and identity not in observed:
            query_output.append(normalized)
            observed.add(identity)

    return json.dumps(
        {
            "task": "discover_verified_trending_and_viral_tiktok_posts",
            "region": intelligence.get("region", "PT"),
            "content_title": title,
            "content_hook": hook,
            "search_queries": query_output[:8],
            "existing_verified_seeds": seed_candidates(
                discovery_results,
                intelligence,
            ),
            "selection_requirements": {
                "direct_tiktok_post_url": True,
                "topic_relevance_required": True,
                "trend_signal_required": True,
                "viral_signal_required": True,
                "official_evidence_only": True,
                "prefer_recent": True,
                "maximum_references": MAX_SEARCH_REFERENCES,
            },
            "governance": {
                "reference_only": True,
                "automatic_download_allowed": False,
                "watermark_removal_allowed": False,
                "automatic_reuse_allowed": False,
                "publication_execution_enabled": False,
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def perform_search(
    content: dict[str, Any],
    discovery_request: dict[str, Any],
    discovery_results: dict[str, Any],
    intelligence: dict[str, Any],
) -> tuple[dict[str, Any], set[str], str, str]:
    fixture_path = os.environ.get(
        "TIKTOK_VIRAL_REVIEW_OFFLINE_FIXTURE",
        "",
    ).strip()

    if fixture_path:
        fixture = load_json(Path(fixture_path))
        payload = require_mapping(fixture.get("payload"), "fixture.payload")
        cited_urls = {
            normalized
            for raw in fixture.get("cited_urls", [])
            if (normalized := normalize_official_url(raw)) is not None
        }
        return payload, cited_urls, "offline-fixture", "offline-fixture"

    base_settings = OpenAIClientSettings.from_environment()
    model = (
        os.environ.get("TIKTOK_VIRAL_REVIEW_MODEL", "").strip()
        or base_settings.model
    )
    settings = replace(
        base_settings,
        model=model,
        max_output_tokens=min(base_settings.max_output_tokens, 7_000),
    )
    client = create_client(settings)

    response = client.responses.create(
        model=settings.model,
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(
            content,
            discovery_request,
            discovery_results,
            intelligence,
        ),
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
        reasoning={"effort": "medium"},
        max_output_tokens=settings.max_output_tokens,
        text={
            "format": {
                "type": "json_schema",
                "name": "football_shorts_tiktok_viral_reference_review",
                "description": (
                    "Referências TikTok atuais, trending e virais, "
                    "com evidência oficial."
                ),
                "strict": True,
                "schema": REVIEW_JSON_SCHEMA,
            }
        },
    )

    status = getattr(response, "status", None)
    if status == "incomplete":
        raise OpenAIResponseError("A pesquisa viral ficou incompleta.")
    if status == "failed":
        raise OpenAIResponseError(
            f"A pesquisa viral falhou: {getattr(response, 'error', None)}"
        )

    payload = parse_response_json(response)
    cited_urls = collect_cited_urls(response)
    request_id = str(getattr(response, "_request_id", "indisponível"))
    return payload, cited_urls, request_id, settings.model


def metric_bonus(metrics: dict[str, int | None]) -> int:
    bonus = 0
    views = metrics.get("view_count")
    likes = metrics.get("like_count")
    comments = metrics.get("comment_count")
    shares = metrics.get("share_count")

    if views is not None:
        if views >= 1_000_000:
            bonus += 8
        elif views >= 250_000:
            bonus += 5
        elif views >= 100_000:
            bonus += 3

    if likes is not None:
        if likes >= 100_000:
            bonus += 5
        elif likes >= 25_000:
            bonus += 3

    if comments is not None:
        if comments >= 5_000:
            bonus += 3
        elif comments >= 1_000:
            bonus += 2

    if shares is not None:
        if shares >= 10_000:
            bonus += 5
        elif shares >= 2_500:
            bonus += 3

    return min(15, bonus)


def total_score(
    relevance: int,
    trend: int,
    viral: int,
    metrics: dict[str, int | None],
) -> int:
    weighted = relevance * 0.42 + trend * 0.29 + viral * 0.29
    return min(
        100,
        max(0, int(round(weighted + metric_bonus(metrics)))),
    )


def rejection_reasons(
    *,
    relevance_score: int,
    trend_score: int,
    viral_score: int,
    trend_status: str,
    viral_status: str,
    score: int,
) -> list[str]:
    reasons: list[str] = []

    if relevance_score < MIN_RELEVANCE_SCORE:
        reasons.append("Relevância temática insuficiente.")
    if trend_status != "verified":
        reasons.append("Sinal de tendência não verificado.")
    if viral_status != "verified":
        reasons.append("Sinal de viralidade não verificado.")
    if trend_score < MIN_TREND_CONFIDENCE:
        reasons.append("Confiança de tendência abaixo do mínimo.")
    if viral_score < MIN_VIRAL_CONFIDENCE:
        reasons.append("Confiança de viralidade abaixo do mínimo.")
    if score < MIN_TOTAL_SCORE:
        reasons.append("Score total abaixo do mínimo governado.")

    return reasons


def evaluate_reference(
    raw: dict[str, Any],
    cited_urls: set[str],
    index: int,
) -> dict[str, Any] | None:
    parsed = parse_video_url(raw.get("source_url"))
    if parsed is None:
        return None

    source_url, username, video_id = parsed
    cited_identities = {url_identity(value) for value in cited_urls}

    if url_identity(source_url) not in cited_identities:
        return None

    raw_evidence_urls = raw.get("evidence_urls")
    if not isinstance(raw_evidence_urls, list):
        raw_evidence_urls = []

    evidence_urls: list[str] = []
    observed_evidence: set[str] = set()

    for value in raw_evidence_urls:
        normalized = normalize_official_url(value)
        if normalized is None:
            continue
        identity = url_identity(normalized)
        if identity not in cited_identities or identity in observed_evidence:
            continue
        evidence_urls.append(normalized)
        observed_evidence.add(identity)

    if source_url not in evidence_urls:
        evidence_urls.insert(0, source_url)

    metrics_raw = raw.get("metrics")
    if not isinstance(metrics_raw, dict):
        metrics_raw = {}

    metrics: dict[str, int | None] = {
        field_name: optional_nonnegative_integer(metrics_raw.get(field_name))
        for field_name in (
            "view_count",
            "like_count",
            "comment_count",
            "share_count",
        )
    }

    relevance_score = clamp_score(raw.get("relevance_score"))
    trend_score = clamp_score(raw.get("trend_confidence_score"))
    viral_score = clamp_score(raw.get("viral_confidence_score"))
    trend_status = str(
        raw.get("trend_signal_status", "insufficient")
    ).strip().lower()
    viral_status = str(
        raw.get("viral_signal_status", "insufficient")
    ).strip().lower()

    score = total_score(
        relevance_score,
        trend_score,
        viral_score,
        metrics,
    )

    reasons = rejection_reasons(
        relevance_score=relevance_score,
        trend_score=trend_score,
        viral_score=viral_score,
        trend_status=trend_status,
        viral_status=viral_status,
        score=score,
    )

    start_seconds = optional_nonnegative_integer(
        raw.get("engagement_peak_start_seconds")
    )
    if start_seconds is None:
        start_seconds = 0

    creator_username = str(
        raw.get("creator_username", f"@{username}")
    ).strip()
    if not creator_username:
        creator_username = f"@{username}"
    if not creator_username.startswith("@"):
        creator_username = "@" + creator_username

    caption = str(raw.get("caption", "")).strip()[:500]
    if not caption:
        caption = "Referência TikTok relacionada com o tema vencedor."

    return {
        "reference_id": (
            "viral_reference_"
            + hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:20]
        ),
        "rank": index + 1,
        "source_url": source_url,
        "video_id": video_id,
        "creator_username": creator_username,
        "caption": caption,
        "relevance_reason": str(
            raw.get("relevance_reason", "")
        ).strip()[:600],
        "trend_signal": {
            "status": trend_status,
            "confidence_score": trend_score,
            "evidence": str(raw.get("trend_evidence", "")).strip()[:700],
        },
        "viral_signal": {
            "status": viral_status,
            "confidence_score": viral_score,
            "evidence": str(raw.get("viral_evidence", "")).strip()[:700],
        },
        "published_at": (
            raw.get("published_at")
            if isinstance(raw.get("published_at"), str)
            and raw.get("published_at").strip()
            else None
        ),
        "metrics": metrics,
        "editorial_relevance_score": relevance_score,
        "metric_bonus": metric_bonus(metrics),
        "total_score": score,
        "eligible_for_internal_player": not reasons,
        "rejection_reasons": reasons,
        "embed": {
            "provider": "tiktok_official_player",
            "player_url": (
                "https://www.tiktok.com/"
                f"player/v1/{video_id}"
                "?controls=1"
                "&progress_bar=1"
                "&play_button=1"
                "&volume_control=1"
                "&fullscreen_button=1"
                "&timestamp=1"
                "&loop=0"
                "&autoplay=0"
                "&music_info=1"
                "&description=1"
                "&rel=0"
                "&native_context_menu=1"
                "&closed_caption=1"
                "&muted=0"
            ),
            "lazy_user_initiated": True,
            "reference_window": {
                "start_seconds": start_seconds,
                "duration_seconds": REFERENCE_WINDOW_SECONDS,
            },
        },
        "evidence_urls": evidence_urls[:4],
        "rights": {
            "status": "reference_only",
            "creator_attribution_required": True,
            "local_copy_allowed": False,
            "automatic_download_allowed": False,
            "automatic_clip_extraction_allowed": False,
            "reuse_in_master_allowed": False,
        },
    }


def build_review(
    content: dict[str, Any],
    discovery_request: dict[str, Any],
    discovery_results: dict[str, Any],
    intelligence: dict[str, Any],
) -> dict[str, Any]:
    raw_result, cited_urls, request_id, model = perform_search(
        content,
        discovery_request,
        discovery_results,
        intelligence,
    )

    raw_references = require_list(
        raw_result.get("references"),
        "search.references",
    )

    evaluated: list[dict[str, Any]] = []
    observed: set[str] = set()

    for index, raw in enumerate(raw_references):
        if not isinstance(raw, dict):
            continue

        reference = evaluate_reference(raw, cited_urls, index)
        if reference is None:
            continue

        identity = url_identity(reference["source_url"])
        if identity in observed:
            continue

        evaluated.append(reference)
        observed.add(identity)

    evaluated.sort(
        key=lambda item: (
            item["eligible_for_internal_player"],
            item["total_score"],
            item["viral_signal"]["confidence_score"],
            item["trend_signal"]["confidence_score"],
        ),
        reverse=True,
    )

    selected = [
        item
        for item in evaluated
        if item["eligible_for_internal_player"]
    ][:MAX_SELECTED_REFERENCES]

    selected_ids = {item["reference_id"] for item in selected}
    rejected = [
        item
        for item in evaluated
        if item["reference_id"] not in selected_ids
    ]

    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank

    status = (
        "ready_for_internal_review"
        if selected
        else "no_verified_viral_references"
    )

    source_topic = require_mapping(
        content.get("source_topic"),
        "content.source_topic",
    )

    payload: dict[str, Any] = {
        "review_version": REVIEW_VERSION,
        "generated_at": now_iso(),
        "status": status,
        "region": intelligence.get("region", "PT"),
        "content": {
            "title": require_text(
                source_topic.get("title"),
                "content.source_topic.title",
            ),
            "hook": require_text(
                source_topic.get("hook"),
                "content.source_topic.hook",
            ),
        },
        "provider": {
            "provider_id": "openai_web_search",
            "model": model,
            "request_id": request_id,
        },
        "selection_policy": {
            "maximum_selected_references": MAX_SELECTED_REFERENCES,
            "reference_window_seconds": REFERENCE_WINDOW_SECONDS,
            "minimum_relevance_score": MIN_RELEVANCE_SCORE,
            "minimum_trend_confidence_score": MIN_TREND_CONFIDENCE,
            "minimum_viral_confidence_score": MIN_VIRAL_CONFIDENCE,
            "minimum_total_score": MIN_TOTAL_SCORE,
            "trend_signal_must_be_verified": True,
            "viral_signal_must_be_verified": True,
        },
        "selected_references": selected,
        "rejected_references": rejected,
        "summary": {
            "evaluated_count": len(evaluated),
            "selected_count": len(selected),
            "rejected_count": len(rejected),
            "search_summary": str(
                raw_result.get("search_summary", "")
            ).strip()[:1_200],
        },
        "evidence": {
            "cited_urls": sorted(cited_urls),
            "citation_count": len(cited_urls),
        },
        "governance": {
            "internal_review_only": True,
            "official_tiktok_player_only": True,
            "lazy_user_initiated_player_load": True,
            "browser_official_embed_player_enabled": True,
            "browser_api_calls_enabled": False,
            "automatic_reference_ranking_enabled": True,
            "automatic_reuse_selection_enabled": False,
            "third_party_download_allowed": False,
            "automatic_clip_extraction_allowed": False,
            "watermark_removal_allowed": False,
            "creator_attribution_required": True,
            "rights_status_default": "reference_only",
            "publication_execution_enabled": False,
        },
        "review_identity_sha256": "",
    }

    payload["review_identity_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in payload.items()
            if key != "review_identity_sha256"
        }
    )

    write_json_atomically(OUTPUT_PATH, payload)
    return payload


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.5G")
    print("TIKTOK VIRAL REFERENCE REVIEW")
    print("VERIFIED TREND + VERIFIED VIRAL SIGNALS")
    print("OFFICIAL PLAYER - NO DOWNLOAD - NO PUBLICATION")
    print("=" * 70)

    try:
        review = build_review(
            load_json(CONTENT_PATH),
            load_json(DISCOVERY_REQUEST_PATH),
            load_json(DISCOVERY_RESULTS_PATH),
            load_json(TREND_INTELLIGENCE_PATH),
        )
    except OpenAIConfigurationError as exc:
        print(
            f"TIKTOK_VIRAL_REVIEW_CONFIGURATION_ERROR={exc}",
            file=sys.stderr,
        )
        return 2
    except (
        OpenAIResponseError,
        OpenAIClientError,
        openai.OpenAIError,
        ViralReferenceReviewError,
    ) as exc:
        print(f"TIKTOK_VIRAL_REVIEW_ERROR={exc}", file=sys.stderr)
        return 3
    except Exception as exc:
        print(
            f"TIKTOK_VIRAL_REVIEW_UNEXPECTED_ERROR={exc}",
            file=sys.stderr,
        )
        return 1

    print(f"TIKTOK_VIRAL_REVIEW_STATUS={review['status'].upper()}")
    print(
        "EVALUATED_REFERENCE_COUNT="
        f"{review['summary']['evaluated_count']}"
    )
    print(
        "SELECTED_REFERENCE_COUNT="
        f"{review['summary']['selected_count']}"
    )
    print(f"REFERENCE_WINDOW_SECONDS={REFERENCE_WINDOW_SECONDS}")
    print("OFFICIAL_TIKTOK_PLAYER_ONLY=YES")
    print("AUTOMATIC_REFERENCE_RANKING=YES")
    print("AUTOMATIC_REUSE_SELECTION=NO")
    print("THIRD_PARTY_DOWNLOAD_ALLOWED=NO")
    print("AUTOMATIC_CLIP_EXTRACTION_ALLOWED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("TIKTOK_VIRAL_REFERENCE_REVIEW=PASS")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
