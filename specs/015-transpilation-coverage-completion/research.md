# Research: Transpilation Coverage Completion

**Feature**: 015-transpilation-coverage-completion  
**Date**: 2026-01-20  
**Status**: In Progress

## Objective

Analyze each coverage gap in parser/asg/analysis layers to determine:
- **Category A**: Missing codegen implementation needed
- **Category B**: Codegen could be improved by using this analysis
- **Category C**: Dead code to remove (no valid codegen use case)

## Current Metrics

- **Raw Coverage**: 70% (parser/asg/analysis when running codegen+cross_cutting tests)
- **Normalized Progress**: 78.6% (target: 100% = 85% raw)
- **Gap to close**: ~15% raw coverage = ~21.4% normalized

## Coverage Gap Inventory

### Parser Layer Gaps

#### P1: `parser/exceptions.py` (14% coverage)

**Uncovered Lines**: 32-55, 85-90

**Code Purpose**: Error message formatting for MUMPSSyntaxError and MUMPSUnknownCommandError

**Analysis**:
- Lines 32-55: `__init__` method building formatted error messages with location info
- Lines 85-90: `__init__` for MUMPSUnknownCommandError

**Category**: [NEEDS RESEARCH]
- Does codegen ever trigger these errors?
- Are these only triggered during initial parse (before codegen)?

**Resolution**: [TBD]

---

#### P2: `parser/line_parser.py` (39% coverage)

**Uncovered Lines**: 32, 43-46, 107-109, 115-117, 144, 168-182, 197-202, 216-250

**Code Purpose**: Low-level textX line parsing utilities for FOR loop classification

**Analysis**:
- Lines 168-182: `detect_quit_after_for()` - detects QUIT after FOR on same line
- Lines 197-202: `extract_for_commands()` - extracts FOR commands from a line
- Lines 216-250: `classify_for_command()` - classifies FOR loop types

**Category**: [NEEDS RESEARCH]
- These are FOR loop analysis utilities
- Used by `classify_for_patterns()` in parser.py (also uncovered)
- Question: Is this dead code or should codegen use it?

**Resolution**: [TBD]

---

#### P3: `parser/parser.py` (70% coverage)

**Uncovered Lines**: 71-72, 94, 127-131, 169-183, 178-180, 195-216, 245, 259-277, 277-285, 301, 324-328, 388, 404, 421-425, 458, 523-524, 526-528, 532-542, 569-609, 642-674, 663-669, 709, 724-725, 776-777, 796-799, 825, 848-905, 922-933, 1053-1055

**Major Uncovered Regions**:

1. **Lines 569-609**: `classify_for_patterns()` method
   - Purpose: Parse and classify FOR loop patterns from source
   - Uses line_parser utilities
   
2. **Lines 848-905**: `classify_for_patterns()` implementation body
   - Iterates over lines, extracts FOR commands, classifies them

3. **Lines 922-933**: `classify_for_patterns_from_file()`
   - File-based wrapper for FOR pattern classification

4. **Lines 195-216**: `_find_argumentless_do_for_dot_lines()` deep recursion paths
   - Handles nested control flow for dot-line collection

**Category**: [NEEDS RESEARCH]
- FOR pattern classification API - is this used anywhere?
- Some paths may be edge cases in parsing

**Resolution**: [TBD]

---

#### P4: `parser/textx_classes.py` (68% coverage)

**Uncovered Lines**: 58, 84, 97, 109, 119, 126, 130-133, 147, 151, 157, 161-167, 173, 203, 215, 234, 252, 286-288, 309, 349-352, 364-367, 399-441, 454-456, 482-483, 521-522, 534-536, 579-581, 603-610, 636-655, 638, 649, 687-688, 711-717, 736, 744, 782-784, 825, 831, 881, 886, 903-905

**Code Purpose**: textX custom class definitions for grammar rules

**Analysis**:
- Many uncovered lines are `__repr__` methods (debugging only)
- Some are edge case handling in various custom classes
- Lines 399-441: `_unwrap_zwrite_subscripts()` - ZWRITE subscript handling

**Category**: [NEEDS RESEARCH]
- `__repr__` methods are Category C (debugging only)
- Need to check specific handlers for edge cases

**Resolution**: [TBD]

---

### ASG Layer Gaps

#### A1: `asg/elements.py` (56% coverage)

**Uncovered Lines**: 17-19, 41-44, 84-117, 123-150, 189, 258-263, 264, 332-335, 353-355, 369-372

**Major Uncovered Regions**:

1. **Lines 84-117**: `to_dict()` method on ASGElement
   - Purpose: Serialize ASG to dictionary for debugging/inspection
   
2. **Lines 123-150**: `_serialize_value()` helper
   - Recursive serialization for to_dict()

3. **Lines 332-335, 353-355, 369-372**: MLabel/MRoutine iteration helpers
   - `__iter__`, `get_label()` variations

