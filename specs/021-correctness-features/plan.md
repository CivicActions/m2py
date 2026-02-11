# Implementation Plan: Phase 3 — Correctness Fixes & New Features

**Branch**: `021-correctness-features` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-correctness-features/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Phase 3 implements new MUMPS/YDB features and correctness fixes on top of Phase 1 (foundation) and Phase 2 (codegen refactoring). Unlike the prior refactoring phases, Phase 3 is primarily **new functionality**: error handling (`$ETRAP`/`$ECODE` stack unwinding, `$ZTRAP`/`$ZSTATUS`/`$ZPOSITION`), `$STACK` introspection, LOCK indirection (C-05), TSTART restart variables (F-05), READ `#maxlen` with `$KEY`, `$ZDATE`, ZSYSTEM, unconditional LVUNDEF (M6), SSVNs, YDB SVNs, and extended global references. The work spans 5 independent tracks touching distinct subsystems, enabling high parallelism.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX ≥ 4.0 (parser), `copy` (stdlib, deepcopy for transactions), `subprocess` (stdlib, ZSYSTEM), `glob`/`pathlib` (stdlib, $ZSEARCH), `importlib` (stdlib, ZLINK — already used), `datetime` (stdlib, $ZDATE)
**Storage**: N/A (in-memory global storage, no persistence changes)
**Testing**: pytest with `uv run pytest` (6,023 tests, 0 xfails, 0 skips at baseline)
**Target Platform**: Linux (dev container, Ubuntu 24.04), any Python 3.10+
**Project Type**: Single Python package (`src/m2py/`)
**Performance Goals**: No regression — transpiler throughput unchanged; all existing tests pass
**Constraints**: Zero test failures at every commit; no new xfail/skip markers; new unit + integration tests for every feature
**Scale/Scope**: 12 features (C-05, F-03, F-05, F-06, F-07, F-08, F-09, F-10, F-11, F-12 partial, F-13, F-14) across 5 tracks touching ~15 source files

### Key Files and Baseline Metrics

| File | Lines (est.) | Phase 3 Role |
|---|---|---|
| `runtime/__init__.py` | ~6,200 | All tracks: new ISV accessors, error handler expansion, lock indirection, TSTART vars, READ maxlen, $STACK frames, SSVNs, SVNs |
| `runtime/helpers.py` | ~1,900 | Track C: `$ZDATE` runtime function; Track E: `m_read_maxlen()` |
| `codegen/statements.py` | ~6,500 | Tracks A–E: error wrap patterns, LOCK indirection codegen, TSTART vars codegen, READ maxlen codegen, ZSYSTEM codegen |
| `codegen/expressions.py` | ~2,600 | Tracks A/C/D: $ZTRAP/$ZSTATUS/$ZPOSITION reads, $ZDATE function, $STACK(n,info) function, SSVNs, $ZSEARCH/$ZRO/$ZMESSAGE |
| `codegen/routine.py` | ~1,300 | Track A: enhanced try/except wrappers, $STACK frame push/pop |
| `codegen/indirection.py` | ~1,200 | Track B: `generate_lock_indirection()` |
| `asg/statements.py` | ~1,400 | Track B: MTStartStatement restart vars |
| `core/scope.py` | ~400 | Track C: remove `strict_mode` conditional, unconditional LVUNDEF |
| `core/exceptions.py` | ~35 | Track C: LVUNDEFError (already exists) |

### Phase 1 + Phase 2 Deliverables Available

