from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIT_ID = "FOOTBALL-SHORTS-AI-0040A"
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = (
    ROOT
    / "output"
    / "audits"
    / "production_brain_readiness"
)
WORKFLOW_FILE = (
    ROOT
    / ".github"
    / "workflows"
    / "football-shorts.yml"
)

SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "output",
}

ENGINE_TERMS: dict[str, tuple[str, ...]] = {
    "research": ("research", "discovery", "digest", "feed"),
    "knowledge": ("knowledge", "football", "entity", "topic"),
    "evidence": ("evidence", "fact", "verify", "certify"),
    "reference": ("reference", "trend", "tiktok", "media_acquisition"),
    "story": ("story", "storyboard", "editorial", "script", "narrative"),
    "production": ("production", "preview", "render", "asset", "media"),
    "publishing": ("publishing", "publish", "platform_variant", "seo"),
    "analytics": ("analytics", "metric", "retention", "performance"),
    "dashboard": ("dashboard", "executive_overview", "ui"),
    "quality": ("quality", "review", "validation", "governance"),
    "orchestration": ("orchestrator", "production_brain", "workflow", "pipeline"),
}

PACKAGE_FILENAMES = {
    "digest.json",
    "editorial_package.json",
    "dashboard_model.json",
    "content_package.json",
    "media_acquisition_plan.json",
    "trend_discovery_request.json",
    "tiktok_trend_discovery_results.json",
    "tiktok_trend_runtime_intake.json",
    "tiktok_trend_intelligence.json",
    "platform_variants.json",
    "tiktok_viral_reference_review.json",
    "publishing_evidence.json",
    "publishing_package.json",
    "production_preview.json",
    "analytics_package.json",
}

DOMAIN_TERMS = {
    "topic",
    "story",
    "reference",
    "evidence",
    "analytics",
    "publishing",
    "asset",
    "entity",
    "player",
    "club",
    "match",
    "goal",
    "content",
    "production",
    "trend",
}


@dataclass(frozen=True)
class PythonModule:
    path: Path
    module: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(name: str, payload: Any) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def write_text(name: str, content: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(content.rstrip() + "\n", encoding="utf-8")
    temporary.replace(target)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if parts & SKIP_PARTS:
            continue
        result.append(path)
    return sorted(result, key=relative)


def python_modules() -> list[PythonModule]:
    modules: list[PythonModule] = []
    source_root = ROOT / "src"
    if not source_root.exists():
        return modules

    for path in sorted(source_root.rglob("*.py")):
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        rel = path.relative_to(source_root).with_suffix("")
        parts = list(rel.parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        module = ".".join(parts)
        if module:
            modules.append(PythonModule(path=path, module=module))
    return modules


def classify_engine(path: Path, content: str) -> list[str]:
    haystack = f"{relative(path)}\n{content[:20000]}".lower()
    matches = []
    for engine, terms in ENGINE_TERMS.items():
        if any(term in haystack for term in terms):
            matches.append(engine)
    return matches


def parse_python(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None


def internal_imports(module: PythonModule, known: set[str]) -> set[str]:
    tree = parse_python(module.path)
    if tree is None:
        return set()

    imports: set[str] = set()
    package_parts = module.module.split(".")[:-1]

    for node in ast.walk(tree):
        candidate: str | None = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                if candidate in known:
                    imports.add(candidate)
                else:
                    root = candidate.split(".")[0]
                    matches = [item for item in known if item == root or item.startswith(root + ".")]
                    imports.update(matches[:1])
        elif isinstance(node, ast.ImportFrom):
            base_parts = package_parts[:]
            if node.level:
                trim = max(node.level - 1, 0)
                if trim:
                    base_parts = base_parts[:-trim]
            if node.module:
                base_parts.extend(node.module.split("."))
            candidate = ".".join(base_parts)
            if candidate in known:
                imports.add(candidate)
            else:
                matches = [item for item in known if item == candidate or item.startswith(candidate + ".")]
                imports.update(matches[:1])

    imports.discard(module.module)
    return imports


def strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    result: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbour in graph.get(node, set()):
            if neighbour not in indexes:
                visit(neighbour)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbour])
            elif neighbour in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[neighbour])

        if lowlinks[node] == indexes[node]:
            component: list[str] = []
            while True:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            result.append(sorted(component))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)

    return sorted(result, key=lambda item: (len(item), item))


