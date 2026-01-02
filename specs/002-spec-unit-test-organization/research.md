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
## Phase 8: Migration Baseline

**Pre-Migration Test Count**: 2,139 tests (1,277 passed, 754 xfailed, 108 skipped)

### Legacy Files Requiring Migration

| File | Test Count | Target Directory |
|------|------------|------------------|
| test_command_grammar.py | 283 | parser/s8_commands/, parser/extensions/ydb/ |
| test_expression_grammar.py | 123 | parser/s7_expressions/ |
| test_grammar.py | 111 | parser/s7_expressions/, parser/s8_commands/ |
| test_variables.py | 93 | asg/s8_commands/, analysis/ |
| test_parser.py | 93 | meta/, parser/s8_commands/ |
| test_classifier.py | 89 | analysis/ |
| test_semantic_analyzer.py | 62 | asg/s7_expressions/, asg/s8_commands/ |
| test_line_parser.py | 61 | meta/, parser/s8_commands/ |
| test_local_variables.py | 48 | asg/s8_commands/ |
| test_if_else.py | 45 | asg/s8_commands/, codegen/s8_commands/ |
| test_asg_serialization.py | 42 | meta/ |
| test_interpreter.py | 39 | meta/, codegen/ |
| test_for_loop.py | 38 | asg/s8_commands/, codegen/s8_commands/ |
| test_runtime_errors.py | 32 | codegen/, cross_cutting/ |
| test_indirect_syntax.py | 30 | parser/s7_expressions/, asg/s7_expressions/ |
| test_globals.py | 28 | asg/s8_commands/, codegen/s8_commands/ |
| test_do_command.py | 25 | parser/s8_commands/, asg/s8_commands/ |
| test_write_command.py | 19 | parser/s8_commands/, asg/s8_commands/ |
| test_function_grammar.py | 18 | parser/s7_expressions/ |
| test_routine.py | 16 | parser/s6_routine/, asg/s6_routine/ |
| test_special_variables.py | 16 | parser/s7_expressions/, asg/s7_expressions/ |
| test_scoping.py | 12 | asg/s8_commands/, analysis/ |
| test_operators.py | 11 | parser/s7_expressions/, asg/s7_expressions/ |
| test_parser_edge_cases.py | 8 | meta/, cross_cutting/ |
| test_codegen.py | 8 | codegen/ |
| test_intrinsic_functions.py | 7 | parser/s7_expressions/, asg/s7_expressions/ |

**Total Legacy Tests**: ~1,390 test methods across 26 files
### Migration Progress (Phase 8)

**Post-Migration Test Count**: 2,599 tests (2,137 passed, 52 skipped, 410 xfailed)

**Migration Status**: Partial migration completed. Tests have been migrated to spec-aligned structure, but legacy files still exist and contain duplicate tests. The spec-aligned directories now contain:
- parser/s8_commands/: Command parsing tests (SET, WRITE, READ, IF, FOR, GOTO, etc.)
- parser/s7_expressions/: Expression parsing tests (operators, functions, variables)
- parser/extensions/ydb/: YDB Z-command tests (16 files)
- asg/s8_commands/: Command ASG analysis tests
- asg/s7_expressions/: Expression ASG tests  
- asg/extensions/ydb/: YDB extension ASG tests
- analysis/: Internal algorithm tests (classifier, resolver, variable analysis)
- meta/: Parser API, error handling, serialization tests
- cross_cutting/: Indirection, postconditions, timeout tests

**Key Migrations Completed**:
- TestSetCommand (12 tests) → parser/s8_commands/test_s8_2_18_set.py
- TestWriteCommand (11 tests) → parser/s8_commands/test_s8_2_27_write.py
- TestReadCommand (12 tests) → parser/s8_commands/test_s8_2_17_read.py
- TestForCommand (6 tests) → parser/s8_commands/test_s8_2_05_for.py
- TestGotoCommand (8 tests) → parser/s8_commands/test_s8_2_06_goto.py
- TestDoCommand (13 tests) → parser/s8_commands/test_s8_2_03_do.py
- TestQuitCommand (12 tests) → parser/s8_commands/test_s8_2_16_quit.py
- Z-command classes (92 tests) → parser/extensions/ydb/*
- Expression/operator classes (50+ tests) → parser/s7_expressions/*
- Indirection tests (51 tests) → parser/s7_expressions/test_s7_3_indirection.py
- Pattern match tests (28 tests) → parser/s7_expressions/test_s7_2_5_pattern_match.py
- Meta tests (89 tests) → meta/*
- Analysis tests (100+ tests) → analysis/*
