from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest

from assets.materialize_selected_media import (
    MediaDeliveryError,
    materialize_selected_media,
    write_delivery_manifest,
)


def _candidate(delivery_url: str) -> dict:
    return {
        "provider_id": "owned_library",
        "provider_asset_id": "OWN-001",
        "media_type": "video",
        "subject_scope": "generic_football",
        "title": "Vertical football clip",
        "source_url": "internal://owned/OWN-001",
        "preview_url": None,
        "delivery_url": delivery_url,
        "duration_seconds": 6.0,
        "width": 1080,
        "height": 1920,
        "rights_basis": "owned",
        "rights_status": "approved",
        "license_reference": "OWNERSHIP-001",
        "creator_reference": None,
        "attribution_text": "Football Shorts AI owned media",
        "watermark_present": False,
        "cross_platform_allowed": True,
        "original_file_available": True,
        "relevance_score": 0.9,
        "quality_score": 0.9,
        "freshness_score": 0.8,
        "provider_priority": 1,
        "metadata": {},
    }


def _manifest(delivery_url: str) -> dict:
    return {
        "artifact": "FOOTBALL-SHORTS-AI-0048A",
        "status": "PASS",
        "generated_at": "2026-07-30T10:00:00+00:00",
        "source_plan_sha256": "a" * 64,
        "scene_count": 1,
        "selected_asset_count": 1,
        "blocked_scene_count": 0,
        "results": [
            {
                "scene_number": 1,
                "status": "selected",
                "selected": {
                    "candidate": _candidate(delivery_url),
                    "score": 0.9,
                    "decision": "approved",
                    "blockers": [],
                },
                "candidates_considered": 1,
                "rejected_candidates": 0,
                "provider_failures": [],
            }
        ],
    }


def _mp4() -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"video-payload"


def test_materializes_selected_mp4_atomically(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(_mp4())
    workspace = tmp_path / "acquired"

    manifest = materialize_selected_media(
        _manifest(source.as_posix()),
        workspace=workspace,
    )

    assert manifest.status == "PASS"
    assert manifest.delivered_asset_count == 1
    asset = manifest.assets[0]
    target = workspace / "scene-01-owned-library-own-001.mp4"
    assert target.read_bytes() == _mp4()
    assert asset.mime_type == "video/mp4"
    assert asset.size_bytes == len(_mp4())
    assert asset.checksum_sha256 == hashlib.sha256(_mp4()).hexdigest()
    assert not list(workspace.glob("*.tmp"))


def test_rejects_non_pass_acquisition_manifest(tmp_path: Path) -> None:
    payload = _manifest("source.mp4")
    payload["status"] = "BLOCKED"

    with pytest.raises(MediaDeliveryError, match="not PASS"):
        materialize_selected_media(payload, workspace=tmp_path)


def test_rejects_watermarked_candidate(tmp_path: Path) -> None:
    payload = _manifest("source.mp4")
    payload["results"][0]["selected"]["candidate"]["watermark_present"] = True

    with pytest.raises(MediaDeliveryError, match="watermarked"):
        materialize_selected_media(payload, workspace=tmp_path)


def test_rejects_oversized_delivery_without_partial_file(tmp_path: Path) -> None:
    payload = _manifest("https://example.test/video.mp4")

    def opener(_: str):
        return io.BytesIO(_mp4() + b"x" * 128)

    with pytest.raises(MediaDeliveryError, match="maximum governed size"):
        materialize_selected_media(
            payload,
            workspace=tmp_path / "acquired",
            maximum_asset_bytes=16,
            open_url=opener,
        )

    assert not list((tmp_path / "acquired").glob("*"))


def test_rejects_invalid_video_signature(tmp_path: Path) -> None:
    payload = _manifest("https://example.test/video.mp4")

    with pytest.raises(MediaDeliveryError, match="validated MP4"):
        materialize_selected_media(
            payload,
            workspace=tmp_path / "acquired",
            open_url=lambda _: io.BytesIO(b"not-an-mp4"),
        )


def test_writes_delivery_manifest_atomically(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(_mp4())
    manifest = materialize_selected_media(
        _manifest(source.as_posix()),
        workspace=tmp_path / "acquired",
    )
    output = tmp_path / "media_delivery_manifest.json"

    write_delivery_manifest(output, manifest)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["artifact"] == "FOOTBALL-SHORTS-AI-0048C"
    assert payload["status"] == "PASS"
    assert payload["delivered_asset_count"] == 1
    assert not (tmp_path / ".media_delivery_manifest.json.tmp").exists()
