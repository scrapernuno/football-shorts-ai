from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from discovery.certify_live_youtube_dashboard import (
    LiveYouTubeDashboardCertificationError,
    certify_live_youtube_dashboard,
)


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def _payload(*, render_allowed: bool = False) -> bytes:
    value = {
        "library": {
            "assets": [
                {
                    "provider": "youtube",
                    "provider_asset_id": "video-one",
                    "rights_status": "reference_only",
                    "preview_allowed": True,
                    "render_allowed": render_allowed,
                    "acquisition_allowed": False,
                }
            ]
        }
    }
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def test_local_certification(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload())

    result = certify_live_youtube_dashboard(library_path=path)

    assert result.status == "LOCAL_CERTIFIED"
    assert result.asset_count == 1
    assert result.youtube_asset_count == 1
    assert result.public_verified is False
    assert result.download_enabled is False
    assert result.acquisition_enabled is False
    assert result.render_enabled is False
    assert result.publishing_enabled is False


def test_live_certification_requires_identical_public_library(tmp_path: Path) -> None:
    payload = _payload()
    path = tmp_path / "football_library.json"
    path.write_bytes(payload)

    result = certify_live_youtube_dashboard(
        library_path=path,
        public_library_url="https://example.test/data/football_library.json",
        open_url=lambda url, timeout: Response(payload),
    )

    assert result.status == "LIVE_CERTIFIED"
    assert result.public_verified is True
    assert result.public_library_sha256 == result.library_sha256


def test_public_mismatch_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload())
    different = _payload().replace(b"video-one", b"video-two")

    result = certify_live_youtube_dashboard(
        library_path=path,
        public_library_url="https://example.test/data/football_library.json",
        open_url=lambda url, timeout: Response(different),
    )

    assert result.status == "BLOCKED"
    assert result.blockers == ("PUBLIC_LIBRARY_SHA256_MISMATCH",)


def test_public_failure_is_redacted_and_blocked(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload())

    def fail(url, timeout):
        raise OSError("network detail")

    result = certify_live_youtube_dashboard(
        library_path=path,
        public_library_url="https://example.test/data/football_library.json",
        open_url=fail,
    )

    assert result.status == "BLOCKED"
    assert result.blockers == ("PUBLIC_LIBRARY_VERIFICATION_FAILED",)


def test_unsafe_youtube_asset_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload(render_allowed=True))

    with pytest.raises(LiveYouTubeDashboardCertificationError, match="rendering"):
        certify_live_youtube_dashboard(library_path=path)


def test_minimum_asset_count_is_enforced(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload())

    with pytest.raises(LiveYouTubeDashboardCertificationError, match="minimum"):
        certify_live_youtube_dashboard(library_path=path, minimum_assets=2)


def test_replay_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "football_library.json"
    path.write_bytes(_payload())

    first = certify_live_youtube_dashboard(library_path=path)
    second = certify_live_youtube_dashboard(library_path=path)

    assert first.to_dict() == second.to_dict()
