# Implementation Plan: Spec 014 xfail Elimination

**Branch**: `014-xfail-elimination` | **Date**: 2025-01-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/014-xfail-elimination/spec.md`

## Summary

Eliminate 163 xfail tests by implementing missing features (64 tests) or adding explicit
`NotImplementedError` for documented limitations (99 tests). All prerequisite specs
(001-013) are complete - nothing is blocked.

**Approach**: Start with error handling (99 tests, lowest complexity) then proceed to
feature implementations ordered by priority and independence.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX (parser), pytest (testing)
**Storage**: N/A (codegen focus)
**Testing**: pytest with YDB validation (`uv run pytest`)
**Target Platform**: Linux/macOS
**Project Type**: Single project (transpiler)
**Performance Goals**: N/A (correctness focus)
**Constraints**: Must not break existing 4829 passing tests
**Scale/Scope**: 163 xfail tests → 0 xfail (all implementable)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ Pass | Error messages make behavior explicit |
| II. YDB as Reference | ✅ Pass | Tests validated against YDB |
| III. Strict Layer Separation | ✅ Pass | Changes only in codegen layer |
| IV. Explicit Over Implicit | ✅ Pass | Converting silent failures to explicit errors |
| V. Foundational Correctness | ✅ Pass | Error handling is foundation for future work |
| VI. Cross-Cutting Semantics | ✅ Pass | No value model changes |
| VII. Minimize Runtime Surface | ✅ Pass | Errors at codegen time, not runtime |
| VIII. Research Before Implementation | ✅ Pass | Research phase completed |

**Gate Result**: PASS - No violations

## Project Structure

### Documentation (this feature)

```text
specs/014-xfail-elimination/
├── plan.md              # This file
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (completed)
├── contracts/           # Phase 1 output (completed)
│   ├── error-handling.md
│   └── test-conversion.md
├── spec.md              # Feature specification
├── tasks.md             # Phase 2 output (/speckit.tasks)
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code Changes

```text
src/m2py/codegen/
├── expressions.py       # SSVN errors (LIM-003, LIM-011), Library errors (LIM-014)
└── statements.py        # Z-command errors (LIM-015), TROLLBACK:n (LIM-016)

tests/unit/codegen/
├── extensions/ydb/      # Z-command test conversions (15 tests)
├── legacy/              # $NEXT, pre-1995 test conversions (5 tests)
├── s6_routine/          # Routine structure tests (6 tests)
├── s7_expressions/      # Library function tests (70+ tests)
└── s8_commands/         # Command tests
```

**Structure Decision**: Single project transpiler. All changes in `src/m2py/codegen/`
and `tests/unit/codegen/` directories.

---

## Implementation Phases

### Phase A: Error Handling (99 tests) - FIRST PRIORITY

**Rationale**: Quickest path to test reduction. No dependencies. Low complexity.

#### A1: SSVN Error Handling (4 tests)
**File**: `src/m2py/codegen/expressions.py`
**Function**: `_generate_ssvn()`

| SSVN | Limitation | Current | Required |
|------|------------|---------|----------|
| ^$EVENT | LIM-003 | `return "''"` | `raise NotImplementedError("LIM-003: ...")` |
| ^$WINDOW | LIM-003 | `return "''"` | `raise NotImplementedError("LIM-003: ...")` |
| ^$DISPLAY | LIM-003 | `return "''"` | `raise NotImplementedError("LIM-003: ...")` |
| ^$LIBRARY | LIM-011 | `return "''"` | `raise NotImplementedError("LIM-011: ...")` |

**Tests to convert**: `test_s7_1_3_ssvns.py::TestMwapiSsvnsCodegen` (3), `TestLibrarySsvnCodegen` (1)

#### A2: ANSI Library Function Errors (68 tests)
**File**: `src/m2py/codegen/expressions.py`
**Function**: `_generate_extrinsic()`

```python
# Add detection for ANSI library routines
ANSI_LIBRARY_ROUTINES = {"MATH", "STRING", "CHARACTER"}
if routine_name in ANSI_LIBRARY_ROUTINES:
    raise NotImplementedError(
        f"LIM-014: ANSI library function $$%{label_name}^{routine_name} not implemented"
    )
```

**Tests to convert**:
- `test_s7_1_6_5_library_functions_math.py` (57 tests)
- `test_s7_1_6_5_library_functions_string.py` (6 tests)
- `test_s7_1_6_5_library_functions_character.py` (5 tests)

#### A3: Z-Command Errors (15 tests)
**File**: `src/m2py/codegen/statements.py`
**Function**: `generate_statement()`

```python
Z_COMMANDS = {
    "ZALLOCATE", "ZDEALLOCATE", "ZBREAK", "ZCOMPILE", "ZCONTINUE",
    "ZEDIT", "ZHELP", "ZMESSAGE", "ZPRINT", "ZSTEP", "ZSYSTEM", "ZTRIGGER"
}
if command_name.upper() in Z_COMMANDS:
    raise NotImplementedError(f"LIM-015: {command_name} command not implemented")
```

**Tests to convert**: `extensions/ydb/test_z*.py` (15 tests)

#### A4: Zero-VistA Feature Errors (12 tests)
**File**: `src/m2py/codegen/statements.py`

| Feature | Limitation | Tests |
|---------|------------|-------|
| TROLLBACK:n | LIM-016 | 1 |
| $TRESTART | LIM-016 | 1 (already working) |
| $NEXT function | LIM-016 or implement | 3 |
| Legacy behaviors | LIM-016 | 2 |
| Z-functions | LIM-015 | 3 |
| Device params | LIM-016 | 2 |