def parse_workflow_steps() -> list[dict[str, Any]]:
    if not WORKFLOW_FILE.exists():
        return []

    text = WORKFLOW_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()
    steps: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line_number, line in enumerate(lines, start=1):
        match = re.match(r"^\s*- name:\s*(.+?)\s*$", line)
        if match:
            if current:
                steps.append(current)
            current = {
                "name": match.group(1).strip('"\''),
                "line": line_number,
                "commands": [],
                "python_scripts": [],
            }
            continue

        if current is None:
            continue

        stripped = line.strip()
        if stripped.startswith("python ") or stripped.startswith("PYTHONPATH="):
            current["commands"].append(stripped)

        for script in re.findall(r"(?:^|\s)(src/[A-Za-z0-9_./-]+\.py)(?:\s|$)", stripped):
            current["python_scripts"].append(script)

    if current:
        steps.append(current)

    for step in steps:
        step["python_scripts"] = sorted(set(step["python_scripts"]))
        step["engines"] = sorted(
            {
                engine
                for engine, terms in ENGINE_TERMS.items()
                if any(term in step["name"].lower() for term in terms)
            }
        )

    return steps


def package_inventory(files: Iterable[Path], workflow_text: str) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for filename in sorted(PACKAGE_FILENAMES):
        producers: set[str] = set()
        consumers: set[str] = set()
        occurrences: list[str] = []

        for path in files:
            if path.suffix.lower() not in {".py", ".js", ".yml", ".yaml", ".md", ".html"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if filename not in content:
                continue
            occurrences.append(relative(path))
            lower_name = path.name.lower()
            if any(term in lower_name for term in ("build", "generate", "sync", "render")):
                producers.add(relative(path))
            else:
                consumers.add(relative(path))

        workflow_mentions = workflow_text.count(filename)
        inventory.append(
            {
                "package": filename,
                "producers": sorted(producers),
                "consumers": sorted(consumers),
                "occurrences": sorted(set(occurrences)),
                "workflow_mentions": workflow_mentions,
                "contract_visibility": "explicit" if occurrences or workflow_mentions else "not_observed",
            }
        )
    return inventory


def dashboard_inventory(files: Iterable[Path]) -> dict[str, Any]:
    dashboard_root = ROOT / "dashboard"
    dashboard_files = [path for path in files if dashboard_root in path.parents or path == dashboard_root]
    data_files = [path for path in dashboard_files if "data" in path.relative_to(dashboard_root).parts]
    assets = [path for path in dashboard_files if "assets" in path.relative_to(dashboard_root).parts]

    source_references: dict[str, list[str]] = defaultdict(list)
    for path in assets:
        if path.suffix.lower() not in {".js", ".html"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in re.findall(r"data/[A-Za-z0-9_.-]+\.json", content):
            source_references[match].append(relative(path))

    return {
        "root": relative(dashboard_root) if dashboard_root.exists() else "dashboard",
        "file_count": len(dashboard_files),
        "data_files": sorted(relative(path) for path in data_files),
        "asset_files": sorted(relative(path) for path in assets),
        "data_source_references": {
            key: sorted(set(value))
            for key, value in sorted(source_references.items())
        },
        "decoupled_static_consumer": bool(source_references),
    }


def domain_model_inventory(modules: Iterable[PythonModule]) -> list[dict[str, Any]]:
    models: list[dict[str, Any]] = []
    for module in modules:
        tree = parse_python(module.path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                continue
            name = node.name
            matched_terms = sorted(term for term in DOMAIN_TERMS if term in name.lower())
            if not matched_terms:
                continue
            fields: list[str] = []
            if isinstance(node, ast.ClassDef):
                for child in node.body:
                    if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                        fields.append(child.target.id)
            models.append(
                {
                    "symbol": name,
                    "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    "module": module.module,
                    "path": relative(module.path),
                    "line": node.lineno,
                    "matched_terms": matched_terms,
                    "fields": sorted(fields),
                }
            )
    return sorted(models, key=lambda item: (item["path"], item["line"], item["symbol"]))


def topological_order(graph: dict[str, set[str]]) -> list[str] | None:
    indegree = {node: 0 for node in graph}
    for neighbours in graph.values():
        for neighbour in neighbours:
            indegree.setdefault(neighbour, 0)
            indegree[neighbour] += 1

    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbour in sorted(graph.get(node, set())):
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                queue.append(neighbour)

    return order if len(order) == len(indegree) else None


def main() -> int:
    generated_at = utc_now()
    files = source_files()
    modules = python_modules()
    known_modules = {item.module for item in modules}

    module_graph: dict[str, set[str]] = {
        item.module: internal_imports(item, known_modules)
        for item in modules
    }
    components = strongly_connected_components(module_graph)
    cycles = [component for component in components if len(component) > 1]

    workflow_steps = parse_workflow_steps()
    workflow_text = WORKFLOW_FILE.read_text(encoding="utf-8") if WORKFLOW_FILE.exists() else ""

    engine_files: dict[str, set[str]] = defaultdict(set)
    engine_contracts: list[dict[str, Any]] = []
    for path in files:
        if path.suffix.lower() not in {".py", ".js", ".yml", ".yaml", ".md"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        engines = classify_engine(path, content)
        for engine in engines:
            engine_files[engine].add(relative(path))
        if path.suffix == ".py":
            tree = parse_python(path)
            symbols = []
            if tree is not None:
                symbols = sorted(
                    node.name
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")
                )
            engine_contracts.append(
                {
                    "path": relative(path),
                    "engines": engines,
                    "public_symbols": symbols,
                    "explicit_input_output_contract": any(
                        term in content
                        for term in ("INPUT_FILE", "OUTPUT_FILE", "load_", "save_", "to_dict")
                    ),
                }
            )

    packages = package_inventory(files, workflow_text)
    dashboard = dashboard_inventory(files)
    domain_models = domain_model_inventory(modules)

    pipeline_nodes = [step["name"] for step in workflow_steps]
    pipeline_edges = [
        {"from": pipeline_nodes[index], "to": pipeline_nodes[index + 1]}
        for index in range(len(pipeline_nodes) - 1)
    ]

    observed_engines = sorted(engine for engine, paths in engine_files.items() if paths)
    required_core = {"reference", "story", "production", "publishing", "analytics", "dashboard"}
    missing_core = sorted(required_core - set(observed_engines))
    explicit_contract_count = sum(
        1 for item in engine_contracts if item["explicit_input_output_contract"]
    )
    package_without_producer = sorted(
        item["package"]
        for item in packages
        if not item["producers"] and item["workflow_mentions"] == 0
    )

    risks: list[dict[str, Any]] = []
    if cycles:
        risks.append(
            {
                "id": "PB-RISK-001",
                "severity": "high",
                "category": "dependency",
                "description": "Internal Python dependency cycles were observed.",
                "evidence": cycles,
                "recommended_action": "Resolve cycles before central orchestration.",
            }
        )
    if missing_core:
        risks.append(
            {
                "id": "PB-RISK-002",
                "severity": "high",
                "category": "capability",
                "description": "Required core engine categories were not observed.",
                "evidence": missing_core,
                "recommended_action": "Establish or identify the missing engine boundaries.",
            }
        )
    if package_without_producer:
        risks.append(
            {
                "id": "PB-RISK-003",
                "severity": "medium",
                "category": "data_contract",
                "description": "Some canonical packages have no observed producer or workflow authority.",
                "evidence": package_without_producer,
                "recommended_action": "Confirm package ownership before orchestration.",
            }
        )
    if explicit_contract_count < max(1, len(engine_contracts) // 3):
        risks.append(
            {
                "id": "PB-RISK-004",
                "severity": "medium",
                "category": "contract",
                "description": "A limited share of Python authorities expose recognizable input/output contracts.",
                "evidence": {
                    "explicit_contracts": explicit_contract_count,
                    "python_authorities": len(engine_contracts),
                },
                "recommended_action": "Introduce typed engine contracts incrementally in 0040B/0040C.",
            }
        )
    if not dashboard["decoupled_static_consumer"]:
        risks.append(
            {
                "id": "PB-RISK-005",
                "severity": "medium",
                "category": "dashboard",
                "description": "Dashboard data-source decoupling was not proven.",
                "evidence": dashboard,
                "recommended_action": "Keep dashboard consumption behind synchronized JSON packages.",
            }
        )

    blocking_risks = [risk for risk in risks if risk["severity"] == "high"]
    decision = "READY_FOR_DESIGN" if not blocking_risks else "NOT_READY"

    source_inventory = [
        {
            "path": relative(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "suffix": path.suffix.lower(),
        }
        for path in files
    ]

    production_inventory = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "repository_root": str(ROOT),
        "source_file_count": len(source_inventory),
        "python_module_count": len(modules),
        "workflow_step_count": len(workflow_steps),
        "observed_engines": observed_engines,
        "engine_file_counts": {
            engine: len(paths)
            for engine, paths in sorted(engine_files.items())
        },
        "canonical_packages": [item["package"] for item in packages],
        "source_inventory": source_inventory,
    }

    pipeline_graph = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "workflow": relative(WORKFLOW_FILE) if WORKFLOW_FILE.exists() else None,
        "nodes": workflow_steps,
        "edges": pipeline_edges,
        "sequential_workflow_dag": True,
    }

    dependency_graph = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "nodes": sorted(module_graph),
        "edges": [
            {"from": source, "to": target}
            for source, targets in sorted(module_graph.items())
            for target in sorted(targets)
        ],
        "strongly_connected_components": components,
        "cycles": cycles,
        "acyclic": not cycles,
        "topological_order": topological_order(module_graph),
    }

    contract_inventory = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "authorities": engine_contracts,
        "explicit_contract_count": explicit_contract_count,
        "authority_count": len(engine_contracts),
    }

    domain_inventory = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "symbols": domain_models,
        "symbol_count": len(domain_models),
    }

    risk_register = {
        "audit_id": AUDIT_ID,
        "generated_at": generated_at,
        "risks": risks,
        "blocking_risk_count": len(blocking_risks),
        "risk_count": len(risks),
    }

    checklist = {
        "motors_independentes": bool(observed_engines) and not cycles,
        "interfaces_identificaveis": explicit_contract_count > 0,
        "inputs_outputs_identificados": any(item["producers"] for item in packages),
        "sem_ciclos_python": not cycles,
        "pipeline_deterministica": bool(workflow_steps),
        "dashboard_desacoplado": dashboard["decoupled_static_consumer"],
        "packages_identificados": bool(packages),
        "analytics_identificado": "analytics" in observed_engines,
    }

    report = f"""# {AUDIT_ID} — Production Brain Readiness Audit

**Mode:** READ ONLY  
**Generated:** {generated_at}  
**Decision:** `{decision}`

## Executive summary

The repository exposes {len(workflow_steps)} ordered GitHub Actions steps, {len(modules)} Python modules, {len(observed_engines)} observed engine categories and {len(packages)} canonical data packages.

The audit observed **{len(cycles)} internal Python dependency cycle(s)** and **{len(blocking_risks)} blocking risk(s)**.

## Observed engine categories

{chr(10).join(f'- `{engine}` — {len(engine_files[engine])} file(s)' for engine in observed_engines) or '- None observed'}

## Readiness checklist

{chr(10).join(f'- [{"x" if value else " "}] {key.replace("_", " ")}' for key, value in checklist.items())}

## Risks

{chr(10).join(f'- **{risk["severity"].upper()}** `{risk["id"]}` — {risk["description"]}' for risk in risks) or '- No material risks observed.'}

## Architectural conclusion

The audit does not introduce a Production Brain and does not change application behaviour. It only establishes the evidence base for **FOOTBALL-SHORTS-AI-0040B — Production Brain Design Decision**.
"""

    decision_text = f"""# {AUDIT_ID} — Production Brain Decision

## Decision

`{decision}`

## Authority

- Application source behaviour was not modified by this audit.
- The existing GitHub Actions pipeline remains the current orchestration authority.
- A Production Brain implementation is not authorized by this artefact.
- The next authorized phase is **FOOTBALL-SHORTS-AI-0040B — Production Brain Design Decision** when the decision is `READY_FOR_DESIGN`.

## Blocking risks

{chr(10).join(f'- `{risk["id"]}` — {risk["description"]}' for risk in blocking_risks) or '- None.'}
"""

    write_json("production_brain_inventory.json", production_inventory)
    write_json("production_pipeline_graph.json", pipeline_graph)
    write_json("engine_dependency_graph.json", dependency_graph)
    write_json("engine_contract_inventory.json", contract_inventory)
    write_json("dashboard_inventory.json", dashboard)
    write_json("package_inventory.json", {"audit_id": AUDIT_ID, "generated_at": generated_at, "packages": packages})
    write_json("domain_model_inventory.json", domain_inventory)
    write_json("production_brain_risk_register.json", risk_register)
    write_text("production_brain_readiness_report.md", report)
    write_text("production_brain_decision.md", decision_text)

    print("=" * 72)
    print(AUDIT_ID)
    print("PRODUCTION BRAIN READINESS AUDIT")
    print("READ_ONLY=TRUE")
    print(f"WORKFLOW_STEPS={len(workflow_steps)}")
    print(f"PYTHON_MODULES={len(modules)}")
    print(f"OBSERVED_ENGINES={len(observed_engines)}")
    print(f"DEPENDENCY_CYCLES={len(cycles)}")
    print(f"BLOCKING_RISKS={len(blocking_risks)}")
    print(f"DECISION={decision}")
    print(f"OUTPUT_DIR={OUTPUT_DIR}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
