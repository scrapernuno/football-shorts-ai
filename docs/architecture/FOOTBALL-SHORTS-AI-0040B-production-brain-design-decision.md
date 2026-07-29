# FOOTBALL-SHORTS-AI-0040B — Production Brain Design Decision

## Status

**DESIGN DECISION — NO RUNTIME IMPLEMENTATION**

This document defines the canonical architecture for introducing a Production Brain without changing the current functional behaviour of the Football Shorts AI pipeline.

## Constitutional authority

The decision is authorized by FOOTBALL-SHORTS-AI-0040A, whose certified result was `READY_FOR_DESIGN` with no blocking risks and no detected Python dependency cycles.

## Decision

The Production Brain SHALL be introduced as a deterministic orchestration authority above existing engines. It SHALL NOT absorb engine-specific business logic, silently mutate package schemas, publish content, bypass governance checks, or replace the current GitHub Actions workflow before a separately certified migration phase.

## Canonical boundaries

### Production Brain responsibility

The Production Brain owns only:

1. execution ordering;
2. context handover;
3. precondition evaluation;
4. result registration;
5. failure attribution;
6. deterministic lifecycle state;
7. audit evidence aggregation.

### Engine responsibility

Each engine remains the sole authority for its own domain logic and package generation. Engines MUST NOT depend on Production Brain internals.

### GitHub Actions responsibility

GitHub Actions remains the external execution authority during the compatibility phase. The Production Brain will initially be invoked by the workflow and SHALL NOT autonomously dispatch, publish, or perform network operations.

## Canonical contracts

### ProductionContext

The global context is immutable-by-convention and versioned. It contains identifiers and references, not duplicated package payloads.

Required fields:

- `schema_version`
- `execution_id`
- `correlation_id`
- `started_at`
- `source_topic_ref`
- `artifact_root`
- `engine_results`
- `lifecycle_state`
- `failure`
- `governance`

### EngineContract

Every governed engine exposes one conceptual contract:

- `engine_id`
- `contract_version`
- `requires`
- `produces`
- `execute(context)`
- `validate_result(result)`

The concrete Python interface is deferred to FOOTBALL-SHORTS-AI-0040C.

### EngineResult

Every engine result contains:

- `engine_id`
- `contract_version`
- `status`
- `started_at`
- `completed_at`
- `input_refs`
- `output_refs`
- `evidence_refs`
- `error`

Allowed status values:

- `pending`
- `running`
- `succeeded`
- `failed`
- `blocked`
- `skipped`

## Canonical engine sequence

The initial governed sequence is:

1. research
2. knowledge
3. evidence
4. reference
5. story
6. emotion
7. audience
8. originality
9. production
10. quality
11. publishing
12. analytics
13. learning
14. dashboard

The sequence is declarative. An engine MAY be represented by an adapter around an existing script during migration.

## Failure semantics

The Production Brain is fail-closed.

- Missing required input blocks the dependent engine.
- Invalid output fails the producing engine.
- A failed mandatory engine blocks downstream mandatory engines.
- Optional engines may be skipped only through explicit policy.
- No failure may be converted into success by logging alone.
- Failure evidence must preserve the originating engine and exception classification without secrets.

## Idempotency

An execution is identified by `execution_id` and a deterministic input fingerprint.

- Re-running the same completed engine with the same fingerprint SHALL reuse or verify the existing result according to policy.
- Partial results SHALL NOT be treated as complete.
- Atomic write patterns remain required for generated JSON artifacts.

## Compatibility rules

1. Existing package paths remain canonical during the first implementation phase.
2. Existing builders remain callable independently.
3. Existing workflow ordering remains unchanged until migration certification.
4. The Production Brain adds orchestration evidence without altering package content.
5. Dashboard consumers remain unaware of the Production Brain during compatibility mode.
6. Publication execution remains governed by existing publication controls.

## Security and governance

The Production Brain SHALL:

- avoid storing secrets in context or evidence;
- avoid browser-side privileged execution;
- respect provider and copyright boundaries;
- preserve manual-review gates;
- produce deterministic audit evidence;
- expose no implicit network capability.

## Implementation phases authorized by this decision

### FOOTBALL-SHORTS-AI-0040C

Production Brain contract foundation:

- immutable data contracts;
- engine protocol;
- lifecycle enums;
- validation;
- isolated tests;
- no workflow migration.

### FOOTBALL-SHORTS-AI-0040D

Compatibility orchestrator:

- adapter registration;
- deterministic plan execution;
- dry-run and evidence modes;
- no replacement of the canonical workflow.

### FOOTBALL-SHORTS-AI-0040E

Controlled workflow integration:

- invoke orchestrator from GitHub Actions;
- compare legacy and orchestrated evidence;
- preserve output compatibility;
- fail closed on divergence.

## Explicitly not authorized

This decision does not authorize:

- autonomous publishing;
- removal of existing workflow steps;
- package schema migration;
- engine business-logic rewrites;
- direct TikTok publishing;
- new network providers;
- secret persistence;
- production execution outside GitHub Actions.

## Acceptance criteria

This design decision is certified only when an automated certifier confirms:

- the required sections and clauses exist;
- the canonical engine sequence is complete and unique;
- the contract specification is valid JSON;
- the contract and document agree;
- implementation remains explicitly deferred;
- the next authorized phase is FOOTBALL-SHORTS-AI-0040C.

## Final decision

**APPROVED FOR CONTRACT FOUNDATION ONLY**

Next authorized artefact:

`FOOTBALL-SHORTS-AI-0040C — Production Brain Contract Foundation`
