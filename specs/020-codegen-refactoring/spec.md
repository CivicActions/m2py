# Feature Specification: Codegen Refactoring (Phase 2)

**Feature Branch**: `020-codegen-refactoring`  
**Created**: 2026-02-10  
**Status**: Draft  
**Input**: User description: "Complete implementation of Phase 2 from the refactoring plan: codegen refactoring including subscript tuple extraction (S-02), LHS piece/extract deduplication (S-05), scope-state sync consolidation (S-04), GotoExternal handler extraction (S-14), ZWRITE range correctness (C-09), strategy-dispatch consolidation (S-01), XECUTE coupling cleanup (S-13), comment extraction via ASG (S-19), by-ref call unification (C-07), indirection template extraction (S-03), offset_wrapper consolidation (S-12), and ASG field cleanup (S-16)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Transpiled MUMPS programs produce identical output after codegen refactoring (Priority: P1)

A developer transpiles any MUMPS routine through m2py and receives Python code that executes with **byte-identical output** to the code generated before the refactoring. The refactoring changes only the internal structure of the code generator — not the semantics of the generated Python.

**Why this priority**: The entire refactoring is meaningless if it changes transpilation output. Every other story depends on this invariant holding.

**Independent Test**: Run the full existing test suite (5,883+ tests across unit, functional, and integration tiers). Every test must pass. No new `xfail`, `skip`, or `expectedFailure` markers may be introduced.

**Acceptance Scenarios**:

1. **Given** the complete m2py test suite, **When** all tests are executed via `uv run pytest`, **Then** 100% of tests pass with zero failures, zero errors, zero new xfails, and zero new skips.
2. **Given** a set of MUMPS routines from the YDBTest suite, **When** each is transpiled and executed, **Then** the output matches YottaDB reference output exactly as it did before refactoring.
3. **Given** any MUMPS routine that exercises subscripted variables, indirection, LOCK, KILL, NEW, DO, GOTO, JOB, SET $PIECE, SET $EXTRACT, XECUTE, ZWRITE, IF, HANG, FOR, by-reference calls, and scope sync, **When** transpiled and run, **Then** behavior is identical to pre-refactoring.

---

### User Story 2 — Subscript tuple generation uses a single shared function (Priority: P2)

A codegen maintainer sees that all ~99 occurrences of the 4-line subscript-tuple generation pattern in `codegen/statements.py`, `codegen/expressions.py`, and `codegen/indirection.py` have been replaced by calls to a single `gen_subscripts_tuple()` helper function.

**Why this priority**: This is the most-repeated pattern in the codebase (99 sites). Extracting it first reduces noise for all subsequent refactoring work and has the lowest behavioral risk — the extraction is purely mechanical.

**Independent Test**: After extraction, search for the old inline pattern (list comprehension + single-element trailing-comma check). Zero matches should remain. All tests pass.

**Acceptance Scenarios**:

1. **Given** the codegen module, **When** a developer searches for the inline subscript-tuple pattern, **Then** zero occurrences remain outside the shared helper.
2. **Given** any MUMPS routine with subscripted variables (`SET A(1,2)=3`, `WRITE ^G(X,Y)`), **When** transpiled, **Then** the generated Python uses correctly formed subscript tuples identical to before.
3. **Given** a single-subscript variable (`SET A(1)=2`), **When** transpiled, **Then** the generated tuple includes the trailing comma (`(expr,)`).

---

### User Story 3 — LHS `$PIECE` and `$EXTRACT` share a common getter/setter builder (Priority: P2)

A codegen maintainer sees that `_generate_lhs_piece` and `_generate_lhs_extract` in `codegen/statements.py` share a common `_build_lhs_getter_setter()` helper that handles variable-type dispatch (global, naked global, indirection, local) once. Each function only adds its specific positional-argument handling and runtime call (`m_set_piece` vs `m_set_extract`).

**Why this priority**: ~300 lines of near-identical code become ~100 lines. Bugs in LHS variable resolution only need fixing in one place.