| Module | Key Exports | Used By Phase 3 |
|---|---|---|
| `core/values.py` | `m_str`, `m_num`, `m_truth`, `m_compare` | $ZDATE value formatting |
| `core/parsing.py` | `parse_subscripted_name`, `canonicalize_subscript` | LOCK indirection resolution |
| `core/tokenizer.py` | `split_at_toplevel` | LOCK indirection argument parsing |
| `codegen/exceptions.py` | `CodegenError`, `UnsupportedFeatureError` | Error handling codegen |
| `codegen/var_access.py` | `var_read_expr`, `var_write_stmt`, `var_base_expr` | TSTART restart var snapshots |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All features implement MUMPS standard/YDB-verified behavior. LVUNDEF M6 matches ANSI §7.2. Error handling follows ANSI error processing (§106012). $ZDATE validated against YDB output. |
| II. YDB as Reference Implementation | ✅ PASS | Every feature verified against YDB: $ETRAP fires on M6, $ZTRAP GOTO works, $ZSTATUS contains error message, $ZPOSITION shows label+offset, $STACK(n,"PLACE") returns location, $ZDATE format codes match YDB. Tests will compare against YDB reference output. |
| III. Strict Layer Separation | ✅ PASS | New features follow established patterns: codegen emits `_rt.method()` calls, runtime implements MUMPS semantics. No backward imports. LOCK indirection follows existing indirection pattern. $ZDATE is a pure runtime function. LVUNDEF change is in `core/scope.py` (correct layer). |
| IV. Explicit Over Implicit | ⚠️ CHANGE | Constitution §IV says "Undefined variables return empty string (not exception)." This **must be updated** — MUMPS standard §7.2 mandates M6 error, YDB defaults to LVUNDEF, VistA expects it. The constitution entry contradicts the standard and will be corrected as part of FR-037. |
| V. Foundational Correctness | ✅ PASS | Error handling ($ETRAP/$ZTRAP) and LVUNDEF are foundational corrections. The error infrastructure enables correct VistA Kernel execution. |
| VI. Cross-Cutting Semantics | ✅ PASS | Error handling is cross-cutting — every generated function needs try/except. The existing infrastructure in `codegen/routine.py` already emits these wrappers; Phase 3 enhances them (not duplicates). LVUNDEF is cross-cutting via `core/scope.py`. |
| VII. Minimize Runtime Surface | ✅ PASS | New runtime methods are required because features are inherently dynamic: error trapping, lock resolution, ZSYSTEM shell execution, $ZSEARCH file iteration. No static-analysis alternative exists for these. |
| VIII. Research Before Implementation | ✅ PASS | Research phase completed — see [research.md](research.md). YDB semantics verified for all features. Existing infrastructure audited. |

**Constitution §IV update required**: FR-037 mandates changing "Undefined variables return empty string" to reflect M6 error behavior. This is a corrective change — the original entry contradicted MUMPS ANSI §7.2 and YDB default behavior. Justified by:
- MUMPS standard explicitly says "erroneous" with ecode=M6
- YDB raises LVUNDEF by default
- VistA (0 files use VIEW "NOUNDEF") expects M6 errors
- The constitution's own §I ("Semantic Correctness First") and §II ("YDB as Reference") take precedence

**Gate result: PASS** — No blocking violations. Constitution §IV update is a correction, not a violation.

## Project Structure

### Documentation (this feature)

```text
specs/021-correctness-features/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: New entities and ISV definitions
├── quickstart.md        # Phase 1: Development setup guide
├── contracts/
│   └── runtime-apis.md  # Phase 1: New runtime method contracts
├── checklists/
│   └── requirements.md  # Quality validation checklist (exists)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/m2py/
├── core/
│   ├── scope.py           # MODIFIED — remove strict_mode conditional, unconditional LVUNDEF
│   ├── exceptions.py      # EXISTING — LVUNDEFError (unchanged)
│   └── ...                # unchanged
├── asg/
│   └── statements.py      # MODIFIED — MTStartStatement gains restart_vars list handling
├── codegen/
│   ├── statements.py      # MODIFIED — Tracks A–E: error wrap, LOCK indir, TSTART vars, READ#, ZSYSTEM
│   ├── expressions.py     # MODIFIED — $ZTRAP/$ZSTATUS/$ZPOSITION reads, $ZDATE, $STACK(n), SSVNs, SVNs
│   ├── indirection.py     # MODIFIED — Track B: generate_lock_indirection()
│   ├── routine.py         # MODIFIED — Track A: enhanced try/except, $STACK frame push/pop
│   └── ...                # unchanged
├── runtime/
│   ├── __init__.py        # MODIFIED — All tracks: ISV storage, error handler, lock/tstart/read/stack/ssvn/svn
│   ├── helpers.py         # MODIFIED — $ZDATE function, m_read_maxlen()
│   └── ...                # unchanged
└── parser/
    └── ...                # unchanged (grammar already parses all needed constructs)

tests/
├── unit/
│   ├── runtime/
│   │   ├── test_etrap_ecode.py       # NEW: $ETRAP/$ECODE unit tests
│   │   ├── test_ztrap.py             # NEW: $ZTRAP/$ZSTATUS/$ZPOSITION unit tests
│   │   ├── test_stack_function.py    # NEW: $STACK(n,"info") unit tests
│   │   ├── test_zdate.py             # NEW: $ZDATE unit tests (format codes, edge cases)
│   │   ├── test_read_maxlen.py       # NEW: READ #maxlen unit tests
│   │   └── test_ssvn.py              # NEW/EXTEND: SSVN unit tests
│   ├── codegen/
│   │   ├── test_lock_indirection.py  # NEW: LOCK indirection codegen tests
│   │   ├── test_tstart_vars.py       # NEW: TSTART restart var codegen tests
│   │   ├── test_zsystem_codegen.py   # NEW: ZSYSTEM codegen tests
│   │   └── test_extended_globals.py  # NEW: Extended global ref codegen tests
│   └── core/
│       └── test_lvundef.py           # NEW: Unconditional LVUNDEF tests
├── integration/
│   ├── test_error_handling.py        # NEW: ETRAP/ZTRAP integration (transpile + run)
│   ├── test_tstart_restart.py        # NEW: TSTART restart var integration
│   └── test_extended_globals.py      # NEW: Extended global integration
└── functional/                       # EXISTING: 6,023 tests — all must pass
```