**Category**: [NEEDS RESEARCH]
- `to_dict()` is clearly for debugging/inspection - Category C?
- Or should we keep for devops tooling?

**Resolution**: [TBD]

---

#### A2: `asg/type_helpers.py` (70% coverage)

**Uncovered Lines**: 10-11, 44, 58, 72-74, 88-90, 107-109

**Code Purpose**: Type checking helpers for ASG nodes

**Analysis**:
- Helper functions like `get_then_scope()`, `get_else_scope()`, `get_body_scope()`
- Some paths are None-checks that may not be exercised

**Category**: [NEEDS RESEARCH]

**Resolution**: [TBD]

---

#### A3: `asg/expressions.py` (96% coverage)

**Uncovered Lines**: 25, 385, 390

**Analysis**: Minor gaps - likely edge cases in expression types

**Category**: [NEEDS RESEARCH]

**Resolution**: [TBD]

---

#### A4: `asg/statements.py` (98% coverage)

**Uncovered Lines**: 22-23, 406, 432

**Analysis**: Minor gaps - likely edge cases in statement types

**Category**: [NEEDS RESEARCH]

**Resolution**: [TBD]

---

### Analysis Layer Gaps

#### AN1: `analysis/semantic_analyzer.py` (68% coverage)

**Uncovered Lines**: Many - see full list in coverage report

**Major Themes**:
1. Handler methods for specific statement types not exercised
2. Edge case paths in expression analysis
3. Pattern alternation handling (lines 549-576)
4. Various `_analyze_*` methods for specific grammar rules

**Category**: [NEEDS RESEARCH]
- Some may be missing codegen tests (Category A)
- Some may be edge cases not exercised (need to trace)

**Resolution**: [TBD]

---

#### AN2: `analysis/variables.py` (70% coverage)

**Uncovered Lines**: 197-206, 210-260, 264-282, 286-302, 306-317, 321-322, 326-327, 332-333, 338-339, 400, 489-494, 527-519, 535-541, 587, 612-615, 621-707, 711-724, 739-755, 833-829, 875-882, 894-895, 938-940, 1111, 1138-1142, 1150, 1232, 1261-1263, 1294, 1309, 1323-1330, 1355-1390, 1412-1471

**Major Uncovered Regions**:

1. **Lines 197-339**: `RoutineAnalysisCache` class
   - Purpose: Caching/incremental variable analysis
   - Used for IDE-like scenarios, not batch transpilation
   
2. **Lines 1355-1471**: Advanced variable analysis helpers
   - Transitive closure computation
   - By-reference parameter tracking

**Category**: [NEEDS RESEARCH]
- `RoutineAnalysisCache` looks like Category C (IDE feature, not codegen)
- Some analysis features may be Category B (could improve codegen)

**Resolution**: [TBD]

---

#### AN3: `analysis/for_analysis.py` (61% coverage)

**Uncovered Lines**: 28, 53, 59, 66-69, 117-149, 121-122, 128-130, 132-145, 155, 181, 186, 196-198, 202-209, 214-223, 229, 232-233, 239, 259-271, 303-324, 332, 335-338, 342, 370-371, 425-438, 432-438, 445

**Code Purpose**: FOR loop analysis utilities

**Analysis**:
- Many helpers for analyzing FOR loop behavior
- `_check_var_passed_byref_in_scope()` - byref parameter tracking
- `_check_quit_in_scope()` - quit detection

**Category**: [NEEDS RESEARCH]
- FOR loop analysis is used by codegen for loop optimization
- Need to determine which parts codegen actually uses vs. dead

**Resolution**: [TBD]

---

#### AN4: `analysis/goto_analysis.py` (81% coverage)

**Uncovered Lines**: 44, 136-122, 148-122, 162, 173, 235-240, 252-255, 307-315, 341-338, 360-373, 432-438, 451-457, 519, 548, 575

**Code Purpose**: GOTO classification and control flow analysis

**Analysis**:
- Edge cases in GOTO classification
- Some patterns not exercised by tests

**Category**: [NEEDS RESEARCH]
- GOTO analysis is actively used by codegen
- Gaps may be edge cases that need test coverage

**Resolution**: [TBD]

---

#### AN5: `analysis/pattern_compiler.py` (70% coverage)

**Uncovered Lines**: 70-82, 112, 138, 165-167, 204-205, 210, 213, 216, 226, 236, 245-246, 255, 265, 282-285, 311-312, 313-272, 320, 323, 325, 351, 354, 358-366

**Code Purpose**: Compile MUMPS patterns to Python regex

**Analysis**:
- Pattern alternation handling
- Edge cases in pattern compilation

**Category**: [NEEDS RESEARCH]
- Pattern matching is used by codegen
- Need to check if gaps are missing tests or dead paths

**Resolution**: [TBD]

---

#### AN6: `analysis/resolver.py` (68% coverage)