**Independent Test**: Transpile MUMPS using `SET $P(X,"^",2)=Y` and `SET $E(X,1,3)=Y` for all variable types (local, global, naked global, indirected). Output matches pre-refactoring.

**Acceptance Scenarios**:

1. **Given** `SET $PIECE(^G(1),"^",2)="val"`, **When** transpiled and run, **Then** the global's second `^`-delimited piece is set correctly.
2. **Given** `SET $EXTRACT(X,2,4)="abc"`, **When** transpiled and run, **Then** characters 2–4 of X are replaced.
3. **Given** `SET $PIECE(@VAR,"^",1)="val"` (indirection), **When** transpiled and run, **Then** the indirected variable is correctly modified.
4. **Given** the codegen source, **When** inspected, **Then** the MIndirection handling block (~50 lines) exists in exactly one location, not duplicated.

---

### User Story 4 — Scope-state sync blocks use shared emit helpers (Priority: P2)

A codegen maintainer sees that all 22 scope↔state synchronization blocks (16 in `statements.py`, 6 in `routine.py`) have been replaced with calls to `emit_state_to_scope_sync()` and `emit_scope_to_state_sync()`.

**Why this priority**: These sync blocks are load-bearing correctness code. Having 22 copies means any fix must be applied 22 times. Consolidation directly prevents future bugs.

**Independent Test**: Transpile routines using TRAMPOLINE strategy with dynamic locals. Verify state↔scope synchronization works at subroutine boundaries, after GOTO, and during error handling.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with GOTO that requires state→scope sync, **When** transpiled and run, **Then** variables are correctly available after the GOTO target.
2. **Given** a routine with nested DO calls using TRAMPOLINE, **When** transpiled and run, **Then** scope→state sync preserves all variable values.
3. **Given** the codegen source, **When** searched for inline scope sync patterns, **Then** zero copies remain outside the shared helpers.

---

### User Story 5 — GotoExternal handler blocks use a shared emitter (Priority: P2)

A codegen maintainer sees that all 6 `except GotoExternal` handler blocks (4 in `statements.py`, 2 in `routine.py`) call a single `_emit_goto_external_handler()` function.

**Why this priority**: Small mechanical change with clear boundaries. Reduces maintenance overhead for GotoExternal error handling.

**Independent Test**: Transpile routines with external GOTO (`GOTO label^ROUTINE`). Verify the handler correctly propagates scope sync and re-raises.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with `GOTO label^OtherRoutine`, **When** transpiled and run, **Then** external GOTO behaves correctly, preserving variable state across the transition.
2. **Given** the codegen source, **When** searched for inline `except GotoExternal` blocks with scope sync code, **Then** zero inline copies remain.

---

### User Story 6 — ZWRITE subscript ranges filter correctly instead of treating as wildcard (Priority: P2)

A developer transpiles MUMPS code using `ZWRITE ^A(1:3)` and the generated Python correctly displays only nodes with first subscript between 1 and 3, rather than treating the range as a wildcard that displays all nodes.

**Why this priority**: This is a correctness fix (C-09). The current behavior silently returns wrong results.

**Independent Test**: Create a global with subscripts 0 through 5, then `ZWRITE ^A(2:4)` and verify only subscripts 2, 3, 4 are displayed.

**Acceptance Scenarios**:

1. **Given** a global `^A` with subscripts 0–5, **When** `ZW ^A(2:4)` is transpiled and run, **Then** only `^A(2)`, `^A(3)`, and `^A(4)` are displayed.
2. **Given** `ZW X(1:3)` for a local array with subscripts 0–5, **When** transpiled and run, **Then** only subscripts 1–3 are displayed.
3. **Given** `ZW ^A(1:3,"B":"D")` with mixed numeric/string subscript ranges, **When** transpiled and run, **Then** filtering applies MUMPS collation rules at each subscript level.
4. **Given** the codegen source for ZWRITE, **When** inspected, **Then** the range handling code exists in exactly one location (not duplicated for globals vs locals).

---

### User Story 7 — Strategy-dispatch for variable access uses shared helpers (Priority: P2)

