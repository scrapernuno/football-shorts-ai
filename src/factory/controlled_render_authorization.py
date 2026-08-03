"""FOOTBALL-SHORTS-AI-0061A — controlled render authorization and media intake.

Creates a deterministic authorization package for a previously certified 0060I
render package. It does not execute FFmpeg, render media, download sources or
publish content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class RenderAuthorizationError(ValueError):
    pass


SUPPORTED_MEDIA_KINDS = {"video", "voiceover", "music", "ambience", "sfx", "thumbnail"}
SUPPORTED_RIGHTS = {"owned", "licensed", "reference_only"}
SUPPORTED_STATES = {"authorized", "review_required", "blocked"}


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AuthorizedMediaAsset:
    asset_id: str
    kind: str
    local_uri: str
    sha256: str
    rights_status: str
    rights_reference: str
    owner_confirmation: bool
    intake_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.asset_id.startswith("AUTHMEDIA-"):
            raise RenderAuthorizationError("invalid media identity")
        if self.kind not in SUPPORTED_MEDIA_KINDS:
            raise RenderAuthorizationError("unsupported media kind")
        if self.rights_status not in SUPPORTED_RIGHTS:
            raise RenderAuthorizationError("unsupported rights status")
        if self.sha256 and (len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256)):
            raise RenderAuthorizationError("invalid media sha256")
        if self.rights_status == "reference_only" and self.intake_allowed:
            raise RenderAuthorizationError("reference-only media cannot be authorized")
        if self.intake_allowed and (not self.local_uri or not self.sha256 or not self.owner_confirmation or self.blockers):
            raise RenderAuthorizationError("authorized media must be complete and unblocked")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise RenderAuthorizationError("blockers must be normalized")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "asset_id": self.asset_id,
            "kind": self.kind,
            "local_uri": self.local_uri,
            "sha256": self.sha256,
            "rights_status": self.rights_status,
            "rights_reference": self.rights_reference,
            "owner_confirmation": self.owner_confirmation,
            "intake_allowed": self.intake_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ControlledRenderAuthorization:
    schema: str
    authorization_id: str
    render_package_id: str
    reviewer: str
    authorization_note: str
    assets: tuple[AuthorizedMediaAsset, ...]
    authorization_state: str
    render_execution_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    ffmpeg_execution_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authorization_id": self.authorization_id,
            "render_package_id": self.render_package_id,
            "reviewer": self.reviewer,
            "authorization_note": self.authorization_note,
            "assets": [asset.to_dict() for asset in self.assets],
            "authorization_state": self.authorization_state,
            "render_execution_allowed": self.render_execution_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "ffmpeg_execution_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-render-authorization.v1":
            raise RenderAuthorizationError("unsupported authorization schema")
        if not self.authorization_id.startswith("RENDERAUTH-"):
            raise RenderAuthorizationError("invalid authorization identity")
        if not self.render_package_id.startswith("RENDERPKG-"):
            raise RenderAuthorizationError("invalid render package identity")
        if self.authorization_state not in SUPPORTED_STATES:
            raise RenderAuthorizationError("unsupported authorization state")
        for asset in self.assets:
            asset.validate()
        if self.render_execution_allowed:
            raise RenderAuthorizationError("0061A cannot enable render execution")
        if self.authorization_state == "authorized" and (self.blockers or not self.assets or any(not a.intake_allowed for a in self.assets)):
            raise RenderAuthorizationError("authorized state requires complete authorized assets")
        if self.authorization_state != "authorized" and not self.blockers:
            raise RenderAuthorizationError("non-authorized state requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled, self.ffmpeg_execution_enabled, self.auto_publish)):
            raise RenderAuthorizationError("0061A cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise RenderAuthorizationError("authorization evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_render_authorization(
    *,
    render_package: Mapping[str, object],
    reviewer: str,
    authorization_note: str,
    media_inputs: Sequence[Mapping[str, object]],
) -> ControlledRenderAuthorization:
    blockers: set[str] = set()
    render_package_id = str(render_package.get("render_package_id", ""))
    if not render_package_id.startswith("RENDERPKG-"):
        blockers.add("RENDER_PACKAGE_ID_INVALID")
    if render_package.get("package_state") != "ready_for_authorization":
        blockers.add("RENDER_PACKAGE_NOT_READY")
    if not reviewer.strip():
        blockers.add("HUMAN_REVIEWER_REQUIRED")
    if not authorization_note.strip():
        blockers.add("AUTHORIZATION_NOTE_REQUIRED")

    assets: list[AuthorizedMediaAsset] = []
    for raw in media_inputs:
        asset_blockers: set[str] = set()
        kind = str(raw.get("kind", ""))
        local_uri = str(raw.get("local_uri", ""))
        sha256 = str(raw.get("sha256", "")).lower()
        rights = str(raw.get("rights_status", "reference_only"))
        rights_reference = str(raw.get("rights_reference", ""))
        owner_confirmation = bool(raw.get("owner_confirmation", False))
        if kind not in SUPPORTED_MEDIA_KINDS:
            asset_blockers.add("MEDIA_KIND_UNSUPPORTED")
        if not local_uri:
            asset_blockers.add("MEDIA_LOCAL_URI_MISSING")
        if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            asset_blockers.add("MEDIA_SHA256_MISSING_OR_INVALID")
        if rights == "reference_only":
            asset_blockers.add("MEDIA_NOT_AUTHORIZED")
        if rights not in SUPPORTED_RIGHTS:
            asset_blockers.add("MEDIA_RIGHTS_STATUS_INVALID")
        if not rights_reference:
            asset_blockers.add("MEDIA_RIGHTS_REFERENCE_MISSING")
        if not owner_confirmation:
            asset_blockers.add("MEDIA_OWNER_CONFIRMATION_MISSING")
        core = {
            "kind": kind,
            "local_uri": local_uri,
            "sha256": sha256,
            "rights_status": rights,
            "rights_reference": rights_reference,
            "owner_confirmation": owner_confirmation,
            "intake_allowed": not asset_blockers,
            "blockers": tuple(sorted(asset_blockers)),
        }
        asset = AuthorizedMediaAsset(
            asset_id=f"AUTHMEDIA-{canonical_sha256(core)[:20].upper()}",
            **core,
        )
        asset.validate()
        assets.append(asset)

    if not assets:
        blockers.add("AUTHORIZED_MEDIA_MISSING")
    if any(asset.blockers for asset in assets):
        blockers.add("MEDIA_INTAKE_REVIEW_REQUIRED")

    state = "blocked" if "RENDER_PACKAGE_NOT_READY" in blockers or not assets else "review_required" if blockers else "authorized"
    core = {
        "schema": "football-shorts-ai.controlled-render-authorization.v1",
        "render_package_id": render_package_id,
        "reviewer": reviewer.strip(),
        "authorization_note": authorization_note.strip(),
        "assets": [asset.to_dict() for asset in assets],
        "authorization_state": state,
        "render_execution_allowed": False,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "ffmpeg_execution_enabled": False,
        "auto_publish": False,
    }
    authorization_id = f"RENDERAUTH-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "authorization_id": authorization_id}
    result = ControlledRenderAuthorization(
        schema=core["schema"],
        authorization_id=authorization_id,
        render_package_id=render_package_id,
        reviewer=reviewer.strip(),
        authorization_note=authorization_note.strip(),
        assets=tuple(assets),
        authorization_state=state,
        render_execution_allowed=False,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = [
    "AuthorizedMediaAsset",
    "ControlledRenderAuthorization",
    "RenderAuthorizationError",
    "build_controlled_render_authorization",
    "canonical_sha256",
]