**Uncovered Lines**: 176-189, 201-214, 252, 262-264

**Code Purpose**: Resolve label/routine references in ASG

**Analysis**:
- Edge cases in reference resolution
- External routine resolution paths

**Category**: [NEEDS RESEARCH]
- Reference resolution is core to codegen
- Gaps may need codegen test coverage

**Resolution**: [TBD]

---

## Research Tasks

### Phase 1: Quick Categorization

For each gap, determine preliminary category by:
1. Checking if the code has clear debugging/IDE purpose → Category C candidate
2. Checking if codegen imports/uses the code → Category A/B
3. Checking if tests exist elsewhere → May just need codegen test

### Phase 2: Detailed Analysis

For Category A candidates:
- What MUMPS feature is this supporting?
- What codegen test would exercise it?

For Category B candidates:
- How could codegen use this better?
- What would the improvement be?

For Category C candidates:
- Does removing this break anything?
- Is there devops/debugging value to keep?

### Phase 3: Resolution Planning

Create specific tasks for each resolution:
- A: Add codegen test for feature
- B: Refactor codegen to use analysis
- C: Remove code (verify no dependencies first)

---

## Findings Log

### 2026-01-20: Initial Inventory

Created inventory of all coverage gaps across parser/asg/analysis layers.

### 2026-01-20: Final Research Complete

#### Category C (Dead Code - Remove)

| Code Region | Coverage | Rationale |
|-------------|----------|-----------|
| `parser/exceptions.py` (lines 32-55, 85-90) | 14% | Error formatting only triggered during parse, before codegen runs |
| `asg/elements.py` to_dict() (lines 84-150) | 56% | Serialization for debugging/inspection only |
| `parser/textx_classes.py` __repr__ methods | 68% | Debugging only - not used by codegen |
| `analysis/variables.py` RoutineAnalysisCache (lines 174-339) | 70% | IDE-like caching for incremental updates, not batch codegen |
| `parser/parser.py` classify_for_patterns() (lines 569-609, 848-933) | 70% | Only called from tests, not part of transpilation pipeline |
| `parser/line_parser.py` detect_quit_after_for, extract_for_commands, classify_for_command | 39% | Exported but NOT used by codegen - only by tests |
| `analysis/resolver.py` utility functions (lines 184-214) | 68% | get_all_labels(), get_all_routines() - exported but unused |

**Note**: Category C items should use `# pragma: no cover` exclusions rather than deletion where they have debugging/devops value. Exception formatting and RoutineAnalysisCache have clear intrinsic value. The classify_for_patterns API may be useful for tooling even if not used by codegen.

#### Category A (Missing Codegen Tests - Add Tests)

| Code Region | Coverage | Uncovered Patterns |
|-------------|----------|-------------------|
| `analysis/semantic_analyzer.py` | 68% | Indirect GOTO/DO (`G @X`, `D @Y^ROUTINE`), pattern compilation edge cases, offset expressions |
| `analysis/for_analysis.py` | 61% | Indirected loop vars (`F @X=1:1:10`), READ/KILL modifying loop var, pass-by-ref tracking |
| `analysis/goto_analysis.py` | 81% | MULTI_LOOP_EXIT, dynamic offset targets, cross-label GOTO |
| `analysis/resolver.py` external calls | 68% | External routine resolution (`D ^ROUTINE`, `G ^ROUTINE`) |

#### Category B (Codegen Improvement Opportunities)

| Code Region | Coverage | Optimization |
|-------------|----------|--------------|
| `analysis/pattern_compiler.py` | 70% | compiled_pattern stored but codegen re-compiles at runtime; could inline pre-compiled regex |

---

## Resolution Strategy

### Phase 1: Category C - Pragma Exclusions (~100 lines)

For code with debugging/intrinsic value, add `# pragma: no cover` exclusions:
1. `parser/exceptions.py` - error formatting
2. `asg/elements.py` - to_dict() serialization  
3. `parser/textx_classes.py` - __repr__ methods
4. `analysis/variables.py` - RoutineAnalysisCache

For code with questionable value, consider removal:
1. `parser/parser.py` classify_for_patterns() - test-only API
2. `parser/line_parser.py` FOR utilities - test-only, not used by codegen

### Phase 2: Category A - Add Codegen Tests (~50 lines)

Create targeted MUMPS test cases exercising:
1. Indirect GOTO/DO patterns
2. FOR loops with READ/KILL modification
3. External routine calls
4. MULTI_LOOP_EXIT goto patterns

### Phase 3: Category B - Codegen Optimization

Update codegen to use pre-compiled patterns from analysis instead of re-compiling at runtime:
1. `analysis/pattern_compiler.py` - stores `compiled_pattern` at analysis time
2. Codegen currently ignores this and re-compiles via runtime helper
3. Fix: Pass compiled regex through to generated code, eliminating dead analysis code
