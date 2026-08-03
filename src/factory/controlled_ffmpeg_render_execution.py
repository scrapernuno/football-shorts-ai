"""FOOTBALL-SHORTS-AI-0061B — controlled FFmpeg render execution gate.

Creates a one-time human render order and an auditable execution receipt. FFmpeg
runs only when the order is ready, media hashes match and execute=True is passed.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class ControlledRenderExecutionError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ControlledRenderOrder:
    schema: str
    order_id: str
    authorization_id: str
    render_package_id: str
    ordered_by: str
    order_note: str
    ffmpeg_binary: str
    ffmpeg_args: tuple[str, ...]
    output_uri: str
    expected_assets: tuple[tuple[str, str], ...]
    order_state: str
    execution_requested: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema, "order_id": self.order_id,
            "authorization_id": self.authorization_id,
            "render_package_id": self.render_package_id,
            "ordered_by": self.ordered_by, "order_note": self.order_note,
            "ffmpeg_binary": self.ffmpeg_binary, "ffmpeg_args": list(self.ffmpeg_args),
            "output_uri": self.output_uri,
            "expected_assets": [list(item) for item in self.expected_assets],
            "order_state": self.order_state,
            "execution_requested": self.execution_requested,
            "blockers": list(self.blockers),
            "network_enabled": False, "acquisition_enabled": False, "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-render-order.v1":
            raise ControlledRenderExecutionError("unsupported render order schema")
        if not self.order_id.startswith("RENDERORDER-"):
            raise ControlledRenderExecutionError("invalid render order identity")
        if not self.authorization_id.startswith("RENDERAUTH-") or not self.render_package_id.startswith("RENDERPKG-"):
            raise ControlledRenderExecutionError("invalid authority identity")
        if self.order_state not in {"ready", "blocked"}:
            raise ControlledRenderExecutionError("unsupported render order state")
        if self.order_state == "ready" and self.blockers:
            raise ControlledRenderExecutionError("ready order cannot contain blockers")
        if self.order_state == "blocked" and not self.blockers:
            raise ControlledRenderExecutionError("blocked order requires blockers")
        if not self.ffmpeg_args or self.ffmpeg_args[0] != "-hide_banner":
            raise ControlledRenderExecutionError("unexpected ffmpeg argument contract")
        if "-nostdin" not in self.ffmpeg_args or "-y" not in self.ffmpeg_args:
            raise ControlledRenderExecutionError("mandatory ffmpeg safety arguments missing")
        if any((self.network_enabled, self.acquisition_enabled, self.auto_publish)):
            raise ControlledRenderExecutionError("0061B cannot enable unrelated capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledRenderExecutionError("render order evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


@dataclass(frozen=True)
class ControlledRenderReceipt:
    schema: str
    receipt_id: str
    order_id: str
    execution_state: str
    return_code: int | None
    output_uri: str
    output_sha256: str
    stderr_tail: str
    blockers: tuple[str, ...]
    evidence_sha256: str

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema, "receipt_id": self.receipt_id,
            "order_id": self.order_id, "execution_state": self.execution_state,
            "return_code": self.return_code, "output_uri": self.output_uri,
            "output_sha256": self.output_sha256, "stderr_tail": self.stderr_tail,
            "blockers": list(self.blockers),
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-render-receipt.v1":
            raise ControlledRenderExecutionError("unsupported receipt schema")
        if not self.receipt_id.startswith("RENDERRECEIPT-"):
            raise ControlledRenderExecutionError("invalid receipt identity")
        if self.execution_state not in {"not_executed", "rendered", "failed", "blocked"}:
            raise ControlledRenderExecutionError("unsupported execution state")
        if self.execution_state == "rendered" and (self.return_code != 0 or len(self.output_sha256) != 64):
            raise ControlledRenderExecutionError("rendered receipt requires successful output")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledRenderExecutionError("render receipt evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_render_order(
    *, authorization: Mapping[str, object], render_package: Mapping[str, object],
    ordered_by: str, order_note: str, execution_requested: bool,
) -> ControlledRenderOrder:
    blockers: set[str] = set()
    authorization_id = str(authorization.get("authorization_id", ""))
    render_package_id = str(render_package.get("render_package_id", ""))
    if authorization.get("authorization_state") != "authorized": blockers.add("RENDER_AUTHORIZATION_NOT_GRANTED")
    if str(authorization.get("render_package_id", "")) != render_package_id: blockers.add("AUTHORIZATION_RENDER_PACKAGE_MISMATCH")
    if render_package.get("package_state") != "ready_for_authorization": blockers.add("RENDER_PACKAGE_NOT_READY")
    if not ordered_by.strip(): blockers.add("HUMAN_RENDER_OPERATOR_REQUIRED")
    if not order_note.strip(): blockers.add("HUMAN_RENDER_ORDER_NOTE_REQUIRED")
    if not execution_requested: blockers.add("EXPLICIT_EXECUTION_REQUEST_REQUIRED")

    expected_assets: list[tuple[str, str]] = []
    assets = authorization.get("assets", [])
    if not isinstance(assets, Sequence) or isinstance(assets, (str, bytes)) or not assets:
        blockers.add("AUTHORIZED_MEDIA_MISSING")
    else:
        for asset in assets:
            if not isinstance(asset, Mapping) or asset.get("intake_allowed") is not True:
                blockers.add("AUTHORIZED_MEDIA_INVALID"); continue
            uri, sha = str(asset.get("local_uri", "")), str(asset.get("sha256", "")).lower()
            if not uri or len(sha) != 64: blockers.add("AUTHORIZED_MEDIA_INVALID")
            expected_assets.append((uri, sha))

    design = render_package.get("ffmpeg_design", {})
    if not isinstance(design, Mapping):
        design = {}; blockers.add("FFMPEG_DESIGN_MISSING")
    executable = str(design.get("executable", ""))
    raw_args = design.get("arguments", [])
    output_uri = str(design.get("output_uri", ""))
    if executable != "ffmpeg": blockers.add("FFMPEG_EXECUTABLE_INVALID")
    if design.get("execution_enabled") is not False: blockers.add("FFMPEG_DESIGN_NOT_INERT")
    if not isinstance(raw_args, Sequence) or isinstance(raw_args, (str, bytes)):
        blockers.add("FFMPEG_ARGUMENTS_MISSING"); ffmpeg_args: tuple[str, ...] = ()
    else:
        ffmpeg_args = tuple(str(item) for item in raw_args)
    if not output_uri: blockers.add("RENDER_OUTPUT_URI_MISSING")

    state = "blocked" if blockers else "ready"
    core = {
        "schema": "football-shorts-ai.controlled-render-order.v1",
        "authorization_id": authorization_id, "render_package_id": render_package_id,
        "ordered_by": ordered_by.strip(), "order_note": order_note.strip(),
        "ffmpeg_binary": executable or "ffmpeg", "ffmpeg_args": list(ffmpeg_args),
        "output_uri": output_uri, "expected_assets": [list(item) for item in sorted(expected_assets)],
        "order_state": state, "execution_requested": bool(execution_requested),
        "blockers": sorted(blockers), "network_enabled": False,
        "acquisition_enabled": False, "auto_publish": False,
    }
    order_id = f"RENDERORDER-{canonical_sha256(core)[:20].upper()}"
    result = ControlledRenderOrder(
        schema=core["schema"], order_id=order_id, authorization_id=authorization_id,
        render_package_id=render_package_id, ordered_by=ordered_by.strip(),
        order_note=order_note.strip(), ffmpeg_binary=core["ffmpeg_binary"],
        ffmpeg_args=ffmpeg_args, output_uri=output_uri,
        expected_assets=tuple(sorted(expected_assets)), order_state=state,
        execution_requested=bool(execution_requested), blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256({**core, "order_id": order_id}),
    )
    result.validate(); return result


def execute_controlled_render(
    order: ControlledRenderOrder, *, execute: bool = False,
    cwd: str | os.PathLike[str] | None = None, timeout_seconds: int = 300,
) -> ControlledRenderReceipt:
    order.validate()
    blockers: set[str] = set()
    if order.order_state != "ready": blockers.add("RENDER_ORDER_NOT_READY")
    if not execute: blockers.add("EXECUTION_FLAG_NOT_ENABLED")
    root = Path(cwd or ".")
    for uri, expected_sha in order.expected_assets:
        path = root / uri
        if not path.is_file(): blockers.add("AUTHORIZED_MEDIA_FILE_MISSING")
        elif file_sha256(path) != expected_sha: blockers.add("AUTHORIZED_MEDIA_HASH_MISMATCH")
    output_path = root / order.output_uri
    if blockers:
        state = "not_executed" if blockers == {"EXECUTION_FLAG_NOT_ENABLED"} else "blocked"
        return _receipt(order, state, None, output_path, "", blockers)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [order.ffmpeg_binary, *order.ffmpeg_args], cwd=cwd,
            capture_output=True, text=True, timeout=timeout_seconds, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _receipt(order, "failed", None, output_path, str(exc)[-2000:], {"FFMPEG_EXECUTION_FAILED"})
    stderr_tail = completed.stderr[-4000:]
    if completed.returncode != 0 or not output_path.is_file():
        return _receipt(order, "failed", completed.returncode, output_path, stderr_tail, {"FFMPEG_RENDER_FAILED"})
    return _receipt(order, "rendered", 0, output_path, stderr_tail, set())


def _receipt(order: ControlledRenderOrder, state: str, return_code: int | None,
             output_path: Path, stderr_tail: str, blockers: set[str]) -> ControlledRenderReceipt:
    output_sha = file_sha256(output_path) if state == "rendered" and output_path.is_file() else ""
    core = {
        "schema": "football-shorts-ai.controlled-render-receipt.v1",
        "order_id": order.order_id, "execution_state": state,
        "return_code": return_code, "output_uri": order.output_uri,
        "output_sha256": output_sha, "stderr_tail": stderr_tail,
        "blockers": sorted(blockers),
    }
    receipt_id = f"RENDERRECEIPT-{canonical_sha256(core)[:20].upper()}"
    result = ControlledRenderReceipt(
        schema=core["schema"], receipt_id=receipt_id, order_id=order.order_id,
        execution_state=state, return_code=return_code, output_uri=order.output_uri,
        output_sha256=output_sha, stderr_tail=stderr_tail,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256({**core, "receipt_id": receipt_id}),
    )
    result.validate(); return result


__all__ = ["ControlledRenderExecutionError", "ControlledRenderOrder", "ControlledRenderReceipt",
           "build_controlled_render_order", "canonical_sha256", "execute_controlled_render", "file_sha256"]