A codegen maintainer sees that all ~69 occurrences of the 3-way variable-access dispatch pattern (TRAMPOLINE + dynamic_locals / TRAMPOLINE + state_vars / SIMPLE_FUNCTIONS) have been replaced with calls to helper functions in a new `codegen/var_access.py` module.

**Why this priority**: The largest single duplication pattern (69 sites). This is scheduled after S-02 and S-04 to reduce code volume first, making this extraction safer and more readable.

**Independent Test**: Transpile routines exercising all three strategies. Verify variable reads/writes produce identical Python.

**Acceptance Scenarios**:

1. **Given** a routine using SIMPLE_FUNCTIONS strategy, **When** transpiled, **Then** variable access uses `_scope.get(...)` expressions identical to before.
2. **Given** a routine using TRAMPOLINE with static state vars, **When** transpiled, **Then** variable access uses `state.xxx` expressions identical to before.
3. **Given** a routine using TRAMPOLINE with dynamic locals, **When** transpiled, **Then** variable access uses `state._locals.get(...)` expressions identical to before.
4. **Given** the codegen source, **When** searched for the inline 3-way dispatch pattern, **Then** zero occurrences remain outside `codegen/var_access.py`.

---

### User Story 8 — XECUTE compilation pipeline uses a shared function (Priority: P2)

A codegen maintainer sees that the inline XECUTE handler in `codegen/statements.py` no longer directly imports parser functions or duplicates the analysis pipeline. Instead, a shared `compile_mumps_line()` function handles the full parse→analyze→structure pipeline, used by both regular parsing and XECUTE.

**Why this priority**: Eliminates a backward codegen→parser dependency and removes inline pipeline duplication.

**Independent Test**: Transpile routines with XECUTE ("W 1 Q"). Verify the compiled code produces identical behavior.

**Acceptance Scenarios**:

1. **Given** `XECUTE "WRITE 1,! QUIT"`, **When** transpiled and run, **Then** output is `1` followed by a newline.
2. **Given** `XECUTE X` (dynamic XECUTE with variable), **When** transpiled and run, **Then** the variable's content is compiled and executed correctly.
3. **Given** the codegen source, **When** inspected, **Then** `statements.py` does not import from `parser/` directly.

---

### User Story 9 — Comment extraction reads from ASG annotation instead of re-scanning source (Priority: P3)

A codegen maintainer sees that `_emit_source_comment` in `codegen/statements.py` reads a pre-populated `comment` field from the ASG `MStatement` node rather than re-scanning original MUMPS source lines for unquoted semicolons.

**Why this priority**: Lower priority because the current approach works correctly. This is a structural improvement that moves analysis out of codegen.

**Independent Test**: Transpile a routine with inline comments (`;`). Verify comments appear in generated Python output identically.

**Acceptance Scenarios**:

1. **Given** `SET X=1 ; initialize`, **When** transpiled, **Then** the generated Python includes `# initialize` as a comment.
2. **Given** `WRITE "hello;world"` (semicolon inside string), **When** transpiled, **Then** no spurious comment is extracted.
3. **Given** the ASG `MStatement` class, **When** inspected, **Then** it has a `comment: Optional[str]` field populated during parsing.

---

### User Story 10 — By-reference call handling is unified across strategies (Priority: P3)

A codegen maintainer sees that both SIMPLE_FUNCTIONS and TRAMPOLINE strategies use the same MArray-aliasing approach for by-reference parameter passing. The TRAMPOLINE strategy no longer uses a value-result approach that can lose mutations on error.

**Why this priority**: This is the highest-risk correctness change (C-07) and is scheduled last, benefiting from all prior cleanup. It's P3 because the current behavior only diverges in error scenarios.

**Independent Test**: Create MUMPS routines with by-reference calls under both strategies. Verify that mutations by the callee are visible to the caller, including when the callee errors.

**Acceptance Scenarios**:

