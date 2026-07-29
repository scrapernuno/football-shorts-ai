from __future__ import annotations

import hashlib
import json
import subprocess

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PREVIEW = ROOT / "output/production_preview.json"
PUBLIC_PREVIEW = ROOT / "dashboard/data/production_preview.json"
PUBLIC_VIDEO = ROOT / "dashboard/assets/generated/production-preview.mp4"
PUBLIC_VTT = ROOT / "dashboard/assets/generated/production-preview.vtt"


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")
    return payload


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return float(result.stdout.strip())


def main() -> int:
    preview = load(PREVIEW)
    if preview != load(PUBLIC_PREVIEW):
        raise ValueError("Preview público não corresponde ao output.")

    format_payload = preview.get("format")
    governance = preview.get("governance")

    if (
        preview.get("status") != "ready_for_internal_review"
        or not isinstance(format_payload, dict)
        or format_payload.get("width") != 1080
        or format_payload.get("height") != 1920
        or format_payload.get("aspect_ratio") != "9:16"
        or format_payload.get("duration_seconds") != 45
    ):
        raise ValueError("Contrato visual do preview inválido.")

    if not isinstance(governance, dict):
        raise ValueError("Governança inválida.")

    for field in (
        "publication_execution_enabled",
        "browser_api_calls_enabled",
        "unlicensed_assets_used",
        "selected_source_assets_used",
        "synthetic_player_likenesses_generated",
        "club_logo_generation_enabled",
        "commercial_music_embedded",
        "third_party_tiktok_download_allowed",
        "watermark_removal_allowed",
    ):
        if governance.get(field) is not False:
            raise ValueError(f"{field} deve permanecer false.")

    if (
        governance.get("internal_review_only") is not True
        or governance.get("not_for_publication") is not True
    ):
        raise ValueError("Classificação interna inválida.")

    for path in (PUBLIC_VIDEO, PUBLIC_VTT):
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(f"Artefacto em falta: {path}")

    expected_sha = preview["artifacts"]["video"]["sha256"]
    if sha(PUBLIC_VIDEO) != expected_sha:
        raise ValueError("SHA256 do vídeo público inválido.")

    if not 44.5 <= probe(PUBLIC_VIDEO) <= 45.5:
        raise ValueError("Duração pública fora da tolerância.")

    print("PREVIEW_STATUS=READY_FOR_INTERNAL_REVIEW")
    print("PREVIEW_FORMAT=1080x1920_9:16")
    print("PREVIEW_DURATION=45")
    print("VIDEO_SHA256_INTEGRITY=PASS")
    print("CAPTIONS_PUBLIC=PASS")
    print("INTERNAL_REVIEW_ONLY=YES")
    print("UNLICENSED_ASSETS_USED=NO")
    print("SYNTHETIC_PLAYER_LIKENESSES=NO")
    print("COMMERCIAL_MUSIC_EMBEDDED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("PRODUCTION_PREVIEW_CERTIFICATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
