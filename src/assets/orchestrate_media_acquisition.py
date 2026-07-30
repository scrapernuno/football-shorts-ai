from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from assets.build_media_acquisition_plan import (
    build_plan,
    load_json,
    validate_plan,
    write_json_atomically,
)
from assets.controlled_provider_discovery import build_controlled_runtime_providers
from assets.media_acquisition_runtime import (
    MediaAcquisitionRuntime,
    RuntimeProvider,
    write_manifest_atomically,
)
from assets.materialize_selected_media import (
    MediaDeliveryManifest,
    OpenUrl,
    materialize_selected_media,
    write_delivery_manifest,
)
from assets.provider_registry import load_policy


class MediaAcquisitionOrchestrationError(RuntimeError):
    """Raised when the governed acquisition chain cannot complete safely."""


@dataclass(frozen=True, slots=True)
class MediaAcquisitionOrchestrationReport:
    artifact: str
    status: str
    plan_status: str
    discovery_status: str
    delivery_status: str
    provider_count: int
    scene_count: int
    selected_asset_count: int
    delivered_asset_count: int
    plan_path: str
    acquisition_manifest_path: str
    delivery_manifest_path: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        return payload


def orchestrate_media_acquisition(
    *,
    content_path: Path = Path("output/content_package.json"),
    policy_path: Path = Path("config/media_provider_policy.json"),
    owned_catalog_path: Path = Path("config/owned_media_catalog.json"),
    plan_path: Path = Path("output/media_acquisition_plan.json"),
    acquisition_manifest_path: Path = Path("output/media_acquisition_manifest.json"),
    delivery_workspace: Path = Path("output/assets/acquired"),
    delivery_manifest_path: Path = Path("output/media_delivery_manifest.json"),
    report_path: Path = Path("output/media_acquisition_orchestration.json"),
    providers: Sequence[RuntimeProvider] | None = None,
    pexels_api_key: str | None = None,
    open_url: OpenUrl | None = None,
    maximum_asset_bytes: int = 100 * 1024 * 1024,
) -> MediaAcquisitionOrchestrationReport:
    if maximum_asset_bytes <= 0:
        raise ValueError("maximum_asset_bytes must be positive")

    _remove_stale_outputs(acquisition_manifest_path, delivery_manifest_path, report_path)

    content = load_json(content_path)
    policy = load_policy(policy_path)
    plan = build_plan(content=content, policy=policy)
    validate_plan(plan)
    write_json_atomically(plan_path, plan)

    runtime_providers = tuple(providers) if providers is not None else build_controlled_runtime_providers(
        owned_catalog_path=owned_catalog_path,
        pexels_api_key=(
            pexels_api_key
            if pexels_api_key is not None
            else os.getenv("PEXELS_API_KEY", "")
        ),
    )

    if not runtime_providers:
        report = MediaAcquisitionOrchestrationReport(
            artifact="FOOTBALL-SHORTS-AI-0048D",
            status="BLOCKED",
            plan_status="PASS",
            discovery_status="BLOCKED",
            delivery_status="NOT_EXECUTED",
            provider_count=0,
            scene_count=len(plan.get("scene_plans", [])),
            selected_asset_count=0,
            delivered_asset_count=0,
            plan_path=plan_path.as_posix(),
            acquisition_manifest_path=acquisition_manifest_path.as_posix(),
            delivery_manifest_path=delivery_manifest_path.as_posix(),
            blockers=("NO_CONTROLLED_PROVIDER_AVAILABLE",),
        )
        _write_report(report_path, report)
        return report

    acquisition_manifest = MediaAcquisitionRuntime(runtime_providers).execute(plan)
    write_manifest_atomically(acquisition_manifest_path, acquisition_manifest)

    if acquisition_manifest.status != "PASS":
        blockers = tuple(
            f"SCENE_{result.scene_number}_NO_APPROVED_ASSET"
            for result in acquisition_manifest.results
            if result.status != "selected"
        )
        report = MediaAcquisitionOrchestrationReport(
            artifact="FOOTBALL-SHORTS-AI-0048D",
            status="BLOCKED",
            plan_status="PASS",
            discovery_status="BLOCKED",
            delivery_status="NOT_EXECUTED",
            provider_count=len(runtime_providers),
            scene_count=acquisition_manifest.scene_count,
            selected_asset_count=acquisition_manifest.selected_asset_count,
            delivered_asset_count=0,
            plan_path=plan_path.as_posix(),
            acquisition_manifest_path=acquisition_manifest_path.as_posix(),
            delivery_manifest_path=delivery_manifest_path.as_posix(),
            blockers=blockers or ("ACQUISITION_MANIFEST_BLOCKED",),
        )
        _write_report(report_path, report)
        return report

    delivery_manifest = materialize_selected_media(
        acquisition_manifest.to_dict(),
        workspace=delivery_workspace,
        maximum_asset_bytes=maximum_asset_bytes,
        open_url=open_url,
    )
    _validate_delivery_binding(acquisition_manifest.selected_asset_count, delivery_manifest)
    write_delivery_manifest(delivery_manifest_path, delivery_manifest)

    report = MediaAcquisitionOrchestrationReport(
        artifact="FOOTBALL-SHORTS-AI-0048D",
        status="PASS",
        plan_status="PASS",
        discovery_status="PASS",
        delivery_status="PASS",
        provider_count=len(runtime_providers),
        scene_count=acquisition_manifest.scene_count,
        selected_asset_count=acquisition_manifest.selected_asset_count,
        delivered_asset_count=delivery_manifest.delivered_asset_count,
        plan_path=plan_path.as_posix(),
        acquisition_manifest_path=acquisition_manifest_path.as_posix(),
        delivery_manifest_path=delivery_manifest_path.as_posix(),
        blockers=(),
    )
    _write_report(report_path, report)
    return report


