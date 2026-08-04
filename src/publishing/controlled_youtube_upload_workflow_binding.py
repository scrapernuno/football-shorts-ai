"""FOOTBALL-SHORTS-AI-0061G — manual YouTube upload workflow binding.

Builds a deterministic, fail-closed binding between an approved 0061F publishing
authorization and the names of GitHub Actions OAuth secrets. It never reads secret
values, opens a network connection, uploads a video or publishes content.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping


class YouTubeWorkflowBindingError(ValueError):
    pass


CONFIRMATION_PHRASE = "EXECUTE AUTHORIZED YOUTUBE UPLOAD ONCE"
SUPPORTED_STATES = {"ready_for_manual_dispatch", "blocked"}


def canonical_sha256(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ControlledYouTubeWorkflowBinding:
    schema: str
    binding_id: str
    publishing_authorization_id: str
    render_intake_id: str
    youtube_channel_id: str
    credential_profile: str
    client_id_secret_name: str
    client_secret_secret_name: str
    refresh_token_secret_name: str
    requested_by: str
    execution_note: str
    confirmation_phrase: str
    binding_state: str
    manual_dispatch_allowed: bool
    blockers: tuple[str, ...]
    evidence_sha256: str
    secret_values_read: bool = False
    network_enabled: bool = False
    upload_enabled: bool = False
    publish_enabled: bool = False
    auto_publish: bool = False

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "binding_id": self.binding_id,
            "publishing_authorization_id": self.publishing_authorization_id,
            "render_intake_id": self.render_intake_id,
            "youtube_channel_id": self.youtube_channel_id,
            "credential_profile": self.credential_profile,
            "client_id_secret_name": self.client_id_secret_name,
            "client_secret_secret_name": self.client_secret_secret_name,
            "refresh_token_secret_name": self.refresh_token_secret_name,
            "requested_by": self.requested_by,
            "execution_note": self.execution_note,
            "confirmation_phrase": self.confirmation_phrase,
            "binding_state": self.binding_state,
            "manual_dispatch_allowed": self.manual_dispatch_allowed,
            "blockers": list(self.blockers),
            "secret_values_read": False,
            "network_enabled": False,
            "upload_enabled": False,
            "publish_enabled": False,
            "auto_publish": False,
        }

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.youtube-upload-workflow-binding.v1":
            raise YouTubeWorkflowBindingError("unsupported binding schema")
        if not self.binding_id.startswith("YTWFBIND-"):
            raise YouTubeWorkflowBindingError("invalid binding identity")
        if not self.publishing_authorization_id.startswith("YTPUBAUTH-"):
            raise YouTubeWorkflowBindingError("invalid publishing authorization identity")
        if not self.render_intake_id.startswith("RENDERINTAKE-"):
            raise YouTubeWorkflowBindingError("invalid render intake identity")
        if self.binding_state not in SUPPORTED_STATES:
            raise YouTubeWorkflowBindingError("unsupported binding state")
        if self.binding_state == "ready_for_manual_dispatch":
            if self.blockers or not self.manual_dispatch_allowed:
                raise YouTubeWorkflowBindingError("ready binding must be allowed and unblocked")
        elif self.manual_dispatch_allowed or not self.blockers:
            raise YouTubeWorkflowBindingError("blocked binding must be denied with blockers")
        if any((self.secret_values_read, self.network_enabled, self.upload_enabled, self.publish_enabled, self.auto_publish)):
            raise YouTubeWorkflowBindingError("0061G cannot enable external operations")
        if tuple(sorted(set(self.blockers))) != self.blockers:
            raise YouTubeWorkflowBindingError("blockers must be normalized")
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise YouTubeWorkflowBindingError("workflow binding evidence mismatch")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_controlled_youtube_workflow_binding(
    *,
    publishing_authorization: Mapping[str, object],
    requested_by: str,
    execution_note: str,
    confirmation_phrase: str,
    client_id_secret_name: str,
    client_secret_secret_name: str,
    refresh_token_secret_name: str,
) -> ControlledYouTubeWorkflowBinding:
    blockers: set[str] = set()
    authorization_id = str(publishing_authorization.get("authorization_id", ""))
    render_intake_id = str(publishing_authorization.get("render_intake_id", ""))
    channel_id = str(publishing_authorization.get("youtube_channel_id", ""))
    credential_profile = str(publishing_authorization.get("credential_profile", ""))

    if publishing_authorization.get("authorization_state") != "authorized_for_handover":
        blockers.add("YOUTUBE_PUBLISHING_AUTHORIZATION_NOT_GRANTED")
    if publishing_authorization.get("upload_handover_allowed") is not True:
        blockers.add("YOUTUBE_UPLOAD_HANDOVER_NOT_ALLOWED")
    if not authorization_id.startswith("YTPUBAUTH-"):
        blockers.add("YOUTUBE_PUBLISHING_AUTHORIZATION_ID_INVALID")
    if not render_intake_id.startswith("RENDERINTAKE-"):
        blockers.add("RENDER_INTAKE_ID_INVALID")
    if not channel_id:
        blockers.add("YOUTUBE_CHANNEL_ID_REQUIRED")
    if not credential_profile:
        blockers.add("YOUTUBE_CREDENTIAL_PROFILE_REQUIRED")
    if not requested_by.strip():
        blockers.add("HUMAN_REQUESTER_REQUIRED")
    if not execution_note.strip():
        blockers.add("EXECUTION_NOTE_REQUIRED")
    if confirmation_phrase != CONFIRMATION_PHRASE:
        blockers.add("EXPLICIT_HUMAN_UPLOAD_CONFIRMATION_REQUIRED")

    secret_names = {
        "client_id": client_id_secret_name.strip(),
        "client_secret": client_secret_secret_name.strip(),
        "refresh_token": refresh_token_secret_name.strip(),
    }
    for key, value in secret_names.items():
        if not value:
            blockers.add(f"YOUTUBE_{key.upper()}_SECRET_NAME_REQUIRED")
        elif not value.replace("_", "").isalnum() or value.upper() != value:
            blockers.add(f"YOUTUBE_{key.upper()}_SECRET_NAME_INVALID")

    state = "ready_for_manual_dispatch" if not blockers else "blocked"
    allowed = state == "ready_for_manual_dispatch"
    core = {
        "schema": "football-shorts-ai.youtube-upload-workflow-binding.v1",
        "publishing_authorization_id": authorization_id,
        "render_intake_id": render_intake_id,
        "youtube_channel_id": channel_id,
        "credential_profile": credential_profile,
        "client_id_secret_name": secret_names["client_id"],
        "client_secret_secret_name": secret_names["client_secret"],
        "refresh_token_secret_name": secret_names["refresh_token"],
        "requested_by": requested_by.strip(),
        "execution_note": execution_note.strip(),
        "confirmation_phrase": confirmation_phrase,
        "binding_state": state,
        "manual_dispatch_allowed": allowed,
        "blockers": sorted(blockers),
        "secret_values_read": False,
        "network_enabled": False,
        "upload_enabled": False,
        "publish_enabled": False,
        "auto_publish": False,
    }
    binding_id = f"YTWFBIND-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "binding_id": binding_id}
    result = ControlledYouTubeWorkflowBinding(
        schema=core["schema"],
        binding_id=binding_id,
        publishing_authorization_id=authorization_id,
        render_intake_id=render_intake_id,
        youtube_channel_id=channel_id,
        credential_profile=credential_profile,
        client_id_secret_name=secret_names["client_id"],
        client_secret_secret_name=secret_names["client_secret"],
        refresh_token_secret_name=secret_names["refresh_token"],
        requested_by=requested_by.strip(),
        execution_note=execution_note.strip(),
        confirmation_phrase=confirmation_phrase,
        binding_state=state,
        manual_dispatch_allowed=allowed,
        blockers=tuple(sorted(blockers)),
        evidence_sha256=canonical_sha256(unsigned),
    )
    result.validate()
    return result


__all__ = [
    "CONFIRMATION_PHRASE",
    "ControlledYouTubeWorkflowBinding",
    "YouTubeWorkflowBindingError",
    "build_controlled_youtube_workflow_binding",
    "canonical_sha256",
]