1. **Given** a SIMPLE_FUNCTIONS routine passing a variable by reference (`DO SUB(.X)`), **When** the callee modifies X and returns, **Then** the caller sees the modification.
2. **Given** a TRAMPOLINE routine passing a variable by reference, **When** the callee modifies the variable and returns, **Then** the caller sees the modification.
3. **Given** a TRAMPOLINE routine where the callee modifies the by-ref variable then encounters an error, **When** the error is trapped, **Then** the mutation made before the error is preserved (not rolled back by value-result semantics).
4. **Given** a routine with multiple by-reference parameters, **When** transpiled and run under both strategies, **Then** all parameter modifications are correctly propagated.
5. **Given** a caller passing `.X` where X has descendants (`X(1)`, `X(2)`), **When** the callee does `SET A(3)="new"` and `KILL A(1)`, **Then** the caller sees `X(3)="new"` and `X(1)` is undefined — matching YDB DATA-CELL aliasing semantics.
6. **Given** a caller passing `.X` by reference, **When** the callee checks `$DATA(A)`, **Then** it returns `11` (has value and descendants) if X had both, matching YDB behavior.

---

### User Story 11 — Indirection functions use a shared template (Priority: P2)

A codegen maintainer sees that the 14 near-identical templatizable indirection generation functions in `codegen/indirection.py` (out of 16 total, ~800 lines of duplicated logic across 2,092 total lines) have been collapsed to a shared `_build_indirection_call()` template function plus thin 3–5 line wrappers. The 2 complex functions (`generate_indirect_do`, `generate_indirect_goto`) are simplified but retain their own implementations.

**Why this priority**: ~800 lines of near-identical code with subtle variation across 14 functions. Bugs fixed in one indirection type must currently be fixed 13 more times.

**Independent Test**: Transpile MUMPS using all indirection forms (SET @X, WRITE @Y, KILL @Z, etc.). Verify each produces correct runtime behavior.

**Acceptance Scenarios**:

1. **Given** `SET @X=1` (SET indirection), **When** transpiled and run, **Then** the indirected variable is set correctly.
2. **Given** `WRITE @X` (WRITE indirection), **When** transpiled and run, **Then** the indirected variable's value is written.
3. **Given** `KILL @X` (KILL indirection), **When** transpiled and run, **Then** the indirected variable is killed.
4. **Given** `IF @X` (IF indirection), **When** transpiled and run, **Then** the indirected expression is evaluated as a truth value.
5. **Given** multi-level indirection (`SET @(@X)=1`), **When** transpiled and run, **Then** nested indirection resolves correctly.
6. **Given** `codegen/indirection.py`, **When** its line count is measured, **Then** it is reduced by at least 40% from the pre-refactoring baseline (~2,092 lines).

---

### User Story 12 — offset_wrapper closures are consolidated (Priority: P3)

A codegen maintainer sees that the two ~100-line `offset_wrapper` closures in `runtime/__init__.py` (sharing ~80% identical logic) have been replaced by a single `_create_offset_entry_wrapper()` factory function.

**Why this priority**: Lower priority structural improvement. Two copies with subtle differences in error handling and state sync are a maintenance hazard but not an active correctness issue.

**Independent Test**: Transpile routines with label+offset entry points. Verify they execute correctly.

**Acceptance Scenarios**:

1. **Given** a routine called with a label offset (`DO LABEL+2^ROUTINE`), **When** transpiled and run, **Then** execution starts at the correct offset.
2. **Given** the runtime source, **When** inspected, **Then** the scope init, state creation, trampoline loop, and state sync logic exist in exactly one location.
3. **Given** error handling during offset entry, **When** an error occurs, **Then** it is propagated correctly through the unified wrapper.

---

### User Story 13 — ASG deprecated fields and missing types are cleaned up (Priority: P3)

A codegen maintainer sees that the ASG dataclass definitions have been cleaned up: redundant fields removed, untyped fields given proper dataclass types, and alias commands delegate properly.

**Why this priority**: Structural cleanup that makes the ASG definitions accurate and reduces confusion for future development.

**Independent Test**: Transpile routines exercising IF, HANG, LOCK, XECUTE, and ZWithdraw. All produce correct output.

