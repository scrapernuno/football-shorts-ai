from __future__ import annotations

import hashlib
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from factory.controlled_ffmpeg_execution_gate import (
    ControlledFFmpegExecutionError,
    build_controlled_ffmpeg_execution_order,
    execute_controlled_render,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixtures(tmp_path: Path):
    media = tmp_path / "source.mp4"
    media.write_bytes(b"authorized-video")
    output = tmp_path / "final" / "short.mp4"
    render_package = {
        "render_package_id": "RENDERPKG-1234567890ABCDEF1234",
        "package_state": "ready_for_authorization",
        "ffmpeg_design": {
            "executable": "ffmpeg",
            "arguments": ["-hide_banner", "-nostdin", "-i", str(media), str(output)],
            "output_uri": str(output),
            "execution_enabled": False,
        },
    }
    authorization = {
        "authorization_id": "RENDERAUTH-1234567890ABCDEF1234",
        "render_package_id": render_package["render_package_id"],
        "authorization_state": "authorized",
        "assets": [{
            "local_uri": str(media),
            "sha256": _sha(media.read_bytes()),
            "intake_allowed": True,
        }],
    }
    return media, output, render_package, authorization


def _order(tmp_path: Path):
    _, _, render_package, authorization = _fixtures(tmp_path)
    return build_controlled_ffmpeg_execution_order(
        authorization=authorization,
        render_package=render_package,
        requested_by="Nuno Freitas",
        execution_note="Renderização manual aprovada para revisão interna.",
        explicit_human_command=True,
    )


def test_builds_ready_single_use_execution_order(tmp_path: Path) -> None:
    order = _order(tmp_path)
    order.validate()
    assert order.execution_state == "ready"
    assert order.execution_allowed is True
    assert order.blockers == ()
    assert order.ffmpeg_binary == "ffmpeg"
    assert order.network_enabled is False
    assert order.auto_publish is False


def test_explicit_human_command_is_required(tmp_path: Path) -> None:
    _, _, render_package, authorization = _fixtures(tmp_path)
    order = build_controlled_ffmpeg_execution_order(
        authorization=authorization,
        render_package=render_package,
        requested_by="Nuno Freitas",
        execution_note="Preparar renderização.",
        explicit_human_command=False,
    )
    assert order.execution_state == "blocked"
    assert order.execution_allowed is False
    assert "EXPLICIT_HUMAN_RENDER_COMMAND_REQUIRED" in order.blockers


def test_authorization_and_render_package_must_match(tmp_path: Path) -> None:
    _, _, render_package, authorization = _fixtures(tmp_path)
    authorization["render_package_id"] = "RENDERPKG-OTHER000000000000000"
    order = build_controlled_ffmpeg_execution_order(
        authorization=authorization,
        render_package=render_package,
        requested_by="reviewer",
        execution_note="approved",
        explicit_human_command=True,
    )
    assert order.execution_state == "blocked"
    assert "AUTHORIZATION_RENDER_PACKAGE_MISMATCH" in order.blockers


def test_execution_requires_second_confirmation(tmp_path: Path) -> None:
    with pytest.raises(ControlledFFmpegExecutionError, match="explicit execution"):
        execute_controlled_render(_order(tmp_path), explicit_execute=False)


def test_hash_mismatch_fails_closed_before_runner(tmp_path: Path) -> None:
    media, _, _, _ = _fixtures(tmp_path)
    order = _order(tmp_path)
    media.write_bytes(b"tampered")
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        return subprocess.CompletedProcess(args[0], 0, "", "")

    with pytest.raises(ControlledFFmpegExecutionError, match="hash mismatch"):
        execute_controlled_render(order, explicit_execute=True, runner=runner)
    assert called is False


def test_successful_controlled_execution_records_output_evidence(tmp_path: Path) -> None:
    _, output, _, _ = _fixtures(tmp_path)
    order = _order(tmp_path)

    def runner(command, **kwargs):
        assert command[0] == "ffmpeg"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"rendered-mp4")
        return subprocess.CompletedProcess(command, 0, "ok", "")

    result = execute_controlled_render(order, explicit_execute=True, runner=runner)
    assert result["return_code"] == 0
    assert result["output_sha256"] == _sha(b"rendered-mp4")
    assert result["publication_performed"] is False
    assert result["network_used"] is False


def test_existing_output_blocks_reexecution(tmp_path: Path) -> None:
    _, output, _, _ = _fixtures(tmp_path)
    order = _order(tmp_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"existing")
    with pytest.raises(ControlledFFmpegExecutionError, match="single-use"):
        execute_controlled_render(order, explicit_execute=True)


def test_ffmpeg_failure_is_fail_closed(tmp_path: Path) -> None:
    order = _order(tmp_path)

    def runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 7, "", "failure")

    with pytest.raises(ControlledFFmpegExecutionError, match="rc=7"):
        execute_controlled_render(order, explicit_execute=True, runner=runner)


def test_evidence_tampering_is_detected(tmp_path: Path) -> None:
    order = _order(tmp_path)
    tampered = replace(order, execution_note="changed")
    with pytest.raises(ControlledFFmpegExecutionError, match="evidence mismatch"):
        tampered.validate()


def test_operational_capabilities_cannot_be_enabled(tmp_path: Path) -> None:
    order = _order(tmp_path)
    with pytest.raises(ControlledFFmpegExecutionError, match="prohibited capabilities"):
        replace(order, auto_publish=True).validate()
