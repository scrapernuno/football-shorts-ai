from __future__ import annotations

import json
import shutil

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output" / "tiktok_viral_reference_review.json"
TARGET = ROOT / "dashboard" / "data" / "tiktok_viral_reference_review.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")
    return payload


def main() -> int:
    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0031C.5G")
    print("TIKTOK VIRAL REFERENCE REVIEW SYNC")
    print("=" * 70)

    review = load_json(SOURCE)
    governance = review.get("governance")

    if (
        not isinstance(governance, dict)
        or governance.get("third_party_download_allowed") is not False
        or governance.get("automatic_clip_extraction_allowed") is not False
        or governance.get("publication_execution_enabled") is not False
    ):
        raise ValueError("Governança do TikTok Viral Review inválida.")

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    temporary = TARGET.with_suffix(TARGET.suffix + ".tmp")
    shutil.copyfile(SOURCE, temporary)
    temporary.replace(TARGET)

    if load_json(TARGET) != review:
        raise ValueError("O review público não corresponde ao output.")

    print("TIKTOK_VIRAL_REVIEW_JSON_SYNC=PASS")
    print("THIRD_PARTY_DOWNLOAD_ALLOWED=NO")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
