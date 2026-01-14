# Feature Specification: External Calls & Cross-Routine Infrastructure

**Feature Branch**: `008-external-calls`  
**Created**: 2026-01-12  
**Completed**: 2026-01-13  
**Status**: Complete  
**Input**: Spec 008 from codegen-plan.md - External Calls & Cross-Routine Infrastructure

## Overview

This specification implements **cross-routine coordination and module loading** — architecturally significant infrastructure for translating MUMPS systems like VistA that heavily use external routine calls.

External routine calls (`D ^ROUTINE`, `D LABEL^ROUTINE`, `G LABEL^ROUTINE`, `$$FUNC^ROUTINE`) require:

1. **Module loading** - Translating and importing other `.m` files as Python modules
2. **Shared variable scope** - MUMPS variables are visible across routine boundaries by default
3. **Control transfer** - DO returns after QUIT; GOTO transfers permanently
4. **$TEXT function** - Returns source code lines, supporting external routine references

**Implementation status**: All external routine patterns are supported. Codegen generates standard Python `import` statements and function calls.

**Parser status**: The parser captures external references via `MCall.routine` field and `CallType.ROUTINE_CALL`. Codegen and runtime handle all call patterns.

## Pre-requisites from Spec 007

The following infrastructure is available:

- Line-to-entry mapping (`_line_map`) for line-based dispatch
- Statement line numbers populated by parser
- `MRoutine.source_lines` for $TEXT support
- Trampoline pattern for cross-label control flow

### Infrastructure Verified as Existing

| Component | Status | Details |
|-----------|--------|---------|
| `MCall.routine` | ✅ Parsed | Routine name for `^ROUTINE` references |
| `CallType.ROUTINE_CALL` | ✅ Set | Distinguishes external from internal calls |
| `MExtrinsicFunction.target.routine` | ✅ Parsed | For `$$FUNC^ROUTINE` |
| `MRoutine.source_lines` | ✅ Stored | List of original source lines |
| Line dispatch (`_line_map`) | ✅ Spec 007 | For $TEXT with offsets |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - External DO Routine Call (Priority: P1)

As a developer, when I generate Python from MUMPS code with `D ^ROUTINE` (call entry label of external routine), the code generator produces working Python that loads the external routine's translated module and calls its first label, returning after QUIT.

**Why this priority**: This is the most common external call pattern. VistA routines frequently call utility routines at their entry point. Without this, no multi-routine MUMPS programs can be transpiled.

**Independent Test**: Can be tested with two simple routines where one calls the other.

**YottaDB Verified Behavior**:
```
D ^ext2 → Calls entry label of ext2, returns after QUIT
Output: "In ext2\nBack in EXT1"
```

**Acceptance Scenarios**:

1. **Given** `EXT1 D ^exttest2 W "Back",! Q` and `exttest2 W "In ext2",! Q`, **When** generated and EXT1 executed, **Then** output is "In ext2\nBack\n"
2. **Given** `EXT1 D ^exttest2 D ^exttest2 W "Done",! Q` and `exttest2 W "X",! Q`, **When** generated and EXT1 executed, **Then** output is "X\nX\nDone\n" (multiple calls work)
3. **Given** `EXT1 D ^missing Q`, **When** executed, **Then** raises error with routine name indicating routine not found

---

### User Story 2 - External DO Label Call (Priority: P1)

As a developer, when I generate Python from MUMPS code with `D LABEL^ROUTINE` (call specific label in external routine), the code generator produces working Python that loads the module and calls the specified label function.

**Why this priority**: This pattern is equally common as Story 1 - many VistA calls target specific entry points like `D HELPER^UTILITY`.

**Independent Test**: Can be tested with a routine calling a non-entry label in another routine.

**YottaDB Verified Behavior**:
```
D HELPER^exttest2 → Calls HELPER label in exttest2
Output: "In HELPER\nBack in EXT1"
```

**Acceptance Scenarios**:

