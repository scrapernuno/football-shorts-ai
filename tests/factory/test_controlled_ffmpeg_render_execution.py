from dataclasses import replace
from pathlib import Path

import pytest

from factory.controlled_ffmpeg_render_execution import (
    ControlledRenderExecutionError,
    build_controlled_render_order,
    execute_controlled_render,
    file_sha256,
)


def _fixtures(tmp_path: Path):
    media = tmp_path / "media" / "source.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"authorized-video-fixture")
    output = "artifacts/final/football-short.mp4"
    package = {
        "render_package_id": "RENDERPKG-ABCDEF0123456789ABCD",
        "package_state": "ready_for_authorization",
        "ffmpeg_design": {
            "executable": "ffmpeg",
            "arguments": [
                "-hide_banner", "-nostdin", "-y", "-i", "media/source.mp4",
                "-c:v", "libx264", output,
            ],
            "output_uri": output,
            "execution_enabled": False,
        },
    }
    authorization = {
        "authorization_id": "RENDERAUTH-ABCDEF0123456789ABCD",
        "render_package_id": package["render_package_id"],
        "authorization_state": "authorized",
        "assets": [{
            "asset_id": "AUTHMEDIA-ABCDEF0123456789ABCD",
            "local_uri": "media/source.mp4",
            "sha256": file_sha256(media),
            "intake_allowed": True,
        }],
    }
    return package, authorization, media


def _ready_order(tmp_path: Path):
    package, authorization, media = _fixtures(tmp_path)
    order = build_controlled_render_order(
        authorization=authorization,
        render_package=package,
        ordered_by="Nuno Freitas",
        order_note="Renderização manual autorizada para revisão privada.",
        execution_requested=True,
    )
    return order, package, authorization, media


def test_builds_ready_one_time_render_order(tmp_path: Path):
    order, package, authorization, _ = _ready_order(tmp_path)
    order.validate()
    assert order.order_state == "ready"
    assert order.execution_requested is True
    assert order.authorization_id == authorization["authorization_id"]
    assert order.render_package_id == package["render_package_id"]
    assert order.ffmpeg_args[0] == "-hide_banner"
    assert "-nostdin" in order.ffmpeg_args
    assert order.blockers == ()
    assert order.network_enabled is False
    assert order.acquisition_enabled is False
    assert order.auto_publish is False


def test_requires_explicit_human_execution_request(tmp_path: Path):
    package, authorization, _ = _fixtures(tmp_path)
    order = build_controlled_render_order(
        authorization=authorization,
        render_package=package,
        ordered_by="Nuno Freitas",
        order_note="Preparar sem executar.",
        execution_requested=False,
    )
    assert order.order_state == "blocked"
    assert "EXPLICIT_EXECUTION_REQUEST_REQUIRED" in order.blockers


def test_rejects_authorization_package_mismatch(tmp_path: Path):
    package, authorization, _ = _fixtures(tmp_path)
    authorization["render_package_id"] = "RENDERPKG-00000000000000000000"
    order = build_controlled_render_order(
        authorization=authorization,
        render_package=package,
        ordered_by="Nuno",
        order_note="Teste",
        execution_requested=True,
    )
    assert order.order_state == "blocked"
    assert "AUTHORIZATION_RENDER_PACKAGE_MISMATCH" in order.blockers


def test_execute_false_never_invokes_ffmpeg(tmp_path: Path, monkeypatch):
    order, *_ = _ready_order(tmp_path)
    monkeypatch.setattr(
        "factory.controlled_ffmpeg_render_execution.subprocess.run",
        lambda *args, **kwargs: pytest.fail("FFmpeg must not run without execute=True"),
    )
    receipt = execute_controlled_render(order, execute=False, cwd=tmp_path)
    assert receipt.execution_state == "not_executed"
    assert receipt.return_code is None
    assert receipt.output_sha256 == ""
    assert receipt.blockers == ("EXECUTION_FLAG_NOT_ENABLED",)


def test_hash_mismatch_blocks_before_subprocess(tmp_path: Path, monkeypatch):
    order, _, _, media = _ready_order(tmp_path)
    media.write_bytes(b"tampered")
    monkeypatch.setattr(
        "factory.controlled_ffmpeg_render_execution.subprocess.run",
        lambda *args, **kwargs: pytest.fail("FFmpeg must not run after hash mismatch"),
    )
    receipt = execute_controlled_render(order, execute=True, cwd=tmp_path)
    assert receipt.execution_state == "blocked"
    assert "AUTHORIZED_MEDIA_HASH_MISMATCH" in receipt.blockers


def test_successful_controlled_execution_creates_receipt(tmp_path: Path, monkeypatch):
    order, *_ = _ready_order(tmp_path)

    class Completed:
        returncode = 0
        stderr = "fixture ffmpeg success"

    def fake_run(command, *, cwd, capture_output, text, timeout, check):
        assert command[0] == "ffmpeg"
        assert "-nostdin" in command
        output = Path(cwd) / order.output_uri
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"rendered-mp4-fixture")
        return Completed()

    monkeypatch.setattr("factory.controlled_ffmpeg_render_execution.subprocess.run", fake_run)
    receipt = execute_controlled_render(order, execute=True, cwd=tmp_path)
    receipt.validate()
    assert receipt.execution_state == "rendered"
    assert receipt.return_code == 0
    assert len(receipt.output_sha256) == 64
    assert receipt.blockers == ()


def test_replay_is_deterministic(tmp_path: Path):
    first, *_ = _ready_order(tmp_path)
    second, *_ = _ready_order(tmp_path)
    assert first.to_dict() == second.to_dict()


def test_evidence_tampering_is_rejected(tmp_path: Path):
    order, *_ = _ready_order(tmp_path)
    with pytest.raises(ControlledRenderExecutionError, match="evidence mismatch"):
        replace(order, order_note="altered").validate()


def test_operational_capabilities_remain_disabled(tmp_path: Path):
    order, *_ = _ready_order(tmp_path)
    with pytest.raises(ControlledRenderExecutionError, match="unrelated capabilities"):
        replace(order, auto_publish=True).validate()
