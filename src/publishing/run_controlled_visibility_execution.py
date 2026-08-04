"""CLI for one controlled 0062B YouTube visibility execution."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from publishing.controlled_visibility_execution import execute_controlled_visibility_change
from publishing.youtube_visibility_oauth_adapter import OAuthCredentialValues, YouTubeVisibilityOAuthAdapter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    adapter = YouTubeVisibilityOAuthAdapter(
        credentials=OAuthCredentialValues(
            client_id=os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", ""),
            client_secret=os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", ""),
            refresh_token=os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", ""),
        )
    )
    try:
        result = execute_controlled_visibility_change(
            decision=decision,
            execution_confirmation=args.confirmation,
            update_visibility=adapter.update_visibility,
            verify_visibility=adapter.verify_visibility,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"EXECUTION_STATE={result.execution_state}")
        print(f"VISIBILITY_CHANGE_EXECUTED={str(result.visibility_change_executed).upper()}")
        print(f"VERIFIED_VISIBILITY={result.verified_visibility}")
        print("CREDENTIALS_PERSISTED=FALSE")
        print("AUTO_PUBLISH=FALSE")
        return 0 if result.execution_state in {"published", "no_change"} else 1
    finally:
        adapter.clear_ephemeral_token()


if __name__ == "__main__":
    raise SystemExit(main())