1. **Given** `EXT1 D HELPER^ext2 W "Back",! Q` and `ext2 Q` / `HELPER W "Hi",! Q`, **When** generated and EXT1 executed, **Then** output is "Hi\nBack\n"
2. **Given** `EXT1 D A^ext2 D B^ext2 Q` and `ext2 Q` / `A W "A",! Q` / `B W "B",! Q`, **When** executed, **Then** output is "A\nB\n"
3. **Given** `EXT1 D MISSING^ext2 Q` and `ext2 W "X",! Q`, **When** executed, **Then** raises LabelNotFoundError indicating label not found in routine
4. **Given** `EXT1 D A+1^ext2 Q` and `ext2 Q` / `A W "Line1",!` / ` W "Line2",! Q`, **When** executed, **Then** output is "Line2\n" (offset skips to line after label)
5. **Given** `EXT1 D +2^ext2 Q` and `ext2 W "L1",!` / ` W "L2",! Q`, **When** executed, **Then** output is "L2\n" (absolute line offset)

---

### User Story 3 - External GOTO (Priority: P2)

As a developer, when I generate Python from MUMPS code with `G ^ROUTINE` or `G LABEL^ROUTINE`, the code generator produces working Python that transfers control to the external routine permanently (does NOT return).

**Why this priority**: Less common than DO but still used in VistA for dispatch patterns and error handlers.

**Independent Test**: Can be tested by verifying code after GOTO is unreachable.

**YottaDB Verified Behavior**:
```
G ^exttest2 → Transfers to exttest2, "Unreachable" never prints
Output: "Starting\nIn exttest2"
```

**Acceptance Scenarios**:

1. **Given** `EXT1 W "Start",! G ^ext2 W "Never",! Q` and `ext2 W "End",! Q`, **When** executed, **Then** output is "Start\nEnd\n" (no "Never")
2. **Given** `EXT1 G LABEL^ext2 Q` and `ext2 Q` / `LABEL W "At LABEL",! Q`, **When** executed, **Then** output is "At LABEL\n"
3. **Given** multi-level call `EXT1 D ^ext2 W "Return",! Q` and `ext2 G ^ext3` and `ext3 W "ext3",! Q`, **When** executed, **Then** output is "ext3\n" (GOTO from called routine doesn't return)
4. **Given** `EXT1 G A+1^ext2` and `ext2 Q` / `A W "Line1",!` / ` W "Line2",! Q`, **When** executed, **Then** output is "Line2\n" (GOTO with label+offset)
5. **Given** `EXT1 G +2^ext2` and `ext2 W "L1",!` / ` W "L2",! Q`, **When** executed, **Then** output is "L2\n" (GOTO with absolute line offset)

---

### User Story 4 - Cross-Routine Variable Visibility (Priority: P1)

As a developer, MUMPS variables set in one routine are visible in called external routines, and modifications made in external routines are visible to the caller (unless NEWed).

**Why this priority**: This is fundamental MUMPS semantics. Without correct variable visibility, no real MUMPS program will work correctly.

**Independent Test**: Set variable before external call, modify in callee, verify visible to caller.

**YottaDB Verified Behavior**:
```
S X=100 D SUB^exttest2 W X → Outputs 999 (X modified in SUB)
```

**Acceptance Scenarios**:

1. **Given** `EXT1 S X=100 D ^ext2 W X,! Q` and `ext2 S X=999 Q`, **When** executed, **Then** output is "999\n" (callee modification visible)
2. **Given** `EXT1 S X=100 D ^ext2 W X,! Q` and `ext2 N X S X=999 Q`, **When** executed, **Then** output is "100\n" (NEW protects caller)
3. **Given** `EXT1 D ^ext2 W X,! Q` and `ext2 S X=42 Q`, **When** executed, **Then** output is "42\n" (variable created in callee visible to caller)

---

### User Story 5 - External Extrinsic Function (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$$FUNC^ROUTINE(args)`, the code generator produces working Python that calls the external function and returns its value, with $TEST properly saved/restored.

**Why this priority**: Extrinsic functions are heavily used in VistA for utility calculations. Without this, utility libraries can't be called.

**Independent Test**: Call external extrinsic and use returned value.

**YottaDB Verified Behavior**:
```
S X=$$ADD^exttest2(3,5) W X → Outputs 8
```

**Acceptance Scenarios**:

1. **Given** `EXT1 S X=$$ADD^ext2(3,5) W X,! Q` and `ext2 Q ""` / `ADD(A,B) Q A+B`, **When** executed, **Then** output is "8\n"
2. **Given** `EXT1 W $$DOUBLE^ext2(21),! Q` and `ext2 Q ""` / `DOUBLE(N) Q N*2`, **When** executed, **Then** output is "42\n"
3. **Given** `EXT1 I 1 S X=$$F^ext2() I  W "TEST=1" E  W "TEST=0" Q` and `ext2 Q ""` / `F() I 0 Q 1`, **When** executed, **Then** output is "TEST=1" ($TEST restored after extrinsic)

---

### User Story 6 - $TEXT Function with Current Routine (Priority: P2)

As a developer, when I use `$TEXT(+N)` or `$TEXT(LABEL+N)` to access source code lines from the current routine, the code generator produces working Python that returns the original source line text.

**Why this priority**: $TEXT is used for self-documenting code, configuration data in comments, and routine checksums. Foundation for external $TEXT.

**Independent Test**: Read source lines with $TEXT and verify content.

**YottaDB Verified Behavior**:
```
$T(+1) → Returns first line of current routine "TEST ; Test $TEXT function"
$T(TEST+1) → Returns second line " W \"Line 1: \",$T(+1),!"
```

**Acceptance Scenarios**:

1. **Given** `TEST ; comment line` / ` W $T(+1),! Q`, **When** executed, **Then** output contains "TEST ; comment line"
2. **Given** `TEST W $T(+0),! Q`, **When** executed, **Then** output is "texttest\n" ($T(+0) returns routine name)
3. **Given** `TEST W $T(+99),! Q` (past end), **When** executed, **Then** output is "\n" (returns empty)
4. **Given** `TEST W $T(-1),! Q` (negative offset), **When** executed, **Then** output is "\n" (returns empty per YDB behavior)

---

### User Story 7 - $TEXT Function with External Routine (Priority: P3)

As a developer, when I use `$TEXT(LABEL^ROUTINE)` or `$TEXT(+N^ROUTINE)` to access source code lines from an external routine, the code generator loads the external routine and returns its source line.

**Why this priority**: External $TEXT is less common but used in VistA for routine checksums and installation verification.

**Independent Test**: Read source line from another routine.

**YottaDB Verified Behavior**:
```
$T(+1^exttest2) → Returns first line of exttest2 "exttest2 ; Another routine"
$T(SUB^exttest2) → Returns "SUB ; Label in exttest2"
```

**Acceptance Scenarios**:

1. **Given** `EXT1 W $T(+1^ext2),! Q` and `ext2 ; first line...`, **When** executed, **Then** output contains "ext2 ; first line..."
2. **Given** `EXT1 W $T(LAB^ext2),! Q` and `ext2 Q` / `LAB ; my label`, **When** executed, **Then** output contains "LAB ; my label"
3. **Given** `EXT1 W $T(+99^ext2),! Q` and `ext2` (short routine), **When** executed, **Then** output is "\n" (past end returns empty)

---

### User Story 8 - Module Caching (Priority: P2)

As a developer, when external routines are called multiple times, they are loaded/translated only once and cached for subsequent calls.

**Why this priority**: Performance - without caching, repeated calls would re-translate and re-import.

**Independent Test**: Call same routine multiple times, verify translation happens once.

**Acceptance Scenarios**:

1. **Given** `EXT1 D ^ext2 D ^ext2 D ^ext2 Q`, **When** executed, **Then** ext2 module is imported only once
2. **Given** `EXT1 D A^ext2 D B^ext2 Q`, **When** executed, **Then** ext2 module is imported once (shared for both labels)

---

### Edge Cases

- What happens when external routine has parse errors? → Translate entire routine eagerly at first reference; raise exception immediately with routine name and error details (fail fast)
- What happens when calling `D +5^ROUTINE` (line offset, no label)? → Jump to 5th line of routine (use Spec 007 line dispatch)
- What happens when GOTO to external routine never QUITs? → Execution ends there (expected)
- What happens when extrinsic in external routine calls back to caller? → Works (recursive routine loading)
- What happens with circular calls (A calls B calls A)? → Works - standard Python import handles cycles
- What happens with `$TEXT(-1)` (negative offset)? → Return empty string (YDB behavior; MDC M5 error not enforced)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate standard Python `import` statements for external routine references
- **FR-002**: System MUST rely on Python's `sys.modules` for module caching (no custom cache)
- **FR-003**: System MUST support `D ^ROUTINE` calling entry label of external routine
- **FR-004**: System MUST support `D LABEL^ROUTINE` calling specific label in external routine
- **FR-005**: System MUST support `G ^ROUTINE` transferring control to external routine (no return)
- **FR-006**: System MUST support `G LABEL^ROUTINE` transferring to specific label (no return)
- **FR-007**: System MUST maintain variable visibility across routine boundaries (shared scope)
- **FR-008**: System MUST respect NEW in external routines (hides caller's variables)
- **FR-009**: System MUST support `$$FUNC^ROUTINE(args)` extrinsic function calls
- **FR-010**: System MUST save/restore $TEST around external extrinsic calls (per spec)
- **FR-011**: System MUST support `$TEXT(+N)` returning Nth line of current routine
- **FR-012**: System MUST support `$TEXT(LABEL+N)` returning line at label+offset in current routine
- **FR-013**: System MUST support `$TEXT(+N^ROUTINE)` returning Nth line of external routine
- **FR-014**: System MUST support `$TEXT(LABEL^ROUTINE)` and `$TEXT(LABEL+N^ROUTINE)`
- **FR-015**: System MUST use standard `sys.path` for module search (configurable via PYTHONPATH)
- **FR-016**: System MUST raise Python `ImportError` when external routine module not found
- **FR-017**: System MUST raise clear error when label not found in external routine
- **FR-018**: External DO with offset (`D LABEL+N^ROUTINE`, `D +N^ROUTINE`) MUST use line dispatch from Spec 007
- **FR-019**: External GOTO with offset (`G LABEL+N^ROUTINE`, `G +N^ROUTINE`) MUST use line dispatch from Spec 007
- **FR-020**: System MUST raise SyntaxError with routine name and error details when external routine has parse errors

### Key Entities

- **Module Import**: Standard Python `import` statements generated at transpile time
- **sys.path**: Standard Python search path mechanism (configured via PYTHONPATH or sys.path.insert)
- **Shared Scope**: Runtime `_scope` dictionary passed to all external calls, containing all non-NEWed variables. This approach prioritizes semantic correctness over generated code aesthetics, handling indirection and XECUTE gracefully.
- **Source Lines**: `_source_lines` list embedded in each generated `.py` module for $TEXT support

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `D ^ROUTINE` and `D LABEL^ROUTINE` produce correct output matching YottaDB
- **SC-002**: `G ^ROUTINE` and `G LABEL^ROUTINE` produce correct output matching YottaDB
- **SC-003**: Variable modifications in external routines are visible to caller (unless NEWed)
- **SC-004**: `$$FUNC^ROUTINE` returns correct value with $TEST properly isolated
- **SC-005**: `$TEXT(+N)` returns correct source line from current routine
- **SC-006**: `$TEXT(LABEL^ROUTINE)` returns correct source line from external routine
- **SC-007**: Python's `sys.modules` caching prevents redundant imports (standard behavior)
- **SC-008**: Python `ImportError` raised for missing routine modules
- **SC-009**: Generated Python remains syntactically valid (`ast.parse()` succeeds)
- **SC-010**: Basic cross-routine test suite (extcall.m, extcall2.m) produces output matching YottaDB

## Assumptions

1. External routines are pre-transpiled to `.py` files in configurable search paths
2. Routine names map to Python module filenames (e.g., `UTILITY` → `utility.py`)
3. Standard Python `import` statement handles module loading (no importlib needed)
4. Circular routine calls are handled by Python's import cycle handling
5. All routines share a common variable scope (no process isolation)
6. NEW semantics work correctly within external routines (from Spec 005)
7. Line dispatch infrastructure from Spec 007 is available for `D LABEL+N^ROUTINE`
8. Entry label (first label) name matches routine filename (VistA convention verified)

## Explicitly Out of Scope (Deferred to Later Specs)

**Spec 009** (LHS Functions & Globals):
- Global variables (`^NAME`) - needed for some VistA cross-routine patterns
- Subscripted local variables (`X(1,2)`) in cross-routine scope

**Spec 010** (Intrinsic Functions):
- $NAME, $ORDER, $QUERY on external routine data structures
- Most intrinsic functions (already tested separately)

**Spec 011** (Operators & Commands):
- Postconditioned external calls (`D:cond LABEL^ROUTINE`)
- MERGE across routine boundaries

**Spec 012** (Indirection & XECUTE):
- Indirect routine references (`D @X^ROUTINE`, `D LABEL^@ROUTINE`)
- XECUTE of external routine code
- `^%ZOSF` system routine patterns

## Clarifications

### Session 2025-01-13

- Q: Should cross-routine variable passing use static analysis with explicit parameters, runtime shared scope dictionary, or hybrid? → A: Runtime shared scope dictionary (`_scope` dict passed to all external calls)
- Q: When should external routine translation errors be detected (eager at load, lazy at call, or hybrid)? → A: Eager at load time - translate and validate entire routine when first referenced
- Q: How should external routines be loaded at runtime (on-the-fly transpilation, pre-transpiled .py, or hybrid)? → A: Pre-transpiled Python modules - assume all routines are pre-transpiled to `.py` files and just import them. Note: XECUTE (Spec 012) will still need embedded transpiler for runtime eval of string code, but that's separate from file-based routine loading.
- Q: What information should be included in "routine not found" errors? → A: Python's standard ImportError is raised. The error message includes the routine name. Search paths are available via `sys.path` for debugging. Example: `ModuleNotFoundError: No module named 'ext2'`
- Q: How should source lines be stored for $TEXT support? → A: Embedded in generated Python as `_source_lines = [...]` module-level constant in every generated `.py` file. Always embed (not conditional) to support external $TEXT(^routine) queries.
- Q: Should external GOTO follow strict MDC 8.2.6 (same routine restriction, M45 error) or YDB-permissive behavior? → A: Permissive (YDB-compatible) - allow cross-routine GOTO without LEVEL checks. VistA has 11,000+ cross-routine GOTOs across 3,000+ files; strict MDC would break the codebase.

## Dependencies

### This Spec Produces (for later specs):

- Module loading and caching infrastructure (used throughout)
- Cross-routine variable scope pattern (foundation for globals in Spec 009)
- $TEXT implementation (complete with this spec)
- External extrinsic function calls (enables VistA utility libraries)

### This Spec Consumes (from earlier specs):

- Line dispatch (`_line_map`) from Spec 007 (for `D LABEL+N^ROUTINE`, `$TEXT(LABEL+N)`)
- Trampoline pattern from Spec 006 (extended for external GOTO)
- $TEST save/restore from Spec 005 (for extrinsic function semantics)
- Name translation from Spec 004 (for routine name → module name mapping)
- `MRoutine.source_lines` from parser (for $TEXT)
