# Feature Specification: Phase 1 — Foundation & Cleanup

**Feature Branch**: `019-foundation-cleanup`
**Created**: 2026-02-09
**Status**: Draft
**Input**: User description: "Phase 1 Foundation and Cleanup — Unify canonical number formatters, resolve architecture violations, consolidate duplicated parsing utilities, clean up analysis layer, and create core abstractions"
**Source**: [refactoring-plan.md](../refactoring-plan.md) — Phase 1 section

## Overview

Phase 1 is the preparatory layer of M2PY's refactoring plan. It addresses foundational issues that block later phases: duplicated value-formatting logic that can diverge on edge cases, architecture violations where the runtime depends on the codegen layer, duplicated parsing utilities with incompatible return types, and analysis-layer code that is unnecessarily repeated or misplaced.

The deliverables are:
- New shared modules (`core/values.py`, `core/names.py`, `core/parsing.py`, `core/tokenizer.py`, `asg/traversal.py`, `codegen/exceptions.py`) that centralize previously scattered logic
- Elimination of 15 backward imports from runtime/core into codegen
- Consolidation of 3 independent canonical-number formatters into 1
- Consolidation of 3 independent subscript-name parsers into 1
- Consolidation of 15+ parenthesis-depth state machines into 1 utility
- Analysis-layer deduplication (kill analyzers, call-argument processing, variable-write detection, expression unwrapping, naked-global detection)
- A reusable ASG statement-walking utility
- Trivial fixes: exception hierarchy, dead code removal, docstring correction, forcing `uses_dynamic_locals` for exclusive KILL/NEW

All changes are internal refactoring. No user-facing behavior changes. Existing tests must continue to pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Transpiler Produces Identical Output After Refactoring (Priority: P1)

A developer transpiles any MUMPS routine through m2py. The generated Python code is functionally identical to what the pre-refactoring version produced. No existing test fails.

**Why this priority**: This is the fundamental contract — refactoring must not change behavior. Every other story is worthless if this one fails.

**Independent Test**: Run the full test suite (`uv run pytest`) and the YDB validation suite. All tests pass. Spot-check generated output for representative routines to confirm no semantic drift.

**Acceptance Scenarios**:

1. **Given** the existing test suite, **When** all Phase 1 changes are applied, **Then** every previously-passing test still passes with no modifications to test assertions.
2. **Given** a MUMPS routine that uses canonical number formatting (e.g., `W +.50`, `W 1E-44`), **When** transpiled and executed, **Then** the output matches YottaDB exactly — confirming the unified formatter produces correct results.
3. **Given** a MUMPS routine that uses exclusive KILL (`K (X)`) or argumentless NEW, **When** transpiled under the TRAMPOLINE strategy without other dynamic-local triggers, **Then** the routine compiles and runs correctly instead of raising `NotImplementedError`.
4. **Given** the full test suite, **When** run after all Phase 1 changes, **Then** there are zero failures, zero xfails, and zero skips. Any test updated for refactoring retains its original intent and coverage.

---

### User Story 2 — Runtime Can Be Used Without Codegen Layer (Priority: P2)

A developer imports `m2py.runtime` in isolation (e.g., for embedding the MUMPS runtime in a Python application) without importing `m2py.codegen`. All runtime operations — including canonical number formatting, subscript canonicalization, and variable comparison — work correctly.

**Why this priority**: The architecture violation (runtime importing from codegen) prevents modular use and creates fragile deferred imports that can crash at runtime. Fixing this unblocks independent testing and future runtime-only distribution.

**Independent Test**: Write a test that imports only `from m2py.runtime import MUMPSRuntime` and `from m2py.core.values import m_num, m_str, m_truth, m_compare` — without any codegen import — and exercises basic value operations. The test passes.

**Acceptance Scenarios**:

1. **Given** a clean Python environment, **When** `from m2py.runtime import MUMPSRuntime` is executed without importing codegen, **Then** no `ImportError` is raised.
2. **Given** the runtime module, **When** `m_str`, `m_num`, `m_truth`, and `m_compare` are called via `core.values`, **Then** they return results identical to the current codegen-hosted implementations.
3. **Given** the 15 backward imports currently in runtime/core, **When** Phase 1 is complete, **Then** zero deferred imports from `m2py.codegen` remain in `runtime/` or `core/` (except the single acceptable `generate_python` dependency for XECUTE, which is injected via callback).

---

### User Story 3 — Contributor Can Modify Subscript Parsing in One Place (Priority: P2)

A contributor needs to fix a subscript-parsing bug (e.g., handling of quoted strings containing parentheses). They find a single `parse_subscripted_name()` function in `core/parsing.py` and a single `split_at_toplevel()` function in `core/tokenizer.py`. They fix it once and all call sites benefit.

