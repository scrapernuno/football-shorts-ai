"""FOOTBALL-SHORTS-AI-0061C — authorized media binding and render dry-run.

Validates a ready 0061B render order against local repository media without
executing FFmpeg, acquiring assets, rendering, or publishing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class RenderDryRunError(ValueError):
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
class BoundMediaAsset:
    uri: str
    expected_sha256: str
    observed_sha256: str
    exists: bool
    hash_matches: bool
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "uri": self.uri,
            "expected_sha256": self.expected_sha256,
            "observed_sha256": self.observed_sha256,
            "exists": self.exists,
            "hash_matches": self.hash_matches,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class RenderDryRunReport:
    schema: str
    dry_run_id: str
    order_id: str
    render_package_id: str
    assets: tuple[BoundMediaAsset, ...]
    ffmpeg_binary: str
    ffmpeg_args: tuple[str, ...]
    output_uri: str
    dry_run_state: str
    execution_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    ffmpeg_execution_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "dry_run_id": self.dry_run_id,
            "order_id": self.order_id,
            "render_package_id": self.render_package_id,
            "assets": [asset.to_dict() for asset in self.assets],
            "ffmpeg_binary": self.ffmpeg_binary,
            "ffmpeg_args": list(self.ffmpeg_args),
            "output_uri": self.output_uri,
            "dry_run_state": self.dry_run_state,
            "execution_allowed": self.execution_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "ffmpeg_execution_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.render-dry-run.v1":
            raise RenderDryRunError("unsupported dry-run schema")
        if not self.dry_run_id.startswith("RENDERDRYRUN-"):
            raise RenderDryRunError("invalid dry-run identity")
        if self.dry_run_state not in {"ready", "blocked"}:
            raise RenderDryRunError("unsupported dry-run state")
        if self.execution_allowed or self.ffmpeg_execution_enabled:
            raise RenderDryRunError("0061C cannot authorize or execute FFmpeg")
        if self.dry_run_state == "ready" and self.blockers:
            raise RenderDryRunError("ready dry-run cannot contain blockers")
        if self.dry_run_state == "blocked" and not self.blockers:
            raise RenderDryRunError("blocked dry-run requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.auto_publish)):
            raise RenderDryRunError("0061C cannot enable unrelated capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise RenderDryRunError("dry-run evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_render_dry_run(*, order: Mapping[str, object], root: str | Path = ".") -> RenderDryRunReport:
    blockers: set[str] = set()
    if order.get("order_state") != "ready":
        blockers.add("RENDER_ORDER_NOT_READY")
    if order.get("execution_requested") is not True:
        blockers.add("EXPLICIT_EXECUTION_REQUEST_REQUIRED")

    expected_assets = order.get("expected_assets", [])
    assets: list[BoundMediaAsset] = []
    if not isinstance(expected_assets, Sequence) or isinstance(expected_assets, (str, bytes)) or not expected_assets:
        blockers.add("EXPECTED_MEDIA_MISSING")
    else:
        for item in expected_assets:
            uri, expected = str(item[0]), str(item[1]).lower()
            path = Path(root) / uri
            exists = path.is_file()
            observed = file_sha256(path) if exists else ""
            local_blockers: set[str] = set()
            if not exists:
                local_blockers.add("AUTHORIZED_MEDIA_FILE_MISSING")
            elif observed != expected:
                local_blockers.add("AUTHORIZED_MEDIA_HASH_MISMATCH")
            blockers.update(local_blockers)
            assets.append(BoundMediaAsset(uri, expected, observed, exists, exists and observed == expected, tuple(sorted(local_blockers))))

    ffmpeg_args = tuple(str(x) for x in order.get("ffmpeg_args", []))
    if not ffmpeg_args or ffmpeg_args[0] != "-hide_banner" or "-nostdin" not in ffmpeg_args:
        blockers.add("FFMPEG_ARGUMENT_CONTRACT_INVALID")
    output_uri = str(order.get("output_uri", ""))
    if not output_uri:
        blockers.add("RENDER_OUTPUT_URI_MISSING")

    core = {
        "schema": "football-shorts-ai.render-dry-run.v1",
        "order_id": str(order.get("order_id", "")),
        "render_package_id": str(order.get("render_package_id", "")),
        "assets": [asset.to_dict() for asset in assets],
        "ffmpeg_binary": str(order.get("ffmpeg_binary", "ffmpeg")),
        "ffmpeg_args": list(ffmpeg_args),
        "output_uri": output_uri,
        "dry_run_state": "blocked" if blockers else "ready",
        "execution_allowed": False,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "ffmpeg_execution_enabled": False,
        "auto_publish": False,
    }
    dry_run_id = f"RENDERDRYRUN-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "dry_run_id": dry_run_id}
    report = RenderDryRunReport(
        schema=core["schema"], dry_run_id=dry_run_id,
        order_id=core["order_id"], render_package_id=core["render_package_id"],
        assets=tuple(assets), ffmpeg_binary=core["ffmpeg_binary"], ffmpeg_args=ffmpeg_args,
        output_uri=output_uri, dry_run_state=core["dry_run_state"], execution_allowed=False,
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    report.validate()
    return report


__all__ = ["BoundMediaAsset", "RenderDryRunError", "RenderDryRunReport", "build_render_dry_run", "canonical_sha256", "file_sha256"]