**Acceptance Scenarios**:

1. **Given** `MIfStatement`, **When** inspected, **Then** it has only `conditions` (list), not a redundant `condition` field.
2. **Given** `MHangStatement`, **When** inspected, **Then** it has only `durations` (list), not a deprecated `duration` field.
3. **Given** `MLockStatement.targets`, **When** inspected, **Then** each target is an `MLockTarget` dataclass rather than an untyped dict.
4. **Given** `MXecuteStatement`, **When** inspected, **Then** it has only `arguments`, not a legacy `code_expressions` field.
5. **Given** the analysis of `ZWITHDRAW A`, **When** inspected, **Then** `_analyze_ZWithdrawCommand` delegates to `_analyze_ZKillCommand`.
6. **Given** all consumers of the changed ASG fields, **When** transpilation runs, **Then** all consumers correctly use the updated field names and types.

---

### Edge Cases

- What happens when a subscript list is empty (no subscripts)? The shared `gen_subscripts_tuple()` must handle this correctly (return `()` or omit entirely depending on caller needs).
- What happens when indirection resolves to an expression with further indirection (multi-level)? The shared template must handle arbitrary nesting.
- What happens when ZWRITE range bounds are non-numeric strings? MUMPS collation ordering (empty string < numeric < string) must be respected. YDB-confirmed: `A("A":"B")` includes "AA"; `A(2:)` includes all numerics >=2 plus all strings; `A(:2)` includes only numerics <=2.
- What happens when a by-ref parameter is passed to a routine that never modifies it? The MArray aliasing approach must not introduce overhead or change behavior for unmodified parameters.
- What happens when the same variable appears in both a scope→state sync and a state→scope sync within the same block? The consolidated emitter must handle this correctly.
- What happens when `_emit_source_comment` is called for a line that has no comment? The ASG `comment` field must be `None` and codegen must skip comment emission.
- What happens when an `MIfStatement` has multiple conditions (MUMPS `IF cond1,cond2`)? The cleaned ASG must represent multi-condition IF correctly using only the `conditions` list.

## Requirements *(mandatory)*

### Functional Requirements

#### Test Suite Integrity

- **FR-001**: 100% of existing tests (5,883+ as of baseline) MUST continue to pass after every individual refactoring item. No test may be marked `xfail`, `skip`, `expectedFailure`, or otherwise disabled as a consequence of the refactoring.
- **FR-002**: Each refactoring item MUST include new unit tests covering the extracted helper function or new module in isolation, verifying its behavior for representative inputs.
- **FR-003**: Each refactoring item that touches codegen output MUST include integration tests that transpile representative MUMPS routines and compare generated Python output to pre-refactoring baselines.
- **FR-004**: The ZWRITE range correctness fix (C-09) and by-reference call unification (C-07) MUST each include dedicated regression tests exercising the specific bug scenarios they fix.

#### Track A — `codegen/statements.py` Sequential Refactoring

