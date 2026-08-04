from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from factory.controlled_ffmpeg_execution_gate import ControlledFFmpegExecutionError
from factory.run_controlled_render import CONFIRMATION_PHRASE, run


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"authorized-video")
    digest = hashlib.sha256(media.read_bytes()).hexdigest()

    render_package = {
        "render_package_id": "RENDERPKG-00000000000000000001",
        "package_state": "ready_for_authorization",
        "ffmpeg_design": {
            "executable": "ffmpeg",
            "arguments": ["-i", str(media), str(tmp_path / "output.mp4")],
            "output_uri": str(tmp_path / "output.mp4"),
            "execution_enabled": False,
        },
    }
    authorization = {
        "authorization_id": "RENDERAUTH-00000000000000000001",
        "render_package_id": render_package["render_package_id"],
        "authorization_state": "authorized",
        "assets": [{
            "local_uri": str(media),
            "sha256": digest,
            "intake_allowed": True,
        }],
    }

    render_path = tmp_path / "render.json"
    authorization_path = tmp_path / "authorization.json"
    render_path.write_text(json.dumps(render_package), encoding="utf-8")
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    return authorization_path, render_path


def test_prepare_only_writes_non_operational_evidence(tmp_path: Path) -> None:
    authorization, render_package = _write_inputs(tmp_path)
    result = tmp_path / "result.json"

    assert run([
        "--authorization", str(authorization),
        "--render-package", str(render_package),
        "--requested-by", "human-reviewer",
        "--execution-note", "Prepare exactly one authorized render.",
        "--confirmation", CONFIRMATION_PHRASE,
        "--result", str(result),
        "--prepare-only",
    ]) == 0

    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["render_performed"] is False
    assert payload["publication_performed"] is False
    assert payload["network_used"] is False
    assert payload["execution_order"]["execution_state"] == "ready"


def test_exact_confirmation_phrase_is_required(tmp_path: Path) -> None:
    authorization, render_package = _write_inputs(tmp_path)
    with pytest.raises(ControlledFFmpegExecutionError, match="exact human confirmation"):
        run([
            "--authorization", str(authorization),
            "--render-package", str(render_package),
            "--requested-by", "human-reviewer",
            "--execution-note", "test",
            "--confirmation", "yes",
            "--result", str(tmp_path / "result.json"),
            "--prepare-only",
        ])


def test_missing_json_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ControlledFFmpegExecutionError, match="JSON input missing"):
        run([
            "--authorization", str(tmp_path / "missing-auth.json"),
            "--render-package", str(tmp_path / "missing-render.json"),
            "--requested-by", "human-reviewer",
            "--execution-note", "test",
            "--confirmation", CONFIRMATION_PHRASE,
            "--result", str(tmp_path / "result.json"),
            "--prepare-only",
        ])
