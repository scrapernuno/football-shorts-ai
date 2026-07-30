from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from assets.contracts import RightsBasis, SubjectScope


class MediaAcquisitionRuntimeError(RuntimeError):
    """Base error for governed media acquisition runtime failures."""


class RightsEvidenceError(MediaAcquisitionRuntimeError):
    """Raised when an asset does not carry sufficient rights evidence."""


class ProviderExecutionError(MediaAcquisitionRuntimeError):
    """Raised when a configured provider fails during discovery."""


@dataclass(frozen=True, slots=True)
class RuntimeSceneRequest:
    scene_number: int
    asset_role: str
    visual_instruction: str
    caption_text: str
    duration_seconds: int
    subject_scope: SubjectScope
    media_type_preference: tuple[str, ...]
    search_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssetCandidate:
    provider_id: str
    provider_asset_id: str
    media_type: str
    subject_scope: SubjectScope
    title: str
    source_url: str
    preview_url: str | None
    delivery_url: str | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    rights_basis: RightsBasis
    rights_status: str
    license_reference: str | None
    creator_reference: str | None
    attribution_text: str | None
    watermark_present: bool
    cross_platform_allowed: bool
    original_file_available: bool
    relevance_score: float
    quality_score: float
    freshness_score: float
    provider_priority: int
    metadata: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RankedAsset:
    candidate: AssetCandidate
    score: float
    decision: str
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SceneAcquisitionResult:
    scene_number: int
    status: str
    selected: RankedAsset | None
    candidates_considered: int
    rejected_candidates: int
    provider_failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MediaAcquisitionManifest:
    artifact: str
    status: str
    generated_at: str
    source_plan_sha256: str
    scene_count: int
    selected_asset_count: int
    blocked_scene_count: int
    results: tuple[SceneAcquisitionResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "generated_at": self.generated_at,
            "source_plan_sha256": self.source_plan_sha256,
            "scene_count": self.scene_count,
            "selected_asset_count": self.selected_asset_count,
            "blocked_scene_count": self.blocked_scene_count,
            "results": [
                {
                    "scene_number": result.scene_number,
                    "status": result.status,
                    "selected": _ranked_to_dict(result.selected),
                    "candidates_considered": result.candidates_considered,
                    "rejected_candidates": result.rejected_candidates,
                    "provider_failures": list(result.provider_failures),
                }
                for result in self.results
            ],
        }


class RuntimeProvider(Protocol):
    provider_id: str
    priority: int

    def discover(self, request: RuntimeSceneRequest) -> Sequence[AssetCandidate]:
        """Return provider candidates without mutating project state."""


Clock = Callable[[], datetime]


class MediaAcquisitionRuntime:
    """Discover, validate and rank media candidates under fail-closed policy.

    The runtime deliberately does not download arbitrary third-party media.
    It selects only candidates with explicit rights evidence and emits a
    deterministic manifest that a later delivery authority may materialize.
    """

    def __init__(
        self,
        providers: Sequence[RuntimeProvider],
        *,
        clock: Clock = lambda: datetime.now(timezone.utc),
        allow_editorial_exception: bool = False,
    ) -> None:
        observed: set[str] = set()
        ordered = sorted(providers, key=lambda item: item.priority)
        for provider in ordered:
            if not provider.provider_id.strip():
                raise ValueError("provider_id cannot be empty")
            if provider.provider_id in observed:
                raise ValueError(f"duplicate provider_id: {provider.provider_id}")
            if provider.priority <= 0:
                raise ValueError("provider priority must be positive")
            observed.add(provider.provider_id)
        self._providers = tuple(ordered)
        self._clock = clock
        self._allow_editorial_exception = allow_editorial_exception

    def execute(self, plan: Mapping[str, Any]) -> MediaAcquisitionManifest:
        requests = _parse_plan(plan)
        source_hash = canonical_sha256(plan)
        results = tuple(self._execute_scene(request) for request in requests)
        selected_count = sum(result.selected is not None for result in results)
        blocked_count = sum(result.status != "selected" for result in results)
        return MediaAcquisitionManifest(
            artifact="FOOTBALL-SHORTS-AI-0048A",
            status="PASS" if blocked_count == 0 else "BLOCKED",
            generated_at=self._clock().astimezone(timezone.utc).isoformat(),
            source_plan_sha256=source_hash,
            scene_count=len(results),
            selected_asset_count=selected_count,
            blocked_scene_count=blocked_count,
            results=results,
        )

    def _execute_scene(self, request: RuntimeSceneRequest) -> SceneAcquisitionResult:
        ranked: list[RankedAsset] = []
        provider_failures: list[str] = []
        considered = 0

        for provider in self._providers:
            try:
                candidates = tuple(provider.discover(request))
            except Exception as exc:
                provider_failures.append(f"{provider.provider_id}: {type(exc).__name__}: {exc}")
                continue

            for candidate in candidates:
                considered += 1
                ranked.append(
                    evaluate_candidate(
                        request,
                        candidate,
                        allow_editorial_exception=self._allow_editorial_exception,
                    )
                )

        approved = [item for item in ranked if item.decision == "approved"]
        approved.sort(
            key=lambda item: (
                -item.score,
                item.candidate.provider_priority,
                item.candidate.provider_id,
                item.candidate.provider_asset_id,
            )
        )
        selected = approved[0] if approved else None
        return SceneAcquisitionResult(
            scene_number=request.scene_number,
            status="selected" if selected is not None else "blocked",
            selected=selected,
            candidates_considered=considered,
            rejected_candidates=sum(item.decision != "approved" for item in ranked),
            provider_failures=tuple(provider_failures),
        )