- **FR-010**: A `gen_subscripts_tuple(subscripts, ctx)` function MUST be created that generates a Python tuple expression from a list of ASG subscript nodes. All ~99 inline occurrences of the subscript-tuple pattern across `codegen/statements.py`, `codegen/expressions.py`, and `codegen/indirection.py` MUST be replaced by calls to this function.
- **FR-011**: A `_build_lhs_getter_setter(target, ctx)` helper MUST be created that returns `(getter_expr, setter_expr)` for any variable type (local, global, naked global, indirected). `_generate_lhs_piece` and `_generate_lhs_extract` MUST both delegate to this helper for variable-type dispatch, retaining only their position-argument logic and runtime function call (`m_set_piece` / `m_set_extract`).
- **FR-012**: `emit_state_to_scope_sync(ctx)` and `emit_scope_to_state_sync(ctx)` helper functions MUST be created. All 22 inline scope↔state synchronization blocks (16 in `statements.py`, 6 in `routine.py`) MUST be replaced by calls to these helpers.
- **FR-013**: An `_emit_goto_external_handler(ctx)` function MUST be created. All 6 inline `except GotoExternal` handler blocks (4 in `statements.py`, 2 in `routine.py`) MUST be replaced by calls to this function.
- **FR-014**: ZWRITE subscript range handling MUST be corrected so that `MZWriteSubscriptRange` nodes filter output to only matching subscripts instead of treating the range as a wildcard. The fix MUST apply to both global and local variable ZWRITE paths (eliminating their code duplication simultaneously). Range comparison MUST use `m_sorts_after` / `_mumps_collation_key` from `runtime/helpers.py` (MUMPS collation ordering), NOT simple Python comparison operators. The runtime `zwrite_local()` and `zwrite_global()` functions MUST be extended to accept optional range bounds and filter child subscripts using collation-order comparison. YDB-verified edge cases that MUST be handled: (1) numeric ranges like `A(1:10)` include intervening values like 1.5 and 2; (2) string ranges like `A("A":"B")` include intermediates like "AA"; (3) open-end ranges like `A(2:)` include all subsequent numerics AND all strings (strings sort after all numerics); (4) open-start ranges like `A(:2)` include all values up to the bound but NOT strings.
- **FR-015**: A new `codegen/var_access.py` module MUST be created containing `var_read_expr()`, `var_write_stmt()`, and `var_base_expr()` functions that encapsulate the 3-way strategy dispatch for variable access. All ~69 inline occurrences across `codegen/statements.py`, `codegen/expressions.py`, and `codegen/indirection.py` MUST be replaced by calls to these helpers.
- **FR-016**: A `compile_mumps_line(code_str, context)` function MUST be created in `parser/compiler.py` that runs the full parse→analyze→structure pipeline for a MUMPS code string. The XECUTE handler in `codegen/statements.py` MUST use this function instead of directly importing and calling parser internals.
- **FR-017**: An `Optional[str]` `comment` field MUST be added to the `MStatement` ASG node. The parser MUST populate this field during parsing. `_emit_source_comment` in `codegen/statements.py` MUST read from this ASG field instead of re-scanning source lines.
- **FR-018**: By-reference call handling MUST be unified across SIMPLE_FUNCTIONS and TRAMPOLINE strategies to use MArray aliasing (DATA-CELL pointer aliasing per MUMPS standard section 8.1.7). The TRAMPOLINE strategy MUST NOT use value-result semantics for by-reference parameters. The semantic analyzer MUST force `uses_dynamic_locals=True` for any routine that declares by-reference formal parameters, ensuring dict-based access that naturally supports MArray aliasing. Callee mutations — including SET/KILL of descendants — MUST be visible to the caller, matching YDB behavior. `$DATA` on the caller's variable MUST reflect the callee's modifications to the variable tree.

#### Track B — `codegen/indirection.py` Template Extraction

- **FR-020**: A shared `_build_indirection_call(ind, ctx, runtime_method, **kwargs)` template function MUST be created in `codegen/indirection.py`. All 14 templatizable indirection generation functions (out of 16 total) MUST be refactored to thin wrappers (3–5 lines each) that call this shared template, passing only the runtime method name and any function-specific parameters. The 2 complex functions (`generate_indirect_do`, `generate_indirect_goto`) MUST be simplified but MAY retain their own implementations.
- **FR-021**: The refactored indirection functions MUST produce byte-identical generated code for all supported indirection types (SET, WRITE, KILL, IF, MERGE, $ORDER, $DATA, $GET, $QUERY, $INCREMENT, $PIECE indirection).

#### Track C — Runtime and ASG Cleanup

