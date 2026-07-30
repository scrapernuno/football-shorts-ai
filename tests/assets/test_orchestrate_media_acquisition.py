from __future__ import annotations

import io
import json
from pathlib import Path

from assets.contracts import RightsBasis, SubjectScope
from assets.media_acquisition_runtime import AssetCandidate, RuntimeSceneRequest
from assets.orchestrate_media_acquisition import orchestrate_media_acquisition


class StaticProvider:
    provider_id = "owned_library"
    priority = 1

    def __init__(self, candidate: AssetCandidate | None) -> None:
        self._candidate = candidate

    def discover(self, request: RuntimeSceneRequest):
        return () if self._candidate is None else (self._candidate,)


def _content() -> dict:
    return {
        "generated_at": "2026-07-30T11:00:00+00:00",
        "source_topic": {
            "title": "Football fans before kickoff",
            "hook": "The stadium is ready",
        },
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 6,
                "visual_instruction": "generic stadium crowd fans",
                "caption_text": "The crowd is ready",
            }
        ],
    }


def _policy() -> dict:
    return {
        "policy_version": "1.1",
        "policy_id": "football-media-copyright-aware-v2",
        "mode": "copyright_aware_fail_closed",
        "publication_execution_enabled": False,
        "automatic_license_purchase_enabled": False,
        "unlicensed_media_allowed": False,
        "editorial_exception_requires_manual_review": True,
        "third_party_download_allowed": False,
        "third_party_watermark_removal_allowed": False,
        "platform_native_remix_cross_platform_allowed": False,
        "provider_order": [
            "owned_library",
            "imago",
            "reuters_connect",
            "tiktok_licensed_ugc",
            "pexels",
        ],
        "providers": {
            "owned_library": {
                "enabled": True,
                "configured": True,
                "inventory_ready": True,
                "priority": 1,
                "allowed_media_types": ["image", "video"],
                "allowed_subject_scope": ["specific_football", "generic_football"],
                "allowed_rights_basis": ["owned"],
            },
            "imago": {
                "enabled": True,
                "configured": False,
                "contract_required": True,
                "priority": 2,
                "allowed_media_types": ["image", "video"],
                "allowed_subject_scope": ["specific_football", "generic_football"],
                "allowed_rights_basis": ["licensed"],
            },
            "reuters_connect": {
                "enabled": True,
                "configured": False,
                "contract_required": True,
                "priority": 3,
                "allowed_media_types": ["image", "video"],
                "allowed_subject_scope": ["specific_football", "generic_football"],
                "allowed_rights_basis": ["licensed"],
            },
            "tiktok_licensed_ugc": {
                "enabled": True,
                "configured": False,
                "contract_required": True,
                "priority": 4,
                "allowed_media_types": ["video"],
                "allowed_subject_scope": ["specific_football", "generic_football"],
                "allowed_rights_basis": ["licensed"],
            },
            "pexels": {
                "enabled": True,
                "configured": False,
                "contract_required": False,
                "priority": 5,
                "allowed_media_types": ["image", "video"],
                "allowed_subject_scope": ["generic_football"],
                "allowed_rights_basis": ["licensed"],
            },
        },
    }


def _candidate() -> AssetCandidate:
    return AssetCandidate(
        provider_id="owned_library",
        provider_asset_id="OWN-ORCH-001",
        media_type="video",
        subject_scope=SubjectScope.GENERIC_FOOTBALL,
        title="Generic stadium crowd fans",
        source_url="internal://owned/OWN-ORCH-001",
        preview_url=None,
        delivery_url="https://media.example/owned-orch-001.mp4",
        duration_seconds=6.0,
        width=1080,
        height=1920,
        rights_basis=RightsBasis.OWNED,
        rights_status="approved",
        license_reference="OWNERSHIP-ORCH-001",
        creator_reference=None,
        attribution_text="Owned media",
        watermark_present=False,
        cross_platform_allowed=True,
        original_file_available=True,
        relevance_score=1.0,
        quality_score=1.0,
        freshness_score=0.8,
        provider_priority=1,
        metadata={},
    )


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    content_path = tmp_path / "output" / "content_package.json"
    policy_path = tmp_path / "config" / "media_provider_policy.json"
    content_path.parent.mkdir(parents=True)
    policy_path.parent.mkdir(parents=True)
    content_path.write_text(json.dumps(_content()), encoding="utf-8")
    policy_path.write_text(json.dumps(_policy()), encoding="utf-8")
    return content_path, policy_path


