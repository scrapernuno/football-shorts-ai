"""
FOOTBALL-SHORTS-AI-0055E
LIVE YOUTUBE DISCOVERY AND DASHBOARD PUBLICATION CERTIFICATION

Validates a synchronized Football Library and, optionally, its public GitHub
Pages representation. Certification is metadata-only and never downloads,
acquires, renders or republishes provider media.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping


class LiveYouTubeDashboardCertificationError(RuntimeError):
    """Raised when live discovery publication evidence is invalid."""


OpenUrl = Callable[..., object]


@dataclass(frozen=True)
class LiveYouTubeDashboardCertification:
    schema: str
    status: str
    asset_count: int
    youtube_asset_count: int
    public_verification_enabled: bool
    public_verified: bool
    library_sha256: str
    public_library_sha256: str | None
    blockers: tuple[str, ...]
    evidence_sha256: str
    metadata_only: bool = True
    download_enabled: bool = False
    acquisition_enabled: bool = False
    render_enabled: bool = False
    publishing_enabled: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.live-youtube-dashboard-certification.v1":
            raise LiveYouTubeDashboardCertificationError("unsupported certification schema")
        if self.status not in {"LIVE_CERTIFIED", "LOCAL_CERTIFIED", "BLOCKED"}:
            raise LiveYouTubeDashboardCertificationError("unsupported certification status")
        if self.asset_count < 1 or self.youtube_asset_count < 1:
            raise LiveYouTubeDashboardCertificationError("certification requires YouTube assets")
        if self.youtube_asset_count > self.asset_count:
            raise LiveYouTubeDashboardCertificationError("YouTube count exceeds asset count")
        if self.status == "LIVE_CERTIFIED" and not self.public_verified:
            raise LiveYouTubeDashboardCertificationError("live certification requires public verification")
        if self.status == "LOCAL_CERTIFIED" and self.public_verification_enabled:
            raise LiveYouTubeDashboardCertificationError("local certification cannot request public verification")
        if self.status == "BLOCKED" and not self.blockers:
            raise LiveYouTubeDashboardCertificationError("blocked certification requires blockers")
        if self.status != "BLOCKED" and self.blockers:
            raise LiveYouTubeDashboardCertificationError("successful certification cannot contain blockers")
        for value in (self.library_sha256, self.evidence_sha256):
            _require_sha256(value)
        if self.public_library_sha256 is not None:
            _require_sha256(self.public_library_sha256)
        if self.public_verified and self.public_library_sha256 != self.library_sha256:
            raise LiveYouTubeDashboardCertificationError("public library differs from local library")
        if not self.metadata_only or any((
            self.download_enabled,
            self.acquisition_enabled,
            self.render_enabled,
            self.publishing_enabled,
        )):
            raise LiveYouTubeDashboardCertificationError("unsafe media capability detected")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise LiveYouTubeDashboardCertificationError("certification evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "status": self.status,
            "asset_count": self.asset_count,
            "youtube_asset_count": self.youtube_asset_count,
            "public_verification_enabled": self.public_verification_enabled,
            "public_verified": self.public_verified,
            "library_sha256": self.library_sha256,
            "public_library_sha256": self.public_library_sha256,
            "blockers": list(self.blockers),
            "metadata_only": True,
            "download_enabled": False,
            "acquisition_enabled": False,
            "render_enabled": False,
            "publishing_enabled": False,
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def certify_live_youtube_dashboard(
    *,
    library_path: str | Path,
    public_library_url: str | None = None,
    minimum_assets: int = 1,
    open_url: OpenUrl = urllib.request.urlopen,
) -> LiveYouTubeDashboardCertification:
    if minimum_assets < 1:
        raise LiveYouTubeDashboardCertificationError("minimum_assets must be positive")

    local_bytes = Path(library_path).read_bytes()
    local_payload = _load_library(local_bytes)
    assets = _assets(local_payload)
    youtube_assets = [asset for asset in assets if asset.get("provider") == "youtube"]
    _validate_assets(assets, youtube_assets, minimum_assets)

    local_sha = hashlib.sha256(local_bytes).hexdigest()
    public_enabled = bool(public_library_url and public_library_url.strip())
    public_verified = False
    public_sha: str | None = None
    blockers: tuple[str, ...] = ()

    if public_enabled:
        try:
            with open_url(public_library_url, timeout=20) as response:
                status = int(getattr(response, "status", 200))
                public_bytes = response.read()
            if status != 200:
                raise LiveYouTubeDashboardCertificationError(
                    f"public library returned HTTP {status}"
                )
            public_payload = _load_library(public_bytes)
            public_assets = _assets(public_payload)
            _validate_assets(
                public_assets,
                [asset for asset in public_assets if asset.get("provider") == "youtube"],
                minimum_assets,
            )
            public_sha = hashlib.sha256(public_bytes).hexdigest()
            public_verified = public_sha == local_sha
            if not public_verified:
                blockers = ("PUBLIC_LIBRARY_SHA256_MISMATCH",)
        except (OSError, ValueError, LiveYouTubeDashboardCertificationError):
            blockers = ("PUBLIC_LIBRARY_VERIFICATION_FAILED",)

    status = (
        "BLOCKED"
        if blockers
        else "LIVE_CERTIFIED"
        if public_enabled and public_verified
        else "LOCAL_CERTIFIED"
    )
    unsigned = {
        "schema": "football-shorts-ai.live-youtube-dashboard-certification.v1",
        "status": status,
        "asset_count": len(assets),
        "youtube_asset_count": len(youtube_assets),
        "public_verification_enabled": public_enabled,
        "public_verified": public_verified,
        "library_sha256": local_sha,
        "public_library_sha256": public_sha,
        "blockers": list(blockers),
        "metadata_only": True,
        "download_enabled": False,
        "acquisition_enabled": False,
        "render_enabled": False,
        "publishing_enabled": False,
    }
    result = LiveYouTubeDashboardCertification(
        evidence_sha256=canonical_sha256(unsigned),
        blockers=blockers,
        **{key: value for key, value in unsigned.items() if key != "blockers"},
    )
    result.validate()
    return result


def _load_library(payload: bytes) -> Mapping[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveYouTubeDashboardCertificationError("library is not valid UTF-8 JSON") from exc
    if not isinstance(value, Mapping):
        raise LiveYouTubeDashboardCertificationError("library root must be an object")
    return value


def _assets(payload: Mapping[str, object]) -> list[Mapping[str, object]]:
    library = payload.get("library")
    if not isinstance(library, Mapping):
        raise LiveYouTubeDashboardCertificationError("library object is missing")
    assets = library.get("assets")
    if not isinstance(assets, list) or any(not isinstance(item, Mapping) for item in assets):
        raise LiveYouTubeDashboardCertificationError("library assets are invalid")
    return list(assets)


def _validate_assets(
    assets: list[Mapping[str, object]],
    youtube_assets: list[Mapping[str, object]],
    minimum_assets: int,
) -> None:
    if len(assets) < minimum_assets or len(youtube_assets) < minimum_assets:
        raise LiveYouTubeDashboardCertificationError("minimum YouTube asset count not met")
    for asset in youtube_assets:
        if asset.get("rights_status") != "reference_only":
            raise LiveYouTubeDashboardCertificationError("YouTube asset must be reference-only")
        if asset.get("preview_allowed") is not True:
            raise LiveYouTubeDashboardCertificationError("YouTube preview must be allowed")
        if asset.get("render_allowed") is not False:
            raise LiveYouTubeDashboardCertificationError("YouTube rendering must be blocked")
        if asset.get("acquisition_allowed") is not False:
            raise LiveYouTubeDashboardCertificationError("YouTube acquisition must be blocked")


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _require_sha256(value: str) -> None:
    if len(value) != 64:
        raise LiveYouTubeDashboardCertificationError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise LiveYouTubeDashboardCertificationError("evidence must be hexadecimal") from exc


__all__ = [
    "LiveYouTubeDashboardCertification",
    "LiveYouTubeDashboardCertificationError",
    "certify_live_youtube_dashboard",
    "canonical_sha256",
]
