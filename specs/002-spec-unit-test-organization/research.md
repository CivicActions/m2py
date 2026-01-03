# Research: MUMPS Spec-Aligned Unit Test Organization

**Branch**: `002-spec-unit-test-organization` | **Date**: 2026-01-01

## Research Tasks

### 1. Existing Test Structure Analysis

**Question**: What tests currently exist and how are they organized?

**Finding**: 
- 20+ test files in `tests/unit/` with varied naming conventions
- Tests organized by implementation concern (grammar, parser, classifier) rather than MUMPS spec section
- Current files include: `test_command_grammar.py`, `test_expression_grammar.py`, `test_parser.py`, `test_semantic_analyzer.py`, etc.
- No systematic coverage tracking against MUMPS spec sections

**Decision**: Create parallel spec-aligned structure, migrate tests incrementally
**Rationale**: Avoids breaking existing tests while building new structure
**Alternatives Considered**: In-place rename (rejected: too disruptive to CI)

### 2. MUMPS 1995 Spec Section Enumeration

**Question**: What are the exact spec sections requiring test coverage?

**Finding**:
- §5 Metalanguage (informative, minimal testing needed)
- §6 Routine Structure: 6.1-6.4 (4 major subsections)
- §7 Expressions: 7.1-7.3 (variables, functions, operators, indirection)
  - §7.1.5 alone has ~30 intrinsic functions ($ASCII through $VIEW)
  - §7.1.7 has ~20 special variables ($DEVICE through $Y)
- §8 Commands: 8.1-8.3 (27 commands plus general rules)
- §9 Character Set (informative, limited testing needed)

**Decision**: Use spec section numbering directly in directory/file names
**Rationale**: Direct traceability to ANSI standard
**Alternatives Considered**: Semantic grouping (rejected: loses traceability)

### 3. pytest Marker Best Practices

**Question**: How should we implement the three-level testing with markers?

**Finding**:
- pytest supports custom markers via `pytest.ini` or `conftest.py`
- `@pytest.mark.xfail(reason="...")` allows expected failures without breaking CI
- Compound markers work: `@pytest.mark.stub @pytest.mark.parser`
- Filtering: `pytest -m "parser and not stub"` runs implemented parser tests only

**Decision**: Register markers in `conftest.py`, use compound markers for categorization
**Rationale**: Maximum flexibility, explicit test status
**Alternatives Considered**: Separate test suites per category (rejected: increases maintenance)

### 4. Backward Compatibility Syntax Differences

**Question**: What syntax changed between 1977/1984/1990 and 1995 standards?

**Finding**:
- Most core syntax remained stable across standards
- 1990 added: Transaction processing (TSTART, TCOMMIT, TROLLBACK, TRESTART)
- 1995 added: Some intrinsic functions, SSVNs (^$JOB, ^$ROUTINE, etc.)
- VistA codebase uses predominantly compatible syntax
- No breaking syntax changes identified that require special handling

**Decision**: Mark pre-1995 constructs with `@pytest.mark.pre1995` where applicable
**Rationale**: Tracks historical compatibility without separate test suite
**Alternatives Considered**: Version-specific test directories (rejected: overkill)

### 5. YottaDB Z-Command Inventory

**Question**: Which Z-commands need test coverage?

**Finding**:
From YDBTest and implementation:
- Implemented: ZBREAK, ZCOMPILE, ZCONTINUE, ZGOTO, ZLINK, ZMESSAGE, ZPRINT, ZSHOW, ZSTEP, ZSYSTEM, ZWRITE
- Commonly used in production: ZWRITE (debugging), ZGOTO (error handling), ZSHOW (diagnostics)
- Not implemented: ZEDIT, ZHELP, and some vendor-specific variants

**Decision**: Create `extensions/ydb/` directory with tests for implemented Z-commands
**Rationale**: Clear separation of standard vs vendor-specific
**Alternatives Considered**: Mix with standard tests (rejected: pollutes spec alignment)

### 6. Migration Strategy

**Question**: How to migrate 20+ existing test files without losing coverage?

**Finding**:
- Current test count: ~400+ test cases across 20 files
- Most tests can map to specific spec sections
- Some tests are cross-cutting (indirection, postconditions)
- Existing fixtures in `conftest.py` are reusable
- Some tests (e.g., `test_classifier.py`, `test_resolver.py`) test internal analysis algorithms, not MUMPS spec compliance
- Some tests (e.g., `test_textx_classes.py`) test tooling infrastructure, not language features

