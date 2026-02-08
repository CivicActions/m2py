# Implementation Plan: Unified Variable/Expression/Indirection/Subscript System

**Branch**: `018-unified-variable-system` | **Date**: 2025-01-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-unified-variable-system/spec.md`

## Summary

Unify variable access, indirection resolution, subscript handling, and name translation across codegen and runtime layers. The key insight from research is that Name Indirection (SET, WRITE) and Argument Indirection (IF, FOR) have fundamentally different semantics that must be handled separately while sharing common resolution infrastructure.

**Approach**: Build four shared components (`NameTranslator`, `SubscriptCanonicalizer`, `IndirectionResolver`, `CurrentScope`) in `src/m2py/core/`, then migrate commands incrementally with aggressive dead code cleanup.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing), uv (package management)  
**Storage**: MArray (in-memory sparse tree), globals database (MState.globals)  
**Testing**: pytest + MUGJ test suite extraction + YDB docker validation  
**Target Platform**: Linux/macOS (cross-platform Python)  
**Project Type**: Single project (transpiler)  
**Performance Goals**: No regression vs current implementation  
**Constraints**: Must pass all existing tests + new MUGJ-extracted tests  
**Scale/Scope**: ~1500 LOC in codegen/indirection.py to unify, 38 functional requirements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All designs validated against YDB + MUGJ tests |
| II. YDB as Reference | ✅ PASS | Research used `docker run --rm -i ydb` extensively |
| III. Strict Layer Separation | ✅ PASS | New components in `core/` shared by codegen and runtime; no parse logic in codegen |
| IV. Explicit Over Implicit | ✅ PASS | IndirectionContext enum makes context explicit |
| V. Foundational Correctness | ✅ PASS | Indirection is foundational; solving early |
| VI. Cross-Cutting Semantics | ✅ PASS | Value model (m_num, m_truth) preserved; scope unification addresses cross-cutting |
| VII. Minimize Runtime Surface | ✅ PASS | Static cases emit inline Python; runtime only for truly dynamic |
| VIII. Research Before Implementation | ✅ PASS | Comprehensive research.md created with MUGJ patterns and YDB verification |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/m2py/
├── core/                    # NEW: Shared components (this feature)
│   ├── __init__.py
│   ├── names.py             # NameTranslator
│   ├── subscripts.py        # SubscriptCanonicalizer  
│   ├── scope.py             # CurrentScope
│   └── indirection.py       # IndirectionResolver, IndirectionContext
├── asg/                     # Existing: No changes expected
│   ├── expressions.py       # MIndirection, MVariable, MGlobal
│   └── enums.py             # IndirectionType (existing)
├── analysis/                # Existing: Minor enhancements
│   └── semantic_analyzer.py # Consolidate indirection classification
├── codegen/                 # Existing: Per-command migration
│   ├── indirection.py       # Migrate to use core components
│   ├── statements.py        # SET, WRITE, IF, etc. migration
│   └── helpers.py           # m_str, m_num, etc. unchanged
├── runtime/                 # Existing: Use core components
│   └── __init__.py          # MState, existing indirection functions
└── parser/                  # Existing: No changes expected

tests/
├── unit/                    # NEW: MUGJ-extracted unit tests
│   └── core/
│       ├── test_names.py
│       ├── test_subscripts.py
│       ├── test_scope.py
│       └── test_indirection.py
├── functional/
│   └── mugj/                # Existing MUGJ tests
└── integration/             # Existing integration tests
```

**Structure Decision**: Single project with new `src/m2py/core/` module for shared components. This maintains layer separation while providing single-source-of-truth implementations.

## Complexity Tracking

No constitution violations requiring justification. The design:
- Uses existing project structure (no new projects)
- Adds one new module (`core/`) with focused responsibilities
- Migrates incrementally rather than rewriting
- Removes dead code aggressively per clarification

## Architectural Challenges Identified

**From deep codebase analysis - address during implementation:**

### Challenge 1: Three Scope Storage Mechanisms
The codebase currently uses three different storage mechanisms based on strategy:
- `_scope` dict (SIMPLE_FUNCTIONS strategy)
- `state.VAR` fields (TRAMPOLINE with static vars)
- `state._locals` dict (TRAMPOLINE with dynamic locals)

