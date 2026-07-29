# FOOTBALL-SHORTS-AI-0040D — Engine Adapter Design Decision

## Status

**DECIDED — READY FOR CONTRACT IMPLEMENTATION**

## Purpose

Define the governed boundary between the canonical Production Brain contracts introduced by `FOOTBALL-SHORTS-AI-0040C` and the existing repository engines, scripts, package builders and workflow entry points.

This decision does **not** install executable adapters, migrate engine business logic, introduce a Production Brain orchestrator or alter the production workflow.

## Decision

Every existing engine integrated into the future Production Brain shall be exposed through one explicit adapter that implements the canonical `EngineContract` protocol.

The adapter is an anti-corruption boundary. It translates between the immutable Production Brain model and the existing engine-specific invocation and output model while preserving existing business logic outside the adapter.

## Canonical adapter responsibilities

An adapter shall:

1. expose one stable `engine_id`;
2. declare exactly one canonical `ProductionStage`;
3. accept only a `ProductionContext` at its public execution boundary;
4. validate that `context.current_stage` matches the adapter stage before invocation;
5. resolve repository-relative input artifacts without mutating the context;
6. invoke one pre-existing engine authority through dependency injection;
7. translate the engine outcome into one canonical `EngineResult`;
8. emit repository-relative `ArtifactReference` values;
9. include deterministic, non-secret execution evidence;
10. convert expected engine failures into fail-closed failed results;
11. allow unexpected programming defects to propagate;
12. perform no stage sequencing and make no next-engine decision.

## Forbidden responsibilities

An adapter shall not:

- contain or duplicate editorial, ranking, generation, publishing or analytics business logic;
- select the next production stage;
- invoke more than one engine authority;
- mutate a `ProductionContext` or `EngineResult`;
- use absolute paths or parent traversal;
- perform implicit network access;
- read undeclared environment values or secrets;
- perform publication merely because its stage is `PUBLISHING`;
- silently convert failures into `SKIPPED` or `SUCCEEDED`;
- return unregistered or unverifiable artefacts;
- depend on GitHub Actions as its runtime API.

## Adapter identity

Each adapter shall have a stable identifier using:

```text
<domain>.<capability>.adapter.v1
```

Identifiers shall be unique and shall not be derived from volatile module paths or workflow job names.

## Invocation boundary

The legacy engine authority shall be supplied by dependency injection. Global mutable discovery is prohibited.

The injected authority may be a callable, object method or narrowly scoped service interface, but each adapter owns exactly one deterministic invocation boundary.

## Input translation

- required artifact IDs are declared;
- missing or duplicate required artifacts fail closed;
- media types are validated before invocation;
- paths remain repository-relative;
- consumed metadata keys are declared;
- undeclared metadata shall not influence execution;
- source artefacts are never modified in place.

## Output translation

The returned `EngineResult` shall have matching adapter identity, stage and context stage. Produced artefacts shall be validated repository-relative references. Evidence shall be deterministic and non-secret. Failed outcomes require a stable error code and safe message. Non-failed outcomes contain no error fields.

Produced artefacts are not automatically appended to the context by the adapter. Context advancement and aggregation belong to the future orchestration authority.

## Failure model

Known operational or validation failures become `EngineStatus.FAILED`.

`EngineStatus.SKIPPED` is allowed only under explicit adapter policy. Missing required input is not implicitly a skip.

Unexpected exceptions, contract violations and invalid outputs propagate and terminate the future governed execution fail closed.

## Side-effect policy

Side effects are denied by default. File writes, network access, publication, credentials and external APIs require explicit future capability declarations and separate activation authority.

This decision grants no network, publication or credential capability.

## Registry decision

The future adapter registry shall be explicit and immutable during one execution. It shall fail closed on duplicate IDs, unknown IDs, missing specifications, contract non-conformance or divergence between registered and runtime identity/stage.

Dynamic import scanning and implicit module discovery are prohibited as the canonical registry mechanism.

## Compatibility with 0040C

This decision preserves `ProductionStage`, `EngineStatus`, `ArtifactReference`, `ProductionContext`, `EngineResult` and `EngineContract` unchanged.

No modification to `src/production_brain/contracts.py` is authorised by `0040D`.

## Explicit non-authorisations

This decision does not authorise executable adapters, registry implementation, orchestration, workflow migration, publication execution, network calls, secret resolution or production activation.

## Next authorised artefact

**FOOTBALL-SHORTS-AI-0040E — Engine Adapter Contract Foundation**
