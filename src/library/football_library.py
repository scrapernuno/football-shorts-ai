"""
FOOTBALL-SHORTS-AI-0054B
FOOTBALL LIBRARY ENGINE

Deterministic in-memory catalog for external video assets. Supports indexing,
search, filtering, sorting, state transitions, deduplication and dashboard
export. It performs no network access, media acquisition, rendering or
publication.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping

from discovery.external_provider_contract import (
    ExternalVideoAsset,
    SUPPORTED_LIBRARY_STATES,
)


class FootballLibraryError(ValueError):
    """Raised when library input or a state transition is invalid."""


ALLOWED_STATE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "discovered": frozenset({"indexed", "archived"}),
    "indexed": frozenset({"reviewed", "selected", "archived"}),
    "reviewed": frozenset({"selected", "archived"}),
    "selected": frozenset({"in_project", "reviewed", "archived"}),
    "in_project": frozenset({"rendered", "selected", "archived"}),
    "rendered": frozenset({"published", "archived"}),
    "published": frozenset({"archived"}),
    "archived": frozenset(),
}

SUPPORTED_SORTS = {
    "score_desc",
    "views_desc",
    "likes_desc",
    "published_desc",
    "discovered_desc",
    "title_asc",
}


@dataclass(frozen=True)
class LibraryQuery:
    text: str = ""
    providers: tuple[str, ...] = ()
    rights_statuses: tuple[str, ...] = ()
    library_states: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()
    players: tuple[str, ...] = ()
    competitions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    render_allowed: bool | None = None
    preview_allowed: bool | None = None
    minimum_score: float = 0.0
    sort: str = "score_desc"
    offset: int = 0
    limit: int = 50

    def validate(self) -> None:
        if self.sort not in SUPPORTED_SORTS:
            raise FootballLibraryError("unsupported sort")
        if not 0 <= self.minimum_score <= 100:
            raise FootballLibraryError("minimum_score must be between 0 and 100")
        if not isinstance(self.offset, int) or isinstance(self.offset, bool) or self.offset < 0:
            raise FootballLibraryError("offset must be a non-negative integer")
        if not isinstance(self.limit, int) or isinstance(self.limit, bool):
            raise FootballLibraryError("limit must be an integer")
        if not 1 <= self.limit <= 500:
            raise FootballLibraryError("limit must be between 1 and 500")
        if any(state not in SUPPORTED_LIBRARY_STATES for state in self.library_states):
            raise FootballLibraryError("unsupported library state filter")


@dataclass(frozen=True)
class LibrarySearchResult:
    schema: str
    query_sha256: str
    total_matches: int
    offset: int
    limit: int
    assets: tuple[ExternalVideoAsset, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "query_sha256": self.query_sha256,
            "total_matches": self.total_matches,
            "offset": self.offset,
            "limit": self.limit,
            "assets": [asset.to_dict() for asset in self.assets],
        }


class FootballLibrary:
    """Provider-neutral deterministic football video catalog."""

    def __init__(self, assets: Iterable[ExternalVideoAsset] = ()) -> None:
        self._assets: dict[str, ExternalVideoAsset] = {}
        self._provider_keys: dict[tuple[str, str], str] = {}
        for asset in assets:
            self.index(asset)

    def __len__(self) -> int:
        return len(self._assets)

    def index(self, asset: ExternalVideoAsset) -> ExternalVideoAsset:
        asset.validate()
        provider_key = (asset.provider, asset.provider_asset_id)
        existing_id = self._provider_keys.get(provider_key)
        if existing_id is not None and existing_id != asset.asset_id:
            raise FootballLibraryError("provider asset identity collision")
        existing = self._assets.get(asset.asset_id)
        if existing is not None and existing.to_dict() != asset.to_dict():
            raise FootballLibraryError("asset_id collision with different evidence")
        self._assets[asset.asset_id] = asset
        self._provider_keys[provider_key] = asset.asset_id
        return asset

    def get(self, asset_id: str) -> ExternalVideoAsset:
        try:
            return self._assets[asset_id]
        except KeyError as exc:
            raise FootballLibraryError("asset not found") from exc

    def transition(self, asset_id: str, new_state: str) -> ExternalVideoAsset:
        if new_state not in SUPPORTED_LIBRARY_STATES:
            raise FootballLibraryError("unsupported target state")
        current = self.get(asset_id)
        if new_state == current.library_state:
            return current
        if new_state not in ALLOWED_STATE_TRANSITIONS[current.library_state]:
            raise FootballLibraryError(
                f"invalid state transition: {current.library_state} -> {new_state}"
            )
        updated = dataclasses.replace(current, library_state=new_state)
        updated.validate()
        self._assets[asset_id] = updated
        return updated

    def search(self, query: LibraryQuery) -> LibrarySearchResult:
        query.validate()
        matches = [asset for asset in self._assets.values() if _matches(asset, query)]
        matches.sort(key=_sort_key(query.sort))
        total = len(matches)
        page = tuple(matches[query.offset : query.offset + query.limit])
        return LibrarySearchResult(
            schema="football-shorts-ai.football-library-search.v1",
            query_sha256=canonical_sha256(dataclasses.asdict(query)),
            total_matches=total,
            offset=query.offset,
            limit=query.limit,
            assets=page,
        )

    def to_dashboard_dict(self) -> dict[str, object]:
        assets = sorted(self._assets.values(), key=lambda item: item.asset_id)
        providers: dict[str, int] = {}
        states: dict[str, int] = {}
        rights: dict[str, int] = {}
        for asset in assets:
            providers[asset.provider] = providers.get(asset.provider, 0) + 1
            states[asset.library_state] = states.get(asset.library_state, 0) + 1
            rights[asset.rights_status] = rights.get(asset.rights_status, 0) + 1
        payload: dict[str, object] = {
            "schema": "football-shorts-ai.football-library.v1",
            "asset_count": len(assets),
            "summary": {
                "providers": dict(sorted(providers.items())),
                "states": dict(sorted(states.items())),
                "rights_statuses": dict(sorted(rights.items())),
                "previewable": sum(asset.preview_allowed for asset in assets),
                "renderable": sum(asset.render_allowed for asset in assets),
                "acquirable": sum(asset.acquisition_allowed for asset in assets),
            },
            "assets": [asset.to_dict() for asset in assets],
            "auto_acquire": False,
            "auto_publish": False,
        }
        payload["evidence_sha256"] = canonical_sha256(payload)
        return payload


def _matches(asset: ExternalVideoAsset, query: LibraryQuery) -> bool:
    if asset.score < query.minimum_score:
        return False
    if query.providers and asset.provider not in query.providers:
        return False
    if query.rights_statuses and asset.rights_status not in query.rights_statuses:
        return False
    if query.library_states and asset.library_state not in query.library_states:
        return False
    if query.render_allowed is not None and asset.render_allowed != query.render_allowed:
        return False
    if query.preview_allowed is not None and asset.preview_allowed != query.preview_allowed:
        return False
    if query.competitions and _normalize(asset.competition or "") not in _normalized(query.competitions):
        return False
    if query.teams and not _normalized(query.teams).intersection(_normalized(asset.teams)):
        return False
    if query.players and not _normalized(query.players).intersection(_normalized(asset.players)):
        return False
    if query.tags and not _normalized(query.tags).intersection(_normalized(asset.tags)):
        return False
    terms = tuple(term for term in _normalize(query.text).split() if term)
    if terms:
        haystack = _normalize(" ".join([
            asset.title,
            asset.description,
            asset.channel_name,
            asset.competition or "",
            *asset.teams,
            *asset.players,
            *asset.tags,
        ]))
        if not all(term in haystack for term in terms):
            return False
    return True


def _sort_key(name: str):
    if name == "score_desc":
        return lambda asset: (-asset.score, -int(asset.views or 0), asset.asset_id)
    if name == "views_desc":
        return lambda asset: (-int(asset.views or 0), -asset.score, asset.asset_id)
    if name == "likes_desc":
        return lambda asset: (-int(asset.likes or 0), -asset.score, asset.asset_id)
    if name == "published_desc":
        return lambda asset: (asset.published_at is None, _descending_text(asset.published_at), asset.asset_id)
    if name == "discovered_desc":
        return lambda asset: (_descending_text(asset.discovered_at), asset.asset_id)
    return lambda asset: (_normalize(asset.title), asset.asset_id)


def _descending_text(value: str | None) -> tuple[int, ...]:
    return tuple(-ord(char) for char in (value or ""))


def _normalized(values: Iterable[str]) -> set[str]:
    return {_normalize(value) for value in values if value.strip()}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold().strip()


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ALLOWED_STATE_TRANSITIONS",
    "FootballLibrary",
    "FootballLibraryError",
    "LibraryQuery",
    "LibrarySearchResult",
    "SUPPORTED_SORTS",
    "canonical_sha256",
]
