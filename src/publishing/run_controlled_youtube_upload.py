"""CLI for one explicitly authorized 0061H upload."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from publishing.controlled_oauth_resumable_upload_activation import execute_authorized_youtube_upload_once
from publishing.controlled_youtube_upload_design import (
    ControlledYouTubeUploadDesign,
    ResumableUploadPolicy,
    YouTubeUploadArtifact,
    YouTubeUploadMetadata,
)


def load_design(payload: dict[str, object]) -> ControlledYouTubeUploadDesign:
    artifact = payload["artifact"]
    metadata = payload["metadata"]
    policy = payload["policy"]
    if not isinstance(artifact, dict) or not isinstance(metadata, dict) or not isinstance(policy, dict):
        raise ValueError("invalid design payload")
    result = ControlledYouTubeUploadDesign(
        schema=str(payload["schema"]),
        design_id=str(payload["design_id"]),
        request_id=str(payload["request_id"]),
        preparation_id=str(payload["preparation_id"]),
        channel_verification_id=str(payload["channel_verification_id"]),
        artifact=YouTubeUploadArtifact(
            video_id=str(artifact["video_id"]),
            video_path=str(artifact["video_path"]),
            video_sha256=str(artifact["video_sha256"]),
            size_bytes=int(artifact["size_bytes"]),
            mime_type=str(artifact.get("mime_type", "video/mp4")),
        ),
        metadata=YouTubeUploadMetadata(
            title=str(metadata["title"]),
            description=str(metadata["description"]),
            tags=tuple(str(v) for v in metadata["tags"]),
            category_id=str(metadata["category_id"]),
            made_for_kids=bool(metadata["made_for_kids"]),
            contains_synthetic_media=bool(metadata["contains_synthetic_media"]),
            initial_privacy=str(metadata["initial_privacy"]),
            scheduled_at=None if metadata.get("scheduled_at") is None else str(metadata["scheduled_at"]),
        ),
        policy=ResumableUploadPolicy(
            protocol=str(policy.get("protocol", "resumable")),
            chunk_size_bytes=int(policy["chunk_size_bytes"]),
            max_attempts=int(policy["max_attempts"]),
            idempotency_required=bool(policy.get("idempotency_required", True)),
            persist_session_uri=False,
            persist_access_token=False,
            network_enabled=False,
            upload_enabled=False,
        ),
        idempotency_key=str(payload["idempotency_key"]),
        post_upload_actions=tuple(str(v) for v in payload["post_upload_actions"]),
        checks={str(k): bool(v) for k, v in dict(payload["checks"]).items()},
        status=str(payload["status"]),
        blockers=tuple(str(v) for v in payload["blockers"]),
        evidence_sha256=str(payload["evidence_sha256"]),
    )
    result.validate()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    binding = json.loads(Path(args.binding).read_text(encoding="utf-8"))
    design = load_design(json.loads(Path(args.design).read_text(encoding="utf-8")))
    result = execute_authorized_youtube_upload_once(
        binding=binding,
        design=design,
        explicit_execute=args.execute,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"UPLOAD_STATUS={result.status}")
    print(f"YOUTUBE_VIDEO_ID={result.youtube_video_id}")
    print("PUBLICATION_PERFORMED=FALSE")
    print("AUTO_PUBLISH=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
