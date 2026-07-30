from __future__ import annotations

import json
from pathlib import Path

from assets.contracts import SubjectScope
from assets.controlled_provider_discovery import (
    OwnedLibraryDiscoveryAdapter,
    PexelsDiscoveryAdapter,
    build_controlled_runtime_providers,
)
from assets.media_acquisition_runtime import RuntimeSceneRequest


def _request(scope: SubjectScope = SubjectScope.GENERIC_FOOTBALL) -> RuntimeSceneRequest:
    return RuntimeSceneRequest(
        scene_number=1,
        asset_role="opening_hook",
        visual_instruction="generic football stadium fans",
        caption_text="Opening moment",
        duration_seconds=6,
        subject_scope=scope,
        media_type_preference=("video", "image"),
        search_terms=("football stadium", "fans"),
    )


def test_owned_library_discovers_only_approved_matching_original(tmp_path: Path) -> None:
    video = tmp_path / "owned.mp4"
    video.write_bytes(b"owned-video")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "assets": [
                    {
                        "asset_id": "OWN-001",
                        "status": "approved",
                        "media_type": "video",
                        "subject_scope": "generic_football",
                        "title": "Football stadium fans",
                        "description": "fans before the match",
                        "tags": ["football stadium", "fans"],
                        "delivery_path": str(video),
                        "source_reference": "internal://owned/OWN-001",
                        "ownership_evidence": "OWNERSHIP-001",
                        "cross_platform_allowed": True,
                        "watermark_present": False,
                        "duration_seconds": 7,
                        "width": 1080,
                        "height": 1920,
                        "quality_score": 0.9,
                        "freshness_score": 0.8,
                    },
                    {
                        "asset_id": "OWN-REJECTED",
                        "status": "review_required",
                        "media_type": "video",
                        "subject_scope": "generic_football",
                        "title": "Fans",
                        "tags": ["fans"],
                        "delivery_path": str(video),
                        "source_reference": "internal://owned/rejected",
                        "ownership_evidence": "OWNERSHIP-002",
                        "cross_platform_allowed": True,
                        "quality_score": 0.9,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    candidates = OwnedLibraryDiscoveryAdapter(catalog).discover(_request())

    assert len(candidates) == 1
    assert candidates[0].provider_asset_id == "OWN-001"
    assert candidates[0].original_file_available is True
    assert candidates[0].license_reference == "OWNERSHIP-001"


def test_owned_library_marks_missing_original_fail_closed(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "asset_id": "OWN-001",
                        "status": "approved",
                        "media_type": "video",
                        "subject_scope": "generic_football",
                        "title": "Football stadium",
                        "tags": ["football stadium"],
                        "delivery_path": str(tmp_path / "missing.mp4"),
                        "source_reference": "internal://owned/OWN-001",
                        "ownership_evidence": "OWNERSHIP-001",
                        "cross_platform_allowed": True,
                        "quality_score": 0.8,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    candidate = OwnedLibraryDiscoveryAdapter(catalog).discover(_request())[0]
    assert candidate.original_file_available is False


def test_pexels_discovers_highest_resolution_portrait_mp4() -> None:
    observed: dict = {}

    def transport(url: str, headers: dict[str, str]) -> dict:
        observed["url"] = url
        observed["headers"] = headers
        return {
            "videos": [
                {
                    "id": 42,
                    "url": "https://www.pexels.com/video/42/",
                    "image": "https://images.pexels.com/42.jpg",
                    "duration": 8,
                    "user": {"name": "Creator", "url": "https://www.pexels.com/@creator"},
                    "video_files": [
                        {
                            "id": 1,
                            "file_type": "video/mp4",
                            "width": 1280,
                            "height": 720,
                            "link": "https://cdn.pexels.com/landscape.mp4",
                        },
                        {
                            "id": 2,
                            "file_type": "video/mp4",
                            "width": 720,
                            "height": 1280,
                            "link": "https://cdn.pexels.com/portrait-720.mp4",
                        },
                        {
                            "id": 3,
                            "file_type": "video/mp4",
                            "width": 1080,
                            "height": 1920,
                            "link": "https://cdn.pexels.com/portrait-1080.mp4",
                        },
                    ],
                }
            ]
        }

    candidates = PexelsDiscoveryAdapter("secret", transport).discover(_request())

    assert len(candidates) == 1
    assert candidates[0].delivery_url == "https://cdn.pexels.com/portrait-1080.mp4"
    assert candidates[0].cross_platform_allowed is True
    assert candidates[0].watermark_present is False
    assert observed["headers"] == {"Authorization": "secret"}
    assert "orientation=portrait" in observed["url"]


def test_pexels_refuses_specific_football_request_without_calling_network() -> None:
    called = False

    def transport(url: str, headers: dict[str, str]) -> dict:
        nonlocal called
        called = True
        return {}

    candidates = PexelsDiscoveryAdapter("secret", transport).discover(
        _request(SubjectScope.SPECIFIC_FOOTBALL)
    )

    assert candidates == ()
    assert called is False


def test_provider_builder_is_configuration_driven(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text('{"assets": []}', encoding="utf-8")

    providers = build_controlled_runtime_providers(
        owned_catalog_path=catalog,
        pexels_api_key="secret",
        transport=lambda _url, _headers: {"videos": []},
    )

    assert [provider.provider_id for provider in providers] == ["owned_library", "pexels"]
