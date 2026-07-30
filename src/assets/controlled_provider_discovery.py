from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from assets.contracts import RightsBasis, SubjectScope
from assets.media_acquisition_runtime import AssetCandidate, RuntimeSceneRequest


class ControlledProviderDiscoveryError(RuntimeError):
    """Raised when a controlled discovery adapter cannot operate safely."""


JsonTransport = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class OwnedLibraryDiscoveryAdapter:
    catalog_path: Path
    provider_id: str = "owned_library"
    priority: int = 1

    def discover(self, request: RuntimeSceneRequest) -> Sequence[AssetCandidate]:
        payload = _load_json(self.catalog_path, "owned media catalog")
        assets = payload.get("assets")
        if not isinstance(assets, list):
            raise ControlledProviderDiscoveryError("owned media catalog assets must be a list")

        candidates: list[AssetCandidate] = []
        for index, raw in enumerate(assets):
            if not isinstance(raw, dict):
                raise ControlledProviderDiscoveryError(f"owned asset {index} must be an object")
            if raw.get("status") != "approved":
                continue
            media_type = _required_text(raw, "media_type")
            if media_type not in request.media_type_preference:
                continue
            subject_scope = SubjectScope(_required_text(raw, "subject_scope"))
            if subject_scope != request.subject_scope:
                continue
            searchable = " ".join(
                [
                    _required_text(raw, "title"),
                    " ".join(_text_list(raw.get("tags"), "tags")),
                    str(raw.get("description") or ""),
                ]
            ).casefold()
            relevance = _term_relevance(request.search_terms, searchable)
            if relevance <= 0:
                continue

            delivery_path = _required_text(raw, "delivery_path")
            evidence = _required_text(raw, "ownership_evidence")
            candidates.append(
                AssetCandidate(
                    provider_id=self.provider_id,
                    provider_asset_id=_required_text(raw, "asset_id"),
                    media_type=media_type,
                    subject_scope=subject_scope,
                    title=_required_text(raw, "title"),
                    source_url=_required_text(raw, "source_reference"),
                    preview_url=_optional_text(raw.get("preview_path")),
                    delivery_url=delivery_path,
                    duration_seconds=_optional_positive_number(raw.get("duration_seconds")),
                    width=_optional_positive_int(raw.get("width")),
                    height=_optional_positive_int(raw.get("height")),
                    rights_basis=RightsBasis.OWNED,
                    rights_status="approved",
                    license_reference=evidence,
                    creator_reference=_optional_text(raw.get("creator_reference")),
                    attribution_text=_optional_text(raw.get("attribution_text")),
                    watermark_present=bool(raw.get("watermark_present", False)),
                    cross_platform_allowed=raw.get("cross_platform_allowed") is True,
                    original_file_available=Path(delivery_path).is_file(),
                    relevance_score=relevance,
                    quality_score=_bounded_score(raw.get("quality_score"), "quality_score"),
                    freshness_score=_bounded_score(raw.get("freshness_score", 0.5), "freshness_score"),
                    provider_priority=self.priority,
                    metadata={"catalog_path": self.catalog_path.as_posix()},
                )
            )
        return tuple(candidates)


