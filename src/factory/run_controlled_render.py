"""FOOTBALL-SHORTS-AI-0061C — manual controlled-render CLI.

Loads a certified 0060I render package and a 0061A authorization package, builds
an execution order through 0061B and executes FFmpeg only when the exact human
confirmation phrase is supplied. No publication or network action is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from factory.controlled_ffmpeg_execution_gate import (
    ControlledFFmpegExecutionError,
    build_controlled_ffmpeg_execution_order,
    execute_controlled_render,
)

CONFIRMATION_PHRASE = "EXECUTE AUTHORIZED RENDER ONCE"


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ControlledFFmpegExecutionError(f"JSON input missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ControlledFFmpegExecutionError(f"JSON input must be an object: {path}")
    return payload


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one authorized Football Shorts AI render")
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--render-package", required=True, type=Path)
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--execution-note", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(argv)

    if args.confirmation != CONFIRMATION_PHRASE:
        raise ControlledFFmpegExecutionError("exact human confirmation phrase required")

    authorization = _load_json(args.authorization)
    render_package = _load_json(args.render_package)
    order = build_controlled_ffmpeg_execution_order(
        authorization=authorization,
        render_package=render_package,
        requested_by=args.requested_by,
        execution_note=args.execution_note,
        explicit_human_command=True,
    )

    args.result.parent.mkdir(parents=True, exist_ok=True)
    if args.prepare_only:
        payload: dict[str, object] = {
            "schema": "football-shorts-ai.controlled-render-preparation.v1",
            "execution_order": order.to_dict(),
            "render_performed": False,
            "publication_performed": False,
            "network_used": False,
        }
    else:
        payload = execute_controlled_render(order, explicit_execute=True)

    args.result.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
