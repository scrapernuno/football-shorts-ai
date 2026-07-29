from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCUMENT = ROOT / "docs" / "architecture" / (
    "FOOTBALL-SHORTS-AI-0040B-production-brain-design-decision.md"
)
CONTRACT = ROOT / "src" / "governance" / "production_brain_design_contract.json"
OUTPUT_DIR = ROOT / "output" / "governance" / "production_brain_design_decision"
OUTPUT = OUTPUT_DIR / "production_brain_design_decision_certification.json"

EXPECTED_SEQUENCE = [
    "research",
    "knowledge",
    "evidence",
    "reference",
    "story",
    "emotion",
    "audience",
    "originality",
    "production",
    "quality",
    "publishing",
    "analytics",
    "learning",
    "dashboard",
]

REQUIRED_DOCUMENT_MARKERS = [
    "# FOOTBALL-SHORTS-AI-0040B",
    "## Canonical boundaries",
    "## Canonical contracts",
    "## Canonical engine sequence",
    "## Failure semantics",
    "## Idempotency",
    "## Compatibility rules",
    "## Explicitly not authorized",
    "APPROVED FOR CONTRACT FOUNDATION ONLY",
    "FOOTBALL-SHORTS-AI-0040C",
]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    if not DOCUMENT.is_file():
        fail(f"Missing design document: {DOCUMENT}")

    if not CONTRACT.is_file():
        fail(f"Missing design contract: {CONTRACT}")

    document_text = DOCUMENT.read_text(encoding="utf-8")

    missing_markers = [
        marker
        for marker in REQUIRED_DOCUMENT_MARKERS
        if marker not in document_text
    ]
    if missing_markers:
        fail(f"Missing document markers: {missing_markers}")

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"Invalid design contract JSON: {exc}")

    if not isinstance(contract, dict):
        fail("Design contract must be a JSON object")

    if contract.get("artifact_id") != "FOOTBALL-SHORTS-AI-0040B":
        fail("Invalid artifact authority")

    if contract.get("status") != "APPROVED_FOR_CONTRACT_FOUNDATION_ONLY":
        fail("Invalid design status")

    authority = contract.get("authority")
    if not isinstance(authority, dict):
        fail("Missing authority object")

    if authority.get("predecessor") != "FOOTBALL-SHORTS-AI-0040A":
        fail("Invalid predecessor authority")

    if authority.get("predecessor_decision") != "READY_FOR_DESIGN":
        fail("Invalid predecessor decision")

    if authority.get("next_authorized_artifact") != "FOOTBALL-SHORTS-AI-0040C":
        fail("Invalid next authorized artifact")

    sequence = contract.get("engine_sequence")
    if sequence != EXPECTED_SEQUENCE:
        fail("Canonical engine sequence mismatch")

    if len(sequence) != len(set(sequence)):
        fail("Canonical engine sequence contains duplicates")

    implementation = contract.get("implementation_authority")
    if not isinstance(implementation, dict):
        fail("Missing implementation authority")

    expected_authority = {
        "runtime_implementation_authorized": False,
        "contract_foundation_authorized": True,
        "workflow_migration_authorized": False,
        "autonomous_publishing_authorized": False,
    }
    if implementation != expected_authority:
        fail("Implementation authority violates design boundary")

    production_brain = contract.get("production_brain")
    if not isinstance(production_brain, dict):
        fail("Missing Production Brain boundary")

    if production_brain.get("role") != "deterministic_orchestration_authority":
        fail("Invalid Production Brain role")

    if contract.get("failure_policy") != "fail_closed":
        fail("Production Brain must be fail-closed")

    compatibility = contract.get("compatibility")
    if not isinstance(compatibility, dict) or not all(
        value is True for value in compatibility.values()
    ):
        fail("Compatibility protections are incomplete")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    certification = {
        "artifact_id": "FOOTBALL-SHORTS-AI-0040B",
        "status": "CERTIFIED",
        "decision": "APPROVED_FOR_CONTRACT_FOUNDATION_ONLY",
        "next_authorized_artifact": "FOOTBALL-SHORTS-AI-0040C",
        "runtime_implementation_authorized": False,
        "workflow_migration_authorized": False,
        "canonical_engine_count": len(EXPECTED_SEQUENCE),
        "canonical_engine_sequence": EXPECTED_SEQUENCE,
        "document_markers_verified": len(REQUIRED_DOCUMENT_MARKERS),
    }
    OUTPUT.write_text(
        json.dumps(certification, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0040B")
    print("PRODUCTION BRAIN DESIGN DECISION CERTIFICATION")
    print("STATUS=CERTIFIED")
    print("DECISION=APPROVED_FOR_CONTRACT_FOUNDATION_ONLY")
    print("NEXT_AUTHORIZED_ARTIFACT=FOOTBALL-SHORTS-AI-0040C")
    print("RUNTIME_IMPLEMENTATION_AUTHORIZED=FALSE")
    print("WORKFLOW_MIGRATION_AUTHORIZED=FALSE")
    print(f"CANONICAL_ENGINE_COUNT={len(EXPECTED_SEQUENCE)}")
    print(f"OUTPUT={OUTPUT}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
