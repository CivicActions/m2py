# Implementation Plan: Extended Operators, Commands & Completion

**Branch**: `011-operators-commands-completion` | **Date**: 2026-01-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-operators-commands-completion/spec.md`

## Summary

Complete remaining operators, statements, and edge cases for MUMPS-to-Python code generation. This is cleanup work that fills in the gaps after core infrastructure is established.

Technical approach:
- Extend `_generate_binary_op()` with logical, string, and pattern operators
- Fix `_generate_unary_op()` NOT to return 0/1 instead of True/False
- Handle `MFormatControl` nodes in `_generate_write()` for format controls
- Add postcondition checking in `generate_statement()`
- Extend runtime with $X/$Y tracking, $HOROLOG, and other special variables
- Complete NEW/KILL/MERGE/HANG/HALT/READ command generators

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX (parser), pytest (testing), MArray (Spec 009), pattern_compiler (analysis)
**Storage**: InMemoryGlobalStorage for tests (Spec 009)
**Testing**: pytest with YottaDB Docker validation
**Target Platform**: Linux/macOS CLI transpiler
**Project Type**: single (transpiler library)
**Performance Goals**: Not performance-critical; correctness is paramount
**Constraints**: Generated Python must match YottaDB output exactly

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All behavior validated against YottaDB |
| II. YDB as Reference Implementation | ✅ PASS | All acceptance scenarios validated with `docker run ydb` |
| III. Strict Layer Separation | ✅ PASS | Codegen only; parser/ASG already handles all node types |
| IV. Explicit Over Implicit | ✅ PASS | Using helper functions for M-specific semantics |
| V. Foundational Correctness | ✅ PASS | Building on proven Spec 009/010 infrastructure |
| VI. Cross-Cutting Semantics | ✅ PASS | Uses existing m_num(), m_truth(), m_compare() helpers |
| VII. Minimize Runtime Surface | ✅ PASS | Inline Python for operators; runtime only for $X/$Y tracking |
| VIII. Research Before Implementation | ✅ PASS | Docs, ASG, tests reviewed; research.md produced |

## Project Structure

### Documentation (this feature)

```text
specs/011-operators-commands-completion/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity documentation
├── quickstart.md        # Implementation guide
├── contracts/           # API contracts
│   ├── operator-codegen.md
│   ├── format-controls.md
│   └── special-variables.md
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code

```text
src/m2py/
├── codegen/
│   ├── expressions.py   # Operator codegen (modify)
│   └── statements.py    # Statement codegen (modify)
├── runtime/
│   ├── __init__.py      # MUMPSRuntime class (modify)
│   └── helpers.py       # Runtime helpers (modify)
└── analysis/
    └── pattern_compiler.py  # Already exists (use)

tests/unit/codegen/
├── s7_expressions/
│   └── test_s7_2_operators.py  # Operator tests (modify)
└── s8_commands/
    ├── test_s8_2_25_write.py   # Format control tests (modify)
    ├── test_s8_2_12_new.py     # NEW command tests (modify)
    ├── test_s8_2_10_kill.py    # KILL command tests (modify)
    ├── test_s8_2_11_merge.py   # MERGE command tests (create)
    └── test_s8_2_07_hang.py    # HANG command tests (create)
```

## Current State Analysis

### Operators (from research)

| Operator | Status | Notes |
|----------|--------|-------|
| `+`, `-`, `*`, `/` | ✅ Works | Arithmetic |
| `\`, `#` | ✅ Works | Integer div, modulo |
| `=`, `<`, `>` | ✅ Works | Comparison |
| `_` | ✅ Works | Concatenation |
| `'` (NOT) | ⚠️ Broken | Returns False instead of 0 |
| `&` (AND) | ❌ Missing | NotImplementedError |
| `!` (OR) | ❌ Missing | NotImplementedError |
| `[` (contains) | ❌ Missing | NotImplementedError |
| `]` (follows) | ❌ Missing | NotImplementedError |
| `]]` (sorts after) | ❌ Missing | NotImplementedError |
| `?` (pattern) | ❌ Missing | NotImplementedError |

### Format Controls (from research)

| Control | Status | Notes |
|---------|--------|-------|
| `!` (newline) | ❌ Missing | MFormatControl not handled in _generate_write |
| `#` (formfeed) | ❌ Missing | Same |
| `?n` (tab) | ❌ Missing | Same, needs column tracking |
| `*n` (charcode) | ❌ Missing | Same |

### Commands (from research)

| Command | Status | Notes |
|---------|--------|-------|
| Multiple SET | ✅ Works | Already handles list of assignments |
| KILL (basic) | ✅ Works | Local and global |
| KILL (exclusive) | ❌ Missing | NotImplementedError |
| NEW (basic) | ❌ Missing | Not implemented |
| MERGE | ❌ Missing | Not implemented |
| HANG | ❌ Missing | Not implemented |
| HALT | ❌ Missing | Not implemented |
| READ | ❌ Missing | Not implemented |

### Special Variables

| Variable | Status | Notes |
|----------|--------|-------|
| $TEST | ✅ Works | Spec 005 |
| $HOROLOG | ❌ Missing | NotImplementedError |
| $JOB | ❌ Missing | NotImplementedError |
| $IO | ❌ Missing | NotImplementedError |
| $X, $Y | ❌ Missing | NotImplementedError |
| $STORAGE | ❌ Missing | NotImplementedError |
| $STACK | ❌ Missing | NotImplementedError |
| $QUIT | ❌ Missing | NotImplementedError |

## Implementation Phases

### Phase 1: P1 Operators (Critical Path)
1. Fix NOT operator to return int(0/1)
2. Add AND operator (`&`)
3. Add OR operator (`!`)
4. Add negated comparisons (`'=`, `'<`, `'>`)

### Phase 2: P1 Format Controls
1. Handle MFormatControl in _generate_write()
2. Implement NEWLINE (`!`)
3. Implement FORMFEED (`#`)
4. Implement CHARCODE (`*n`)
5. Implement TAB (`?n`) with column tracking

### Phase 3: P1 Postconditions
1. Check postcondition in generate_statement()
2. Wrap statement in conditional when present

### Phase 4: P2 String/Pattern Operators
1. Add contains (`[`)
2. Add follows (`]`)
3. Add sorts after (`]]`)
4. Add pattern match (`?`) using pattern_compiler

### Phase 5: P2 Special Variables
1. Add $HOROLOG (datetime calculation)
2. Add $JOB (os.getpid())
3. Add $IO (device tracking)
4. Add $X, $Y (column/line tracking)
5. Add $STORAGE (large constant)
6. Add $STACK (call depth)
7. Add $QUIT (extrinsic context)

### Phase 6: P2 Commands
1. NEW command (selective)
2. KILL command (exclusive)
3. MERGE command

### Phase 7: P3 Commands
1. HANG command
2. HALT command
3. READ command (basic + timeout)

## Dependencies

- **Spec 009**: MArray class for MERGE, NEW/KILL semantics
- **Spec 010**: Intrinsic functions for validation tests ($GET, etc.)
- **pattern_compiler.py**: Already exists in analysis/ for pattern match

