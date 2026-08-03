"""
FOOTBALL-SHORTS-AI-0055A
REAL YOUTUBE DISCOVERY PROVIDER AND DASHBOARD LIBRARY ACTIVATION

Provider-neutral YouTube Data API v3 discovery adapter. Network access is only
possible through an explicitly injected client and an enabled policy. The module
retrieves metadata only; it never downloads, acquires, edits, renders or publishes
YouTube media.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Protocol, Sequence

from discovery.external_provider_contract import (
    ExternalVideoAsset,
    ProviderCapabilities,
    build_external_video_asset,
)


class YouTubeDiscoveryError(ValueError):
    """Raised when YouTube discovery is disabled or returns malformed evidence."""


class YouTubeDataApiClient(Protocol):
    def search_videos(
        self,
        *,
        query: str,
        max_results: int,
        region_code: str,
        relevance_language: str,
        video_duration: str,
        video_embeddable: bool,
        safe_search: str,
    ) -> Sequence[Mapping[str, object]]:
        ...

    def list_videos(self, *, video_ids: Sequence[str]) -> Sequence[Mapping[str, object]]:
        ...


@dataclass(frozen=True)
class YouTubeDiscoveryPolicy:
    enabled: bool = False
    network_enabled: bool = False
    metadata_only: bool = True
    max_results: int = 12
    region_code: str = "PT"
    relevance_language: str = "pt"
    video_duration: str = "short"
    safe_search: str = "moderate"

    def validate(self) -> None:
        if self.enabled and not self.network_enabled:
            raise YouTubeDiscoveryError("enabled discovery requires network_enabled")
        if not self.metadata_only:
            raise YouTubeDiscoveryError("YouTube discovery must remain metadata-only")
        if not 1 <= self.max_results <= 50:
            raise YouTubeDiscoveryError("max_results must be between 1 and 50")
        if not re.fullmatch(r"[A-Z]{2}", self.region_code):
            raise YouTubeDiscoveryError("region_code must be ISO alpha-2 uppercase")
        if not self.relevance_language.strip():
            raise YouTubeDiscoveryError("relevance_language is required")
        if self.video_duration not in {"any", "short", "medium", "long"}:
            raise YouTubeDiscoveryError("unsupported video_duration")
        if self.safe_search not in {"none", "moderate", "strict"}:
            raise YouTubeDiscoveryError("unsupported safe_search")


@dataclass(frozen=True)
class YouTubeDiscoveryResult:
    status: str
    query: str
    assets: tuple[ExternalVideoAsset, ...]
    blockers: tuple[str, ...]
    network_used: bool
    acquisition_enabled: bool = False
    download_enabled: bool = False
    auto_publish: bool = False

    def validate(self) -> None:
        if self.status not in {"DISCOVERED", "NOT_ACTIVATED", "BLOCKED"}:
            raise YouTubeDiscoveryError("unsupported discovery status")
        if self.status == "DISCOVERED" and (self.blockers or not self.assets):
            raise YouTubeDiscoveryError("discovered result requires assets and no blockers")
        if self.status in {"NOT_ACTIVATED", "BLOCKED"} and not self.blockers:
            raise YouTubeDiscoveryError("non-success result requires blockers")
        for asset in self.assets:
            asset.validate()
            if asset.provider != "youtube" or asset.rights_status != "reference_only":
                raise YouTubeDiscoveryError("YouTube discovery assets must be reference-only")
        if self.acquisition_enabled or self.download_enabled or self.auto_publish:
            raise YouTubeDiscoveryError("automatic media operations are forbidden")


class YouTubeDiscoveryProvider:
    provider_name = "youtube"
    capabilities = ProviderCapabilities(
        supports_embed=True,
        supports_thumbnail=True,
        supports_metadata=True,
        supports_preview=True,
        supports_manual_import=True,
        supports_direct_acquisition=False,
    )

    def __init__(self, *, client: YouTubeDataApiClient, policy: YouTubeDiscoveryPolicy) -> None:
        self._client = client
        self._policy = policy
        policy.validate()

    def discover(self, query: str, *, discovered_at: str | None = None) -> YouTubeDiscoveryResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise YouTubeDiscoveryError("query is required")
        if not self._policy.enabled:
            result = YouTubeDiscoveryResult(
                status="NOT_ACTIVATED",
                query=normalized_query,
                assets=(),
                blockers=("YOUTUBE_DISCOVERY_NOT_ACTIVATED",),
                network_used=False,
            )
            result.validate()
            return result

        search_items = tuple(
            self._client.search_videos(
                query=normalized_query,
                max_results=self._policy.max_results,
                region_code=self._policy.region_code,
                relevance_language=self._policy.relevance_language,
                video_duration=self._policy.video_duration,
                video_embeddable=True,
                safe_search=self._policy.safe_search,
            )
        )
        ids = tuple(_video_id(item) for item in search_items)
        ids = tuple(dict.fromkeys(value for value in ids if value))
        if not ids:
            result = YouTubeDiscoveryResult(
                status="BLOCKED",
                query=normalized_query,
                assets=(),
                blockers=("YOUTUBE_SEARCH_RETURNED_NO_VIDEO_IDS",),
                network_used=True,
            )
            result.validate()
            return result

        detail_items = tuple(self._client.list_videos(video_ids=ids))
        details = {_video_id(item): item for item in detail_items if _video_id(item)}
        timestamp = discovered_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        assets = tuple(
            self.normalize(details[video_id], discovered_at=timestamp)
            for video_id in ids
            if video_id in details
        )
        if not assets:
            result = YouTubeDiscoveryResult(
                status="BLOCKED",
                query=normalized_query,
                assets=(),
                blockers=("YOUTUBE_VIDEO_DETAILS_UNAVAILABLE",),
                network_used=True,
            )
            result.validate()
            return result

        result = YouTubeDiscoveryResult(
            status="DISCOVERED",
            query=normalized_query,
            assets=assets,
            blockers=(),
            network_used=True,
        )
        result.validate()
        return result

    def normalize(self, payload: Mapping[str, object], *, discovered_at: str) -> ExternalVideoAsset:
        video_id = _video_id(payload)
        snippet = _mapping(payload.get("snippet"), "snippet")
        statistics = payload.get("statistics")
        content_details = payload.get("contentDetails")
        statistics_map = statistics if isinstance(statistics, Mapping) else {}
        content_map = content_details if isinstance(content_details, Mapping) else {}
        thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), Mapping) else {}
        thumbnail = _best_thumbnail(thumbnails)
        duration = _parse_iso8601_duration(str(content_map.get("duration", "")))
        title = _text(snippet, "title")
        channel_title = _text(snippet, "channelTitle")
        published_at = _optional_text(snippet.get("publishedAt"))
        tags_value = snippet.get("tags")
        tags = tuple(str(value).strip() for value in tags_value if str(value).strip()) if isinstance(tags_value, list) else ()

        return build_external_video_asset(
            provider="youtube",
            provider_asset_id=video_id,
            provider_url=f"https://www.youtube.com/watch?v={video_id}",
            embed_url=f"https://www.youtube.com/embed/{video_id}",
            thumbnail_url=thumbnail,
            title=title,
            description=str(snippet.get("description", "")),
            channel_name=channel_title,
            channel_id=_optional_text(snippet.get("channelId")),
            capabilities=self.capabilities,
            discovered_at=discovered_at,
            published_at=published_at,
            duration_seconds=duration,
            views=_optional_int(statistics_map.get("viewCount")),
            likes=_optional_int(statistics_map.get("likeCount")),
            language=_optional_text(snippet.get("defaultLanguage")),
            tags=tags,
            source_metadata=payload,
            rights_status="reference_only",
            library_state="discovered",
        )


def _video_id(payload: Mapping[str, object]) -> str:
    direct = payload.get("id")
    if isinstance(direct, str):
        return direct.strip()
    if isinstance(direct, Mapping):
        value = direct.get("videoId")
        if isinstance(value, str):
            return value.strip()
    return ""


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise YouTubeDiscoveryError(f"{name} must be an object")
    return value


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise YouTubeDiscoveryError(f"{key} is required")
    return value.strip()


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except ValueError as exc:
        raise YouTubeDiscoveryError("invalid YouTube statistic") from exc
    if parsed < 0:
        raise YouTubeDiscoveryError("YouTube statistic cannot be negative")
    return parsed


def _best_thumbnail(payload: Mapping[str, object]) -> str | None:
    for key in ("maxres", "standard", "high", "medium", "default"):
        candidate = payload.get(key)
        if isinstance(candidate, Mapping):
            url = candidate.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()
    return None


def _parse_iso8601_duration(value: str) -> float | None:
    if not value:
        return None
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", value)
    if not match:
        raise YouTubeDiscoveryError("invalid YouTube ISO-8601 duration")
    hours, minutes, seconds = match.groups()
    return float(hours or 0) * 3600 + float(minutes or 0) * 60 + float(seconds or 0)


__all__ = [
    "YouTubeDataApiClient",
    "YouTubeDiscoveryError",
    "YouTubeDiscoveryPolicy",
    "YouTubeDiscoveryProvider",
    "YouTubeDiscoveryResult",
]