def test_orchestration_executes_plan_discovery_and_delivery(tmp_path: Path) -> None:
    content_path, policy_path = _write_inputs(tmp_path)
    output = tmp_path / "output"
    mp4 = b"\x00\x00\x00\x18ftypisom" + b"governed-video"

    report = orchestrate_media_acquisition(
        content_path=content_path,
        policy_path=policy_path,
        plan_path=output / "media_acquisition_plan.json",
        acquisition_manifest_path=output / "media_acquisition_manifest.json",
        delivery_workspace=output / "assets" / "acquired",
        delivery_manifest_path=output / "media_delivery_manifest.json",
        report_path=output / "media_acquisition_orchestration.json",
        providers=(StaticProvider(_candidate()),),
        open_url=lambda _: io.BytesIO(mp4),
    )

    assert report.status == "PASS"
    assert report.plan_status == "PASS"
    assert report.discovery_status == "PASS"
    assert report.delivery_status == "PASS"
    assert report.selected_asset_count == 1
    assert report.delivered_asset_count == 1
    assert (output / "media_acquisition_plan.json").is_file()
    assert (output / "media_acquisition_manifest.json").is_file()
    assert (output / "media_delivery_manifest.json").is_file()
    delivery = json.loads((output / "media_delivery_manifest.json").read_text(encoding="utf-8"))
    local_path = Path(delivery["assets"][0]["local_path"])
    assert local_path.is_file()
    assert local_path.read_bytes() == mp4


def test_orchestration_blocks_without_controlled_provider(tmp_path: Path) -> None:
    content_path, policy_path = _write_inputs(tmp_path)
    output = tmp_path / "output"
    stale_delivery = output / "media_delivery_manifest.json"
    stale_delivery.write_text("stale", encoding="utf-8")

    report = orchestrate_media_acquisition(
        content_path=content_path,
        policy_path=policy_path,
        plan_path=output / "media_acquisition_plan.json",
        acquisition_manifest_path=output / "media_acquisition_manifest.json",
        delivery_workspace=output / "assets" / "acquired",
        delivery_manifest_path=stale_delivery,
        report_path=output / "media_acquisition_orchestration.json",
        providers=(),
    )

    assert report.status == "BLOCKED"
    assert report.blockers == ("NO_CONTROLLED_PROVIDER_AVAILABLE",)
    assert not stale_delivery.exists()
    assert not (output / "media_acquisition_manifest.json").exists()


def test_orchestration_does_not_deliver_when_discovery_is_blocked(tmp_path: Path) -> None:
    content_path, policy_path = _write_inputs(tmp_path)
    output = tmp_path / "output"

    report = orchestrate_media_acquisition(
        content_path=content_path,
        policy_path=policy_path,
        plan_path=output / "media_acquisition_plan.json",
        acquisition_manifest_path=output / "media_acquisition_manifest.json",
        delivery_workspace=output / "assets" / "acquired",
        delivery_manifest_path=output / "media_delivery_manifest.json",
        report_path=output / "media_acquisition_orchestration.json",
        providers=(StaticProvider(None),),
    )

    assert report.status == "BLOCKED"
    assert report.discovery_status == "BLOCKED"
    assert report.delivery_status == "NOT_EXECUTED"
    assert report.blockers == ("SCENE_1_NO_APPROVED_ASSET",)
    assert (output / "media_acquisition_manifest.json").is_file()
    assert not (output / "media_delivery_manifest.json").exists()