**Structure Decision**: Single project structure. No new top-level directories. New source modifications in existing files. New test files under existing test directories.

## Implementation Tracks

### Track A — Error Handling (F-03, F-09, F-08) — Critical Path

The most complex track. Implements full MUMPS/YDB error handling infrastructure.
F-03 and F-09 share the same try/except wrapper infrastructure in `codegen/routine.py`
and should be implemented together. F-08 builds on the call stack tracking needed by F-03.

| Step | Item | Files | Effort |
|------|------|-------|--------|
| A1 | $ECODE accumulation with `,Merr,` format | `runtime/__init__.py` | 0.5 day |
| A2 | $ETRAP stack unwinding (QUIT from trap unwinds to setter level) | `runtime/__init__.py`, `codegen/routine.py` | 2 days |
| A3 | NEW $ETRAP / NEW $ESTACK support | `codegen/statements.py`, `runtime/__init__.py` | 0.5 day |
| A4 | Nested error detection (error during error processing → TROLLBACK + QUIT) | `runtime/__init__.py` | 1 day |
| A5 | $ZTRAP ISV storage + SET/read codegen | `runtime/__init__.py`, `codegen/statements.py`, `codegen/expressions.py` | 0.5 day |
| A6 | $ZTRAP dispatch (XECUTE vs GOTO based on content) | `runtime/__init__.py` | 1 day |
| A7 | $ZSTATUS / $ZPOSITION population on error | `runtime/__init__.py`, `codegen/expressions.py` | 0.5 day |
| A8 | $ETRAP↔$ZTRAP mutual exclusion (SET one implicitly NEWs the other) | `runtime/__init__.py`, `codegen/statements.py` | 0.5 day |
| A9 | $STACK call stack tracking (push/pop frames with routine, label, offset, mcode) | `runtime/__init__.py`, `codegen/routine.py` | 1 day |
| A10 | $STACK(n), $STACK(n,"PLACE"/"MCODE"/"ECODE"), $STACK(-1) | `runtime/__init__.py`, `codegen/expressions.py` | 1 day |
| A11 | $STACK snapshot freeze on error, reset on SET $ECODE="" | `runtime/__init__.py` | 0.5 day |

**Total Track A**: ~9 days

**Key semantics verified via YDB**:
- `$ZTRAP` set to `"G ERR"` → GOTO ERR on error ✅
- `$ZSTATUS` contains `"150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: UNDEFINED"` ✅
- `$ZPOSITION` contains `"ERR+1^test"` (position after GOTO) ✅
- `$STACK(n)` returns `"DO"` for DO-frame, `$STACK(n,"PLACE")` returns `"SUB+2^test"` ✅
- `$ECODE` accumulates with commas: `,M6,Z150373850,` ✅

### Track B — LOCK Indirection + TSTART Restart Variables (C-05, F-05)

