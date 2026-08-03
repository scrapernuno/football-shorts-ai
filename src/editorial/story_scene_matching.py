"""
FOOTBALL-SHORTS-AI-0056C
STORY-TO-SCENE SEMANTIC MATCHING ENGINE

Deterministically ranks 0056B scene classifications against governed story beats.
The engine performs no model inference, network access, media acquisition,
rendering or publication. It prepares reviewable editorial matching evidence only.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping, Sequence

from editorial.football_scene_understanding import (
    EditorialSignalClassification,
    FootballSceneUnderstandingReport,
)
from editorial.semantic_scene_indexer import SemanticScene, SemanticSceneIndex


class StorySceneMatchingError(ValueError):
    """Raised when story-to-scene matching evidence is invalid."""


SUPPORTED_STORY_ROLES = {
    "hook",
    "context",
    "development",
    "climax",
    "reaction",
    "resolution",
    "cta",
}

ROLE_ACTION_PREFERENCES: dict[str, tuple[str, ...]] = {
    "hook": ("goal", "shot", "save", "celebration", "dribble"),
    "context": ("build_up", "pass", "interview", "coach_reaction"),
    "development": ("build_up", "pass", "dribble", "shot"),
    "climax": ("goal", "save", "celebration", "trophy"),
    "reaction": ("celebration", "crowd_reaction", "coach_reaction"),
    "resolution": ("goal", "save", "trophy", "celebration"),
    "cta": ("celebration", "crowd_reaction", "interview", "trophy"),
}

ROLE_EDITORIAL_PREFERENCES: dict[str, tuple[str, ...]] = {
    "hook": ("hook", "climax"),
    "context": ("context", "development"),
    "development": ("development", "context"),
    "climax": ("climax", "resolution"),
    "reaction": ("reaction", "resolution"),
    "resolution": ("resolution", "reaction"),
    "cta": ("cta_support", "reaction", "resolution"),
}


@dataclass(frozen=True)
class StoryBeat:
    beat_id: str
    order: int
    role: str
    text: str
    keywords: tuple[str, ...]
    players: tuple[str, ...] = ()
    teams: tuple[str, ...] = ()
    competition: str | None = None
    emotions: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.beat_id.startswith("BEAT-"):
            raise StorySceneMatchingError("beat_id must start with BEAT-")
        if self.order < 1:
            raise StorySceneMatchingError("beat order must be positive")
        if self.role not in SUPPORTED_STORY_ROLES:
            raise StorySceneMatchingError("unsupported story role")
        if not self.text.strip():
            raise StorySceneMatchingError("story beat text is required")
        for values, name in (
            (self.keywords, "keywords"),
            (self.players, "players"),
            (self.teams, "teams"),
            (self.emotions, "emotions"),
            (self.actions, "actions"),
        ):
            if tuple(sorted(set(values))) != values:
                raise StorySceneMatchingError(f"{name} must be normalized, unique and sorted")
        if self.competition is not None and not self.competition.strip():
            raise StorySceneMatchingError("competition cannot be blank")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "beat_id": self.beat_id,
            "order": self.order,
            "role": self.role,
            "text": self.text,
            "keywords": list(self.keywords),
            "players": list(self.players),
            "teams": list(self.teams),
            "competition": self.competition,
            "emotions": list(self.emotions),
            "actions": list(self.actions),
        }


@dataclass(frozen=True)
class SceneMatchCandidate:
    scene_id: str
    classification_id: str
    rank: int
    total_score: float
    semantic_score: float
    role_score: float
    action_score: float
    entity_score: float
    emotion_score: float
    quality_score: float
    retention_score: float
    rights_score: float
    matched_terms: tuple[str, ...]
    render_allowed: bool
    blockers: tuple[str, ...]

    def validate(self) -> None:
        if not self.scene_id.startswith("SCENE-"):
            raise StorySceneMatchingError("invalid candidate scene identity")
        if not self.classification_id.startswith("SCENECLS-"):
            raise StorySceneMatchingError("invalid classification identity")
        if self.rank < 1:
            raise StorySceneMatchingError("candidate rank must be positive")
        for name, value in (
            ("total_score", self.total_score),
            ("semantic_score", self.semantic_score),
            ("role_score", self.role_score),
            ("action_score", self.action_score),
            ("entity_score", self.entity_score),
            ("emotion_score", self.emotion_score),
            ("quality_score", self.quality_score),
            ("retention_score", self.retention_score),
            ("rights_score", self.rights_score),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise StorySceneMatchingError(f"{name} must be numeric")
            if not 0.0 <= float(value) <= 1.0:
                raise StorySceneMatchingError(f"{name} must be between 0 and 1")
        if tuple(sorted(set(self.matched_terms))) != self.matched_terms:
            raise StorySceneMatchingError("matched_terms must be normalized")
        if self.render_allowed and self.blockers:
            raise StorySceneMatchingError("renderable candidate cannot contain blockers")
        if not self.render_allowed and not self.blockers:
            raise StorySceneMatchingError("non-renderable candidate requires blockers")

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "scene_id": self.scene_id,
            "classification_id": self.classification_id,
            "rank": self.rank,
            "total_score": self.total_score,
            "semantic_score": self.semantic_score,
            "role_score": self.role_score,
            "action_score": self.action_score,
            "entity_score": self.entity_score,
            "emotion_score": self.emotion_score,
            "quality_score": self.quality_score,
            "retention_score": self.retention_score,
            "rights_score": self.rights_score,
            "matched_terms": list(self.matched_terms),
            "render_allowed": self.render_allowed,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class BeatSceneMatch:
    schema: str
    match_id: str
    beat: StoryBeat
    candidates: tuple[SceneMatchCandidate, ...]
    selected_scene_id: str
    match_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str

    def validate(self) -> None:
        if self.schema != "football-shorts-ai.beat-scene-match.v1":
            raise StorySceneMatchingError("unsupported beat match schema")
        if not self.match_id.startswith("BEATMATCH-"):
            raise StorySceneMatchingError("invalid beat match identity")
        self.beat.validate()
        if not self.candidates:
            raise StorySceneMatchingError("beat match requires candidates")
        for expected_rank, candidate in enumerate(self.candidates, start=1):
            candidate.validate()
            if candidate.rank != expected_rank:
                raise StorySceneMatchingError("candidate ranks must be contiguous")
        ids = {candidate.scene_id for candidate in self.candidates}
        if self.selected_scene_id not in ids:
            raise StorySceneMatchingError("selected scene must be a candidate")
        if self.match_state not in {"matched", "blocked"}:
            raise StorySceneMatchingError("unsupported match state")
        selected = next(item for item in self.candidates if item.scene_id == self.selected_scene_id)
        if self.match_state == "matched" and (self.blockers or not selected.render_allowed):
            raise StorySceneMatchingError("matched beat must select a renderable scene")
        if self.match_state == "blocked" and not self.blockers:
            raise StorySceneMatchingError("blocked beat requires blockers")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise StorySceneMatchingError("beat match evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "match_id": self.match_id,
            "beat": self.beat.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "selected_scene_id": self.selected_scene_id,
            "match_state": self.match_state,
            "blockers": list(self.blockers),
        }

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


@dataclass(frozen=True)
class StorySceneMatchingReport:
    schema: str
    report_id: str
    index_id: str
    understanding_report_id: str
    story_id: str
    matches: tuple[BeatSceneMatch, ...]
    report_state: str
    blockers: tuple[str, ...]
    evidence_sha256: str
    model_execution_enabled: bool = False
    network_enabled: bool = False
    acquisition_enabled: bool = False
    auto_render: bool = False
    auto_publish: bool = False

    def validate(self, index: SemanticSceneIndex, understanding: FootballSceneUnderstandingReport) -> None:
        index.validate()
        understanding.validate(index)
        if self.schema != "football-shorts-ai.story-scene-matching.v1":
            raise StorySceneMatchingError("unsupported matching report schema")
        if not self.report_id.startswith("STORYMATCH-"):
            raise StorySceneMatchingError("invalid matching report identity")
        if self.index_id != index.index_id:
            raise StorySceneMatchingError("scene index identity mismatch")
        if self.understanding_report_id != understanding.report_id:
            raise StorySceneMatchingError("understanding report identity mismatch")
        if not self.story_id.startswith("STORY-"):
            raise StorySceneMatchingError("story_id must start with STORY-")
        if not self.matches:
            raise StorySceneMatchingError("matching report requires story beats")
        for order, match in enumerate(self.matches, start=1):
            match.validate()
            if match.beat.order != order:
                raise StorySceneMatchingError("story beat order must be contiguous")
        if self.report_state not in {"matched", "blocked"}:
            raise StorySceneMatchingError("unsupported report state")
        if self.report_state == "matched" and self.blockers:
            raise StorySceneMatchingError("matched report cannot contain blockers")
        if self.report_state == "blocked" and not self.blockers:
            raise StorySceneMatchingError("blocked report requires blockers")
        if any((
            self.model_execution_enabled,
            self.network_enabled,
            self.acquisition_enabled,
            self.auto_render,
            self.auto_publish,
        )):
            raise StorySceneMatchingError("0056C cannot execute operational capabilities")
        _validate_sha256(self.evidence_sha256)
        if canonical_sha256(self._unsigned()) != self.evidence_sha256:
            raise StorySceneMatchingError("matching report evidence mismatch")

    def _unsigned(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "report_id": self.report_id,
            "index_id": self.index_id,
            "understanding_report_id": self.understanding_report_id,
            "story_id": self.story_id,
            "matches": [match.to_dict() for match in self.matches],
            "report_state": self.report_state,
            "blockers": list(self.blockers),
            "model_execution_enabled": False,
            "network_enabled": False,
            "acquisition_enabled": False,
            "auto_render": False,
            "auto_publish": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._unsigned(), "evidence_sha256": self.evidence_sha256}


def build_story_scene_matching(
    *,
    story: Mapping[str, object],
    index: SemanticSceneIndex,
    understanding: FootballSceneUnderstandingReport,
    max_candidates_per_beat: int = 5,
) -> StorySceneMatchingReport:
    index.validate()
    understanding.validate(index)
    if not 1 <= max_candidates_per_beat <= 20:
        raise StorySceneMatchingError("max_candidates_per_beat must be between 1 and 20")
    beats = _story_beats(story)
    story_core = {"beats": [beat.to_dict() for beat in beats]}
    story_id = f"STORY-{canonical_sha256(story_core)[:20].upper()}"
    scene_by_id = {scene.scene_id: scene for scene in index.scenes}
    classification_by_id = {item.scene_id: item for item in understanding.classifications}

    matches = tuple(
        _match_beat(
            beat=beat,
            scenes=index.scenes,
            classifications=classification_by_id,
            max_candidates=max_candidates_per_beat,
        )
        for beat in beats
    )
    blockers = tuple(sorted({blocker for match in matches for blocker in match.blockers}))
    state = "blocked" if blockers else "matched"
    core = {
        "schema": "football-shorts-ai.story-scene-matching.v1",
        "index_id": index.index_id,
        "understanding_report_id": understanding.report_id,
        "story_id": story_id,
        "matches": [match.to_dict() for match in matches],
        "report_state": state,
        "blockers": list(blockers),
        "model_execution_enabled": False,
        "network_enabled": False,
        "acquisition_enabled": False,
        "auto_render": False,
        "auto_publish": False,
    }
    provisional = canonical_sha256(core)
    report_id = f"STORYMATCH-{provisional[:20].upper()}"
    unsigned = {**core, "report_id": report_id}
    evidence = canonical_sha256(unsigned)
    result = StorySceneMatchingReport(
        report_id=report_id,
        evidence_sha256=evidence,
        matches=matches,
        blockers=blockers,
        **{key: value for key, value in unsigned.items() if key not in {"report_id", "evidence_sha256", "matches", "blockers"}},
    )
    result.validate(index, understanding)
    return result


def _match_beat(
    *,
    beat: StoryBeat,
    scenes: Sequence[SemanticScene],
    classifications: Mapping[str, EditorialSignalClassification],
    max_candidates: int,
) -> BeatSceneMatch:
    scored: list[tuple[dict[str, object], SemanticScene, EditorialSignalClassification]] = []
    for scene in scenes:
        classification = classifications[scene.scene_id]
        score = _score_candidate(beat, scene, classification)
        scored.append((score, scene, classification))
    scored.sort(
        key=lambda item: (
            -float(item[0]["total_score"]),
            -float(item[0]["rights_score"]),
            -float(item[0]["retention_score"]),
            item[1].scene_id,
        )
    )
    candidates: list[SceneMatchCandidate] = []
    for rank, (scores, scene, classification) in enumerate(scored[:max_candidates], start=1):
        blockers = () if scene.render_allowed else ("SCENE_NOT_RENDERABLE",)
        candidate = SceneMatchCandidate(
            scene_id=scene.scene_id,
            classification_id=classification.classification_id,
            rank=rank,
            matched_terms=tuple(scores.pop("matched_terms")),
            render_allowed=scene.render_allowed,
            blockers=blockers,
            **scores,
        )
        candidate.validate()
        candidates.append(candidate)
    renderable = [candidate for candidate in candidates if candidate.render_allowed]
    selected = renderable[0] if renderable else candidates[0]
    blockers = () if renderable else (f"NO_RENDERABLE_SCENE_FOR_BEAT:{beat.beat_id}",)
    state = "matched" if renderable else "blocked"
    core = {
        "schema": "football-shorts-ai.beat-scene-match.v1",
        "beat": beat.to_dict(),
        "candidates": [candidate.to_dict() for candidate in candidates],
        "selected_scene_id": selected.scene_id,
        "match_state": state,
        "blockers": list(blockers),
    }
    match_id = f"BEATMATCH-{canonical_sha256(core)[:20].upper()}"
    unsigned = {**core, "match_id": match_id}
    evidence = canonical_sha256(unsigned)
    result = BeatSceneMatch(
        match_id=match_id,
        beat=beat,
        candidates=tuple(candidates),
        blockers=blockers,
        evidence_sha256=evidence,
        **{key: value for key, value in unsigned.items() if key not in {"match_id", "beat", "candidates", "blockers", "evidence_sha256"}},
    )
    result.validate()
    return result


def _score_candidate(
    beat: StoryBeat,
    scene: SemanticScene,
    classification: EditorialSignalClassification,
) -> dict[str, object]:
    scene_terms = _scene_terms(scene, classification)
    beat_terms = set((*beat.keywords, *beat.players, *beat.teams, *beat.emotions, *beat.actions))
    if beat.competition:
        beat_terms.add(_normalize_token(beat.competition))
    matched = tuple(sorted(term for term in beat_terms if term and term in scene_terms))
    semantic = _ratio(len(matched), max(1, len(beat_terms)))

    editorial_preferences = ROLE_EDITORIAL_PREFERENCES[beat.role]
    role = 1.0 if classification.editorial_role == editorial_preferences[0] else (
        0.65 if classification.editorial_role in editorial_preferences[1:] else 0.15
    )
    action_preferences = set(ROLE_ACTION_PREFERENCES[beat.role]) | set(beat.actions)
    action = 1.0 if classification.action in action_preferences else 0.15

    entity_matches = 0
    entity_total = len(beat.players) + len(beat.teams) + (1 if beat.competition else 0)
    scene_players = {_normalize_token(value) for value in scene.signals.players}
    scene_teams = {_normalize_token(value) for value in scene.signals.teams}
    entity_matches += sum(1 for value in beat.players if value in scene_players)
    entity_matches += sum(1 for value in beat.teams if value in scene_teams)
    if beat.competition and scene.signals.competition:
        entity_matches += int(_normalize_token(scene.signals.competition) == beat.competition)
    entity = 0.5 if entity_total == 0 else _ratio(entity_matches, entity_total)

    emotions = set(beat.emotions)
    emotion = 0.5 if not emotions else (1.0 if _normalize_token(scene.signals.emotion) in emotions else 0.1)
    quality = round(classification.quality_score, 4)
    retention = round(classification.retention_score, 4)
    rights = 1.0 if scene.render_allowed else 0.0

    total = _clamp(
        0.28 * semantic
        + 0.16 * role
        + 0.14 * action
        + 0.14 * entity
        + 0.08 * emotion
        + 0.08 * quality
        + 0.08 * retention
        + 0.04 * rights
    )
    return {
        "total_score": total,
        "semantic_score": semantic,
        "role_score": round(role, 4),
        "action_score": round(action, 4),
        "entity_score": entity,
        "emotion_score": round(emotion, 4),
        "quality_score": quality,
        "retention_score": retention,
        "rights_score": rights,
        "matched_terms": matched,
    }


def _story_beats(story: Mapping[str, object]) -> tuple[StoryBeat, ...]:
    raw_beats = story.get("beats")
    if not isinstance(raw_beats, Sequence) or isinstance(raw_beats, (str, bytes)) or not raw_beats:
        raise StorySceneMatchingError("story beats are required")
    beats: list[StoryBeat] = []
    for order, raw in enumerate(raw_beats, start=1):
        if not isinstance(raw, Mapping):
            raise StorySceneMatchingError("each story beat must be an object")
        role = str(raw.get("role", "")).strip().lower()
        text = str(raw.get("text", "")).strip()
        keywords = _terms(raw.get("keywords")) or _keywords_from_text(text)
        core = {
            "order": order,
            "role": role,
            "text": text,
            "keywords": list(keywords),
            "players": list(_terms(raw.get("players"))),
            "teams": list(_terms(raw.get("teams"))),
            "competition": _optional_token(raw.get("competition")),
            "emotions": list(_terms(raw.get("emotions"))),
            "actions": list(_terms(raw.get("actions"))),
        }
        beat_id = f"BEAT-{canonical_sha256(core)[:16].upper()}"
        beat = StoryBeat(
            beat_id=beat_id,
            order=order,
            role=role,
            text=text,
            keywords=tuple(core["keywords"]),
            players=tuple(core["players"]),
            teams=tuple(core["teams"]),
            competition=core["competition"],
            emotions=tuple(core["emotions"]),
            actions=tuple(core["actions"]),
        )
        beat.validate()
        beats.append(beat)
    return tuple(beats)


def _scene_terms(scene: SemanticScene, classification: EditorialSignalClassification) -> set[str]:
    values = {
        _normalize_token(classification.action),
        _normalize_token(classification.editorial_role),
        _normalize_token(scene.signals.scene_type),
        _normalize_token(scene.signals.shot_type),
        _normalize_token(scene.signals.emotion),
    }
    values.update(_normalize_token(value) for value in scene.signals.players)
    values.update(_normalize_token(value) for value in scene.signals.teams)
    values.update(_normalize_token(value) for value in scene.signals.semantic_tags)
    values.update(_normalize_token(value) for value in classification.labels)
    if scene.signals.competition:
        values.add(_normalize_token(scene.signals.competition))
    return {value for value in values if value}


def _keywords_from_text(text: str) -> tuple[str, ...]:
    stop = {"a", "o", "as", "os", "de", "do", "da", "dos", "das", "e", "que", "um", "uma", "para", "no", "na", "em", "the", "and", "of", "to", "in"}
    return tuple(sorted({token for token in _tokenize(text) if len(token) >= 3 and token not in stop}))


def _terms(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        source = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        source = list(value)
    else:
        raise StorySceneMatchingError("story terms must be a string or array")
    return tuple(sorted({_normalize_token(str(item)) for item in source if _normalize_token(str(item))}))


def _optional_token(value: object) -> str | None:
    if value is None:
        return None
    token = _normalize_token(str(value))
    return token or None


def _tokenize(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char)).lower()
    return tuple(re.findall(r"[a-z0-9]+", ascii_text))


def _normalize_token(value: str) -> str:
    return "_".join(_tokenize(value))


def _ratio(numerator: int, denominator: int) -> float:
    return round(max(0.0, min(1.0, numerator / max(1, denominator))), 4)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_sha256(value: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise StorySceneMatchingError("evidence must be SHA-256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise StorySceneMatchingError("evidence must be hexadecimal") from exc


__all__ = [
    "BeatSceneMatch",
    "SceneMatchCandidate",
    "StoryBeat",
    "StorySceneMatchingError",
    "StorySceneMatchingReport",
    "SUPPORTED_STORY_ROLES",
    "build_story_scene_matching",
    "canonical_sha256",
]