---

### Phase B: Core Language Semantics (12 tests) - HIGH PRIORITY

**Rationale**: VistA-critical features with high usage counts.

#### B1: Special Variables (4 tests)
- `$TLEVEL` - Add to `_generate_special_variable()` → `_rt.tlevel`
- `$QUIT` - Context-aware: 1 in extrinsic, 0 in DO
- `$TEXT` external - Requires routine lookup

#### B2: Indirection (3 tests)
- Subscript indirection: `@var(sub)` → `_rt.indirect_subscript(var, sub)`
- Argument indirection: `@var` → `_rt.indirect_argument(var)`
- Runtime resolution: Verify dynamic evaluation

#### B3: Transaction Commands (4 tests)
- TSTART/TCOMMIT: Basic transaction markers
- TROLLBACK basic: Without level argument
- TRESTART: Restart tracking

#### B4: Error Processing (1 test)
- Error propagation across label calls

---

### Phase C: Data Operations (8 tests) - MEDIUM PRIORITY

**Rationale**: Global operations with existing infrastructure.

#### C1: MERGE Globals (2 tests)
- Local to global: `M ^GLO=LOCAL`
- Global to global: `M ^GLO1=^GLO2`

#### C2: Naked References (5 tests)
- Error without prior global
- $DATA/$ORDER with naked
- MERGE/LOCK with naked

#### C3: KILL Global (1 test)
- `K ^GLO` → `_rt.globals.kill("GLO")`

---

### Phase D: Routine Structure (6 tests) - LOW PRIORITY

**Rationale**: Cosmetic improvements, low VistA impact.

#### D1: Routine Metadata (3 tests)
- Docstring from MUMPS header
- Empty label translation
- Comment preservation

#### D2: Extrinsic Advanced (3 tests)
- Module caching for imports
- Cross-routine variable passing
- Routine name translation

---

### Phase E: Advanced Features (14 tests) - LOW PRIORITY

**Rationale**: Complex features with lower VistA frequency.

#### E1: Language Semantics (5 tests)
- $TEST stacking rules for various contexts
- Execution level tracking
- Extrinsic return semantics

#### E2: Postconditions (3 tests)
- Independent argument postconditions
- Evaluation order
- Side effect handling

#### E3: XECUTE Runtime (3 tests)
- Global access in XECUTE
- ZOSF optimization
- ZOSF fallback

#### E4: Character Set (3 tests)
- M character encoding
- Graphic/control characters

---

### Phase F: Control Flow Advanced (17 tests) - MEDIUM PRIORITY

**Status**: Prerequisites complete (Specs 006/007/008 ✅ COMPLETE)

**Rationale**: These features depend on cross-label infrastructure which is now fully implemented.

#### F1: DO External (6 tests) - Spec 008 infrastructure ready
- DO external routine (D LABEL^ROUTINE)
- Scope strategy codegen (PURE_FUNCTION, SUBROUTINE, etc.)
- Partial indirection (D @var^ROUTINE)

#### F2: GOTO Advanced (5 tests) - Spec 006 infrastructure ready
- Computed GOTO (G LABEL+offset)
- State machine fallback
- State machine variable scope
- Same-level enforcement
- Partial indirection (G @var)

#### F3: Computed Offsets (6 tests) - Spec 007 infrastructure ready
- DO/GOTO with literal offset
- Offset with variable/global/function
- Offset arithmetic

**Action**: Implement using existing cross-label infrastructure.

---

## Test Count Tracking

| Phase | Start xfail | End xfail | Reduction |
|-------|-------------|-----------|-----------|
| Baseline | 163 | 163 | 0 |
| Phase A | 163 | 64 | -99 |
| Phase B | 64 | 52 | -12 |
| Phase C | 52 | 44 | -8 |
| Phase D | 44 | 38 | -6 |
| Phase E | 38 | 24 | -14 |
| Phase F | 24 | 7 | -17 |
| Misc | 7 | 0 | -7 |
| **Final** | — | **0** | **-163** |

**Note**: All specs 001-013 are complete. Target is ZERO xfail tests.

---

## Validation Strategy

### After Each Phase
```bash
# Count remaining xfails
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1

# Run full test suite (no regressions)
uv run pytest

# Check for xpass (unexpected passes)
uv run pytest 2>&1 | grep -i xpass
```

### Phase A Specific
```bash
# SSVN tests
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py -v

# Library tests
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_*.py -v

# Z-command tests
uv run pytest tests/unit/codegen/extensions/ydb/ -v
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full suite after each change |
| Missing edge cases | Error messages include context |
| Blocked dependencies | Document clearly, defer to future spec |
| Test count discrepancy | Use actual count (163), not spec count (156) |

---

## Success Criteria

1. ✅ `uv run pytest --collect-only -m xfail -q` returns 0 (zero xfail)
2. ✅ `uv run pytest` passes with 0 failures
3. ✅ All PARSES_OK limitations raise `NotImplementedError("LIM-XXX: ...")`
4. ✅ No test duplicates created
5. ✅ No tests removed without implementation verification

---

## Complexity Tracking

> **No constitution violations to justify**

This plan follows all constitution principles:
- Explicit errors over silent failures (Principle IV)
- Codegen-only changes (Principle III layer separation)
- Error at codegen time, not runtime (Principle VII)
- Research completed before implementation (Principle VIII)

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