| Step | Item | Files | Effort |
|------|------|-------|--------|
| B1 | `generate_lock_indirection()` in codegen/indirection.py | `codegen/indirection.py` | 0.5 day |
| B2 | `lock_indirected()` runtime method | `runtime/__init__.py` | 0.5 day |
| B3 | Wire `_generate_lock_target()` to emit indirection call | `codegen/statements.py` | 0.5 day |
| B4 | LOCK indirection: multi-level, timeout+$TEST, +/- forms | `runtime/__init__.py`, tests | 0.5 day |
| B5 | TSTART (var1,var2,...) snapshot with deepcopy | `runtime/__init__.py` | 1 day |
| B6 | TSTART * — snapshot all locals | `runtime/__init__.py` | 0.5 day |
| B7 | TROLLBACK restore of snapshots | `runtime/__init__.py` | 0.5 day |
| B8 | Nested transaction snapshots | `runtime/__init__.py`, tests | 0.5 day |
| B9 | TSTART codegen: emit snapshot calls | `codegen/statements.py` | 0.5 day |

**Total Track B**: ~5 days

**Key semantics verified via YDB**:
- TSTART (X) + TROLLBACK does NOT restore X (restart vars are for TRESTART, not TROLLBACK for local vars in YDB) — but globals are rolled back ✅
- `$ZSTATUS` format confirmed for LVUNDEF ✅

### Track C — Standalone Functions + Compliance (F-10, F-11, F-14)

| Step | Item | Files | Effort |
|------|------|-------|--------|
| C1 | `$ZDATE` runtime function: parse $H, format codes (MM, DD, YY, YYYY, MON, DAY, 24:60:SS, AM, 12) | `runtime/helpers.py` | 1.5 days |
| C2 | `$ZDATE` codegen: wire intrinsic function call | `codegen/expressions.py` | 0.25 day |
| C3 | ZSYSTEM: `subprocess.run()` + `$ZSYSTEM` exit code ISV | `codegen/statements.py`, `runtime/__init__.py` | 0.5 day |
| C4 | Unconditional LVUNDEF: remove `strict_mode` conditional, always raise | `core/scope.py` | 0.5 day |
| C5 | Update constitution §IV | `.specify/memory/constitution.md` | 0.25 day |
| C6 | Fix existing tests broken by unconditional LVUNDEF | tests/ | 1 day |

**Total Track C**: ~4 days

**Key YDB reference data collected**:
- `$ZD(66337)` → `"08/16/22"` (default MM/DD/YY format) ✅
- `$ZD(66337,"YYYY-MM-DD")` → `"2022-08-16"` ✅
- `$ZD(66337,"DD MON YEAR")` → `"16 AUG 2022"` ✅

### Track D — SVNs, SSVNs, Extended Globals (F-07, F-12, F-13)

| Step | Item | Files | Effort |
|------|------|-------|--------|
| D1 | `^$JOB(pid)` — query process table | `runtime/__init__.py` or `runtime/globals.py` | 0.5 day |
| D2 | `^$ROUTINE(name)` — check routine existence | `runtime/__init__.py` or `runtime/globals.py` | 0.5 day |
| D3 | `^$SYSTEM` — meaningful values | `codegen/expressions.py`, `runtime/__init__.py` | 0.25 day |
| D4 | `$ZSEARCH(pattern)` — glob with iterator state | `runtime/__init__.py` | 0.5 day |
| D5 | `$ZRO` / `$ZROUTINES` — configurable path | `runtime/__init__.py`, `codegen/expressions.py` | 0.25 day |
| D6 | `$ZMESSAGE(code)` — error code lookup | `runtime/helpers.py`, `codegen/expressions.py` | 0.5 day |
| D7 | Extended global: pipe form `^|"env"|NAME` codegen + runtime | `codegen/expressions.py`, `codegen/statements.py`, `runtime/__init__.py` | 1 day |
| D8 | Extended global: bracket form `^[UCI,VOL]NAME` codegen + runtime | `codegen/statements.py`, `runtime/__init__.py` | 0.5 day |
| D9 | Extended global: all operations ($DATA, $ORDER, $GET, $QUERY, KILL, SET, MERGE) | `codegen/statements.py`, `runtime/__init__.py` | 1 day |

**Total Track D**: ~5 days

### Track E — READ with #maxlen (F-06)