@dataclass(frozen=True, slots=True)
class PexelsDiscoveryAdapter:
    api_key: str
    transport: JsonTransport
    provider_id: str = "pexels"
    priority: int = 5
    per_page: int = 15

    def discover(self, request: RuntimeSceneRequest) -> Sequence[AssetCandidate]:
        if request.subject_scope != SubjectScope.GENERIC_FOOTBALL:
            return ()
        if "video" not in request.media_type_preference:
            return ()
        key = self.api_key.strip()
        if not key:
            raise ControlledProviderDiscoveryError("PEXELS_API_KEY is not configured")

        query = request.search_terms[0] if request.search_terms else request.visual_instruction
        url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
            {"query": query, "orientation": "portrait", "per_page": self.per_page}
        )
        payload = self.transport(url, {"Authorization": key})
        videos = payload.get("videos")
        if not isinstance(videos, list):
            raise ControlledProviderDiscoveryError("Pexels response videos must be a list")

        candidates: list[AssetCandidate] = []
        for raw in videos:
            if not isinstance(raw, dict):
                continue
            files = raw.get("video_files")
            if not isinstance(files, list):
                continue
            selected = _select_pexels_file(files)
            if selected is None:
                continue
            user = raw.get("user") if isinstance(raw.get("user"), dict) else {}
            width = _optional_positive_int(selected.get("width"))
            height = _optional_positive_int(selected.get("height"))
            title = f"Pexels football video {raw.get('id')}"
            searchable = f"{title} {query}".casefold()
            candidates.append(
                AssetCandidate(
                    provider_id=self.provider_id,
                    provider_asset_id=str(raw.get("id")),
                    media_type="video",
                    subject_scope=SubjectScope.GENERIC_FOOTBALL,
                    title=title,
                    source_url=_required_text(raw, "url"),
                    preview_url=_optional_text(raw.get("image")),
                    delivery_url=_required_text(selected, "link"),
                    duration_seconds=_optional_positive_number(raw.get("duration")),
                    width=width,
                    height=height,
                    rights_basis=RightsBasis.LICENSED,
                    rights_status="approved",
                    license_reference="https://www.pexels.com/license/",
                    creator_reference=_optional_text(user.get("name")),
                    attribution_text=(
                        f"Video by {user.get('name')} on Pexels" if user.get("name") else "Video from Pexels"
                    ),
                    watermark_present=False,
                    cross_platform_allowed=True,
                    original_file_available=True,
                    relevance_score=max(0.55, _term_relevance(request.search_terms, searchable)),
                    quality_score=_quality_from_dimensions(width, height),
                    freshness_score=0.5,
                    provider_priority=self.priority,
                    metadata={
                        "pexels_user_url": user.get("url"),
                        "file_type": selected.get("file_type"),
                        "quality": selected.get("quality"),
                    },
                )
            )
        return tuple(candidates)


def build_controlled_runtime_providers(
    *,
    owned_catalog_path: Path = Path("config/owned_media_catalog.json"),
    pexels_api_key: str | None = None,
    transport: JsonTransport | None = None,
) -> tuple[object, ...]:
    providers: list[object] = []
    if owned_catalog_path.is_file():
        providers.append(OwnedLibraryDiscoveryAdapter(owned_catalog_path))
    key = pexels_api_key if pexels_api_key is not None else os.getenv("PEXELS_API_KEY", "")
    if key.strip():
        providers.append(PexelsDiscoveryAdapter(key, transport or default_json_transport))
    return tuple(providers)


def default_json_transport(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
    request = urllib.request.Request(url, headers=dict(headers), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise ControlledProviderDiscoveryError(f"provider request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ControlledProviderDiscoveryError("provider response root must be an object")
    return payload


def _select_pexels_file(files: list[Any]) -> dict[str, Any] | None:
    viable = [
        item
        for item in files
        if isinstance(item, dict)
        and item.get("file_type") == "video/mp4"
        and isinstance(item.get("link"), str)
        and item.get("link").strip()
        and isinstance(item.get("width"), int)
        and isinstance(item.get("height"), int)
        and item["height"] > item["width"]
    ]
    if not viable:
        return None
    viable.sort(key=lambda item: (-(item["width"] * item["height"]), str(item.get("id", ""))))
    return viable[0]


def _term_relevance(terms: tuple[str, ...], searchable: str) -> float:
    normalized = [term.casefold().strip() for term in terms if term.strip()]
    if not normalized:
        return 0.0
    matches = sum(1 for term in normalized if term in searchable)
    return round(matches / len(normalized), 6)


def _quality_from_dimensions(width: int | None, height: int | None) -> float:
    if not width or not height:
        return 0.4
    pixels = width * height
    if pixels >= 1080 * 1920:
        return 1.0
    if pixels >= 720 * 1280:
        return 0.8
    return 0.6


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ControlledProviderDiscoveryError(f"{label} not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ControlledProviderDiscoveryError(f"invalid {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ControlledProviderDiscoveryError(f"{label} root must be an object")
    return payload


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ControlledProviderDiscoveryError(f"{key} must be non-empty text")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ControlledProviderDiscoveryError(f"{label} must be a list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ControlledProviderDiscoveryError(f"{label} entries must be text")
        result.append(item.strip())
    return result


def _optional_positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _optional_positive_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else None


def _bounded_score(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ControlledProviderDiscoveryError(f"{label} must be numeric")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise ControlledProviderDiscoveryError(f"{label} must be between 0 and 1")
    return score
