# FOOTBALL-SHORTS-AI-0040D — Engine Adapter Design Decision

## Status

**DESIGN DECISION — NO RUNTIME IMPLEMENTATION**

This document defines the canonical anti-corruption boundary between the Production Brain contracts and all execution engines.

No runtime adapter implementation is authorized by this decision.

---

# Constitutional authority

This decision is authorized by:

- FOOTBALL-SHORTS-AI-0040C — Production Brain Contract Foundation

The immutable contracts established in 0040C remain the single canonical authority.

No modification to `src/production_brain/contracts.py` is authorized.

---

# Decision

The Engine Adapter layer SHALL provide a deterministic translation boundary between the canonical Production Brain contracts and existing execution engines.

The adapter exists exclusively to isolate engine implementations from orchestration contracts.

The adapter SHALL NOT contain business logic.

The adapter SHALL NOT perform workflow orchestration.

The adapter SHALL NOT publish content.

The adapter SHALL NOT perform implicit provider discovery.

---

# Anti-corruption boundary

The adapter layer is an anti-corruption boundary.

Its only responsibility is translating between:

- ProductionContext
- EngineContract
- EngineResult

and the existing engine implementations.

The boundary prevents internal engine implementations from leaking into the canonical orchestration model.

---

# Canonical responsibilities

Each adapter SHALL:

- receive immutable ProductionContext
- invoke exactly one engine authority
- translate engine output into EngineResult
- preserve deterministic execution evidence
- preserve failure attribution

Adapters SHALL NOT:

- change execution ordering
- mutate context
- perform orchestration
- publish artifacts
- access secrets
- execute network operations
- introduce engine-specific orchestration logic

---

# Dependency injection

Adapter resolution SHALL use dependency injection.

Dynamic import scanning is forbidden.

Global runtime discovery is forbidden.

Every adapter SHALL be registered explicitly.

---

# Registry model

The adapter registry SHALL be:

- immutable
- deterministic
- fail closed

Unknown adapters SHALL terminate execution with explicit certification failure.

---

# Failure semantics

Expected failures translate to failed EngineResult.

Unexpected implementation defects SHALL propagate without suppression.

Side effects are denied by default.

---

# Authorized properties

Required properties include:

- immutable context
- deterministic translation
- explicit dependency injection
- explicit immutable registry
- one adapter per engine authority
- expected failure translation
- preserved execution evidence

---

# Forbidden properties

Forbidden behaviour includes:

- business logic migration
- implicit network access
- runtime mutation
- dynamic discovery
- automatic registration
- implicit provider lookup

---

# Explicitly not authorized

This decision does not authorize:

- executable engine adapters
- Production Brain orchestration
- workflow migration
- publication execution
- network providers
- secret management
- runtime implementation

---

# Next authorized artifact

The next authorized artifact is:

**FOOTBALL-SHORTS-AI-0040E**

No implementation work beyond this architectural decision is authorized by this document.

---

# Final decision

**READY FOR CONTRACT IMPLEMENTATION**
