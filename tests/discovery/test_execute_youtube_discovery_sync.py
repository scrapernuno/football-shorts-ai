from __future__ import annotations

import io
import json
import urllib.parse
from pathlib import Path

import pytest

from discovery.execute_youtube_discovery_sync import (
    YouTubeDiscoverySyncError,
    YouTubeDiscoverySyncPolicy,
    execute_youtube_discovery_sync,
)


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class FakeYouTube:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, request, *, timeout):
        self.urls.append(request.full_url)
        parsed = urllib.parse.urlparse(request.full_url)
        query = urllib.parse.parse_qs(parsed.query)
        assert query["key"] == ["secret-api-key"]
        if parsed.path.endswith("/search"):
            payload = {
                "items": [
                    {"id": {"videoId": "video-one"}},
                    {"id": {"videoId": "video-two"}},
                ]
            }
        elif parsed.path.endswith("/videos"):
            payload = {
                "items": [
                    _video("video-one", "Great goal", "PT12S", "1500", "75"),
                    _video("video-two", "Brilliant save", "PT18S", "900", "30"),
                ]
            }
        else:
            raise AssertionError(parsed.path)
        return Response(json.dumps(payload).encode("utf-8"))


def _video(video_id: str, title: str, duration: str, views: str, likes: str):
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "description": "Football highlight metadata",
            "channelTitle": "Football Channel",
            "channelId": "channel-one",
            "publishedAt": "2026-08-01T12:00:00Z",
            "defaultLanguage": "pt",
            "tags": ["football", "goal"],
            "thumbnails": {
                "high": {"url": f"https://example.test/{video_id}.jpg"}
            },
        },
        "contentDetails": {"duration": duration},
        "statistics": {"viewCount": views, "likeCount": likes},
        "status": {"embeddable": True},
    }


def _enabled_policy() -> YouTubeDiscoverySyncPolicy:
    return YouTubeDiscoverySyncPolicy(
        enabled=True,
        network_enabled=True,
        secret_resolution_enabled=True,
        dashboard_write_enabled=True,
        max_results=5,
    )


def test_not_activated_writes_report_without_network_or_dashboard(tmp_path: Path) -> None:
    dashboard = tmp_path / "dashboard" / "data" / "football_library.json"
    report_path = tmp_path / "report.json"
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    report = execute_youtube_discovery_sync(
        query="Cristiano Ronaldo",
        dashboard_path=dashboard,
        report_path=report_path,
        policy=YouTubeDiscoverySyncPolicy(),
        open_url=forbidden,
    )

    assert report.status == "NOT_ACTIVATED"
    assert report.network_used is False
    assert report.dashboard_written is False
    assert called is False
    assert not dashboard.exists()
    assert json.loads(report_path.read_text())["status"] == "NOT_ACTIVATED"


def test_controlled_execution_discovers_and_synchronizes_dashboard(tmp_path: Path) -> None:
    dashboard = tmp_path / "dashboard" / "data" / "football_library.json"
    report_path = tmp_path / "sync-report.json"
    fake = FakeYouTube()

    report = execute_youtube_discovery_sync(
        query="Champions League goals",
        dashboard_path=dashboard,
        report_path=report_path,
        policy=_enabled_policy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret-api-key"},
        discovered_at="2026-08-03T11:00:00Z",
        open_url=fake,
        sleep=lambda _: None,
    )

    assert report.status == "SYNCHRONIZED"
    assert report.discovered_count == 2
    assert report.library_asset_count == 2
    assert report.network_used is True
    assert report.dashboard_written is True
    assert len(fake.urls) == 2

    payload = json.loads(dashboard.read_text())
    assets = payload["library"]["assets"]
    assert len(assets) == 2
    assert {asset["provider_asset_id"] for asset in assets} == {"video-one", "video-two"}
    assert all(asset["rights_status"] == "reference_only" for asset in assets)
    assert all(asset["preview_allowed"] is True for asset in assets)
    assert all(asset["render_allowed"] is False for asset in assets)
    assert all(asset["acquisition_allowed"] is False for asset in assets)


def test_secret_is_not_persisted_in_dashboard_or_report(tmp_path: Path) -> None:
    dashboard = tmp_path / "football_library.json"
    report_path = tmp_path / "report.json"

    execute_youtube_discovery_sync(
        query="football",
        dashboard_path=dashboard,
        report_path=report_path,
        policy=_enabled_policy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret-api-key"},
        discovered_at="2026-08-03T11:00:00Z",
        open_url=FakeYouTube(),
        sleep=lambda _: None,
    )

    assert "secret-api-key" not in dashboard.read_text()
    assert "secret-api-key" not in report_path.read_text()


def test_missing_secret_blocks_without_writing_dashboard(tmp_path: Path) -> None:
    dashboard = tmp_path / "football_library.json"
    report_path = tmp_path / "report.json"

    report = execute_youtube_discovery_sync(
        query="football",
        dashboard_path=dashboard,
        report_path=report_path,
        policy=_enabled_policy(),
        environment={},
        open_url=FakeYouTube(),
        sleep=lambda _: None,
    )

    assert report.status == "BLOCKED"
    assert report.dashboard_written is False
    assert not dashboard.exists()
    assert report.blockers == ("CONTROLLED_EXECUTION_FAILED:YouTubeDataApiHttpError",)


def test_empty_search_is_blocked_and_dashboard_is_not_written(tmp_path: Path) -> None:
    class EmptySearch:
        def __call__(self, request, *, timeout):
            return Response(json.dumps({"items": []}).encode("utf-8"))

    dashboard = tmp_path / "football_library.json"
    report = execute_youtube_discovery_sync(
        query="nothing",
        dashboard_path=dashboard,
        report_path=tmp_path / "report.json",
        policy=_enabled_policy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret-api-key"},
        open_url=EmptySearch(),
        sleep=lambda _: None,
    )

    assert report.status == "BLOCKED"
    assert "YOUTUBE_SEARCH_RETURNED_NO_VIDEO_IDS" in report.blockers
    assert report.dashboard_written is False
    assert not dashboard.exists()


def test_replay_is_deterministic_for_fixed_inputs(tmp_path: Path) -> None:
    first = execute_youtube_discovery_sync(
        query="football",
        dashboard_path=tmp_path / "a" / "football_library.json",
        report_path=tmp_path / "a" / "report.json",
        policy=_enabled_policy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret-api-key"},
        discovered_at="2026-08-03T11:00:00Z",
        open_url=FakeYouTube(),
        sleep=lambda _: None,
    )
    second = execute_youtube_discovery_sync(
        query="football",
        dashboard_path=tmp_path / "a" / "football_library.json",
        report_path=tmp_path / "b" / "report.json",
        policy=_enabled_policy(),
        environment={"YOUTUBE_DATA_API_KEY": "secret-api-key"},
        discovered_at="2026-08-03T11:00:00Z",
        open_url=FakeYouTube(),
        sleep=lambda _: None,
    )

    assert first.to_dict() == second.to_dict()


def test_policy_rejects_unsafe_capabilities() -> None:
    with pytest.raises(YouTubeDiscoverySyncError, match="forbidden"):
        YouTubeDiscoverySyncPolicy(
            download_enabled=True,
        ).validate()

    with pytest.raises(YouTubeDiscoverySyncError, match="requires"):
        YouTubeDiscoverySyncPolicy(enabled=True).validate()