def evaluate_candidate(
    request: RuntimeSceneRequest,
    candidate: AssetCandidate,
    *,
    allow_editorial_exception: bool,
) -> RankedAsset:
    blockers: list[str] = []

    if candidate.subject_scope != request.subject_scope:
        blockers.append("SUBJECT_SCOPE_MISMATCH")
    if candidate.media_type not in request.media_type_preference:
        blockers.append("MEDIA_TYPE_NOT_REQUESTED")
    if candidate.rights_basis == RightsBasis.UNLICENSED:
        blockers.append("UNLICENSED_MEDIA")
    if candidate.rights_status != "approved":
        blockers.append("RIGHTS_NOT_APPROVED")
    if candidate.rights_basis == RightsBasis.LICENSED and not _non_empty(candidate.license_reference):
        blockers.append("LICENSE_REFERENCE_MISSING")
    if candidate.rights_basis == RightsBasis.OWNED and not _non_empty(candidate.license_reference):
        blockers.append("OWNERSHIP_EVIDENCE_MISSING")
    if candidate.rights_basis == RightsBasis.EDITORIAL_EXCEPTION and not allow_editorial_exception:
        blockers.append("EDITORIAL_EXCEPTION_NOT_AUTHORIZED")
    if candidate.watermark_present:
        blockers.append("WATERMARK_PRESENT")
    if not candidate.cross_platform_allowed:
        blockers.append("CROSS_PLATFORM_NOT_ALLOWED")
    if not candidate.original_file_available:
        blockers.append("ORIGINAL_FILE_NOT_AVAILABLE")
    if not _non_empty(candidate.delivery_url):
        blockers.append("DELIVERY_URL_MISSING")
    if candidate.provider_priority <= 0:
        blockers.append("INVALID_PROVIDER_PRIORITY")
    if not 0.0 <= candidate.relevance_score <= 1.0:
        blockers.append("INVALID_RELEVANCE_SCORE")
    if not 0.0 <= candidate.quality_score <= 1.0:
        blockers.append("INVALID_QUALITY_SCORE")
    if not 0.0 <= candidate.freshness_score <= 1.0:
        blockers.append("INVALID_FRESHNESS_SCORE")

    duration_fit = _duration_fit(request.duration_seconds, candidate.duration_seconds)
    orientation_fit = _orientation_fit(candidate.width, candidate.height)
    score = round(
        candidate.relevance_score * 0.50
        + candidate.quality_score * 0.25
        + candidate.freshness_score * 0.10
        + duration_fit * 0.10
        + orientation_fit * 0.05,
        6,
    )

    return RankedAsset(
        candidate=candidate,
        score=score,
        decision="approved" if not blockers else "blocked",
        blockers=tuple(blockers),
    )


def write_manifest_atomically(path: Path, manifest: MediaAcquisitionManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    payload = json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(payload, encoding="utf-8")
    with temporary.open("rb") as handle:
        import os

        os.fsync(handle.fileno())
    temporary.replace(path)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_plan(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"media acquisition plan not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid media acquisition plan: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("media acquisition plan root must be an object")
    return payload


def _parse_plan(plan: Mapping[str, Any]) -> tuple[RuntimeSceneRequest, ...]:
    raw_scenes = plan.get("scene_plans")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("media acquisition plan requires non-empty scene_plans")

    requests: list[RuntimeSceneRequest] = []
    observed: set[int] = set()
    for index, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            raise ValueError(f"scene_plans[{index}] must be an object")
        scene_number = raw.get("scene_number")
        if not isinstance(scene_number, int) or isinstance(scene_number, bool) or scene_number <= 0:
            raise ValueError(f"scene_plans[{index}].scene_number must be positive integer")
        if scene_number in observed:
            raise ValueError(f"duplicate scene_number: {scene_number}")
        observed.add(scene_number)

        request_payload = raw.get("request", raw)
        if not isinstance(request_payload, dict):
            raise ValueError(f"scene_plans[{index}].request must be an object")

        requests.append(
            RuntimeSceneRequest(
                scene_number=scene_number,
                asset_role=_required_text(request_payload, "asset_role"),
                visual_instruction=_required_text(request_payload, "visual_instruction"),
                caption_text=_required_text(request_payload, "caption_text"),
                duration_seconds=_positive_int(request_payload.get("duration_seconds"), "duration_seconds"),
                subject_scope=SubjectScope(_required_text(request_payload, "subject_scope")),
                media_type_preference=_text_tuple(request_payload.get("media_type_preference"), "media_type_preference"),
                search_terms=_text_tuple(request_payload.get("search_terms"), "search_terms"),
            )
        )
    return tuple(requests)


def _ranked_to_dict(value: RankedAsset | None) -> dict[str, Any] | None:
    if value is None:
        return None
    candidate = asdict(value.candidate)
    candidate["subject_scope"] = value.candidate.subject_scope.value
    candidate["rights_basis"] = value.candidate.rights_basis.value
    candidate["metadata"] = dict(value.candidate.metadata)
    return {
        "candidate": candidate,
        "score": value.score,
        "decision": value.decision,
        "blockers": list(value.blockers),
    }


def _duration_fit(requested: int, observed: float | None) -> float:
    if observed is None or observed <= 0:
        return 0.0
    delta = abs(observed - requested)
    return max(0.0, 1.0 - delta / max(float(requested), 1.0))


def _orientation_fit(width: int | None, height: int | None) -> float:
    if width is None or height is None or width <= 0 or height <= 0:
        return 0.0
    return 1.0 if height > width else 0.35


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value.strip()


def _text_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} entries must be non-empty text")
        result.append(item.strip())
    return tuple(result)


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _non_empty(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())
