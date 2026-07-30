from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import tempfile
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Callable, Mapping


class MediaDeliveryError(RuntimeError):
    """Raised when selected media cannot be safely materialized."""


@dataclass(frozen=True, slots=True)
class DeliveredAsset:
    scene_number: int
    provider_id: str
    provider_asset_id: str
    media_type: str
    source_url: str
    local_path: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    license_reference: str
    attribution_text: str | None


@dataclass(frozen=True, slots=True)
class MediaDeliveryManifest:
    artifact: str
    status: str
    source_manifest_sha256: str
    delivered_asset_count: int
    assets: tuple[DeliveredAsset, ...]

    def to_dict(self) -> dict:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "source_manifest_sha256": self.source_manifest_sha256,
            "delivered_asset_count": self.delivered_asset_count,
            "assets": [asdict(asset) for asset in self.assets],
        }


OpenUrl = Callable[[str], BinaryIO]


def materialize_selected_media(
    acquisition_manifest: Mapping,
    *,
    workspace: Path = Path("output/assets/acquired"),
    maximum_asset_bytes: int = 100 * 1024 * 1024,
    open_url: OpenUrl | None = None,
) -> MediaDeliveryManifest:
    if maximum_asset_bytes <= 0:
        raise ValueError("maximum_asset_bytes must be positive")
    if acquisition_manifest.get("status") != "PASS":
        raise MediaDeliveryError("acquisition manifest is not PASS")
    results = acquisition_manifest.get("results")
    if not isinstance(results, list) or not results:
        raise MediaDeliveryError("acquisition manifest requires results")

    root = workspace.resolve()
    root.mkdir(parents=True, exist_ok=True)
    delivered: list[DeliveredAsset] = []
    opener = open_url or _default_open_url

    for result in results:
        if not isinstance(result, dict) or result.get("status") != "selected":
            raise MediaDeliveryError("all scenes must contain a selected asset")
        selected = result.get("selected")
        candidate = selected.get("candidate") if isinstance(selected, dict) else None
        if not isinstance(candidate, dict):
            raise MediaDeliveryError("selected candidate evidence is missing")
        delivered.append(
            _materialize_candidate(
                int(result.get("scene_number")),
                candidate,
                root=root,
                maximum_asset_bytes=maximum_asset_bytes,
                open_url=opener,
            )
        )

    return MediaDeliveryManifest(
        artifact="FOOTBALL-SHORTS-AI-0048C",
        status="PASS",
        source_manifest_sha256=_canonical_sha256(acquisition_manifest),
        delivered_asset_count=len(delivered),
        assets=tuple(delivered),
    )


def _materialize_candidate(
    scene_number: int,
    candidate: Mapping,
    *,
    root: Path,
    maximum_asset_bytes: int,
    open_url: OpenUrl,
) -> DeliveredAsset:
    if scene_number <= 0:
        raise MediaDeliveryError("scene_number must be positive")
    provider_id = _text(candidate, "provider_id")
    provider_asset_id = _text(candidate, "provider_asset_id")
    media_type = _text(candidate, "media_type")
    delivery_url = _text(candidate, "delivery_url")
    license_reference = _text(candidate, "license_reference")
    if candidate.get("rights_status") != "approved":
        raise MediaDeliveryError("rights_status must be approved")
    if candidate.get("watermark_present") is True:
        raise MediaDeliveryError("watermarked media cannot be delivered")
    if candidate.get("cross_platform_allowed") is not True:
        raise MediaDeliveryError("cross-platform permission is required")
    if candidate.get("original_file_available") is not True:
        raise MediaDeliveryError("original file is required")

    extension = _safe_extension(delivery_url, media_type)
    filename = f"scene-{scene_number:02d}-{_slug(provider_id)}-{_slug(provider_asset_id)}{extension}"
    target = (root / filename).resolve()
    if root != target.parent:
        raise MediaDeliveryError("delivery target escaped governed workspace")

    digest = hashlib.sha256()
    size = 0
    fd, temporary_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".tmp", dir=root)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as output, open_url(delivery_url) as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > maximum_asset_bytes:
                    raise MediaDeliveryError("asset exceeds maximum governed size")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if size <= 0:
            raise MediaDeliveryError("delivered asset is empty")
        mime_type = _detect_mime(temporary, extension)
        _validate_media_signature(temporary, media_type, mime_type)
        os.replace(temporary, target)
        _fsync_directory(root)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return DeliveredAsset(
        scene_number=scene_number,
        provider_id=provider_id,
        provider_asset_id=provider_asset_id,
        media_type=media_type,
        source_url=delivery_url,
        local_path=target.relative_to(Path.cwd().resolve()).as_posix() if Path.cwd().resolve() in target.parents else target.as_posix(),
        mime_type=mime_type,
        size_bytes=size,
        checksum_sha256=digest.hexdigest(),
        license_reference=license_reference,
        attribution_text=candidate.get("attribution_text") if isinstance(candidate.get("attribution_text"), str) else None,
    )


def write_delivery_manifest(path: Path, manifest: MediaDeliveryManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    temporary.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _default_open_url(value: str) -> BinaryIO:
    if value.startswith("file://"):
        return Path(value[7:]).open("rb")
    path = Path(value)
    if path.is_file():
        return path.open("rb")
    if not value.startswith("https://"):
        raise MediaDeliveryError("only local files or HTTPS delivery URLs are allowed")
    return urllib.request.urlopen(value, timeout=45)  # nosec B310: HTTPS enforced above


def _safe_extension(url: str, media_type: str) -> str:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    allowed = {"video": {".mp4", ".mov", ".webm"}, "image": {".jpg", ".jpeg", ".png", ".webp"}}
    if media_type not in allowed or suffix not in allowed[media_type]:
        raise MediaDeliveryError(f"unsupported {media_type} delivery extension: {suffix or '<none>'}")
    return suffix


def _detect_mime(path: Path, extension: str) -> str:
    header = path.read_bytes()[:16]
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "image/webp"
    guessed = mimetypes.types_map.get(extension)
    if guessed:
        return guessed
    raise MediaDeliveryError("unable to determine delivered asset MIME type")


def _validate_media_signature(path: Path, media_type: str, mime_type: str) -> None:
    if media_type == "video" and mime_type != "video/mp4":
        raise MediaDeliveryError("only validated MP4 video delivery is currently supported")
    if media_type == "image" and not mime_type.startswith("image/"):
        raise MediaDeliveryError("delivered image signature is invalid")


def _text(payload: Mapping, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MediaDeliveryError(f"{key} must be a non-empty string")
    return value.strip()


def _slug(value: str) -> str:
    cleaned = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in cleaned.split("-") if part) or "asset"


def _canonical_sha256(payload: Mapping) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize selected governed media assets.")
    parser.add_argument("--manifest", default="output/media_acquisition_manifest.json")
    parser.add_argument("--workspace", default="output/assets/acquired")
    parser.add_argument("--output", default="output/media_delivery_manifest.json")
    parser.add_argument("--maximum-asset-bytes", type=int, default=100 * 1024 * 1024)
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = materialize_selected_media(payload, workspace=Path(args.workspace), maximum_asset_bytes=args.maximum_asset_bytes)
    write_delivery_manifest(Path(args.output), manifest)
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
