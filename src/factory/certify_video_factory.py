"""FOOTBALL-SHORTS-AI-0060J — Video Factory end-to-end final certification.

Read-only certification of 0060A–0060I. No media acquisition, extraction,
FFmpeg execution, rendering, network access or publication is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    "src/factory/video_factory_preview.py",
    "src/factory/multi_clip_timeline_composer.py",
    "src/factory/subtitle_generation.py",
    "src/factory/voiceover_synchronization.py",
    "src/factory/music_ambience_sfx_mixing.py",
    "src/factory/motion_graphics_overlay.py",
    "src/factory/thumbnail_composition.py",
    "src/factory/final_render_package.py",
    "dashboard/video-preview.html",
    "dashboard/thumbnail-preview.html",
    "dashboard/assets/video-preview.js",
    "dashboard/assets/multi-clip-timeline-composer.js",
    "dashboard/assets/video-subtitle-overlay.js",
    "dashboard/assets/video-voiceover-preview.js",
    "dashboard/assets/video-audio-mix-preview.js",
    "dashboard/assets/video-motion-graphics-overlay.js",
    "dashboard/data/video_factory_preview_manifest.json",
    "dashboard/data/video_factory_subtitle_track.json",
    "dashboard/data/video_factory_voiceover_track.json",
    "dashboard/data/video_factory_audio_mix_track.json",
    "dashboard/data/video_factory_motion_graphics_track.json",
    "dashboard/data/video_factory_thumbnail_composition.json",
    "dashboard/data/video_factory_render_package.json",
)

FORBIDDEN_TRUE_TOKENS = (
    '"network_enabled": true',
    '"acquisition_enabled": true',
    '"extraction_enabled": true',
    '"render_enabled": true',
    '"ffmpeg_execution_enabled": true',
    '"auto_publish": true',
)


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class VideoFactoryCertification:
    certification_id: str
    state: str
    inventory: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    extraction_enabled: bool = False
    render_enabled: bool = False
    ffmpeg_execution_enabled: bool = False
    auto_publish: bool = False

    def unsigned(self) -> dict[str, object]:
        return {
            "schema": "football-shorts-ai.video-factory-certification.v1",
            "certification_id": self.certification_id,
            "state": self.state,
            "inventory": [{"path": p, "sha256": h} for p, h in self.inventory],
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "extraction_enabled": False,
            "render_enabled": False,
            "ffmpeg_execution_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if not self.certification_id.startswith("FACTORYCERT-"):
            raise ValueError("invalid certification identity")
        if self.state not in {"certified", "blocked"}:
            raise ValueError("invalid certification state")
        if self.state == "certified" and self.blockers:
            raise ValueError("certified state cannot contain blockers")
        if self.state == "blocked" and not self.blockers:
            raise ValueError("blocked state requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.extraction_enabled,
                self.render_enabled, self.ffmpeg_execution_enabled, self.auto_publish)):
            raise ValueError("0060J cannot enable operational capabilities")
        if canonical_sha256(self.unsigned()) != self.evidence_sha256:
            raise ValueError("certification evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self.unsigned(), "evidence_sha256": self.evidence_sha256}


def certify(root: Path = ROOT, required_files: Iterable[str] = REQUIRED_FILES) -> VideoFactoryCertification:
    blockers: set[str] = set()
    inventory: list[tuple[str, str]] = []
    for relative in required_files:
        path = root / relative
        if not path.is_file():
            blockers.add(f"REQUIRED_FILE_MISSING:{relative}")
            continue
        data = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_TRUE_TOKENS:
            if token in data.lower():
                blockers.add(f"OPERATIONAL_CAPABILITY_ENABLED:{relative}:{token}")
        inventory.append((relative, file_sha256(path)))

    inventory.sort()
    state = "blocked" if blockers else "certified"
    identity_core = {"inventory": inventory, "blockers": sorted(blockers), "state": state}
    cert_id = f"FACTORYCERT-{canonical_sha256(identity_core)[:20].upper()}"
    unsigned = {
        "schema": "football-shorts-ai.video-factory-certification.v1",
        "certification_id": cert_id,
        "state": state,
        "inventory": [{"path": p, "sha256": h} for p, h in inventory],
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "extraction_enabled": False,
        "render_enabled": False,
        "ffmpeg_execution_enabled": False,
        "auto_publish": False,
    }
    result = VideoFactoryCertification(
        certification_id=cert_id,
        state=state,
        inventory=tuple(inventory),
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


def main() -> int:
    report = certify()
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    print(report.state.upper())
    print("NETWORK_ENABLED=DISABLED")
    print("ACQUISITION_ENABLED=DISABLED")
    print("EXTRACTION_ENABLED=DISABLED")
    print("RENDER_ENABLED=DISABLED")
    print("FFMPEG_EXECUTION_ENABLED=DISABLED")
    print("AUTO_PUBLISH=DISABLED")
    return 0 if report.state == "certified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
