from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from video.rendering import RenderRequest, RenderResult


class DashboardAssetInstallationError(RuntimeError):
    """Raised when governed render outputs cannot be installed safely."""


@dataclass(frozen=True, slots=True)
class DashboardAssetInstallationReceipt:
    artifact: str
    video_id: str
    render_id: str
    video_path: str
    thumbnail_path: str
    subtitles_path: str
    checksum_sha256: str
    size_bytes: int
    status: str = "INSTALLED"

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def install_dashboard_assets(
    request: RenderRequest,
    result: RenderResult,
    *,
    source_workspace: Path,
    dashboard_workspace: Path = Path("dashboard"),
) -> DashboardAssetInstallationReceipt:
    """Transactionally install one complete governed render output set.

    All three outputs are validated in the source workspace before the dashboard is
    touched. Destination files are staged, fsynced and swapped into place. Existing
    files are backed up and restored if any replacement fails.
    """

    _validate_identity(request, result)
    source_root = source_workspace.resolve()
    destination_root = dashboard_workspace.resolve()

    relative_paths = (
        request.output_path,
        request.thumbnail_path,
        request.subtitles_path,
    )
    source_paths = tuple(_confined(source_root, path) for path in relative_paths)
    destination_paths = tuple(_confined(destination_root, path) for path in relative_paths)

    for source in source_paths:
        if not source.is_file() or source.stat().st_size <= 0:
            raise DashboardAssetInstallationError(
                f"missing or empty governed source asset: {source}"
            )

    video_checksum = _sha256(source_paths[0])
    video_size = source_paths[0].stat().st_size
    if video_checksum != result.checksum_sha256:
        raise DashboardAssetInstallationError("source video checksum does not match render result")
    if video_size != result.size_bytes:
        raise DashboardAssetInstallationError("source video size does not match render result")

    staged: list[tuple[Path, Path]] = []
    backups: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    try:
        for source, destination in zip(source_paths, destination_paths):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = _stage_copy(source, destination.parent, destination.name)
            staged.append((temporary, destination))

        for _, destination in staged:
            if destination.exists():
                backup = destination.with_name(f".{destination.name}.0046c.bak")
                backup.unlink(missing_ok=True)
                os.replace(destination, backup)
                backups.append((backup, destination))

        for temporary, destination in staged:
            os.replace(temporary, destination)
            installed.append(destination)

        _fsync_directories({path.parent for path in destination_paths})
    except Exception as exc:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
        for destination in reversed(installed):
            destination.unlink(missing_ok=True)
        for backup, destination in reversed(backups):
            if backup.exists():
                os.replace(backup, destination)
        raise DashboardAssetInstallationError(
            f"dashboard asset installation failed: {type(exc).__name__}: {exc}"
        ) from exc
    else:
        for backup, _ in backups:
            backup.unlink(missing_ok=True)

    installed_checksum = _sha256(destination_paths[0])
    installed_size = destination_paths[0].stat().st_size
    if installed_checksum != video_checksum or installed_size != video_size:
        raise DashboardAssetInstallationError("installed video evidence changed after swap")

    return DashboardAssetInstallationReceipt(
        artifact="FOOTBALL-SHORTS-AI-0046C",
        video_id=request.video_id,
        render_id=request.render_id,
        video_path=request.output_path,
        thumbnail_path=request.thumbnail_path,
        subtitles_path=request.subtitles_path,
        checksum_sha256=installed_checksum,
        size_bytes=installed_size,
    )


def _validate_identity(request: RenderRequest, result: RenderResult) -> None:
    if result.status != "succeeded":
        raise DashboardAssetInstallationError("only succeeded render results may be installed")
    if result.video_id != request.video_id or result.render_id != request.render_id:
        raise DashboardAssetInstallationError("render result identity does not match request")
    actual = (result.output_path, result.thumbnail_path, result.subtitles_path)
    expected = (request.output_path, request.thumbnail_path, request.subtitles_path)
    if actual != expected:
        raise DashboardAssetInstallationError("render output paths do not match request")
    if result.checksum_sha256 is None or result.size_bytes is None:
        raise DashboardAssetInstallationError("render evidence is incomplete")


def _confined(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise DashboardAssetInstallationError("asset path escaped its governed workspace")
    return candidate


def _stage_copy(source: Path, directory: Path, destination_name: str) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination_name}.", suffix=".0046c.tmp", dir=directory
    )
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as reader, os.fdopen(descriptor, "wb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directories(directories: set[Path]) -> None:
    for directory in directories:
        try:
            descriptor = os.open(directory, os.O_RDONLY)
        except OSError:
            continue
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
