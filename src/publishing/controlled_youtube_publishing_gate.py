"""FOOTBALL-SHORTS-AI-0061F — controlled YouTube upload authorization gate.

Builds a deterministic, fail-closed handover from an approved 0061E render review
to the already certified controlled YouTube resumable upload runtime. This module
does not access credentials, call Google APIs, upload media or publish content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


class ControlledYouTubePublishingGateError(ValueError):
    pass


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class ControlledYouTubePublishingAuthorization:
    schema: str
    authorization_id: str
    render_review_id: str
    render_output_uri: str
    render_output_sha256: str
    requested_by: str
    authorization_note: str
    channel_id: str
    title: str
    description: str
    tags: tuple[str, ...]
    privacy_status: str
    made_for_kids: bool
    credential_profile: str
    authorization_state: str
    upload_handover_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    credential_access_enabled: bool = False
    upload_enabled: bool = False
    publish_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authorization_id": self.authorization_id,
            "render_review_id": self.render_review_id,
            "render_output_uri": self.render_output_uri,
            "render_output_sha256": self.render_output_sha256,
            "requested_by": self.requested_by,
            "authorization_note": self.authorization_note,
            "channel_id": self.channel_id,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "privacy_status": self.privacy_status,
            "made_for_kids": self.made_for_kids,
            "credential_profile": self.credential_profile,
            "authorization_state": self.authorization_state,
            "upload_handover_allowed": self.upload_handover_allowed,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "credential_access_enabled": False,
            "upload_enabled": False,
            "publish_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.controlled-youtube-publishing-authorization.v1":
            raise ControlledYouTubePublishingGateError("unsupported schema")
        if not self.authorization_id.startswith("YTPUBAUTH-"):
            raise ControlledYouTubePublishingGateError("invalid authorization identity")
        if self.authorization_state not in {"authorized_for_handover", "review_required", "blocked"}:
            raise ControlledYouTubePublishingGateError("unsupported authorization state")
        if self.privacy_status not in {"private", "unlisted", "public"}:
            raise ControlledYouTubePublishingGateError("unsupported privacy status")
        if self.authorization_state == "authorized_for_handover":
            if self.blockers or not self.upload_handover_allowed:
                raise ControlledYouTubePublishingGateError("authorized handover must be unblocked")
        elif self.upload_handover_allowed or not self.blockers:
            raise ControlledYouTubePublishingGateError("non-authorized handover must remain blocked")
        if any((self.network_enabled, self.credential_access_enabled, self.upload_enabled, self.publish_enabled, self.auto_publish)):
            raise ControlledYouTubePublishingGateError("0061F cannot enable operational capabilities")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise ControlledYouTubePublishingGateError("evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_youtube_publishing_authorization(
    *,
    handover: Mapping[str, object],
    requested_by: str,
    authorization_note: str,
    channel_id: str,
    credential_profile: str,
    explicit_human_command: bool,
) -> ControlledYouTubePublishingAuthorization:
    blockers: set[str] = set()
    review_id = str(handover.get("render_review_id") or handover.get("intake_id") or "")
    output_uri = str(handover.get("output_uri", ""))
    output_sha = str(handover.get("output_sha256", "")).lower()
    title = str(handover.get("title", "")).strip()
    description = str(handover.get("description", "")).strip()
    tags = tuple(sorted({str(item).strip() for item in handover.get("tags", ()) if str(item).strip()}))
    privacy = str(handover.get("privacy_status", "private"))

    if handover.get("handover_state") != "approved_for_handover" or handover.get("publishing_handover_allowed") is not True:
        blockers.add("PUBLISHING_HANDOVER_NOT_APPROVED")
    if not output_uri:
        blockers.add("RENDER_OUTPUT_URI_MISSING")
    if len(output_sha) != 64 or any(c not in "0123456789abcdef" for c in output_sha):
        blockers.add("RENDER_OUTPUT_SHA256_INVALID")
    if not requested_by.strip():
        blockers.add("HUMAN_REQUESTER_REQUIRED")
    if not authorization_note.strip():
        blockers.add("AUTHORIZATION_NOTE_REQUIRED")
    if not channel_id.strip():
        blockers.add("YOUTUBE_CHANNEL_ID_REQUIRED")
    if not credential_profile.strip():
        blockers.add("YOUTUBE_CREDENTIAL_PROFILE_REQUIRED")
    if not explicit_human_command:
        blockers.add("EXPLICIT_HUMAN_UPLOAD_COMMAND_REQUIRED")
    if not title:
        blockers.add("YOUTUBE_TITLE_REQUIRED")
    if not description:
        blockers.add("YOUTUBE_DESCRIPTION_REQUIRED")
    if privacy not in {"private", "unlisted", "public"}:
        blockers.add("YOUTUBE_PRIVACY_STATUS_INVALID")

    state = "authorized_for_handover" if not blockers else "blocked" if "PUBLISHING_HANDOVER_NOT_APPROVED" in blockers else "review_required"
    core = {
        "schema": "football-shorts-ai.controlled-youtube-publishing-authorization.v1",
        "render_review_id": review_id,
        "render_output_uri": output_uri,
        "render_output_sha256": output_sha,
        "requested_by": requested_by.strip(),
        "authorization_note": authorization_note.strip(),
        "channel_id": channel_id.strip(),
        "title": title,
        "description": description,
        "tags": list(tags),
        "privacy_status": privacy,
        "made_for_kids": bool(handover.get("made_for_kids", False)),
        "credential_profile": credential_profile.strip(),
        "authorization_state": state,
        "upload_handover_allowed": state == "authorized_for_handover",
        "blockers": sorted(blockers),
        "network_enabled": False,
        "credential_access_enabled": False,
        "upload_enabled": False,
        "publish_enabled": False,
        "auto_publish": False,
    }
    authorization_id = f"YTPUBAUTH-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "authorization_id": authorization_id}
    result = ControlledYouTubePublishingAuthorization(
        schema=core["schema"], authorization_id=authorization_id,
        render_review_id=review_id, render_output_uri=output_uri,
        render_output_sha256=output_sha, requested_by=requested_by.strip(),
        authorization_note=authorization_note.strip(), channel_id=channel_id.strip(),
        title=title, description=description, tags=tags, privacy_status=privacy,
        made_for_kids=bool(handover.get("made_for_kids", False)),
        credential_profile=credential_profile.strip(), authorization_state=state,
        upload_handover_allowed=state == "authorized_for_handover",
        blockers=tuple(sorted(blockers)), evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = ["ControlledYouTubePublishingAuthorization", "ControlledYouTubePublishingGateError", "build_controlled_youtube_publishing_authorization", "canonical_sha256"]
