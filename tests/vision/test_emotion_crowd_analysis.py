from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from vision.emotion_crowd_analysis import (
    EmotionCrowdAnalysisError,
    EmotionCrowdAnalysisReport,
    EmotionSignal,
    SceneEmotionSummary,
    _signal,
    _summaries,
    canonical_sha256,
)


def signal_payload(**overrides):
    payload = {
        "scene_id": "VSCENE-001",
        "frame_ids": ["VFRAME-001", "VFRAME-002"],
        "event_ids": ["FBEVENT-GOAL"],
        "emotion": "euphoria",
        "confidence": 0.94,
        "intensity": 0.98,
        "crowd_energy": 0.97,
        "celebration_probability": 0.99,
        "tension_probability": 0.12,
        "collective_reaction_probability": 0.96,
        "evidence_labels": ["Crowd Motion", "goal celebration", "Crowd Motion"],
    }
    payload.update(overrides)
    return payload


def test_signal_is_normalized_and_deterministic():
    first = _signal(signal_payload())
    second = _signal(signal_payload())

    assert first == second
    assert first.signal_id.startswith("EMOSIGNAL-")
    assert first.evidence_labels == ("crowd_motion", "goal_celebration")
    assert first.emotion == "euphoria"


def test_scene_summary_selects_emotional_peak():
    high = _signal(signal_payload())
    lower = _signal(signal_payload(
        emotion="joy",
        confidence=0.80,
        intensity=0.70,
        crowd_energy=0.60,
        celebration_probability=0.65,
        tension_probability=0.20,
        collective_reaction_probability=0.55,
        evidence_labels=["applause"],
    ))

    summaries = _summaries((lower, high))

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.scene_id == "VSCENE-001"
    assert summary.dominant_emotion == "euphoria"
    assert summary.emotional_peak_score == pytest.approx(0.9212)
    assert summary.crowd_energy_score == pytest.approx(0.785)
    assert summary.celebration_score == pytest.approx(0.82)


def test_multiple_scenes_are_sorted_deterministically():
    scene_b = _signal(signal_payload(scene_id="VSCENE-B", emotion="tension"))
    scene_a = _signal(signal_payload(scene_id="VSCENE-A", emotion="surprise"))

    summaries = _summaries((scene_b, scene_a))

    assert [item.scene_id for item in summaries] == ["VSCENE-A", "VSCENE-B"]


def test_unsupported_emotion_is_rejected_by_signal_validation():
    signal = EmotionSignal(
        signal_id="EMOSIGNAL-TEST",
        scene_id="VSCENE-001",
        frame_ids=("VFRAME-001",),
        event_ids=(),
        emotion="confusion",
        confidence=0.9,
        intensity=0.8,
        crowd_energy=0.7,
        celebration_probability=0.2,
        tension_probability=0.4,
        collective_reaction_probability=0.3,
        evidence_labels=(),
    )

    class Vision:
        frames = (type("Frame", (), {"frame_id": "VFRAME-001"})(),)
        scenes = (type("Scene", (), {"scene_id": "VSCENE-001"})(),)

    class Events:
        events = ()

    with pytest.raises(EmotionCrowdAnalysisError, match="unsupported emotion"):
        signal.validate(Vision(), Events())


def test_scores_outside_unit_interval_are_rejected():
    signal = EmotionSignal(
        signal_id="EMOSIGNAL-TEST",
        scene_id="VSCENE-001",
        frame_ids=("VFRAME-001",),
        event_ids=(),
        emotion="joy",
        confidence=1.1,
        intensity=0.8,
        crowd_energy=0.7,
        celebration_probability=0.2,
        tension_probability=0.4,
        collective_reaction_probability=0.3,
        evidence_labels=(),
    )

    class Vision:
        frames = (type("Frame", (), {"frame_id": "VFRAME-001"})(),)
        scenes = (type("Scene", (), {"scene_id": "VSCENE-001"})(),)

    class Events:
        events = ()

    with pytest.raises(EmotionCrowdAnalysisError, match="confidence"):
        signal.validate(Vision(), Events())


def test_summary_requires_valid_signal_references():
    summary = SceneEmotionSummary(
        scene_id="VSCENE-001",
        dominant_emotion="joy",
        emotional_peak_score=0.8,
        crowd_energy_score=0.7,
        celebration_score=0.6,
        tension_score=0.2,
        confidence=0.9,
        signal_ids=("EMOSIGNAL-MISSING",),
    )

    with pytest.raises(EmotionCrowdAnalysisError, match="valid signal references"):
        summary.validate({"VSCENE-001"}, set())


def test_canonical_sha256_replay_is_deterministic():
    payload = {"b": 2, "a": [3, 1]}
    assert canonical_sha256(payload) == canonical_sha256({"a": [3, 1], "b": 2})
    assert len(canonical_sha256(payload)) == 64


def test_report_contract_keeps_operational_capabilities_disabled():
    source = Path("src/vision/emotion_crowd_analysis.py").read_text(encoding="utf-8")

    for field in (
        "network_enabled: bool = False",
        "acquisition_enabled: bool = False",
        "model_training_enabled: bool = False",
        "render_enabled: bool = False",
        "auto_publish: bool = False",
    ):
        assert field in source

    assert "0057E cannot enable operational capabilities" in source
    assert "EMOTION_REVIEW_REQUIRED" in source
    assert "EMOTION_EVIDENCE_MISSING" in source
    assert "UPSTREAM_VISION_OR_EVENT_EVIDENCE_BLOCKED" in source


def test_report_evidence_tampering_is_detectable():
    unsigned = {
        "schema": "football-shorts-ai.emotion-crowd-analysis.v1",
        "analysis_id": "EMOTION-TEST",
        "vision_report_id": "VISION-TEST",
        "event_detection_id": "EVENTDET-TEST",
        "provider_name": "offline-test",
        "signals": [],
        "scene_summaries": [],
        "peak_scene_id": None,
        "analysis_state": "blocked",
        "blockers": ["EMOTION_EVIDENCE_MISSING"],
        "network_enabled": False,
        "acquisition_enabled": False,
        "model_training_enabled": False,
        "render_enabled": False,
        "auto_publish": False,
    }
    original = canonical_sha256(unsigned)
    tampered = canonical_sha256({**unsigned, "provider_name": "tampered"})
    assert original != tampered
