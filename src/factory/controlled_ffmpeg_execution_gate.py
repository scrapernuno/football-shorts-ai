"""FOOTBALL-SHORTS-AI-0061B — controlled FFmpeg render execution gate.

Validates an authorized 0061A package and creates a single-use execution order.
FFmpeg is invoked only after a second explicit human confirmation. Network access,
media acquisition, extraction and publication remain forbidden.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


class ControlledFFmpegExecutionError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class ControlledRenderExecutionOrder:
    schema: str
    execution_id: str
    authorization_id: str
    render_package_id: str
    requested_by: str
    execution_note: str
    ffmpeg_binary: str
    ffmpeg_arguments: tuple[str, ...]
    output_uri: str
    expected_input_hashes: tuple[tuple[str, str], ...]
    execution_state: str
    execution_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "execution_id": self.execution_id,
            "authorization_id": self.authorization_id,
            "render_package_id": self.render_package_id,
            "requested_by": self.requested_by,
            "execution_note": self.execution_note,
            "ffmpeg_binary": self.ffmpeg_binary,
            "ffmpeg_arguments": list(self.ffmpeg_arguments),
            "output_uri": self.output_uri,
            "expected_input_hashes": [list(item) for item in self.expected_input_hashes],
            "execution_state": self.execution_state,
            "execution_allowed": self.execution_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-ffmpeg-execution.v1":
            raise ControlledFFmpegExecutionError("unsupported execution schema")
        if not self.execution_id.startswith("FFMPEGEXEC-"):
            raise ControlledFFmpegExecutionError("invalid execution identity")
        if not self.authorization_id.startswith("RENDERAUTH-"):
            raise ControlledFFmpegExecutionError("invalid authorization identity")
        if not self.render_package_id.startswith("RENDERPKG-"):
            raise ControlledFFmpegExecutionError("invalid render package identity")
        if self.execution_state not in {"ready", "blocked"}:
            raise ControlledFFmpegExecutionError("unsupported execution state")
        if self.execution_state == "ready" and (self.blockers or not self.execution_allowed):
            raise ControlledFFmpegExecutionError("ready execution requires explicit allowance")
        if self.execution_state != "ready" and self.execution_allowed:
            raise ControlledFFmpegExecutionError("blocked execution cannot be allowed")
        if not self.ffmpeg_arguments or self.ffmpeg_arguments[0] == self.ffmpeg_binary:
            raise ControlledFFmpegExecutionError("arguments must exclude executable")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.auto_publish)):
            raise ControlledFFmpegExecutionError("0061B cannot enable prohibited capabilities")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise ControlledFFmpegExecutionError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledFFmpegExecutionError("execution evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_ffmpeg_execution_order(
    *,
    authorization: Mapping[str, object],
    render_package: Mapping[str, object],
    requested_by: str,
    execution_note: str,
    explicit_human_command: bool,
) -> ControlledRenderExecutionOrder:
    blockers: set[str] = set()
    authorization_id = str(authorization.get("authorization_id", ""))
    render_package_id = str(render_package.get("render_package_id", ""))

    if authorization.get("authorization_state") != "authorized":
        blockers.add("RENDER_AUTHORIZATION_NOT_GRANTED")
    if str(authorization.get("render_package_id", "")) != render_package_id:
        blockers.add("AUTHORIZATION_RENDER_PACKAGE_MISMATCH")
    if render_package.get("package_state") != "ready_for_authorization":
        blockers.add("RENDER_PACKAGE_NOT_READY")
    if not requested_by.strip():
        blockers.add("HUMAN_REQUESTER_REQUIRED")
    if not execution_note.strip():
        blockers.add("EXECUTION_NOTE_REQUIRED")
    if not explicit_human_command:
        blockers.add("EXPLICIT_HUMAN_RENDER_COMMAND_REQUIRED")

    design = render_package.get("ffmpeg_design", {})
    if not isinstance(design, Mapping):
        design = {}
        blockers.add("FFMPEG_DESIGN_INVALID")
    binary = str(design.get("executable", ""))
    arguments = tuple(str(value) for value in design.get("arguments", ()))
    output_uri = str(design.get("output_uri", ""))
    if binary != "ffmpeg":
        blockers.add("FFMPEG_EXECUTABLE_INVALID")
    if design.get("execution_enabled") is not False:
        blockers.add("INERT_FFMPEG_DESIGN_REQUIRED")
    if not arguments:
        blockers.add("FFMPEG_ARGUMENTS_MISSING")
    if not output_uri:
        blockers.add("RENDER_OUTPUT_URI_MISSING")

    expected_hashes: list[tuple[str, str]] = []
    for asset in authorization.get("assets", ()):
        if not isinstance(asset, Mapping):
            blockers.add("AUTHORIZED_MEDIA_INVALID")
            continue
        uri = str(asset.get("local_uri", ""))
        digest = str(asset.get("sha256", "")).lower()
        if asset.get("intake_allowed") is not True:
            blockers.add("AUTHORIZED_MEDIA_NOT_INTAKE_ALLOWED")
        if not uri or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            blockers.add("AUTHORIZED_MEDIA_HASH_INCOMPLETE")
        expected_hashes.append((uri, digest))
    if not expected_hashes:
        blockers.add("AUTHORIZED_MEDIA_MISSING")

    state = "ready" if not blockers else "blocked"
    core = {
        "schema": "football-shorts-ai.controlled-ffmpeg-execution.v1",
        "authorization_id": authorization_id,
        "render_package_id": render_package_id,
        "requested_by": requested_by.strip(),
        "execution_note": execution_note.strip(),
        "ffmpeg_binary": binary,
        "ffmpeg_arguments": list(arguments),
        "output_uri": output_uri,
        "expected_input_hashes": [list(item) for item in sorted(expected_hashes)],
        "execution_state": state,
        "execution_allowed": state == "ready",
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "auto_publish": False,
    }
    execution_id = f"FFMPEGEXEC-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "execution_id": execution_id}
    order = ControlledRenderExecutionOrder(
        schema=core["schema"], execution_id=execution_id,
        authorization_id=authorization_id, render_package_id=render_package_id,
        requested_by=requested_by.strip(), execution_note=execution_note.strip(),
        ffmpeg_binary=binary, ffmpeg_arguments=arguments, output_uri=output_uri,
        expected_input_hashes=tuple(sorted(expected_hashes)), execution_state=state,
        execution_allowed=state == "ready", blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    order.validate()
    return order


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute_controlled_render(
    order: ControlledRenderExecutionOrder,
    *,
    explicit_execute: bool,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Execute one authorized local FFmpeg command after fresh hash verification."""
    order.validate()
    if not explicit_execute:
        raise ControlledFFmpegExecutionError("explicit execution confirmation required")
    if order.execution_state != "ready" or not order.execution_allowed:
        raise ControlledFFmpegExecutionError("execution order is not ready")

    for uri, expected in order.expected_input_hashes:
        path = Path(uri)
        if not path.is_file():
            raise ControlledFFmpegExecutionError(f"authorized media missing: {uri}")
        if _sha256_file(path) != expected:
            raise ControlledFFmpegExecutionError(f"authorized media hash mismatch: {uri}")

    output = Path(order.output_uri)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ControlledFFmpegExecutionError("output already exists; single-use execution refused")

    completed = runner(
        [order.ffmpeg_binary, *order.ffmpeg_arguments],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", "")},
    )
    if completed.returncode != 0:
        raise ControlledFFmpegExecutionError(f"ffmpeg failed with rc={completed.returncode}")
    if not output.is_file():
        raise ControlledFFmpegExecutionError("ffmpeg reported success but output is missing")

    return {
        "schema": "football-shorts-ai.controlled-render-result.v1",
        "execution_id": order.execution_id,
        "render_package_id": order.render_package_id,
        "output_uri": str(output),
        "output_sha256": _sha256_file(output),
        "return_code": completed.returncode,
        "publication_performed": False,
        "network_used": False,
    }


__all__ = [
    "ControlledFFmpegExecutionError", "ControlledRenderExecutionOrder",
    "build_controlled_ffmpeg_execution_order", "canonical_sha256",
    "execute_controlled_render",
]
