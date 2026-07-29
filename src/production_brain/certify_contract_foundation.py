from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from typing import get_type_hints

from production_brain.contracts import (
    ArtifactReference,
    EngineContract,
    EngineResult,
    EngineStatus,
    ProductionContext,
    ProductionStage,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output" / "certifications" / "production_brain"
OUTPUT_FILE = OUTPUT_DIR / "contract_foundation_certification.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    artifact = ArtifactReference(
        artifact_id="content-package",
        path="output/content_package.json",
        sha256="0" * 64,
    )
    context = ProductionContext(
        execution_id="execution-0040c",
        correlation_id="correlation-0040c",
        source_topic_id="topic-0040c",
        current_stage=ProductionStage.STORY,
        artifacts=(artifact,),
        metadata={"mode": "certification"},
    )
    result = EngineResult(
        engine_id="story-engine",
        stage=ProductionStage.STORY,
        status=EngineStatus.SUCCEEDED,
        context=context,
        produced_artifacts=(artifact,),
        evidence={"deterministic": True},
    )

    checks = {
        "production_stage_is_string_enum": issubclass(
            ProductionStage,
            str,
        ),
        "engine_status_is_string_enum": issubclass(
            EngineStatus,
            str,
        ),
        "context_is_immutable": context.__dataclass_params__.frozen,
        "result_is_immutable": result.__dataclass_params__.frozen,
        "artifact_is_immutable": artifact.__dataclass_params__.frozen,
        "metadata_is_read_only": not hasattr(
            context.metadata,
            "__setitem__",
        ),
        "evidence_is_read_only": not hasattr(
            result.evidence,
            "__setitem__",
        ),
        "engine_contract_is_runtime_protocol": getattr(
            EngineContract,
            "_is_runtime_protocol",
            False,
        ),
        "engine_contract_has_execute": hasattr(
            EngineContract,
            "execute",
        ),
        "engine_contract_execute_is_typed": bool(
            get_type_hints(EngineContract.execute)
        ),
        "context_advance_preserves_identity": (
            context.advance(ProductionStage.QUALITY).execution_id
            == context.execution_id
        ),
        "no_runtime_orchestrator_defined": not any(
            name.lower() in {
                "productionbrain",
                "productionbrainorchestrator",
                "orchestrator",
            }
            for name, _ in inspect.getmembers(
                __import__("production_brain.contracts", fromlist=["*"]),
                inspect.isclass,
            )
        ),
    }

    for name, passed in checks.items():
        require(passed, f"Certification check failed: {name}")

    source_path = ROOT / "src" / "production_brain" / "contracts.py"
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

    payload = {
        "artifact": "FOOTBALL-SHORTS-AI-0040C",
        "title": "Production Brain Contract Foundation",
        "status": "CERTIFIED",
        "decision": "READY_FOR_ENGINE_ADAPTER_DESIGN",
        "runtime_orchestration_authorized": False,
        "workflow_migration_authorized": False,
        "publication_execution_authorized": False,
        "source_sha256": source_sha256,
        "checks": checks,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT_FILE)

    print("=" * 70)
    print("FOOTBALL-SHORTS-AI-0040C")
    print("PRODUCTION BRAIN CONTRACT FOUNDATION CERTIFICATION")
    print("STATUS=CERTIFIED")
    print("DECISION=READY_FOR_ENGINE_ADAPTER_DESIGN")
    print("RUNTIME_ORCHESTRATION_AUTHORIZED=NO")
    print(f"CHECKS={len(checks)}")
    print(f"OUTPUT={OUTPUT_FILE}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
