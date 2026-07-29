from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "tiktok_viral_reference_review.json"
PUBLIC = ROOT / "dashboard" / "data" / "tiktok_viral_reference_review.json"
INDEX = ROOT / "dashboard" / "index.html"
JAVASCRIPT = ROOT / "dashboard" / "assets" / "dashboard.js"
CSS = ROOT / "dashboard" / "assets" / "dashboard.css"
MARKER = "FOOTBALL-SHORTS-AI-0031C.5G"

DIRECT_VIDEO_PATTERN = re.compile(
    r"^/@[^/]+/video/[0-9]+$",
    flags=re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")
    return payload


def certify_reference(reference: dict[str, Any], index: int) -> None:
    prefix = f"selected_references[{index}]"
    trend_signal = reference.get("trend_signal")
    viral_signal = reference.get("viral_signal")
    rights = reference.get("rights")
    embed = reference.get("embed")

    if not isinstance(trend_signal, dict):
        raise ValueError(f"{prefix}.trend_signal inválido.")
    if not isinstance(viral_signal, dict):
        raise ValueError(f"{prefix}.viral_signal inválido.")
    if not isinstance(rights, dict):
        raise ValueError(f"{prefix}.rights inválido.")
    if not isinstance(embed, dict):
        raise ValueError(f"{prefix}.embed inválido.")

    if trend_signal.get("status") != "verified":
        raise ValueError(f"{prefix} não tem trend verificada.")
    if viral_signal.get("status") != "verified":
        raise ValueError(f"{prefix} não tem viralidade verificada.")

    if int(reference.get("editorial_relevance_score", 0)) < 65:
        raise ValueError(f"{prefix} tem relevância insuficiente.")
    if int(trend_signal.get("confidence_score", 0)) < 60:
        raise ValueError(f"{prefix} tem confiança trend insuficiente.")
    if int(viral_signal.get("confidence_score", 0)) < 60:
        raise ValueError(f"{prefix} tem confiança viral insuficiente.")
    if int(reference.get("total_score", 0)) < 70:
        raise ValueError(f"{prefix} tem score total insuficiente.")

    source_url = str(reference.get("source_url", ""))
    source_parts = urlsplit(source_url)

    if (
        source_parts.scheme != "https"
        or source_parts.hostname != "www.tiktok.com"
        or DIRECT_VIDEO_PATTERN.fullmatch(source_parts.path.rstrip("/")) is None
    ):
        raise ValueError(
            f"{prefix}.source_url não é um post TikTok direto."
        )

    player_url = str(embed.get("player_url", ""))
    if not player_url.startswith("https://www.tiktok.com/player/v1/"):
        raise ValueError(f"{prefix}.player_url não usa o player oficial.")

    reference_window = embed.get("reference_window")
    if not isinstance(reference_window, dict):
        raise ValueError(f"{prefix}.reference_window inválido.")

    if reference_window.get("duration_seconds") not in {2, 3}:
        raise ValueError(
            f"{prefix} não usa uma janela de 2–3 segundos."
        )

    for field_name in (
        "local_copy_allowed",
        "automatic_download_allowed",
        "automatic_clip_extraction_allowed",
        "reuse_in_master_allowed",
    ):
        if rights.get(field_name) is not False:
            raise ValueError(f"{prefix}.{field_name} deve permanecer false.")


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.5G")
    print("TIKTOK VIRAL REFERENCE REVIEW CERTIFICATION")
    print("=" * 70)

    review = load_json(OUTPUT)
    public = load_json(PUBLIC)

    if public != review:
        raise ValueError("O review público não corresponde ao output.")

    status = review.get("status")
    if status not in {
        "ready_for_internal_review",
        "no_verified_viral_references",
    }:
        raise ValueError("Estado do TikTok Viral Review inválido.")

    selected = review.get("selected_references")
    if not isinstance(selected, list):
        raise ValueError("selected_references deve ser uma lista.")
    if len(selected) > 3:
        raise ValueError("Existem mais de três referências selecionadas.")

    for index, raw in enumerate(selected):
        if not isinstance(raw, dict):
            raise ValueError("Referência selecionada inválida.")
        certify_reference(raw, index)

    if status == "ready_for_internal_review" and not selected:
        raise ValueError("Review ready sem referências selecionadas.")
    if status == "no_verified_viral_references" and selected:
        raise ValueError("Review sem referências contém seleção.")

    governance = review.get("governance")
    if not isinstance(governance, dict):
        raise ValueError("Governança do review inválida.")

    expected_true = (
        "internal_review_only",
        "official_tiktok_player_only",
        "lazy_user_initiated_player_load",
        "browser_official_embed_player_enabled",
        "automatic_reference_ranking_enabled",
        "creator_attribution_required",
    )

    expected_false = (
        "browser_api_calls_enabled",
        "automatic_reuse_selection_enabled",
        "third_party_download_allowed",
        "automatic_clip_extraction_allowed",
        "watermark_removal_allowed",
        "publication_execution_enabled",
    )

    for field_name in expected_true:
        if governance.get(field_name) is not True:
            raise ValueError(f"{field_name} deve ser true.")

    for field_name in expected_false:
        if governance.get(field_name) is not False:
            raise ValueError(f"{field_name} deve ser false.")

    for path in (INDEX, JAVASCRIPT, CSS):
        content = path.read_text(encoding="utf-8")
        if MARKER not in content:
            raise ValueError(f"Marcador 0031C.5G ausente em {path}.")

    javascript = JAVASCRIPT.read_text(encoding="utf-8")
    required_javascript_markers = (
        "renderTikTokViralReferenceReview",
        "activateTikTokReferenceButton",
        (
            'tiktokViralReview: '
            '"data/tiktok_viral_reference_review.json"'
        ),
        "https://www.tiktok.com/player/v1/",
    )

    for marker in required_javascript_markers:
        if marker not in javascript:
            raise ValueError(f"Marcador JavaScript ausente: {marker}")

    print(f"TIKTOK_VIRAL_REVIEW_STATUS={str(status).upper()}")
    print(f"SELECTED_REFERENCE_COUNT={len(selected)}")
    print("VERIFIED_TREND_ONLY=YES")
    print("VERIFIED_VIRAL_ONLY=YES")
    print("OFFICIAL_TIKTOK_PLAYER_ONLY=YES")
    print("REFERENCE_WINDOW=2_TO_3_SECONDS")
    print("THIRD_PARTY_DOWNLOAD_ALLOWED=NO")
    print("AUTOMATIC_CLIP_EXTRACTION_ALLOWED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("TIKTOK_VIRAL_REFERENCE_REVIEW_CERTIFICATION=PASS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