**Impact**: `CurrentScope` must adapt to all three mechanisms. The `_get_scope_expr()` helper in `indirection.py` (L38-44) is a good starting point but not used consistently.

### Challenge 2: Duplicate Name Translation
Name translation exists in TWO places that must stay in sync:
- `src/m2py/codegen/names.py` - `NameTranslator.translate()`
- `src/m2py/runtime/__init__.py` - `_translate_label_to_func()` (L113-148)

The runtime version explicitly notes it "mirrors the logic in m2py.codegen.names.translate_name" but is maintained separately "to avoid circular imports."

**Impact**: Move to `src/m2py/core/names.py` and have both codegen and runtime import from there.

### Challenge 3: Scope Expression Fragmentation  
The scope expression is computed in multiple places with slightly different logic:
- `indirection.py` L38: `_get_scope_expr()` helper
- `statements.py`: Inline conditionals (50+ `ctx.strategy == GotoStrategy.TRAMPOLINE` checks)
- `expressions.py`: Similar inline checks

**Impact**: `CurrentScope.from_generated_context()` must handle all cases, or we need to emit consistent scope setup in routine preamble.

### Challenge 4: MArray .value Extraction Inconsistency
The `.value` extraction is done inconsistently:
- `codegen/expressions.py`: Explicit `.value` access in generated code
- `runtime/__init__.py`: Runtime checks `if isinstance(raw_value, MArray)`
- `runtime/helpers.py`: Special case in `m_format_output()` (T075h)

**Impact**: `CurrentScope.get()` must ALWAYS extract `.value` from MArray (FR-038).

### Challenge 5: `resolve_indirection` vs `resolve_indirection_name`
Runtime has two similar functions with confusingly different semantics:
- `resolve_indirection()` - returns the resolved VALUE
- `resolve_indirection_name()` - returns the resolved variable NAME

**Impact**: `IndirectionResolver` must clearly distinguish these cases via `IndirectionContext`.

### Challenge 6: **CRITICAL BUG** - Argument Indirection Does NOT Evaluate Expressions

**Status**: ❌ **SEMANTIC CORRECTNESS BUG** confirmed via YDB validation

**The Bug**: `I @A` where `A="1=0"` should evaluate the MUMPS expression `1=0` → `0` (FALSE).
Currently, m2py returns the STRING `"1=0"` to `m_truth()`, which converts to `1` (TRUE).

**YDB Verification**:
```bash
printf 'TEST\n S A="1=0" I @A W "TRUE"\n E  W "FALSE"\n Q\n' | docker run --rm -i ydb
# Output: FALSE

uv run python utils/validate.py --code 'TEST S A="1=0" I @A W "TRUE" E  W "FALSE" Q'
# m2py: 'TRUE'  ← WRONG
# ydb:  ''      ← Correct (took ELSE branch)
```

