"""
FOOTBALL-SHORTS-AI-0054A
EXTERNAL PROVIDER CONTRACT

Canonical provider-neutral contract for videos discovered from YouTube, TikTok,
Instagram, user uploads, local libraries and future sources. The contract is
metadata-only by default and does not download, acquire, transform or publish
provider media.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol, runtime_checkable
from urllib.parse import urlparse


SUPPORTED_PROVIDERS = {
    "youtube",
    "tiktok",
    "instagram",
    "user_upload",
    "local_library",
    "licensed_provider",
}

SUPPORTED_LIBRARY_STATES = {
    "discovered",
    "indexed",
    "reviewed",
    "selected",
    "in_project",
    "rendered",
    "published",
    "archived",
}

SUPPORTED_RIGHTS_STATUSES = {
    "reference_only",
    "owned",
    "licensed",
    "creative_commons",
    "public_domain",
    "user_uploaded",
    "legal_exception_reviewed",
}

RENDERABLE_RIGHTS_STATUSES = {
    "owned",
    "licensed",
    "creative_commons",
    "public_domain",
    "user_uploaded",
    "legal_exception_reviewed",
}


class ExternalProviderContractError(ValueError):
    """Raised when an external provider asset is malformed or unsafe."""


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_embed: bool
    supports_thumbnail: bool
    supports_metadata: bool
    supports_preview: bool
    supports_manual_import: bool
    supports_direct_acquisition: bool = False

    def validate(self) -> None:
        values = self.to_dict()
        if any(not isinstance(value, bool) for value in values.values()):
            raise ExternalProviderContractError(
                "provider capabilities must be boolean"
            )

    def to_dict(self) -> dict[str, bool]:
        return {
            "supports_embed": self.supports_embed,
            "supports_thumbnail": self.supports_thumbnail,
            "supports_metadata": self.supports_metadata,
            "supports_preview": self.supports_preview,
            "supports_manual_import": self.supports_manual_import,
            "supports_direct_acquisition": self.supports_direct_acquisition,
        }


@dataclass(frozen=True)
class ExternalVideoAsset:
    schema: str
    asset_id: str
    provider: str
    provider_asset_id: str
    provider_url: str
    embed_url: str | None
    title: str
    description: str
    thumbnail_url: str | None
    duration_seconds: float | None
    published_at: str | None
    channel_name: str
    channel_id: str | None
    views: int | None
    likes: int | None
    language: str | None
    competition: str | None
    teams: tuple[str, ...]
    players: tuple[str, ...]
    tags: tuple[str, ...]
    score: float
    rights_status: str
    library_state: str
    capabilities: ProviderCapabilities
    discovered_at: str
    source_metadata_sha256: str
    render_allowed: bool
    acquisition_allowed: bool
    preview_allowed: bool
    auto_acquire: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.external-video-asset.v1":
            raise ExternalProviderContractError("unsupported asset schema")
        if not self.asset_id.startswith("EXT-"):
            raise ExternalProviderContractError("asset_id must start with EXT-")
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ExternalProviderContractError("unsupported provider")
        if not self.provider_asset_id.strip():
            raise ExternalProviderContractError("provider_asset_id is required")
        _validate_http_url(self.provider_url, "provider_url")
        if self.embed_url is not None:
            _validate_http_url(self.embed_url, "embed_url")
        if self.thumbnail_url is not None:
            _validate_http_url(self.thumbnail_url, "thumbnail_url")
        if not self.title.strip():
            raise ExternalProviderContractError("title is required")
        if not self.channel_name.strip():
            raise ExternalProviderContractError("channel_name is required")
        if self.duration_seconds is not None and self.duration_seconds <= 0:
            raise ExternalProviderContractError(
                "duration_seconds must be positive when declared"
            )
        for name, value in {"views": self.views, "likes": self.likes}.items():
            if value is not None:
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ExternalProviderContractError(f"invalid {name}")
        if not 0 <= self.score <= 100:
            raise ExternalProviderContractError("score must be between 0 and 100")
        if self.rights_status not in SUPPORTED_RIGHTS_STATUSES:
            raise ExternalProviderContractError("unsupported rights_status")
        if self.library_state not in SUPPORTED_LIBRARY_STATES:
            raise ExternalProviderContractError("unsupported library_state")
        if len(set(self.tags)) != len(self.tags):
            raise ExternalProviderContractError("tags must be unique")
        if len(set(self.teams)) != len(self.teams):
            raise ExternalProviderContractError("teams must be unique")
        if len(set(self.players)) != len(self.players):
            raise ExternalProviderContractError("players must be unique")
        if any(not value.strip() for value in (*self.tags, *self.teams, *self.players)):
            raise ExternalProviderContractError("classification values cannot be empty")
        self.capabilities.validate()
        _parse_utc(self.discovered_at)
        if self.published_at is not None:
            _parse_utc(self.published_at)
        if not _is_sha256(self.source_metadata_sha256):
            raise ExternalProviderContractError(
                "source_metadata_sha256 must be SHA-256"
            )
        expected_render = self.rights_status in RENDERABLE_RIGHTS_STATUSES
        if self.render_allowed != expected_render:
            raise ExternalProviderContractError(
                "render_allowed is inconsistent with rights_status"
            )
        if self.acquisition_allowed and not expected_render:
            raise ExternalProviderContractError(
                "reference-only assets cannot be acquired"
            )
        expected_preview = self.capabilities.supports_preview or self.capabilities.supports_embed
        if self.preview_allowed != expected_preview:
            raise ExternalProviderContractError(
                "preview_allowed is inconsistent with provider capabilities"
            )
        if self.embed_url is not None and not self.capabilities.supports_embed:
            raise ExternalProviderContractError(
                "embed_url requires supports_embed"
            )
        if self.thumbnail_url is not None and not self.capabilities.supports_thumbnail:
            raise ExternalProviderContractError(
                "thumbnail_url requires supports_thumbnail"
            )
        if self.auto_acquire:
            raise ExternalProviderContractError("automatic acquisition is forbidden")
        if self.auto_publish:
            raise ExternalProviderContractError("automatic publishing is forbidden")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": self.schema,
            "asset_id": self.asset_id,
            "provider": self.provider,
            "provider_asset_id": self.provider_asset_id,
            "provider_url": self.provider_url,
            "embed_url": self.embed_url,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "published_at": self.published_at,
            "channel_name": self.channel_name,
            "channel_id": self.channel_id,
            "views": self.views,
            "likes": self.likes,
            "language": self.language,
            "competition": self.competition,
            "teams": list(self.teams),
            "players": list(self.players),
            "tags": list(self.tags),
            "score": self.score,
            "rights_status": self.rights_status,
            "library_state": self.library_state,
            "capabilities": self.capabilities.to_dict(),
            "discovered_at": self.discovered_at,
            "source_metadata_sha256": self.source_metadata_sha256,
            "render_allowed": self.render_allowed,
            "acquisition_allowed": self.acquisition_allowed,
            "preview_allowed": self.preview_allowed,
            "auto_acquire": False,
            "auto_publish": False,
        }


@runtime_checkable
class ExternalVideoProvider(Protocol):
    """Provider-neutral discovery boundary."""

    @property
    def provider_name(self) -> str:
        ...

    @property
    def capabilities(self) -> ProviderCapabilities:
        ...

    def search(self, query: str, *, limit: int) -> tuple[Mapping[str, object], ...]:
        ...

    def normalize(self, payload: Mapping[str, object]) -> ExternalVideoAsset:
        ...


def build_external_video_asset(
    *,
    provider: str,
    provider_asset_id: str,
    provider_url: str,
    title: str,
    channel_name: str,
    capabilities: ProviderCapabilities,
    discovered_at: str,
    source_metadata: Mapping[str, object],
    description: str = "",
    embed_url: str | None = None,
    thumbnail_url: str | None = None,
    duration_seconds: float | None = None,
    published_at: str | None = None,
    channel_id: str | None = None,
    views: int | None = None,
    likes: int | None = None,
    language: str | None = None,
    competition: str | None = None,
    teams: tuple[str, ...] = (),
    players: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
    score: float = 0,
    rights_status: str = "reference_only",
    library_state: str = "discovered",
) -> ExternalVideoAsset:
    """Build one deterministic, metadata-only external video asset."""

    source_metadata_sha256 = canonical_sha256(source_metadata)
    identity = {
        "provider": provider,
        "provider_asset_id": provider_asset_id,
        "source_metadata_sha256": source_metadata_sha256,
    }
    asset_id = f"EXT-{canonical_sha256(identity)[:20].upper()}"
    render_allowed = rights_status in RENDERABLE_RIGHTS_STATUSES
    acquisition_allowed = render_allowed and capabilities.supports_direct_acquisition
    preview_allowed = capabilities.supports_preview or capabilities.supports_embed

    result = ExternalVideoAsset(
        schema="football-shorts-ai.external-video-asset.v1",
        asset_id=asset_id,
        provider=provider,
        provider_asset_id=provider_asset_id,
        provider_url=provider_url,
        embed_url=embed_url,
        title=title,
        description=description,
        thumbnail_url=thumbnail_url,
        duration_seconds=duration_seconds,
        published_at=published_at,
        channel_name=channel_name,
        channel_id=channel_id,
        views=views,
        likes=likes,
        language=language,
        competition=competition,
        teams=tuple(_normalize_values(teams)),
        players=tuple(_normalize_values(players)),
        tags=tuple(_normalize_values(tags)),
        score=float(score),
        rights_status=rights_status,
        library_state=library_state,
        capabilities=capabilities,
        discovered_at=_format_utc(_parse_utc(discovered_at)),
        source_metadata_sha256=source_metadata_sha256,
        render_allowed=render_allowed,
        acquisition_allowed=acquisition_allowed,
        preview_allowed=preview_allowed,
        auto_acquire=False,
        auto_publish=False,
    )
    result.validate()
    return result


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_values(values: tuple[str, ...]) -> list[str]:
    normalized = sorted({value.strip() for value in values if value.strip()})
    return normalized


def _validate_http_url(value: str, name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ExternalProviderContractError(f"{name} must be an absolute HTTP URL")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ExternalProviderContractError("UTC timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalProviderContractError("invalid UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalProviderContractError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_sha256(value: str) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = [
    "ExternalProviderContractError",
    "ExternalVideoAsset",
    "ExternalVideoProvider",
    "ProviderCapabilities",
    "RENDERABLE_RIGHTS_STATUSES",
    "SUPPORTED_LIBRARY_STATES",
    "SUPPORTED_PROVIDERS",
    "SUPPORTED_RIGHTS_STATUSES",
    "build_external_video_asset",
    "canonical_sha256",
]
