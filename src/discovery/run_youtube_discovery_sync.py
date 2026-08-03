"""
FOOTBALL-SHORTS-AI-0055D
GITHUB ACTIONS YOUTUBE DISCOVERY WORKFLOW ENTRYPOINT

Explicit command-line boundary for one metadata-only YouTube discovery run.
It never prints the API key and never enables download, acquisition, rendering
or publishing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from discovery.execute_youtube_discovery_sync import (
    YouTubeDiscoverySyncPolicy,
    execute_youtube_discovery_sync,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize YouTube metadata into the Football Library")
    parser.add_argument("--query", required=True)
    parser.add_argument("--dashboard-path", default="dashboard/data/football_library.json")
    parser.add_argument("--report-path", default="artifacts/youtube-discovery-sync-report.json")
    parser.add_argument("--catalog-path")
    parser.add_argument("--max-results", type=int, default=12)
    parser.add_argument("--region-code", default="PT")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--video-duration", choices=("any", "short", "medium", "long"), default="short")
    parser.add_argument("--safe-search", choices=("none", "moderate", "strict"), default="moderate")
    parser.add_argument("--activate", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    active = bool(args.activate)
    report = execute_youtube_discovery_sync(
        query=args.query,
        dashboard_path=Path(args.dashboard_path),
        report_path=Path(args.report_path),
        catalog_path=Path(args.catalog_path) if args.catalog_path else None,
        policy=YouTubeDiscoverySyncPolicy(
            enabled=active,
            network_enabled=active,
            secret_resolution_enabled=active,
            dashboard_write_enabled=active,
            max_results=args.max_results,
            region_code=args.region_code,
            relevance_language=args.language,
            video_duration=args.video_duration,
            safe_search=args.safe_search,
        ),
    )
    print(json.dumps({
        "status": report.status,
        "query": report.query,
        "discovered_count": report.discovered_count,
        "library_asset_count": report.library_asset_count,
        "dashboard_written": report.dashboard_written,
        "evidence_sha256": report.evidence_sha256,
    }, sort_keys=True))
    return 0 if report.status in {"SYNCHRONIZED", "NOT_ACTIVATED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
