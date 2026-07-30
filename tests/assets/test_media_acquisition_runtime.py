from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from assets.contracts import RightsBasis, SubjectScope
from assets.media_acquisition_runtime import (
    AssetCandidate,
    MediaAcquisitionRuntime,
    RuntimeSceneRequest,
    canonical_sha256,
    write_manifest_atomically,
)


class StubProvider:
    def __init__(self, provider_id: str, priority: int, candidates: tuple[AssetCandidate, ...]) -> None:
        self.provider_id = provider_id
        self.priority = priority
        self._candidates = candidates

    def discover(self, request: RuntimeSceneRequest) -> tuple[AssetCandidate, ...]:
        return self._candidates


class FailingProvider:
    provider_id = "broken"
    priority = 1

    def discover(self, request: RuntimeSceneRequest) -> tuple[AssetCandidate, ...]:
        raise RuntimeError("provider unavailable")


def _plan() -> dict:
    return {
        "plan_version": "1.0",
        "scene_plans": [
            {
                "scene_number": 1,
                "request": {
                    "asset_role": "opening_hook",
                    "visual_instruction": "Vertical generic football stadium opening",
                    "caption_text": "The match begins",
                    "duration_seconds": 6,
                    "subject_scope": "generic_football",
                    "media_type_preference": ["video", "image"],
                    "search_terms": ["football stadium", "crowd opening"],
                },
            }
        ],
    }


def _candidate(
    *,
    provider_id: str = "pexels",
    asset_id: str = "asset-1",
    relevance: float = 0.9,
    quality: float = 0.8,
    rights_basis: RightsBasis = RightsBasis.LICENSED,
    rights_status: str = "approved",
    license_reference: str | None = "PEXELS-LICENSE",
    watermark_present: bool = False,
    cross_platform_allowed: bool = True,
    original_file_available: bool = True,
    delivery_url: str | None = "https://example.invalid/video.mp4",
    provider_priority: int = 5,
) -> AssetCandidate:
    return AssetCandidate(
        provider_id=provider_id,
        provider_asset_id=asset_id,
        media_type="video",
        subject_scope=SubjectScope.GENERIC_FOOTBALL,
        title="Generic football stadium",
        source_url="https://example.invalid/source",
        preview_url="https://example.invalid/preview.mp4",
        delivery_url=delivery_url,
        duration_seconds=6.0,
        width=1080,
        height=1920,
        rights_basis=rights_basis,
        rights_status=rights_status,
        license_reference=license_reference,
        creator_reference="creator-1",
        attribution_text="Footage by creator-1",
        watermark_present=watermark_present,
        cross_platform_allowed=cross_platform_allowed,
        original_file_available=original_file_available,
        relevance_score=relevance,
        quality_score=quality,
        freshness_score=0.7,
        provider_priority=provider_priority,
        metadata={"source": "fixture"},
    )


def test_runtime_selects_highest_ranked_rights_approved_candidate() -> None:
    low = _candidate(asset_id="low", relevance=0.55, quality=0.60)
    high = _candidate(asset_id="high", relevance=0.95, quality=0.90)
    runtime = MediaAcquisitionRuntime(
        [StubProvider("pexels", 5, (low, high))],
        clock=lambda: datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc),
    )

    manifest = runtime.execute(_plan())

    assert manifest.status == "PASS"
    assert manifest.selected_asset_count == 1
    selected = manifest.results[0].selected
    assert selected is not None
    assert selected.candidate.provider_asset_id == "high"
    assert selected.decision == "approved"
    assert selected.blockers == ()


def test_runtime_blocks_unlicensed_or_watermarked_candidates() -> None:
    unlicensed = _candidate(
        asset_id="unlicensed",
        rights_basis=RightsBasis.UNLICENSED,
        rights_status="unresolved",
        license_reference=None,
    )
    watermarked = _candidate(asset_id="watermarked", watermark_present=True)
    runtime = MediaAcquisitionRuntime([StubProvider("mixed", 1, (unlicensed, watermarked))])

    manifest = runtime.execute(_plan())

    assert manifest.status == "BLOCKED"
    assert manifest.blocked_scene_count == 1
    assert manifest.results[0].selected is None
    assert manifest.results[0].rejected_candidates == 2


def test_tiktok_candidate_requires_creator_license_and_original_file() -> None:
    candidate = _candidate(
        provider_id="tiktok_licensed_ugc",
        asset_id="tiktok-1",
        license_reference=None,
        original_file_available=False,
        delivery_url=None,
        provider_priority=4,
    )
    runtime = MediaAcquisitionRuntime([StubProvider("tiktok_licensed_ugc", 4, (candidate,))])

    manifest = runtime.execute(_plan())

    assert manifest.status == "BLOCKED"
    assert manifest.results[0].selected is None


def test_provider_failure_is_isolated_when_another_provider_succeeds() -> None:
    approved = _candidate(asset_id="fallback")
    runtime = MediaAcquisitionRuntime(
        [FailingProvider(), StubProvider("pexels", 5, (approved,))]
    )

    manifest = runtime.execute(_plan())

    assert manifest.status == "PASS"
    assert manifest.results[0].selected is not None
    assert manifest.results[0].provider_failures
    assert "provider unavailable" in manifest.results[0].provider_failures[0]


def test_manifest_is_deterministic_except_for_injected_clock() -> None:
    plan = _plan()
    approved = _candidate(asset_id="stable")
    fixed = datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc)
    runtime = MediaAcquisitionRuntime(
        [StubProvider("pexels", 5, (approved,))],
        clock=lambda: fixed,
    )

    first = runtime.execute(plan).to_dict()
    second = runtime.execute(plan).to_dict()

    assert first == second
    assert first["source_plan_sha256"] == canonical_sha256(plan)


def test_atomic_manifest_write_leaves_no_temporary_file(tmp_path: Path) -> None:
    runtime = MediaAcquisitionRuntime(
        [StubProvider("pexels", 5, (_candidate(),))],
        clock=lambda: datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc),
    )
    manifest = runtime.execute(_plan())
    target = tmp_path / "output" / "media_acquisition_runtime.json"

    write_manifest_atomically(target, manifest)

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["artifact"] == "FOOTBALL-SHORTS-AI-0048A"
    assert payload["status"] == "PASS"
    assert not (target.parent / f".{target.name}.tmp").exists()
