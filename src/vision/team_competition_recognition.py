"""
FOOTBALL-SHORTS-AI-0057C
TEAM, CLUB AND COMPETITION RECOGNITION EVIDENCE CONTRACT

Builds deterministic team and competition hypotheses from governed 0057A vision
and optional 0057B player-recognition evidence. No network, acquisition, external
model execution, training, rendering or publication is performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from vision.football_vision_pipeline import FootballVisionReport
from vision.player_recognition import PlayerRecognitionReport


class TeamCompetitionRecognitionError(ValueError):
    """Raised when governed team/competition evidence is invalid."""


SUPPORTED_SIGNAL_TYPES = {"kit", "crest", "scoreboard", "stadium", "broadcast_graphic", "player_track"}
SUPPORTED_ENTITY_TYPES = {"team", "club", "national_team", "competition"}
SUPPORTED_STATES = {"recognized", "review_required", "blocked"}


@dataclass(frozen=True)
class EntitySignal:
    signal_id: str
    signal_type: str
    scene_id: str
    frame_id: str
    entity_type: str
    label: str
    confidence: float
    source_track_id: str | None
    evidence_labels: tuple[str, ...]

    def validate(self, vision: FootballVisionReport, players: PlayerRecognitionReport | None) -> None:
        if not self.signal_id.startswith("ENTITYSIG-"):
            raise TeamCompetitionRecognitionError("invalid entity signal identity")
        if self.signal_type not in SUPPORTED_SIGNAL_TYPES:
            raise TeamCompetitionRecognitionError("unsupported signal type")
        if self.entity_type not in SUPPORTED_ENTITY_TYPES:
            raise TeamCompetitionRecognitionError("unsupported entity type")
        if self.scene_id not in {item.scene_id for item in vision.scenes}:
            raise TeamCompetitionRecognitionError("signal references unknown scene")
        if self.frame_id not in {item.frame_id for item in vision.frames}:
            raise TeamCompetitionRecognitionError("signal references unknown frame")
        if not self.label.strip():
            raise TeamCompetitionRecognitionError("signal label is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise TeamCompetitionRecognitionError("signal confidence must be between 0 and 1")
        if tuple(sorted(set(self.evidence_labels))) != self.evidence_labels:
            raise TeamCompetitionRecognitionError("signal evidence labels must be normalized")
        if self.source_track_id is not None:
            if players is None or self.source_track_id not in {item.track_id for item in players.tracks}:
                raise TeamCompetitionRecognitionError("signal references unknown player track")

    def to_dict(self) -> dict[str, object]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "scene_id": self.scene_id,
            "frame_id": self.frame_id,
            "entity_type": self.entity_type,
            "label": self.label,
            "confidence": round(float(self.confidence), 4),
            "source_track_id": self.source_track_id,
            "evidence_labels": list(self.evidence_labels),
        }


@dataclass(frozen=True)
class RecognizedEntity:
    entity_id: str
    entity_type: str
    label: str
    confidence: float
    signal_ids: tuple[str, ...]
    review_required: bool

    def validate(self, signal_ids: set[str]) -> None:
        if not self.entity_id.startswith("RECOGENTITY-"):
            raise TeamCompetitionRecognitionError("invalid recognized entity identity")
        if self.entity_type not in SUPPORTED_ENTITY_TYPES:
            raise TeamCompetitionRecognitionError("unsupported entity type")
        if not self.label.strip() or not 0.0 <= self.confidence <= 1.0:
            raise TeamCompetitionRecognitionError("recognized entity is invalid")
        if not self.signal_ids or any(item not in signal_ids for item in self.signal_ids):
            raise TeamCompetitionRecognitionError("recognized entity requires valid signals")

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "label": self.label,
            "confidence": round(float(self.confidence), 4),
            "signal_ids": list(self.signal_ids),
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class TeamCompetitionRecognitionReport:
    schema: str
    recognition_id: str
    vision_report_id: str
    player_recognition_id: str | None
    provider_name: str
    signals: tuple[EntitySignal, ...]
    entities: tuple[RecognizedEntity, ...]
    team_labels: tuple[str, ...]
    competition_labels: tuple[str, ...]
    recognition_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    network_enabled: bool = False
    acquisition_enabled: bool = False
    model_training_enabled: bool = False
    render_enabled: bool = False
    auto_publish: bool = False

    def validate(self, vision: FootballVisionReport, players: PlayerRecognitionReport | None = None) -> None:
        vision.validate()
        if players is not None:
            players.validate(vision)
        if self.schema != "football-shorts-ai.team-competition-recognition.v1":
            raise TeamCompetitionRecognitionError("unsupported recognition schema")
        if not self.recognition_id.startswith("TEAMCOMP-"):
            raise TeamCompetitionRecognitionError("invalid recognition identity")
        if self.vision_report_id != vision.report_id:
            raise TeamCompetitionRecognitionError("vision report identity mismatch")
        expected_player_id = None if players is None else players.recognition_id
        if self.player_recognition_id != expected_player_id:
            raise TeamCompetitionRecognitionError("player recognition identity mismatch")
        if not self.provider_name.strip() or self.recognition_state not in SUPPORTED_STATES:
            raise TeamCompetitionRecognitionError("invalid provider or state")
        signal_ids = {item.signal_id for item in self.signals}
        if len(signal_ids) != len(self.signals):
            raise TeamCompetitionRecognitionError("signal identities must be unique")
        for item in self.signals:
            item.validate(vision, players)
        for item in self.entities:
            item.validate(signal_ids)
        expected_teams = tuple(sorted({item.label for item in self.entities if item.entity_type in {"team", "club", "national_team"}}))
        expected_competitions = tuple(sorted({item.label for item in self.entities if item.entity_type == "competition"}))
        if self.team_labels != expected_teams or self.competition_labels != expected_competitions:
            raise TeamCompetitionRecognitionError("recognized labels are inconsistent")
        if self.recognition_state == "recognized" and (self.blockers or not self.entities):
            raise TeamCompetitionRecognitionError("recognized report requires unblocked entities")
        if self.recognition_state in {"review_required", "blocked"} and not self.blockers:
            raise TeamCompetitionRecognitionError("non-ready report requires blockers")
        if any((self.network_enabled, self.acquisition_enabled, self.model_training_enabled, self.render_enabled, self.auto_publish)):
            raise TeamCompetitionRecognitionError("0057C cannot enable operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise TeamCompetitionRecognitionError("team/competition evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "recognition_id": self.recognition_id,
            "vision_report_id": self.vision_report_id,
            "player_recognition_id": self.player_recognition_id,
            "provider_name": self.provider_name,
            "signals": [item.to_dict() for item in self.signals],
            "entities": [item.to_dict() for item in self.entities],
            "team_labels": list(self.team_labels),
            "competition_labels": list(self.competition_labels),
            "recognition_state": self.recognition_state,
            "blockers": list(self.blockers),
            "network_enabled": False,
            "acquisition_enabled": False,
            "model_training_enabled": False,
            "render_enabled": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_team_competition_recognition_report(
    *,
    vision: FootballVisionReport,
    provider_name: str,
    signals: Sequence[Mapping[str, object]] = (),
    players: PlayerRecognitionReport | None = None,
    minimum_confidence: float = 0.75,
) -> TeamCompetitionRecognitionReport:
    vision.validate()
    if players is not None:
        players.validate(vision)
    if not 0.0 <= minimum_confidence <= 1.0:
        raise TeamCompetitionRecognitionError("minimum_confidence must be between 0 and 1")
    parsed = tuple(_signal(item) for item in signals)
    blockers: set[str] = set()
    if vision.pipeline_state != "analyzed":
        blockers.add("VISION_REPORT_NOT_ANALYZED")
    if vision.pipeline_state == "analyzed" and not parsed:
        blockers.add("TEAM_COMPETITION_EVIDENCE_MISSING")
    entities = _entities(parsed, minimum_confidence)
    if any(item.review_required for item in entities):
        blockers.add("ENTITY_REVIEW_REQUIRED")
    if not any(item.entity_type in {"team", "club", "national_team"} for item in entities):
        blockers.add("TEAM_IDENTITY_MISSING")
    if not any(item.entity_type == "competition" for item in entities):
        blockers.add("COMPETITION_IDENTITY_MISSING")
    state = "blocked" if vision.pipeline_state != "analyzed" or not parsed else ("review_required" if blockers else "recognized")
    team_labels = tuple(sorted({item.label for item in entities if item.entity_type in {"team", "club", "national_team"}}))
    competition_labels = tuple(sorted({item.label for item in entities if item.entity_type == "competition"}))
    core = {
        "schema": "football-shorts-ai.team-competition-recognition.v1",
        "vision_report_id": vision.report_id,
        "player_recognition_id": None if players is None else players.recognition_id,
        "provider_name": provider_name.strip(),
        "signals": [item.to_dict() for item in parsed],
        "entities": [item.to_dict() for item in entities],
        "team_labels": list(team_labels),
        "competition_labels": list(competition_labels),
        "recognition_state": state,
        "blockers": sorted(blockers),
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    recognition_id = f"TEAMCOMP-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "recognition_id": recognition_id}
    result = TeamCompetitionRecognitionReport(
        recognition_id=recognition_id,
        evidence_sha256=canonical_sha256(unsigned),
        signals=parsed,
        entities=entities,
        team_labels=team_labels,
        competition_labels=competition_labels,
        blockers=tuple(sorted(blockers)),
        schema=core["schema"],
        vision_report_id=vision.report_id,
        player_recognition_id=None if players is None else players.recognition_id,
        provider_name=provider_name.strip(),
        recognition_state=state,
    )
    result.validate(vision, players)
    return result


def _signal(item: Mapping[str, object]) -> EntitySignal:
    core = {
        "signal_type": str(item["signal_type"]),
        "scene_id": str(item["scene_id"]),
        "frame_id": str(item["frame_id"]),
        "entity_type": str(item["entity_type"]),
        "label": str(item["label"]).strip(),
        "confidence": float(item.get("confidence", 0.0)),
        "source_track_id": None if item.get("source_track_id") is None else str(item["source_track_id"]),
        "evidence_labels": tuple(sorted(set(str(value).strip().lower().replace(" ", "_") for value in item.get("evidence_labels", ()) if str(value).strip()))),
    }
    serializable = {**core, "evidence_labels": list(core["evidence_labels"])}
    return EntitySignal(signal_id=f"ENTITYSIG-{canonical_sha256(serializable)[:20].upper()}", **core)


def _entities(signals: Sequence[EntitySignal], minimum_confidence: float) -> tuple[RecognizedEntity, ...]:
    grouped: dict[tuple[str, str], list[EntitySignal]] = {}
    for item in signals:
        grouped.setdefault((item.entity_type, item.label), []).append(item)
    values: list[RecognizedEntity] = []
    for (entity_type, label), items in sorted(grouped.items()):
        confidence = round(sum(item.confidence for item in items) / len(items), 4)
        core = {"entity_type": entity_type, "label": label, "confidence": confidence, "signal_ids": tuple(item.signal_id for item in items), "review_required": confidence < minimum_confidence}
        serializable = {**core, "signal_ids": list(core["signal_ids"])}
        values.append(RecognizedEntity(entity_id=f"RECOGENTITY-{canonical_sha256(serializable)[:20].upper()}", **core))
    return tuple(values)


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise TeamCompetitionRecognitionError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise TeamCompetitionRecognitionError("evidence must be hexadecimal") from exc


__all__ = ["EntitySignal", "RecognizedEntity", "TeamCompetitionRecognitionError", "TeamCompetitionRecognitionReport", "build_team_competition_recognition_report", "canonical_sha256"]