**Why this priority**: Three divergent implementations of the same parsing logic is a correctness risk — a fix applied to one copy but not the others can cause silent data corruption through subscript mismatches.

**Independent Test**: Unit-test `core/parsing.py` and `core/tokenizer.py` with edge cases (nested parens, quoted commas, empty subscripts, numeric vs string subscripts). Verify that runtime, core/scope, and core/indirection all delegate to these shared functions.

**Acceptance Scenarios**:

1. **Given** the input `'ARR(1,"A,B",3)'`, **When** `parse_subscripted_name()` is called, **Then** it returns `('ARR', ['1', '"A,B"', '3'])`.
2. **Given** 3 previously independent implementations, **When** Phase 1 is complete, **Then** all 3 call sites delegate to `core/parsing.parse_subscripted_name()`.
3. **Given** 15+ hand-rolled parenthesis-depth state machines, **When** Phase 1 is complete, **Then** they delegate to `core/tokenizer.split_at_toplevel()`.

---

### User Story 4 — Contributor Can Add a New Kill-Like Command Without Duplication (Priority: P3)

A contributor needs to add a new KILL variant (e.g., a vendor-specific extension). They find a single `_analyze_kill_like()` helper and add a 3-line method that calls it, rather than copying 30+ lines of boilerplate.

**Why this priority**: Analysis-layer deduplication reduces the surface area for bugs and makes the codebase more approachable for new contributors.

**Independent Test**: Verify that `_analyze_KillCommand`, `_analyze_KSubscriptsCommand`, `_analyze_KValueCommand`, `_analyze_ZKillCommand`, and `_analyze_ZWithdrawCommand` all produce correct ASG nodes by running existing KILL/ZKILL tests.

**Acceptance Scenarios**:

1. **Given** 5 near-identical kill analyzer methods, **When** Phase 1 is complete, **Then** they share a common `_analyze_kill_like()` helper, with `ZWithdraw` delegating directly to `ZKill`.
2. **Given** DO/GOTO/JOB argument processing, **When** Phase 1 is complete, **Then** the shared `_analyze_call_arguments()` helper handles argument iteration for all three commands.

---

### User Story 5 — Contributor Can Walk ASG Statements with a Single Utility (Priority: P3)

A contributor writing a new analysis pass (e.g., detecting unreachable code) uses `asg.traversal.walk_statements()` to visit all statements recursively, instead of reimplementing the walk pattern.

**Why this priority**: Four independent scope-walking implementations means any new ASG node with a body (e.g., a new control-flow construct) must be added in four places. A single walker eliminates this.

**Independent Test**: Write a test that uses `walk_statements()` to count all statements in a routine with nested IF/FOR/DO blocks, and verify the count matches a manual traversal.

**Acceptance Scenarios**:

1. **Given** a routine with nested IF, FOR, and DO blocks, **When** `walk_statements()` is called with a counting visitor, **Then** it visits every statement exactly once.
2. **Given** 4 reimplementations of scope walking, **When** Phase 1 is complete, **Then** at least 2 of the 4 delegate to `asg.traversal.walk_statements()` (the remaining may have specialized needs that require parameters but should still use the shared walker).

---

### Edge Cases

- What happens when `m_str()` receives a `Decimal` with exponent < -43? The unified formatter must apply the exponent guard consistently (return `"0"`), matching YDB behavior.
- What happens when `parse_subscripted_name()` receives a name with no subscripts (e.g., `"X"`)? It returns `('X', [])` — no subscripts, not `None`.
- What happens when `split_at_toplevel()` receives an empty string? It returns `['']` (a list with one empty element), matching the behavior of Python's `str.split()` with no matches.
- What happens when `unwrap_expression()` encounters an `Expr` with operator tails? After Phase 1, it either handles tails correctly or asserts that tails are empty — it never silently drops them.
- What happens when a TRAMPOLINE routine uses `K (X)` without any other dynamic-local triggers? After Phase 1, the semantic analyzer detects exclusive KILL/NEW and forces `uses_dynamic_locals = True`, so the codegen path succeeds.

## Requirements *(mandatory)*

### Functional Requirements

#### Track A — Quick Wins & Analysis Cleanup