- **FR-030**: The two `offset_wrapper` closures in `runtime/__init__.py` (at approximately L1113–1224 and L1470–1556) MUST be consolidated into a single `_create_offset_entry_wrapper()` factory function. The factory MUST parameterize the differences in error handling and state sync mechanism.
- **FR-031**: The `condition` field MUST be removed from `MIfStatement`, leaving only the `conditions: list` field. All consumers MUST be updated.
- **FR-032**: The `duration` field MUST be removed from `MHangStatement`, leaving only the `durations: list` field. All consumers MUST be updated.
- **FR-033**: An `MLockTarget` dataclass MUST be created to replace the `List[Any]` typing on `MLockStatement.targets`. All consumers MUST be updated to use the typed dataclass.
- **FR-034**: The `code_expressions` field MUST be removed from `MXecuteStatement`, leaving only the `arguments` field. All consumers MUST be updated.
- **FR-035**: `_analyze_ZWithdrawCommand` in the semantic analyzer MUST delegate to `_analyze_ZKillCommand` instead of reimplementing the same logic.

#### Ordering and Dependencies

- **FR-040**: Track A items MUST be implemented in the following sequential order: S-02 → S-05 → S-04 → S-14 → C-09 → S-01 → S-13 → S-19 → C-07. Each item MUST leave the test suite fully passing before the next item begins.
- **FR-041**: Track B (S-03) and Track C (S-12, S-16) MAY be implemented in parallel with Track A, as they touch different files.
- **FR-042**: All Phase 1 deliverables (specifically `core/values.py`, `core/parsing.py`, `core/tokenizer.py`, and `asg/traversal.py`) MUST be available before Phase 2 work begins. FR-015 (var_access) and FR-010 (subscript tuple) may reference utilities from Phase 1 modules.

#### Code Quality

- **FR-050**: No new backward imports (lower layer importing from higher layer) MUST be introduced. Specifically: `runtime/` MUST NOT import from `codegen/`, `core/` MUST NOT import from `codegen/` or `runtime/`, `asg/` MUST NOT import from `codegen/` or `runtime/`.
- **FR-051**: Each new helper function or module MUST include a docstring describing its purpose, parameters, return type, and any important behavioral notes.
- **FR-052**: Dead code resulting from refactoring (unreachable functions, unused imports) MUST be removed rather than left commented out.
- **FR-053**: The total line count of `codegen/statements.py` MUST decrease by at least 15% from the pre-refactoring baseline (~6,775 lines).
- **FR-054**: The total line count of `codegen/indirection.py` MUST decrease by at least 40% from the pre-refactoring baseline (~2,092 lines).

### Key Entities

- **`gen_subscripts_tuple()`**: Shared function converting ASG subscript node lists into Python tuple-expression strings. Used by statements, expressions, and indirection codegen.
- **`_build_lhs_getter_setter()`**: Shared function returning `(getter, setter)` expression strings for a variable target across all variable types. Used by `$PIECE` and `$EXTRACT` LHS codegen.
- **`emit_state_to_scope_sync()` / `emit_scope_to_state_sync()`**: Paired helper functions emitting the state↔scope synchronization code blocks used by the TRAMPOLINE strategy.
- **`_emit_goto_external_handler()`**: Shared function emitting the `except GotoExternal` catch block with scope sync.
- **`codegen/var_access.py`**: New module encapsulating the 3-way strategy dispatch for all variable read, write, and base-expression operations.
- **`compile_mumps_line()`**: Top-level function running the full parse→analyze→structure pipeline for a MUMPS code string. Used by regular parsing and XECUTE.
- **`_build_indirection_call()`**: Shared template function for 14 templatizable indirection code-generation functions (out of 16 total).
- **`_create_offset_entry_wrapper()`**: Factory function replacing two ~100-line offset_wrapper closures in runtime.
- **`MLockTarget`**: New ASG dataclass replacing untyped dicts in `MLockStatement.targets`.
- **`MStatement.comment`**: New optional field on the ASG statement base class, populated by the parser with inline MUMPS comments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing tests (5,883+) pass after every individual refactoring item, with zero new xfails, skips, or expected failures.
- **SC-002**: The inline subscript-tuple pattern appears in zero locations outside the shared helper function (down from ~99).
- **SC-003**: The inline 3-way variable-access dispatch pattern appears in zero locations outside `codegen/var_access.py` (down from ~69).
- **SC-004**: Inline scope↔state sync blocks appear in zero locations outside the shared helpers (down from 22).
- **SC-005**: `codegen/indirection.py` line count decreases by at least 40% (from ~2,092 to ≤1,255 lines).
- **SC-006**: `codegen/statements.py` line count decreases by at least 15% (from ~6,775 to ≤5,759 lines).
- **SC-007**: ZWRITE with subscript ranges produces correct filtered output matching YottaDB behavior.
- **SC-008**: By-reference parameter mutations are visible to callers under both SIMPLE_FUNCTIONS and TRAMPOLINE strategies, including error scenarios.
- **SC-009**: Every new helper function and module has at least one dedicated unit test.
- **SC-010**: No inline `except GotoExternal` blocks remain outside the shared handler (down from 6).
- **SC-011**: The LHS `$PIECE` / `$EXTRACT` MIndirection handling block exists in exactly one location (down from 2).
- **SC-012**: The XECUTE handler in `codegen/statements.py` contains zero direct imports from `parser/`.
- **SC-013**: The `offset_wrapper` closure logic exists in exactly one factory function (down from 2 closures).
- **SC-014**: All deprecated/redundant ASG fields (`condition`, `duration`, `code_expressions`) are removed with zero consumer breakage.

