from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/architecture/FOOTBALL-SHORTS-AI-0040D-engine-adapter-design-decision.md"
AUTHORITY = ROOT / "governance/production_brain/engine_adapter_design_decision.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"CERTIFICATION_FAILED: {message}")


def main() -> None:
    require(DECISION.is_file(), "decision document missing")
    require(AUTHORITY.is_file(), "machine-readable authority missing")

    decision_text = DECISION.read_text(encoding="utf-8")
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))

    require(authority["artifact_id"] == "FOOTBALL-SHORTS-AI-0040D", "artifact id mismatch")
    require(authority["status"] == "DECIDED", "decision not decided")
    require(authority["decision"] == "READY_FOR_CONTRACT_IMPLEMENTATION", "invalid decision")
    require(authority["prerequisite"] == "FOOTBALL-SHORTS-AI-0040C", "0040C prerequisite missing")

    boundary = authority["boundary"]
    require(boundary["cardinality"] == "one_adapter_to_one_engine_authority", "invalid adapter cardinality")
    require(boundary["dependency_resolution"] == "explicit_dependency_injection", "dependency injection not required")
    require(boundary["registry"] == "explicit_immutable_fail_closed", "registry not fail closed")
    require(boundary["dynamic_discovery"] == "forbidden", "dynamic discovery not forbidden")

    required = set(authority["required_properties"])
    forbidden = set(authority["forbidden_properties"])
    non_authorized = set(authority["does_not_authorize"])

    require("no_context_mutation" in required, "context immutability missing")
    require("expected_failures_translate_to_failed_result" in required, "failure translation missing")
    require("business_logic_migration" in forbidden, "business logic migration not forbidden")
    require("implicit_network_access" in forbidden, "implicit network access not forbidden")
    require("executable_engine_adapters" in non_authorized, "runtime adapters accidentally authorized")
    require("production_brain_orchestration" in non_authorized, "orchestration accidentally authorized")

    required_phrases = (
        "anti-corruption boundary",
        "dependency injection",
        "Side effects are denied by default",
        "Dynamic import scanning",
        "No modification to `src/production_brain/contracts.py`",
        "FOOTBALL-SHORTS-AI-0040E",
    )
    for phrase in required_phrases:
        require(phrase in decision_text, f"decision phrase missing: {phrase}")

    contracts = importlib.import_module("src.production_brain.contracts")
    for symbol in (
        "ProductionStage",
        "EngineStatus",
        "ArtifactReference",
        "ProductionContext",
        "EngineResult",
        "EngineContract",
    ):
        require(hasattr(contracts, symbol), f"0040C contract symbol missing: {symbol}")

    adapters_dir = ROOT / "src/production_brain/adapters"
    require(not adapters_dir.exists(), "0040D must not install runtime adapters")

    print("FOOTBALL-SHORTS-AI-0040D_CERTIFICATION=PASS")
    print("DECISION=READY_FOR_CONTRACT_IMPLEMENTATION")
    print("RUNTIME_ADAPTER_IMPLEMENTATION=NOT_AUTHORIZED")
    print("NEXT=FOOTBALL-SHORTS-AI-0040E")


if __name__ == "__main__":
    main()