def _validate_delivery_binding(
    selected_asset_count: int,
    delivery_manifest: MediaDeliveryManifest,
) -> None:
    if delivery_manifest.status != "PASS":
        raise MediaAcquisitionOrchestrationError("delivery manifest is not PASS")
    if delivery_manifest.delivered_asset_count != selected_asset_count:
        raise MediaAcquisitionOrchestrationError(
            "delivered asset count does not match selected asset count"
        )
    if len(delivery_manifest.assets) != delivery_manifest.delivered_asset_count:
        raise MediaAcquisitionOrchestrationError("delivery manifest asset count is inconsistent")
    scenes = [asset.scene_number for asset in delivery_manifest.assets]
    if len(scenes) != len(set(scenes)):
        raise MediaAcquisitionOrchestrationError("delivery manifest contains duplicate scenes")


def _remove_stale_outputs(*paths: Path) -> None:
    for path in paths:
        path.unlink(missing_ok=True)
        temporary = path.parent / f".{path.name}.tmp"
        temporary.unlink(missing_ok=True)


def _write_report(path: Path, report: MediaAcquisitionOrchestrationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    temporary.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute the governed media acquisition chain end to end."
    )
    parser.add_argument("--content", default="output/content_package.json")
    parser.add_argument("--policy", default="config/media_provider_policy.json")
    parser.add_argument("--owned-catalog", default="config/owned_media_catalog.json")
    parser.add_argument("--plan", default="output/media_acquisition_plan.json")
    parser.add_argument("--acquisition-manifest", default="output/media_acquisition_manifest.json")
    parser.add_argument("--delivery-workspace", default="output/assets/acquired")
    parser.add_argument("--delivery-manifest", default="output/media_delivery_manifest.json")
    parser.add_argument("--report", default="output/media_acquisition_orchestration.json")
    parser.add_argument("--maximum-asset-bytes", type=int, default=100 * 1024 * 1024)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = orchestrate_media_acquisition(
        content_path=Path(args.content),
        policy_path=Path(args.policy),
        owned_catalog_path=Path(args.owned_catalog),
        plan_path=Path(args.plan),
        acquisition_manifest_path=Path(args.acquisition_manifest),
        delivery_workspace=Path(args.delivery_workspace),
        delivery_manifest_path=Path(args.delivery_manifest),
        report_path=Path(args.report),
        maximum_asset_bytes=args.maximum_asset_bytes,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
