from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_ID = "FOOTBALL-SHORTS-AI-0040A"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = (
    ROOT
    / "output"
    / "audits"
    / "production_brain_readiness"
)

REQUIRED_JSON = (
    "production_brain_inventory.json",
    "production_pipeline_graph.json",
    "engine_dependency_graph.json",
    "engine_contract_inventory.json",
    "dashboard_inventory.json",
    "package_inventory.json",
    "domain_model_inventory.json",
    "production_brain_risk_register.json",
)

REQUIRED_MARKDOWN = (
    "production_brain_readiness_report.md",
    "production_brain_decision.md",
)


class CertificationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CertificationError(f"Missing audit artefact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CertificationError(f"Invalid JSON artefact {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise CertificationError(f"Audit artefact must be an object: {path}")
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CertificationError(message)


def main() -> int:
    require(OUTPUT_DIR.is_dir(), f"Audit output directory missing: {OUTPUT_DIR}")

    payloads = {
        filename: load_json(OUTPUT_DIR / filename)
        for filename in REQUIRED_JSON
    }

    for filename in REQUIRED_MARKDOWN:
        path = OUTPUT_DIR / filename
        require(path.is_file(), f"Missing audit artefact: {path}")
        require(path.stat().st_size > 0, f"Empty audit artefact: {path}")
        content = path.read_text(encoding="utf-8")
        require(AUDIT_ID in content, f"Audit identity missing from {filename}")

    inventory = payloads["production_brain_inventory.json"]
    pipeline = payloads["production_pipeline_graph.json"]
    dependency = payloads["engine_dependency_graph.json"]
    contracts = payloads["engine_contract_inventory.json"]
    dashboard = payloads["dashboard_inventory.json"]
    packages = payloads["package_inventory.json"]
    domains = payloads["domain_model_inventory.json"]
    risks = payloads["production_brain_risk_register.json"]

    for filename, payload in payloads.items():
        if filename == "dashboard_inventory.json":
            continue
        require(
            payload.get("audit_id") == AUDIT_ID,
            f"Audit identity mismatch in {filename}",
        )

    require(
        isinstance(inventory.get("source_file_count"), int)
        and inventory["source_file_count"] > 0,
        "Source inventory is empty",
    )
    require(
        isinstance(inventory.get("python_module_count"), int)
        and inventory["python_module_count"] > 0,
        "Python module inventory is empty",
    )
    require(
        isinstance(inventory.get("observed_engines"), list),
        "Observed engine inventory is invalid",
    )
    require(
        isinstance(pipeline.get("nodes"), list)
        and len(pipeline["nodes"]) > 0,
        "Pipeline graph contains no workflow nodes",
    )
    require(
        isinstance(pipeline.get("edges"), list),
        "Pipeline graph edges are invalid",
    )
    require(
        pipeline.get("sequential_workflow_dag") is True,
        "Pipeline graph is not certified as sequential",
    )
    require(
        isinstance(dependency.get("nodes"), list),
        "Dependency graph nodes are invalid",
    )
    require(
        isinstance(dependency.get("edges"), list),
        "Dependency graph edges are invalid",
    )
    require(
        isinstance(dependency.get("cycles"), list),
        "Dependency cycle evidence is invalid",
    )
    require(
        isinstance(contracts.get("authorities"), list),
        "Contract inventory is invalid",
    )
    require(
        isinstance(packages.get("packages"), list)
        and len(packages["packages"]) > 0,
        "Package inventory is empty",
    )
    require(
        isinstance(domains.get("symbols"), list),
        "Domain model inventory is invalid",
    )
    require(
        isinstance(risks.get("risks"), list),
        "Risk register is invalid",
    )
    require(
        isinstance(dashboard.get("file_count"), int),
        "Dashboard inventory is invalid",
    )

    decision_path = OUTPUT_DIR / "production_brain_decision.md"
    decision_text = decision_path.read_text(encoding="utf-8")
    valid_decisions = ("READY_FOR_DESIGN", "NOT_READY")
    observed_decisions = [value for value in valid_decisions if value in decision_text]
    require(
        len(observed_decisions) == 1,
        "Production Brain decision must contain exactly one canonical decision",
    )

    artefacts = []
    for filename in (*REQUIRED_JSON, *REQUIRED_MARKDOWN):
        path = OUTPUT_DIR / filename
        artefacts.append(
            {
                "filename": filename,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest_material = "\n".join(
        f"{item['sha256']}  {item['filename']}"
        for item in artefacts
    ).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_material).hexdigest()

    certification = {
        "audit_id": AUDIT_ID,
        "certified_at": utc_now(),
        "status": "CERTIFIED",
        "audit_mode": "READ_ONLY_STATIC_INSPECTION",
        "decision": observed_decisions[0],
        "artefact_count": len(artefacts),
        "artefacts": artefacts,
        "manifest_sha256": manifest_sha256,
        "invariants": {
            "required_artefacts_present": True,
            "json_contracts_valid": True,
            "canonical_decision_present": True,
            "application_execution_required": False,
            "network_required": False,
            "production_brain_implementation_authorized": False,
        },
    }

    target = OUTPUT_DIR / "production_brain_readiness_certification.json"
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(certification, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)

    print("=" * 72)
    print(AUDIT_ID)
    print("PRODUCTION BRAIN READINESS CERTIFICATION")
    print("STATUS=CERTIFIED")
    print(f"DECISION={observed_decisions[0]}")
    print(f"ARTEFACT_COUNT={len(artefacts)}")
    print(f"MANIFEST_SHA256={manifest_sha256}")
    print("APPLICATION_EXECUTION=NO")
    print("PRODUCTION_BRAIN_IMPLEMENTATION_AUTHORIZED=NO")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CertificationError as exc:
        print(f"CERTIFICATION_ERROR={exc}")
        raise SystemExit(1) from exc