| Step | Item | Files | Effort |
|------|------|-------|--------|
| E1 | `m_read_maxlen(maxlen)` runtime function (piped input) | `runtime/helpers.py` | 0.5 day |
| E2 | `m_read_maxlen_timeout(maxlen, timeout)` combined | `runtime/helpers.py` | 0.5 day |
| E3 | `$KEY` population on READ (terminator or empty on maxlen reached) | `runtime/__init__.py`, `runtime/helpers.py` | 0.5 day |
| E4 | `_generate_read_target()` codegen: handle `target.fixed_length` | `codegen/statements.py` | 0.5 day |
| E5 | READ #0 edge case (immediate empty string) | `runtime/helpers.py`, tests | 0.25 day |

**Total Track E**: ~2.25 days

## Parallelism

```
Track A ─── (runtime/__init__.py, codegen/routine.py, codegen/expressions.py)
Track B ─── (codegen/indirection.py, codegen/statements.py, runtime/__init__.py)
Track C ─── (runtime/helpers.py, core/scope.py, codegen/expressions.py, constitution)
Track D ─── (runtime/globals.py, codegen/expressions.py, codegen/statements.py)
Track E ─── (runtime/helpers.py, codegen/statements.py)
```

**Conflict zones**:
- `runtime/__init__.py`: Touched by ALL tracks. Serialize within: A first (error infra), then B (lock/tstart), then D (SVNs), then E (READ $KEY).
- `codegen/statements.py`: Tracks A, B, D, E all touch different handlers within this file. Low merge risk but serialize if on same worker.
- `codegen/expressions.py`: Tracks A, C, D add new ISV/function dispatch. Each adds to different `elif` branches — low conflict.
- `runtime/helpers.py`: Tracks C ($ZDATE) and E (READ maxlen) add independent functions — can parallelize.

**With 2 workers**: Worker 1 takes A+C (~13 days). Worker 2 takes B+D+E (~12 days).
**Solo**: ~25 days sequential, ~18 days with interleaving.

## Post-Design Constitution Re-Check

*Re-evaluation after Phase 1 design (data-model.md, contracts/, quickstart.md) is complete.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Semantic Correctness First | ✅ PASS | All contracts specify MUMPS-standard signatures. YDB was used to verify 6 distinct semantic areas. TSTART research corrected a spec assumption (restart vars are for TRESTART, not TROLLBACK). |
| II. YDB as Reference Implementation | ✅ PASS | YDB reference data collected and embedded in plan for all 5 tracks. Quickstart includes `validate.py` commands for every feature. |
| III. Strict Layer Separation | ✅ PASS | Data model places new entities in correct layers: StackFrame in runtime, scope changes in core, codegen changes in codegen. No layer violations in contracts. |
| IV. Explicit Over Implicit | ⚠️ CORRECTIVE UPDATE | FR-037 explicitly plans the constitution update. Data model removes `strict_mode` from `CurrentScope`. No design element relies on "default empty" behavior. |
| V. Foundational Correctness | ✅ PASS | Error handling infrastructure (Track A) is correctly sequenced first. Other tracks depend on it. |
| VI. Cross-Cutting Semantics | ✅ PASS | Error handling and LVUNDEF are correctly identified as cross-cutting. Contracts show they integrate with existing shared infrastructure. |
| VII. Minimize Runtime Surface | ✅ PASS | Every new runtime method in contracts is justified (dynamic dispatch, process state, I/O, file system). No static-analyzable patterns routed through runtime. |
| VIII. Research Before Implementation | ✅ PASS | Phase 0 research completed with 2 subagent tasks, 6 YDB verifications, full codebase audit. All unknowns resolved in research.md. |

**Post-design gate: PASS** — no new violations introduced during design phase.

## Complexity Tracking

> **Constitution §IV violation**: Justified above. The existing entry "Undefined variables return empty string" contradicts MUMPS ANSI §7.2 and YDB default behavior. Correction required by §I (Semantic Correctness First) and §II (YDB as Reference), which take constitutional precedence.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Update §IV "empty string" → M6 error | MUMPS standard §7.2 mandates M6, YDB defaults to LVUNDEF, VistA expects it (0 files suppress) | Keeping empty string contradicts the standard, YDB, and VistA — all three sources of truth |