## Clarifications

### Session 2026-02-10

- Q: Where should `compile_mumps_line()` be placed — `parser/`, `core/compile.py`, or `codegen/`? → A: `parser/` (keeps it alongside the existing pipeline it wraps, avoids layering violations in `core/`).
- Q: Should by-ref call unification (C-07) apply to all TRAMPOLINE routines (full) or only `uses_dynamic_locals=True` (partial)? → A: Full unification (Option A). MUMPS standard 8.1.7 requires DATA-CELL pointer aliasing — value-result is a spec violation. Mechanism: force `uses_dynamic_locals=True` when by-ref formals are present.
- Q: Should ZWRITE range filtering use existing `m_sorts_after`/`_mumps_collation_key` (MUMPS collation) or simple Python comparison? → A: Must use `m_sorts_after`/`_mumps_collation_key`. YDB testing confirmed that ranges follow MUMPS collation (numeric before string, canonical ordering) — simple Python comparison produces wrong results for mixed-type subscripts.

## Assumptions

- **Spec correctness is the primary decision factor.** When a design choice exists between implementation convenience and MUMPS standard compliance (or YDB behavioral fidelity), the spec-correct option MUST be chosen. This principle applies to all ambiguity resolution throughout this specification.
- Phase 1 deliverables (`core/values.py`, `core/parsing.py`, `core/tokenizer.py`, `asg/traversal.py`, and all Track A/B/C/D items from Phase 1) are complete and merged before Phase 2 begins. Phase 2 may reference and use functions from these modules.
- The existing test suite (5,883+ tests) is comprehensive enough to detect behavioral regressions. If any item changes codegen output, the tests will catch it.
- "Byte-identical output" refers to the generated Python source code producing the same runtime results. Minor whitespace or formatting changes in generated code are acceptable as long as runtime behavior is unchanged.
- ZWRITE range filtering follows MUMPS canonical collation: empty string sorts first, then numeric values in numeric order, then string values in ASCII order. The existing `m_sorts_after` / `_mumps_collation_key` functions in `runtime/helpers.py` provide this ordering and MUST be used for range bound comparisons.
- The by-reference unification (C-07) will change TRAMPOLINE behavior: the semantic analyzer will force `uses_dynamic_locals=True` for routines with by-ref formals, which changes state access from named dataclass fields to dict-based `state._locals`. This changes generated code structure but fixes a MUMPS spec violation (value-result instead of true reference aliasing). The resulting behavior will match YDB: callee SET/KILL of descendants visible to caller, `$DATA` reflects full variable tree.
- Line count reduction targets (15% for statements.py, 40% for indirection.py) are estimates based on the duplication analysis. Actual reduction may vary depending on extracted helper sizes but the direction must be a significant reduction.
- The `MLockTarget` dataclass design will be determined during implementation, informed by the actual structure of lock target dicts currently in use.