**Root Cause** ([codegen/indirection.py#L416-476](src/m2py/codegen/indirection.py#L416-L476)):
`generate_argument_indirection()` returns the VALUE of `A` (string `"1=0"`) which gets passed to `m_truth()`.
It does NOT evaluate `"1=0"` as a MUMPS expression.

**Fix Required**: Argument indirection must call a runtime `evaluate_expression()` function that:
1. Parses the string as a MUMPS expression
2. Evaluates it with access to current scope
3. Returns the computed value (not the string)

**Workaround exists**: `execute_mumps(f"S TEMP={expr}", scope)` but this is heavyweight.
The plan's `IndirectionResolver.resolve()` with `IndirectionContext.ARGUMENT` must implement proper expression evaluation.

### Challenge 7: Empty String in Argument Indirection - YDB-Specific Behavior

**Status**: ⚠️ Documentation inconsistency identified

**Finding**: Empty string behaves DIFFERENTLY in argument vs non-argument context:

| Expression | YDB Result | Explanation |
|------------|------------|-------------|
| `I ""` | FALSE | Empty string → m_num("") → 0 → false |
| `S A="" I @A` | **TRUE** | Indirection succeeds, but unexpected behavior |
| `I @""` | **TRUE** | Literal empty indirection - also TRUE |

**Research.md currently says**: `I @""` → false (INCORRECT based on YDB verification)

**Impact**: Need to clarify whether this is YDB-specific or MUMPS standard. Add test case to torture test suite.

## Migration Phases

### Phase 0: Dead Code Marking & Test Infrastructure
**Purpose**: Prepare for migration by marking existing code and building test infrastructure.

#### Task 0.1: Mark Existing Code for Deprecation
Add searchable comment marker `# UNIFIED_VAR_DEPRECATED` to all code expected to be replaced:
- `codegen/indirection.py`: All functions dealing with name indirection
- `codegen/statements.py`: SET/WRITE/IF indirection-specific code paths
- `codegen/expressions.py`: Variable read indirection handling
- `runtime/__init__.py`: `_translate_label_to_func`, `resolve_indirection*`, `get_var`, `set_var`

This enables:
1. Easy navigation during transition (`grep -r UNIFIED_VAR_DEPRECATED`)
2. Verification all deprecated code is removed before completion
3. Tracking progress of migration

#### Task 0.2: Build MUGJ "Torture Test" Suite
Extract complex test patterns from MUGJ into standalone pytest tests:

**From VV2VNIA (Variable Name Indirection):**
- II-120: `@X@(subs)` basic name indirection subscripts
- II-127: `@@X@(1,2)@(5,6)` multi-level with per-level subscripts
- II-129: Naked indicator after indirection access

**From VV2VNIB (Complex Patterns):**
- II-131: `@B@(@B@(@B@(9)),@B,I)` nested indirection in expressions
- II-132.1: Value contains `@B@(1)` recursive @-expression
- II-132.3: `@@@@A` four-level chain where values contain @-expressions

**From V1IDARG (Argument Indirection):**
- I-417: `I @A` where A="1=0" (expression evaluation) **← CURRENTLY FAILING**
- I-420/421: Multi-level argument indirection

**Critical Bug Reproduction Test:**
```python
def test_argument_indirection_expression_evaluation():
    """I @A where A='1=0' must EVALUATE expression, not convert string."""
    # Current bug: m_truth("1=0") → 1 → TRUE (WRONG)
    # Correct: evaluate "1=0" as MUMPS → 0 → FALSE
    result = subprocess.run(...)
    assert "FALSE" in result.stdout  # Currently fails
```

**Test Structure:**
```
tests/unit/core/indirection/
├── test_name_indirection_basic.py      # V1IDNM1/2 patterns
├── test_name_indirection_multilevel.py # VV2VNIA II-120-129
├── test_name_indirection_complex.py    # VV2VNIB II-131-132
├── test_argument_indirection.py        # V1IDARG patterns
├── test_subscript_canonicalization.py  # Numeric/string subscript rules
└── test_scope_integration.py           # Strategy-based scope tests
```

### Phase 1: Core Components
Build shared components with comprehensive unit tests:
1. `NameTranslator` - MUMPS↔Python name translation (consolidate from codegen/names.py and runtime)
2. `SubscriptCanonicalizer` - Subscript normalization
3. `CurrentScope` - Unified variable access (handle all 3 storage mechanisms)
4. `IndirectionResolver` - Runtime indirection resolution (consolidate resolve_indirection/resolve_indirection_name)

### Phase 2: SET Command Migration
- Replace SET indirection codegen with unified resolver calls
- Remove old SET-specific indirection code (marked with `# UNIFIED_VAR_DEPRECATED`)
- Validate with V1IDNM2 tests + torture tests

### Phase 3: WRITE/KILL/READ Migration
- Migrate name indirection for output commands
- Dead code cleanup (verify with `grep UNIFIED_VAR_DEPRECATED`)
- Validate with V1IDNM1, V1IDNM3 tests

### Phase 4: IF/FOR Migration (Argument Indirection)
- Implement expression evaluation in IndirectionResolver
- Migrate IF and FOR argument indirection
- Validate with V1IDARG tests + torture tests

### Phase 5: DO/GOTO Migration
- Migrate label/routine indirection
- Validate with V1IDDO tests

### Phase 6: Final Validation & Cleanup
- Run full VV2VNI test suite
- Fix any remaining edge cases
- **Final dead code scan**: `grep -r UNIFIED_VAR_DEPRECATED src/` must return empty
- Remove deprecation markers from any code intentionally kept
- Update documentation