- **FR-001**: The system MUST define `CodegenError` and `UnsupportedFeatureError(CodegenError)` in a single `codegen/exceptions.py` module, with both `codegen/__init__.py` and `codegen/statements.py` importing from it. *(C-04)*
- **FR-002**: The `m_format_output` docstring MUST accurately describe the function's behavior — string values are returned unchanged; only numeric types undergo canonical formatting. *(S-17)*
- **FR-003**: The dead `generate_xecute_constant()` and `generate_xecute_dynamic()` stubs in `codegen/indirection.py` MUST be removed after verifying no callers exist. *(S-18)*
- **FR-004**: Kill-like analyzer methods (`_analyze_KillCommand`, `_analyze_KSubscriptsCommand`, `_analyze_KValueCommand`, `_analyze_ZKillCommand`, `_analyze_ZWithdrawCommand`) MUST share a common helper, with `ZWithdraw` delegating to `ZKill`. *(S-08)*
- **FR-005**: DO, GOTO, and JOB command argument processing in the semantic analyzer MUST share a common `_analyze_call_arguments()` helper. *(S-09)*
- **FR-006**: `unwrap_expression()` in the semantic analyzer MUST either handle operator tails correctly or assert that tails are empty — it MUST NOT silently discard tails. *(S-15)*
- **FR-007**: The semantic analyzer MUST detect exclusive KILL, argumentless KILL, exclusive NEW, and argumentless NEW commands during analysis and set `uses_dynamic_locals = True` for the containing routine, preventing `NotImplementedError` at codegen time. *(C-06)*

#### Track B — Analysis & ASG Infrastructure

- **FR-008**: `_check_var_modified_in_scope` in `for_analysis.py` MUST delegate to the existing write-detection infrastructure in `variables.py` rather than reimplementing it. *(S-20)*
- **FR-009**: The `contains_naked_global()` function MUST be moved from `codegen/expressions.py` to `analysis/variables.py`, executed during semantic analysis, and its result stored as an ASG annotation (`_has_naked_global`) on the expression node. Codegen MUST read the pre-computed annotation. *(C-08)*
- **FR-010**: A new `asg/traversal.py` module MUST provide a `walk_statements()` function that recursively visits all statements in a scope, descending into IF/FOR/DO bodies. Existing scope-walking reimplementations MUST delegate to this utility where feasible. *(S-10)*

#### Track C — Core Value Abstractions

- **FR-011**: A new `core/values.py` module MUST provide a single `mumps_canonical_str(value) -> str` function implementing MUMPS canonical number formatting, including the exponent guard (exponent < -43 → `"0"`). *(C-01)*
- **FR-012**: `m_str()` in `codegen/helpers.py` and `m_format_output()` in `runtime/helpers.py` MUST delegate canonical number formatting to `mumps_canonical_str()` from `core/values.py`. `m_format_output` retains its string-passthrough and MArray-unwrap responsibilities. *(C-01)*
- **FR-013**: `SubscriptCanonicalizer.canonicalize_numeric()` in `core/subscripts.py` MUST delegate to `mumps_canonical_str()` from `core/values.py`. *(C-01)*
- **FR-014**: `core/values.py` MUST also provide `m_num()`, `m_str()`, `m_truth()`, and `m_compare()` — the MUMPS value-model functions currently in `codegen/helpers.py`. *(C-02)*
- **FR-015**: All 14 deferred imports of `m_num`, `m_str`, `m_truth`, `m_compare` from `m2py.codegen` in `runtime/` MUST be replaced with direct imports from `m2py.core.values`. The 1 deferred import in `core/` MUST also be replaced. *(C-02)*
- **FR-016**: `codegen/helpers.py` MUST re-export the value-model functions from `core/values.py` for backward compatibility with generated code and existing imports. *(C-02)*
- **FR-017**: `translate_name` and `NameTranslator` MUST be moved to `core/names.py`, with re-exports from `codegen/helpers.py` for backward compatibility. *(C-02)*
- **FR-018**: The `generate_python` dependency in the runtime (used for XECUTE) MUST be resolved by injecting it as a callback at `MUMPSRuntime` construction time, rather than importing from codegen. *(C-02)*
- **FR-019**: The duplicate `_is_canonical_numeric` in `runtime/helpers.py` MUST be removed, with its callers using the unified `core/values.py` implementation. *(S-11)*
- **FR-020**: `m_add`, `m_sub`, and `m_mul` MUST share a common `_decimal_binop(left, right, op)` helper, with each function becoming a thin wrapper. *(S-06)*

#### Track D — Core Parsing Utilities

- **FR-021**: A new `core/parsing.py` module MUST provide `parse_subscripted_name(name: str) -> tuple[str, list[str]]` that parses `'ARR(1,2)'` into `('ARR', ['1', '2'])` and returns an empty list for unsubscripted names. *(C-03)*
- **FR-022**: All 3 existing `_parse_subscripted_name` implementations (in `runtime/__init__.py`, `core/scope.py`, and `core/indirection.py`) MUST delegate to `core/parsing.parse_subscripted_name()`. Numeric subscript conversion MUST be a separate `canonicalize_subscript()` step applied only where needed. *(C-03)*
- **FR-023**: A new `core/tokenizer.py` module MUST provide `split_at_toplevel(s: str, delimiter: str = ",", respect_quotes: bool = True) -> list[str]` that splits a string respecting parenthesis nesting and quote state. *(S-07)*
- **FR-024**: Hand-rolled parenthesis-depth + quote-tracking state machines across `runtime/` and `core/` MUST delegate to `core/tokenizer.split_at_toplevel()`. *(S-07)*

