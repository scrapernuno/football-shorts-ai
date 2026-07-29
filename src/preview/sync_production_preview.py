from __future__ import annotations

import json
import shutil

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_JSON = ROOT / "output/production_preview.json"
PUBLIC_JSON = ROOT / "dashboard/data/production_preview.json"
SOURCE_VIDEO = ROOT / "output/assets/previews/production-preview.mp4"
PUBLIC_VIDEO = ROOT / "dashboard/assets/generated/production-preview.mp4"
SOURCE_VTT = ROOT / "output/assets/previews/production-preview.vtt"
PUBLIC_VTT = ROOT / "dashboard/assets/generated/production-preview.vtt"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} deve conter um objeto JSON.")
    return payload


def copy(source: Path, target: Path) -> None:
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(f"Artefacto em falta ou vazio: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    shutil.copyfile(source, temp)
    temp.replace(target)


def main() -> int:
    preview = load_json(SOURCE_JSON)
    governance = preview.get("governance")

    if (
        not isinstance(governance, dict)
        or governance.get("not_for_publication") is not True
        or governance.get("publication_execution_enabled") is not False
    ):
        raise ValueError("Governança do preview inválida.")

    copy(SOURCE_JSON, PUBLIC_JSON)
    copy(SOURCE_VIDEO, PUBLIC_VIDEO)
    copy(SOURCE_VTT, PUBLIC_VTT)

    if load_json(PUBLIC_JSON) != preview:
        raise ValueError("O preview público não corresponde ao output.")

    print("PRODUCTION_PREVIEW_JSON_SYNC=PASS")
    print("PRODUCTION_PREVIEW_MP4_SYNC=PASS")
    print("PRODUCTION_PREVIEW_VTT_SYNC=PASS")
    print("PUBLICATION_EXECUTION_ENABLED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