**Decision**: 
1. Create new structure with stubs (all xfail)
2. Copy existing tests to appropriate new locations
3. Remove xfail as tests are copied
4. After migration, run diff to verify count ≥ original
5. Archive old structure (don't delete until verified)
6. Place analysis algorithm tests in `analysis/` directory (non-spec-aligned)
7. Place tooling/infrastructure tests in `meta/` directory (non-spec-aligned)

**Rationale**: Zero-risk migration with verification; separating spec-aligned from internal tests maintains clarity
**Alternatives Considered**: Big-bang migration (rejected: too risky); mixing internal tests with spec tests (rejected: obscures coverage tracking)

### 7. Non-Spec-Aligned Test Categories

**Question**: How to handle tests that don't map to MUMPS spec sections?

**Finding**:
- `test_classifier.py` - Tests `classify_for_command()` and `classify_goto()` analysis functions
- `test_resolver.py` - Tests `resolve_references()` internal algorithm
- `test_textx_classes.py` - Tests textX metamodel integration
- `test_parse_result_tracking.py` - Tests parse result container classes
- These are valuable but don't verify MUMPS language compliance

**Decision**: Create two non-spec-aligned directories:
- `analysis/` - Unit tests for analysis functions (classifiers, resolver)
- `meta/` - Tooling infrastructure tests (textX, parse tracking)

**Rationale**: Keeps spec-aligned tests pure for coverage tracking; preserves internal algorithm tests
**Alternatives Considered**: Force-fit into ASG category (rejected: would skew coverage metrics)

### 8. Structured System Variables (SSVNs)

**Question**: Are SSVNs adequately covered in the plan?

**Finding**:
- Spec §7.1.3 defines SSVNs: `^$JOB`, `^$ROUTINE`, `^$GLOBAL`, `^$LOCK`, `^$DEVICE`, `^$SYSTEM`
- These use distinct syntax (`^$` prefix) from regular globals and special variables
- Plan's s7_expressions directory list omitted explicit SSVN test file

**Decision**: Add `test_s7_1_3_ssvns.py` to s7_expressions directory
**Rationale**: Direct spec section mapping per FR-002
**Alternatives Considered**: Fold into variables tests (rejected: obscures specific coverage)

## Resolved Unknowns

| Unknown | Resolution |
|---------|------------|
| Spec section count | ~50 sections requiring test coverage across §6-§8 |
| Marker implementation | conftest.py registration with compound markers |
| Backward compat scope | Minimal - syntax is stable, mark with pre1995 |
| Z-command scope | 11 implemented commands in extensions/ydb/ |
| Migration risk | Mitigated via parallel structure + verification |
| Non-spec tests | Separate `analysis/` and `meta/` directories |
| SSVNs | Explicit test file `test_s7_1_3_ssvns.py` added |
| a107096.md ($MIRACLE) | April Fools joke in 1995 spec; not a real function, skip |
| a107301-316.md (MWAPI) | MUMPS Windowing API (GUI attributes: Window, Gadget, Choice, Event) + character set tables (ISO-8859-1, DOS, DEC, EBCDIC); out of scope for core language transpiler |
| MATH library count | Verified 57 functions in 1995 spec (a107127-182): trig, complex, matrix functions |
| $NEXT deprecation | $NEXT is deprecated in favor of $ORDER; documented but functional |
---

## Backward Compatibility Research

### Standard Version Evolution Summary

| Feature | 1977 | 1984 | 1990 | 1995 | Breaking? |
|---------|------|------|------|------|-----------|
| **Commands** |
| BREAK | ✓ | ✓ | ✓ | ✓ | No |
| CLOSE | ✓ | ✓ | ✓ | ✓ | No |
| DO | ✓ | ✓ | ✓ | ✓ | No |
| ELSE | ✓ | ✓ | ✓ | ✓ | No |
| FOR | ✓ | ✓ | ✓ | ✓ | No |
| GOTO | ✓ | ✓ | ✓ | ✓ | No |
| HALT | ✓ | ✓ | ✓ | ✓ | No |
| HANG | ✓ | ✓ | ✓ | ✓ | No |
| IF | ✓ | ✓ | ✓ | ✓ | No |
| JOB | ✓ | ✓ | ✓ | ✓ | No |
| KILL | ✓ | ✓ | ✓ | ✓ | No |
| LOCK | ✓ | ✓ | ✓ | ✓ | No |
| NEW | - | ✓ | ✓ | ✓ | No (addition) |
| MERGE | - | - | ✓ | ✓ | No (addition) |
| OPEN | ✓ | ✓ | ✓ | ✓ | No |
| QUIT | ✓ | ✓ | ✓ | ✓ | No |
| READ | ✓ | ✓ | ✓ | ✓ | No |
| SET | ✓ | ✓ | ✓ | ✓ | No |
| TSTART | - | - | - | ✓ | No (addition) |
| TCOMMIT | - | - | - | ✓ | No (addition) |
| TROLLBACK | - | - | - | ✓ | No (addition) |
| TRESTART | - | - | - | ✓ | No (addition) |
| USE | ✓ | ✓ | ✓ | ✓ | No |
| VIEW | ✓ | ✓ | ✓ | ✓ | No |
| WRITE | ✓ | ✓ | ✓ | ✓ | No |
| XECUTE | ✓ | ✓ | ✓ | ✓ | No |
| KVALUE | - | - | - | ✓ | No (addition) |
| KSUBSCRIPTS | - | - | - | ✓ | No (addition) |
| **Intrinsic Functions** |
| $ASCII | ✓ | ✓ | ✓ | ✓ | No |
| $CHAR | ✓ | ✓ | ✓ | ✓ | No |
| $DATA | ✓ | ✓ | ✓ | ✓ | No |
| $EXTRACT | ✓ | ✓ | ✓ | ✓ | No |
| $FIND | ✓ | ✓ | ✓ | ✓ | No |
| $FNUMBER | - | - | ✓ | ✓ | No (addition) |
| $GET | - | ✓ | ✓ | ✓ | No (addition) |
| $JUSTIFY | ✓ | ✓ | ✓ | ✓ | No |
| $LENGTH | ✓ | ✓ | ✓ | ✓ | No |
| $NAME | - | - | ✓ | ✓ | No (addition) |
| $NEXT | ✓ | ✓ | ✓ | **deprecated** | **Yes (use $ORDER)** |
| $ORDER | - | ✓ | ✓ | ✓ | No (addition) |
| $PIECE | ✓ | ✓ | ✓ | ✓ | No |
| $QLENGTH | - | ✓ | ✓ | ✓ | No (addition) |
| $QSUBSCRIPT | - | ✓ | ✓ | ✓ | No (addition) |
| $QUERY | - | ✓ | ✓ | ✓ | No (addition) |
| $RANDOM | ✓ | ✓ | ✓ | ✓ | No |
| $REVERSE | - | - | ✓ | ✓ | No (addition) |
| $SELECT | ✓ | ✓ | ✓ | ✓ | No |
| $STACK | - | - | - | ✓ | No (addition) |
| $TEXT | ✓ | ✓ | ✓ | ✓ | No |
| $TRANSLATE | - | - | ✓ | ✓ | No (addition) |
| $VIEW | ✓ | ✓ | ✓ | ✓ | No |
| $DEXTRACT | - | proposed | proposed | **dropped** | **Yes (never standardized)** |
| $DPIECE | - | proposed | proposed | **dropped** | **Yes (never standardized)** |
| **Special Variables** |
| $DEVICE | ✓ | ✓ | ✓ | ✓ | No |
| $ECODE | - | - | - | ✓ | No (addition) |
| $ESTACK | - | - | - | ✓ | No (addition) |
| $ETRAP | - | - | - | ✓ | No (addition) |
| $HOROLOG | ✓ | ✓ | ✓ | ✓ | No |
| $IO | ✓ | ✓ | ✓ | ✓ | No |
| $JOB | ✓ | ✓ | ✓ | ✓ | No |
| $KEY | - | - | ✓ | ✓ | No (addition) |
| $PRINCIPAL | - | - | - | ✓ | No (addition) |
| $QUIT | - | - | - | ✓ | No (addition) |
| $REFERENCE | - | - | ✓ | ✓ | No (addition) |
| $STACK | - | - | - | ✓ | No (addition) |
| $STORAGE | ✓ | ✓ | ✓ | ✓ | No |
| $SYSTEM | - | - | - | ✓ | No (addition) |
| $TEST | ✓ | ✓ | ✓ | ✓ | No |
| $TLEVEL | - | - | - | ✓ | No (addition) |
| $TRESTART | - | - | - | ✓ | No (addition) |
| $X, $Y | ✓ | ✓ | ✓ | ✓ | No |
| **SSVNs** |
| ^$JOB | - | - | - | ✓ | No (addition) |
| ^$ROUTINE | - | - | - | ✓ | No (addition) |
| ^$GLOBAL | - | - | - | ✓ | No (addition) |
| ^$LOCK | - | - | - | ✓ | No (addition) |
| ^$DEVICE | - | - | - | ✓ | No (addition) |
| ^$SYSTEM | - | - | - | ✓ | No (addition) |

### Legacy Patterns Found

**$NEXT usage in VistA-M (488 occurrences)**:
```
; VistA-M commonly uses $N(glvn) or $NEXT(glvn) for traversal
; Modern code should use $O(glvn) or $ORDER(glvn)
```

**$NEXT usage in functional test suites (58 occurrences)**:
- `tests/functional/mvts_inref/V1NX1.m` - $NEXT function test -1-
- `tests/functional/mvts_inref/V1NX2.m` - $NEXT function test -2-
- `tests/functional/mvts_inref/V2NO1.m` - $NEXT and $ORDER comparison
- `tests/functional/mvts_inref/V2NO2.m` - $NEXT and $ORDER comparison -2-

These tests explicitly validate backward compatibility of $NEXT against $ORDER behavior.

### BNF Changes

**1977 → 1984 Additions**:
- NEW command (variable scoping)
- $GET function (default value access)
- $ORDER function (replaces $NEXT for traversal)
- $QUERY function (hierarchical traversal)
- $QLENGTH, $QSUBSCRIPT functions (query decomposition)
- Parameter passing with `NEW` command

**1984 → 1990 Additions**:
- MERGE command (array copy)
- $NAME function (construct reference names)
- $FNUMBER function (numeric formatting)
- $REVERSE function (string reversal)
- $TRANSLATE function (character translation)
- $KEY special variable (input terminator)
- $REFERENCE special variable (naked indicator)

**1990 → 1995 Additions**:
- Transaction processing: TSTART, TCOMMIT, TROLLBACK, TRESTART commands
- KVALUE, KSUBSCRIPTS commands (granular kill operations)
- $STACK function and variable (error context)
- $ECODE, $ESTACK, $ETRAP (structured error handling)
- $TLEVEL, $TRESTART (transaction state)
- $PRINCIPAL (original principal device)
- $QUIT (return mode indicator)
- $SYSTEM (system identifier)
- SSVNs: ^$JOB, ^$ROUTINE, ^$GLOBAL, ^$LOCK, ^$DEVICE, ^$SYSTEM

### Deprecated Constructs

| Construct | Status | Replacement | M2PY Behavior |
|-----------|--------|-------------|---------------|
| $NEXT(glvn) | Deprecated per 1995 §7.1.5 | $ORDER(glvn) | Parse and transpile; emit `MUMPSDeprecationWarning` |
| $DEXTRACT | Never standardized | $EXTRACT with multiple args | Not supported; raise parse error |
| $DPIECE | Never standardized | $PIECE with multiple args | Not supported; raise parse error |

### Pre-Migration Test Baseline

- **Pre-migration test count**: 1380 tests collected
- **Post-migration target**: ≥ 1380 tests
- Captured via `uv run pytest tests/unit/ --collect-only -q | tail -1`

### Migration File Inventory

Files to migrate from `tests/unit/`:
- ✓ test_command_grammar.py (migrated)
- ✓ test_expression_grammar.py (migrated)
- ✓ test_grammar.py (migrated)
- ✓ test_parser.py (migrated)
- ✓ test_classifier.py (migrated)
- ✓ test_semantic_analyzer.py (migrated)
- ✓ test_command_analysis.py (migrated)
- ✓ test_goto_for_analysis.py (migrated)
- ✓ test_resolver.py (migrated)
- ✓ test_variables.py (migrated)

All legacy files have been migrated to spec-aligned structure.