#### Test Suite Integrity

- **FR-025**: The full test suite MUST pass with zero xfails, zero skips, and zero failures after all Phase 1 changes are applied. Tests MAY be updated to reflect refactored module paths, renamed functions, or restructured internals, but test *intent* and *coverage* MUST NOT be reduced.

### Key Entities

- **`core/values.py`**: New module — single source of truth for MUMPS value semantics (`mumps_canonical_str`, `m_num`, `m_str`, `m_truth`, `m_compare`)
- **`core/names.py`**: New module — name translation utilities (`translate_name`, `NameTranslator`)
- **`core/parsing.py`**: New module — string-level parsing utilities (`parse_subscripted_name`, `canonicalize_subscript`)
- **`core/tokenizer.py`**: New module — delimiter-aware string splitting (`split_at_toplevel`)
- **`asg/traversal.py`**: New module — recursive ASG statement walker (`walk_statements`)
- **`codegen/exceptions.py`**: New module — codegen exception hierarchy (`CodegenError`, `UnsupportedFeatureError`)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full test suite passes with zero failures, zero xfails, and zero skips. Tests may be updated to reflect refactored module paths or restructured internals, but no test may be removed or have its assertions weakened.
- **SC-002**: Zero deferred imports from `m2py.codegen` remain in `m2py.runtime/` or `m2py.core/` (with the documented exception of the XECUTE callback pattern for `generate_python`).
- **SC-003**: Canonical number formatting logic exists in exactly 1 implementation (`core/values.py`), with all former implementations delegating to it.
- **SC-004**: Subscript-name parsing logic exists in exactly 1 implementation (`core/parsing.py`), with all 3 former implementations delegating to it.
- **SC-005**: MUMPS routines using exclusive KILL (`K (X)`) or argumentless NEW under the TRAMPOLINE strategy compile and execute correctly — no `NotImplementedError` is raised.
- **SC-006**: A new test importing `m2py.runtime.MUMPSRuntime` and `m2py.core.values` without any codegen import passes successfully.
- **SC-007**: The `codegen/exceptions.py` module is the single definition point for `CodegenError` and `UnsupportedFeatureError`, and code catching `CodegenError` catches errors from all codegen modules.
- **SC-008**: The 5 kill-like analyzer methods produce correct ASG output (verified by existing KILL/ZKILL tests) while sharing a common helper.

## Assumptions

- The refactoring plan's item descriptions and candidate designs are accurate and validated. The spec relies on the fact-checked counts (15 backward imports, 3 parse implementations, 69 strategy-dispatch sites, etc.).
- "Backward compatibility re-exports" means existing `from m2py.codegen.helpers import m_str` still works (for generated code that imports these symbols).
- The `generate_python` XECUTE dependency is the only acceptable remaining runtime→codegen coupling, resolved via callback injection rather than direct import.
- The exponent guard behavior (exponent < -43 → `"0"`) in `m_format_output` is the correct MUMPS behavior, and the unified formatter should apply it consistently.
- Phase 2 depends on this phase being fully complete — particularly `core/values.py` (changes codegen import paths) and `asg/traversal.py` (used by S-16 in Phase 2).

## Dependencies

- **Blocked by**: Nothing — Phase 1 has no external dependencies.
- **Blocks**: Phase 2 (Codegen Refactoring) depends on Track C (`core/values.py`) and Track B (`asg/traversal.py`) completing.

## Scope Boundaries

### In Scope

- All items listed in the refactoring plan's Phase 1: C-01, C-02, C-03, C-04, C-06, C-08, S-06, S-07, S-08, S-09, S-10, S-11, S-15, S-17, S-18, S-20
- Creating new core modules: `core/values.py`, `core/names.py`, `core/parsing.py`, `core/tokenizer.py`, `asg/traversal.py`, `codegen/exceptions.py`
- Updating all import sites to use new module locations
- Maintaining backward-compatible re-exports

### Out of Scope

- Phase 2 codegen refactoring (S-01, S-02, S-03, S-04, S-05, S-12, S-13, S-14, S-16, S-19, C-07, C-09)
- Phase 3 new features (F-01 through F-14, C-05)
- Phase 4 large architecture changes (I/O devices, JOB, inter-process LOCK)
- Changes to the 69 strategy-dispatch sites in codegen (Phase 2, S-01)
- Changes to the 99 subscript-tuple-generation sites in codegen (Phase 2, S-02)
- Any user-facing behavior changes
- ASG field cleanup (S-16 — Phase 2)
