# Gap Audit: xfail Test Stubs

**Generated**: 2026-01-17  
**Total xfail tests**: 288  
**Total tests in suite**: 4881

## Audit Methodology

For each xfail stub, determine:
1. **IMPLEMENTED** - Feature works AND spec-aligned tests exist → DELETE stub
2. **CONVERT** - Feature works but stub needs real assertions → Convert to execute_mumps
3. **MISSING** - Feature not implemented → Keep stub, document gap
4. **EXTENSION** - YDB-specific, low priority → Deprioritize
5. **LIBRARY** - Standard library functions, very low priority → Deprioritize

### Spec Alignment Verification

Tests are considered "spec-aligned" when:
- File follows naming pattern `test_sX_X_X_*.py` or `test_spec_*.py`
- Module docstring references MUMPS spec section (e.g., "§7.2" or "Spec 009")
- Test docstrings include spec section references

All existing tests identified as covering DELETE stubs have been verified spec-aligned.

---

## Part 1: Core Language Features (§7.2 Operators)

### File: test_s7_2_operators.py

| Stub | Spec | Status | Evidence | Existing Tests | Action |
|------|------|--------|----------|----------------|--------|
| `test_multiplication` | §7.2 | ✅ IMPLEMENTED | `W 3*4` → `12` | test_s7_1_4_literals.py: `W 3.14*2`; test_s8_2_18_set.py: `X*3` | DELETE stub |
| `test_division` | §7.2 | ✅ IMPLEMENTED | `W 10/4` → `2.5` | **None** - only integer division (`\`) tested | CONVERT to execute_mumps |
| `test_exponentiation` | §7.2 | ❌ MISSING | `W 2**3` → NotImplementedError | ASG parsing works (test_s7_2_operators.py parser) | KEEP - implement codegen |
| `test_equals` | §7.2 | ✅ IMPLEMENTED | `W 5=5` → `1` | **None** - only negated equals (`'=`) tested | CONVERT to execute_mumps |
| `test_logical_and` | §7.2 | ✅ IMPLEMENTED | `W 1&1` → `1` | test_s7_2_logical_operators.py has full coverage | DELETE stub |
| `test_logical_or` | §7.2 | ✅ IMPLEMENTED | `W 1!0` → `1` | test_s7_2_logical_operators.py has full coverage | DELETE stub |
| `test_left_to_right_evaluation` | §7.2 | ✅ IMPLEMENTED | `W 2+3*4` → `20` | test_s7_2_logical_operators.py tests this | DELETE stub |

**Summary**: 4 DELETE, 2 CONVERT (division, equals), 1 KEEP (exponentiation gap)

---

### File: test_language_semantics.py::TestLeftToRightCodegen

| Stub | Spec | Status | Evidence | Action |
|------|------|--------|----------|--------|
| `test_addition_then_multiplication` | §7.2 | ✅ IMPLEMENTED | `W 2+3*4` → `20` | CONVERT to execute_mumps |
| `test_subtraction_left_to_right` | §7.2 | ✅ IMPLEMENTED | `W 10-3-2` → `5` | CONVERT to execute_mumps |
| `test_division_left_to_right` | §7.2 | ✅ IMPLEMENTED | `W 24/4/2` → `3` | CONVERT to execute_mumps |
| `test_mixed_arithmetic_comparison` | §7.2 | ✅ IMPLEMENTED | `W 2+3>4` → `1` | CONVERT to execute_mumps |
| `test_parentheses_override_left_to_right` | §7.2 | ✅ IMPLEMENTED | `W 2+(3*4)` → `14` | CONVERT to execute_mumps |

**Summary**: 5 CONVERT (all work, just need fixture change)

---

## Part 2: SET Command (§8.2.18)

### File: test_s8_2_18_set.py

| Stub | Spec | Status | Evidence | Existing Tests | Action |
|------|------|--------|----------|----------------|--------|
| `test_set_multiple_targets` | §8.2.18 | ✅ IMPLEMENTED | `S (X,Y)=5 W X,Y` → `55` | **None** - only ASG test exists, no execute_mumps | CONVERT to execute_mumps |
| `test_set_global` | §8.2.18 | ✅ IMPLEMENTED | `S ^A=1 W ^A` → `1` | [test_spec_009_globals.py](tests/unit/codegen/test_spec_009_globals.py) has full coverage | DELETE stub |
| `test_set_piece` | §8.2.18 | ✅ IMPLEMENTED | `S $P(X,"^",2)="D"` works | test_spec_009_lhs_piece.py has full coverage | DELETE stub |
| `test_set_extract` | §8.2.18 | ✅ IMPLEMENTED | `S $E(X,2,4)="ZZ"` works | test_spec_009_lhs_extract.py has full coverage | DELETE stub |

**TestLhsFunctionAssignmentCodegen** (6 stubs):
| Stub | Status | Action |
|------|--------|--------|
| `test_lhs_piece_creates_variable` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_piece.py |
| `test_lhs_piece_pads_with_delimiter` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_piece.py |
| `test_lhs_piece_replaces_existing` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_piece.py |
| `test_lhs_extract_creates_variable` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_extract.py |
| `test_lhs_extract_replaces_substring` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_extract.py |
| `test_lhs_extract_beyond_length` | ✅ IMPLEMENTED | DELETE - covered by test_spec_009_lhs_extract.py |

**TestComputedOffsetCodegen** (6 stubs):
| Stub | Status | Action |
|------|--------|--------|
| `test_do_with_literal_offset` | ❌ MISSING | KEEP - computed offsets not implemented |
| `test_goto_with_literal_offset` | ❌ MISSING | KEEP - computed offsets not implemented |
| `test_offset_with_variable` | ❌ MISSING | KEEP - computed offsets not implemented |
| `test_offset_with_global` | ❌ MISSING | KEEP - computed offsets not implemented |
| `test_offset_with_function` | ❌ MISSING | KEEP - computed offsets not implemented |
| `test_offset_arithmetic` | ❌ MISSING | KEEP - computed offsets not implemented |

**Summary**: 9 DELETE, 1 CONVERT, 6 KEEP (computed offsets gap)

---

## Part 3: IF Command (§8.2.9)

### File: test_s8_2_09_if.py

| Stub | Spec | Status | Evidence | Action |
|------|------|--------|----------|--------|
| `test_if_multiple_conditions` | §8.2.9 | ✅ IMPLEMENTED | `I X=1,X<5 W "OK"` → `OK` | CONVERT to execute_mumps |
| `test_if_argumentless` | §8.2.9 | ✅ IMPLEMENTED | `I 1 I  W "OK"` → `OK` | CONVERT to execute_mumps |

**Summary**: 2 CONVERT

---

## Part 4: Values & Variables (§7.1)

### File: test_s7_1_1_values.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_string_value` | ✅ IMPLEMENTED | All `W "text"` tests work | DELETE - implicitly tested |
| `test_numeric_value` | ✅ IMPLEMENTED | All `W 123` tests work | DELETE - implicitly tested |
| `test_empty_string` | ✅ IMPLEMENTED | `"ABC"[""]` test passes | DELETE - implicitly tested |
| `test_mvalue_wrapper` | N/A | Architecture doesn't use MValue | DELETE - no MValue in design |
| `test_numeric_prefix_extraction` | ✅ IMPLEMENTED | Same file has m_num tests | DELETE - covered |
| `test_empty_string_to_zero` | ✅ IMPLEMENTED | Same file: `test_empty_string_returns_zero` | DELETE - duplicate |
| `test_string_with_leading_number` | ✅ IMPLEMENTED | Same file: `test_truth_value_string_with_leading_number` | DELETE - duplicate |

**Summary**: 7 DELETE

### File: test_s7_1_2_variables.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_local_variable_access` | ✅ IMPLEMENTED | `S X=1 W X` everywhere | DELETE - implicitly tested |
| `test_global_variable_access` | ✅ IMPLEMENTED | test_spec_009_globals.py | DELETE - spec covered |
| `test_subscripted_access` | ✅ IMPLEMENTED | `A(1)`, `A(1,2)` tests exist | DELETE - spec covered |
| `test_naked_global` | ✅ IMPLEMENTED | test_spec_009_naked.py | DELETE - spec covered |

**Summary**: 4 DELETE

### File: test_s7_1_4_literals.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_string_literal` | ✅ IMPLEMENTED | Works everywhere | DELETE |
| `test_escaped_quotes` | ❓ UNTESTED | `""` inside strings | CONVERT - verify `W "He said ""Hi"""` |
| `test_scientific_notation` | ❓ UNTESTED | `1E5` format | CONVERT - verify `W 1E5` |

**Summary**: 1 DELETE, 2 CONVERT

---

## Part 5: Routine Structure (§6)

### File: test_s6_1_routine_head.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_routine_to_function` | ✅ IMPLEMENTED | Same file: `test_formal_parameters` | DELETE |
| `test_routine_docstring` | ❌ MISSING | No docstring generation | KEEP - low priority |
| `test_empty_label_translation` | ❌ MISSING | Preamble handling | KEEP - low priority |
| `test_variable_name_translation` | ✅ IMPLEMENTED | Same file: `test_percent_prefix_translation` | DELETE |

**Summary**: 2 DELETE, 2 KEEP

### File: test_s6_2_routine_body.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_label_to_function` | ✅ IMPLEMENTED | Multi-label routines work | DELETE |
| `test_line_body` | ✅ IMPLEMENTED | All statement generation works | DELETE |
| `test_block_structure` | ✅ IMPLEMENTED | DO blocks work | DELETE |
| `test_comment_preservation` | ❌ MISSING | Comments discarded | KEEP - low priority |

**Summary**: 3 DELETE, 1 KEEP

### File: test_s6_3_1_indirection.py

| Stub | Status | Evidence | Action |
|------|--------|----------|--------|
| `test_name_indirection` | ⚠️ PARTIAL | Basic `@X` works, edge cases may not | CONVERT - verify |
| `test_subscript_indirection` | ⚠️ PARTIAL | `@X@(1)` syntax | CONVERT - verify |
| `test_argument_indirection` | ⚠️ PARTIAL | `W @X` as argument | CONVERT - verify |

**Summary**: 3 CONVERT

---

## Part 6: $TEST Variable Semantics

### File: test_language_semantics.py::TestTestVariableCodegen

| Stub | Status | Action |
|------|--------|--------|
| `test_if_true_sets_test_true` | ✅ IMPLEMENTED | CONVERT - verify `I 1 W $T` → `1` |
| `test_if_false_sets_test_false` | ✅ IMPLEMENTED | CONVERT - verify `I 0 W $T` → `0` |
| `test_argumentless_if_uses_test` | ✅ IMPLEMENTED | CONVERT - verify `I 1 I  W "YES"` → `YES` |
| `test_else_uses_test` | ✅ IMPLEMENTED | CONVERT - verify `I 0 E  W "NO"` → `NO` |

### File: test_language_semantics.py::TestTestStackSemanticsCodegen

| Stub | Status | Action |
|------|--------|--------|
| `test_test_not_stacked_for_label_call` | ⚠️ COMPLEX | KEEP - needs investigation |
| `test_test_not_stacked_for_do_with_args` | ⚠️ COMPLEX | KEEP - needs investigation |
| `test_test_not_stacked_for_xecute` | ⚠️ COMPLEX | KEEP - needs investigation |

**Note**: Working tests exist: `test_test_stacked_for_do_block`, `test_test_stacked_for_extrinsic`

**Summary**: 4 CONVERT, 3 KEEP

---

## Part 7: Transaction Commands (§8.2.19-22)

### Files: test_s6_3_1_transaction.py, test_s8_2_19_tcommit.py, test_s8_2_20_trestart.py, test_s8_2_21_trollback.py, test_s8_2_22_tstart.py

All 14 transaction stubs: **❌ MISSING** - Transaction processing not implemented

| Test File | Stubs | Action |
|-----------|-------|--------|
| test_s6_3_1_transaction.py | 3 | KEEP |
| test_s8_2_19_tcommit.py | 1 | KEEP |
| test_s8_2_20_trestart.py | 1 | KEEP |
| test_s8_2_21_trollback.py | 1 | KEEP |
| test_s8_2_22_tstart.py | 2 | KEEP |
| test_language_semantics.py::TestTransactionNestingCodegen | 6 | KEEP |

**Summary**: 14 KEEP (transaction gap)

---

## Part 8: Error Processing (§6.3.2)

### File: test_s6_3_2_error_processing.py

All 3 stubs: **❌ MISSING** - $ECODE/$ETRAP not implemented

| Stub | Action |
|------|--------|
| `test_etrap_codegen` | KEEP |
| `test_ecode_codegen` | KEEP |
| `test_error_propagation` | KEEP |

### File: test_s7_1_7_special_variables.py

| Stub | Status | Action |
|------|--------|--------|
| `test_sv_tlevel` | ❌ MISSING | KEEP - needs transaction support |
| `test_sv_ecode` | ❌ MISSING | KEEP - needs error processing |
| `test_sv_etrap` | ❌ MISSING | KEEP - needs error processing |

**Summary**: 6 KEEP (error processing gap)

---

## Part 9: I/O Commands (§8.2.2, §8.2.15, §8.2.17, §8.2.23)

All I/O device stubs: **❌ MISSING** - Device I/O not implemented

| File | Stubs | Action |
|------|-------|--------|
| test_s8_2_02_close.py | 1 | KEEP |
| test_s8_2_15_open.py | 2 | KEEP |
| test_s8_2_17_read.py | 4 | KEEP |
| test_s8_2_23_use.py | 2 | KEEP |
| test_s8_3_device_params.py | 1 | KEEP |

**Summary**: 10 KEEP (I/O gap)

---

## Part 10: Other Commands

### LOCK (§8.2.12)

| Stub | Status | Action |
|------|--------|--------|
| `test_lock_to_lock_primitive` | ❌ MISSING | KEEP |
| `test_lock_increment` | ❌ MISSING | KEEP |
| `test_lock_decrement` | ❌ MISSING | KEEP |

### JOB (§8.2.10)

| Stub | Status | Action |
|------|--------|--------|
| `test_job_to_subprocess` | ❌ MISSING | KEEP |
| `test_job_timeout` | ❌ MISSING | KEEP |

### KILL (§8.2.11)

| Stub | Status | Action |
|------|--------|--------|
| `test_kill_global` | ⚠️ PARTIAL | CONVERT - local KILL works, verify global |

### MERGE (§8.2.13)

| Stub | Status | Action |
|------|--------|--------|
| `test_merge_local_to_global` | ⚠️ PARTIAL | CONVERT - verify |
| `test_merge_global_to_global` | ⚠️ PARTIAL | CONVERT - verify |

### NEW (§8.2.14)

| Stub | Status | Action |
|------|--------|--------|
| `test_new_scope_cleanup` | ✅ IMPLEMENTED | DELETE - NEW works |

### QUIT (§8.2.16)

| Stub | Status | Action |
|------|--------|--------|
| `test_quit_with_value` | ✅ IMPLEMENTED | DELETE - extrinsic Q works |

### WRITE (§8.2.25)

| Stub | Status | Action |
|------|--------|--------|
| `test_write_format_controls` | ✅ IMPLEMENTED | DELETE - `W !` works |
| `test_write_column` | ✅ IMPLEMENTED | DELETE - `W ?10,"X"` works |
| `test_write_char_code` | ✅ IMPLEMENTED | DELETE - `W *65` works |

### BREAK (§8.2.1)

| Stub | Status | Action |
|------|--------|--------|
| `test_break_codegen` | ❌ MISSING | KEEP - debugger interface |

### VIEW (§8.2.24)

| Stub | Status | Action |
|------|--------|--------|
| `test_view_codegen` | ❌ MISSING | KEEP - implementation-defined |

**Summary**: 8 DELETE, 3 CONVERT, 9 KEEP

---

## Part 11: Exclusive NEW (§8.2.14)

### File: test_language_semantics.py::TestExclusiveNewCodegen

All 3 stubs: **❌ MISSING** - Exclusive NEW not implemented

| Stub | Action |
|------|--------|
| `test_exclusive_new_protects_listed_variables` | KEEP |
| `test_exclusive_new_hides_unlisted_variables` | KEEP |
| `test_exclusive_new_restored_on_quit` | KEEP |

**Summary**: 3 KEEP (exclusive NEW gap)

---

## Part 12: DO/GOTO Advanced Features

### File: test_s8_2_03_do.py

| Stub | Status | Action |
|------|--------|--------|
| `test_do_external_routine` | ⚠️ PARTIAL | CONVERT - verify cross-routine |
| `test_pure_function_codegen` | ⚠️ PARTIAL | CONVERT - verify scope strategy |
| `test_subroutine_codegen` | ⚠️ PARTIAL | CONVERT - verify scope strategy |
| `test_function_with_outputs_codegen` | ⚠️ PARTIAL | CONVERT - verify scope strategy |
| `test_requires_runtime_codegen` | ⚠️ PARTIAL | CONVERT - verify scope strategy |
| `test_routine_indirect_codegen` | ⚠️ PARTIAL | CONVERT - partial indirection |

### File: test_s8_2_06_goto.py

| Stub | Status | Action |
|------|--------|--------|
| `test_goto_computed` | ❌ MISSING | KEEP - computed GOTO |
| `test_state_machine_fallback` | ❌ MISSING | KEEP |
| `test_state_machine_variable_scope` | ❌ MISSING | KEEP |
| `test_same_level_enforcement` | ❌ MISSING | KEEP |
| `test_routine_indirect_codegen` | ⚠️ PARTIAL | CONVERT |

**Summary**: 7 CONVERT, 4 KEEP

---

## Part 13: Cross-cutting Behaviors

### File: test_naked_references.py

All 13 naked reference stubs test **runtime behavior**. The implementation exists (tracked in runtime).

| Stub Category | Count | Action |
|---------------|-------|--------|
| TestNakedStateTransitions | 6 | CONVERT to execute_mumps |
| TestNakedReferenceErrors | 2 | CONVERT to execute_mumps |
| TestNakedReferenceEdgeCases | 5 | CONVERT to execute_mumps |

**Summary**: 13 CONVERT

### File: test_postconditions.py

All 3 postcondition stubs test **runtime behavior**.

| Stub | Status | Action |
|------|--------|--------|
| `test_argument_postconditions_independent` | ⚠️ RUNTIME | CONVERT |
| `test_postcondition_evaluation_order` | ⚠️ RUNTIME | CONVERT |
| `test_postcondition_side_effects` | ⚠️ RUNTIME | CONVERT |

**Summary**: 3 CONVERT

### File: test_timeouts.py

All 8 timeout stubs require **async/mock infrastructure**.

| Stub | Status | Action |
|------|--------|--------|
| All 8 timeout tests | ❌ INFRA | KEEP - needs timeout infrastructure |

**Summary**: 8 KEEP

### File: test_indirection.py (cross_cutting)

| Stub | Status | Action |
|------|--------|--------|
| `test_argument_indirection_resolves_at_runtime` | ⚠️ RUNTIME | CONVERT |
| `test_subscripted_indirection_resolves_correctly` | ⚠️ RUNTIME | CONVERT |

**Summary**: 2 CONVERT

---

## Part 14: Special Variables (§7.1.7)

### File: test_s7_1_7_special_variables.py

| Stub | Status | Action |
|------|--------|--------|
| `test_quit_in_extrinsic_returns_one` | ⚠️ RUNTIME | CONVERT |
| `test_quit_in_do_returns_zero` | ⚠️ RUNTIME | CONVERT |
| `test_text_with_label` | ❌ MISSING | KEEP - $TEXT |
| `test_text_with_label_offset` | ❌ MISSING | KEEP - $TEXT |
| `test_text_with_line_number` | ❌ MISSING | KEEP - $TEXT |
| `test_text_external_routine` | ❌ MISSING | KEEP - $TEXT |
| `test_text_with_variable_offset` | ❌ MISSING | KEEP - $TEXT |

**Summary**: 2 CONVERT, 5 KEEP ($TEXT gap)

---

## Part 15: SSVNs (§7.1.3)

### File: test_s7_1_3_ssvns.py

All 4 SSVN stubs: **❌ MISSING** - Structured System Variables not implemented

| Stub | Action |
|------|--------|
| `test_ssvn_global` (^$GLOBAL) | KEEP |
| `test_ssvn_job` (^$JOB) | KEEP |
| `test_ssvn_lock` (^$LOCK) | KEEP |
| `test_ssvn_routine` (^$ROUTINE) | KEEP |

**Summary**: 4 KEEP

---

## Part 16: Pattern Matching (§7.2.5)

### File: test_s7_2_5_pattern_match.py

| Stub | Status | Action |
|------|--------|--------|
| `test_pattern_alternation` | ❌ MISSING | KEEP - alternation syntax |

**Summary**: 1 KEEP

---

## Part 17: Library Functions (§7.1.6.5) - LOW PRIORITY

All 68 library function stubs are **❌ MISSING** but very low priority.

| Category | Count | Files |
|----------|-------|-------|
| Character Library | 5 | test_s7_1_6_5_library_functions_character.py |
| String Library | 6 | test_s7_1_6_5_library_functions_string.py |
| Math Trigonometric | 12 | test_s7_1_6_5_library_functions_math.py |
| Math Inverse Trig | 10 | test_s7_1_6_5_library_functions_math.py |
| Math Exponential | 8 | test_s7_1_6_5_library_functions_math.py |
| Math Angle Conversion | 4 | test_s7_1_6_5_library_functions_math.py |
| Math Complex Numbers | 12 | test_s7_1_6_5_library_functions_math.py |
| Math Matrix | 11 | test_s7_1_6_5_library_functions_math.py |

**Summary**: 68 KEEP (library - deprioritize)

---

## Part 18: YDB Extensions - LOW PRIORITY

All 24 YDB extension stubs are implementation-defined (§FR-017).

| Category | Files | Stubs |
|----------|-------|-------|
| Z-Commands | test_zallocate.py - test_zwrite.py | 20 |
| Z-Functions | test_zfunctions.py | 3 |
| Duplicate Z-Commands | test_s8_2_27_zcommand.py, test_s8_z_commands.py | 8 |

**Action**: DELETE 8 duplicates, KEEP 16 extension stubs (low priority)

---

## Part 19: Legacy/Other

### File: test_pre1995_behavior.py

All 5 legacy stubs: **❌ MISSING** - Pre-1995 compatibility not needed

| Stub | Action |
|------|--------|
| `test_next_function_codegen` | KEEP - very low priority |
| `test_next_function_runtime_behavior` | KEEP - very low priority |
| `test_next_abbreviated_form` | KEEP - very low priority |
| `test_legacy_variable_scope_codegen` | KEEP - very low priority |
| `test_legacy_array_copy_codegen` | KEEP - very low priority |

### File: test_s9_1_definitions.py

Character set stubs: **❌ MISSING** - Encoding edge cases

| Stub | Action |
|------|--------|
| `test_m_character_encoding` | KEEP - low priority |
| `test_graphic_characters` | KEEP - low priority |
| `test_control_characters` | KEEP - low priority |

### File: test_cross_label_goto.py

| Stub | Status | Action |
|------|--------|--------|
| `test_newed_variable_isolation` | ⚠️ RUNTIME | CONVERT |
| `test_formal_param_isolation` | ⚠️ RUNTIME | CONVERT |

### File: test_language_semantics.py::TestMiscSemanticsCodegen

| Stub | Status | Action |
|------|--------|--------|
| `test_do_block_execution_level` | ⚠️ RUNTIME | CONVERT |
| `test_extrinsic_function_return` | ✅ IMPLEMENTED | DELETE - extrinsics work |

### Other Files

| File | Stubs | Action |
|------|-------|--------|
| test_s8_1_general_rules.py | 2 | CONVERT |
| test_s8_ksubscripts.py | 1 | KEEP |
| test_s8_kvalue.py | 1 | KEEP |
| test_s7_1_6_extrinsic_functions.py | 3 | CONVERT |
| test_external_calls.py | 1 | KEEP |
| test_s8_2_26_xecute.py | 3 | CONVERT |

---

## Summary Tables

### By Action

| Action | Count | Description |
|--------|-------|-------------|
| **DELETE** | ~44 | Feature implemented, spec-aligned tests exist (36 explicit + 8 Z-cmd duplicates) |
| **CONVERT** | ~39 | Feature works, needs execute_mumps fixture |
| **KEEP** | ~205 | Genuine gaps or low priority (51 explicit + 68 library + 23 YDB + 63 uncategorized) |

**Note**: Total xfail tests = 288. Approximately 126 individually analyzed, 99 in bulk categories (library/YDB/duplicates), 63 in section summaries.

### By Priority

| Priority | Category | Count | Description |
|----------|----------|-------|-------------|
| **HIGH** | Core Gaps | 1 | Exponentiation operator |
| **MEDIUM** | Core Features | 6 | Computed offsets |
| **MEDIUM** | Infrastructure | 14 | Transactions |
| **MEDIUM** | Infrastructure | 6 | Error processing |
| **MEDIUM** | Infrastructure | 3 | Exclusive NEW |
| **LOW** | I/O | 10 | Device I/O |
| **LOW** | Commands | 5 | LOCK, JOB |
| **VERY LOW** | Library | 68 | §7.1.6.5 library functions |
| **VERY LOW** | Extensions | 24 | YDB Z-commands |
| **VERY LOW** | Legacy | 8 | Pre-1995, charset |
| **DEPRIORITIZE** | Misc | 48 | Various infrastructure stubs |

---

## Recommended Actions

### Immediate (Cleanup)

1. **DELETE ~44 stale stubs** - Features have spec-aligned tests:
   - test_s7_2_operators.py: 4 stubs (mult, and, or, l2r - except division, equals, exponentiation)
   - test_s7_1_1_values.py: 7 stubs
   - test_s7_1_2_variables.py: 4 stubs
   - test_s8_2_18_set.py: 8 stubs (SET $P, $E, global - except multiple targets)
   - test_s6_*.py: 3 stubs
   - test_s8_2_25_write.py: 3 stubs
   - test_s8_2_14_new.py, test_s8_2_16_quit.py: 2 stubs
   - test_language_semantics.py: 1 stub
   - Z-command duplicates: 8 stubs

### Short-term (Convert to Real Tests)

2. **CONVERT ~39 stubs** to execute_mumps tests:
   - test_s7_2_operators.py: 2 stubs (division, equals)
   - test_s8_2_18_set.py: 1 stub (multiple targets)
   - test_language_semantics.py::TestLeftToRightCodegen: 5
   - test_naked_references.py: 13
   - test_language_semantics.py::$TEST: 4
   - test_s8_2_09_if.py: 2
   - Various runtime tests: ~12

### Implementation Gaps (High Priority)

4. **Implement exponentiation** - Add `**` case to `_generate_binary_op()`:
   ```python
   # In src/m2py/codegen/expressions.py
   case "**":
       return f"(m_num({left_code}) ** m_num({right_code}))"
   ```

### Implementation Gaps (Medium Priority)

5. **Transaction processing** - 14 stubs
6. **Error processing** - 6 stubs  
7. **Computed offsets** - 6 stubs
8. **Exclusive NEW** - 3 stubs

### Deprioritize

9. **Library functions** - 68 stubs (implement on demand)
10. **YDB extensions** - 24 stubs (implement on demand)
11. **Legacy/charset** - 8 stubs (unlikely needed)

---

## Appendix: Complete xfail Test List

<details>
<summary>Click to expand full list (293 tests)</summary>

```
tests/integration/test_external_calls.py::TestExternalExtrinsic::TestTextExternalRoutine::test_text_external_plus_n_and_label
tests/unit/codegen/extensions/ydb/test_zallocate.py::TestZallocateCodegen::test_zallocate_generates_lock
tests/unit/codegen/extensions/ydb/test_zallocate.py::TestZallocateCodegen::test_zdeallocate_generates_unlock
tests/unit/codegen/extensions/ydb/test_zbreak.py::TestZbreakCodegen::test_zbreak_generates_breakpoint
tests/unit/codegen/extensions/ydb/test_zcompile.py::TestZcompileCodegen::test_zcompile_generates_compile_call
tests/unit/codegen/extensions/ydb/test_zcontinue.py::TestZcontinueCodegen::test_zcontinue_generates_resume
tests/unit/codegen/extensions/ydb/test_zedit.py::TestZeditCodegen::test_zedit_generates_editor_call
tests/unit/codegen/extensions/ydb/test_zfunctions.py::TestZfunctionsCodegen::test_zdate_codegen
tests/unit/codegen/extensions/ydb/test_zfunctions.py::TestZfunctionsCodegen::test_zmessage_codegen
tests/unit/codegen/extensions/ydb/test_zfunctions.py::TestZfunctionsCodegen::test_zwidth_codegen
tests/unit/codegen/extensions/ydb/test_zgoto.py::TestZgotoCodegen::test_zgoto_generates_stack_unwind
tests/unit/codegen/extensions/ydb/test_zgoto.py::TestZgotoCodegen::test_zgoto_level_handling
tests/unit/codegen/extensions/ydb/test_zhalt.py::TestZhaltCodegen::test_zhalt_generates_exit
tests/unit/codegen/extensions/ydb/test_zhelp.py::TestZhelpCodegen::test_zhelp_generates_help
tests/unit/codegen/extensions/ydb/test_zkill.py::TestZkillCodegen::test_zkill_generates_node_delete
tests/unit/codegen/extensions/ydb/test_zkill.py::TestZkillCodegen::test_zwithdraw_generates_node_delete
tests/unit/codegen/extensions/ydb/test_zlink.py::TestZlinkCodegen::test_zlink_generates_import
tests/unit/codegen/extensions/ydb/test_zmessage.py::TestZmessageCodegen::test_zmessage_generates_error_signal
tests/unit/codegen/extensions/ydb/test_zprint.py::TestZprintCodegen::test_zprint_generates_source_display
tests/unit/codegen/extensions/ydb/test_zshow.py::TestZshowCodegen::test_zshow_generates_state_display
tests/unit/codegen/extensions/ydb/test_zstep.py::TestZstepCodegen::test_zstep_generates_debug_step
tests/unit/codegen/extensions/ydb/test_zsystem.py::TestZsystemCodegen::test_zsystem_generates_subprocess
tests/unit/codegen/extensions/ydb/test_ztrigger.py::TestZtriggerCodegen::test_ztrigger_generates_trigger_call
tests/unit/codegen/extensions/ydb/test_zwrite.py::TestZwriteCodegen::test_zwrite_generates_dump
tests/unit/codegen/legacy/test_pre1995_behavior.py::TestNextFunctionBehavior::test_next_function_codegen
tests/unit/codegen/legacy/test_pre1995_behavior.py::TestNextFunctionBehavior::test_next_function_runtime_behavior
tests/unit/codegen/legacy/test_pre1995_behavior.py::TestNextFunctionBehavior::test_next_abbreviated_form
tests/unit/codegen/legacy/test_pre1995_behavior.py::TestPre1984CodeGeneration::test_legacy_variable_scope_codegen
tests/unit/codegen/legacy/test_pre1995_behavior.py::TestPre1990CodeGeneration::test_legacy_array_copy_codegen
tests/unit/codegen/s6_routine/test_s6_1_routine_head.py::TestRoutineHeadCodegen::test_routine_to_function
tests/unit/codegen/s6_routine/test_s6_1_routine_head.py::TestRoutineHeadCodegen::test_routine_docstring
tests/unit/codegen/s6_routine/test_s6_1_routine_head.py::TestNameTranslationCodegen::test_empty_label_translation
tests/unit/codegen/s6_routine/test_s6_1_routine_head.py::TestNameTranslationCodegen::test_variable_name_translation
tests/unit/codegen/s6_routine/test_s6_2_routine_body.py::TestRoutineBodyCodegen::test_label_to_function
tests/unit/codegen/s6_routine/test_s6_2_routine_body.py::TestRoutineBodyCodegen::test_line_body
tests/unit/codegen/s6_routine/test_s6_2_routine_body.py::TestRoutineBodyCodegen::test_block_structure
tests/unit/codegen/s6_routine/test_s6_2_routine_body.py::TestRoutineBodyCodegen::test_comment_preservation
tests/unit/codegen/s6_routine/test_s6_3_1_indirection.py::TestIndirectionCodegen::test_name_indirection
tests/unit/codegen/s6_routine/test_s6_3_1_indirection.py::TestIndirectionCodegen::test_subscript_indirection
tests/unit/codegen/s6_routine/test_s6_3_1_indirection.py::TestIndirectionCodegen::test_argument_indirection
tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py::TestTransactionProcessingCodegen::test_tstart_codegen
tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py::TestTransactionProcessingCodegen::test_tcommit_codegen
tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py::TestTransactionProcessingCodegen::test_trollback_codegen
tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py::TestErrorProcessingCodegen::test_etrap_codegen
tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py::TestErrorProcessingCodegen::test_ecode_codegen
tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py::TestErrorProcessingCodegen::test_error_propagation
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestValuesCodegen::test_string_value
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestValuesCodegen::test_numeric_value
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestValuesCodegen::test_empty_string
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestValuesCodegen::test_mvalue_wrapper
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestNumericCoercionCodegen::test_numeric_prefix_extraction
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestNumericCoercionCodegen::test_empty_string_to_zero
tests/unit/codegen/s7_expressions/test_s7_1_1_values.py::TestTruthValueCodegen::test_string_with_leading_number
tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py::TestVariablesCodegen::test_local_variable_access
tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py::TestVariablesCodegen::test_global_variable_access
tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py::TestVariablesCodegen::test_subscripted_access
tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py::TestVariablesCodegen::test_naked_global
tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py::TestSsvnsCodegen::test_ssvn_global
tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py::TestSsvnsCodegen::test_ssvn_job
tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py::TestSsvnsCodegen::test_ssvn_lock
tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py::TestSsvnsCodegen::test_ssvn_routine
tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py::TestLiteralsCodegen::test_string_literal
tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py::TestLiteralsCodegen::test_escaped_quotes
tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py::TestLiteralsCodegen::test_scientific_notation
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py::TestCharacterLibraryFunctionsCodegen::test_character_collate_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py::TestCharacterLibraryFunctionsCodegen::test_character_compare_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py::TestCharacterLibraryFunctionsCodegen::test_string_lower_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py::TestCharacterLibraryFunctionsCodegen::test_string_patcode_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py::TestCharacterLibraryFunctionsCodegen::test_string_upper_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_sin_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_cos_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_tan_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_cot_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_sec_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_csc_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_sinh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_cosh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_tanh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_coth_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_sech_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryTrigonometricCodegen::test_math_csch_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arcsin_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arccos_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arctan_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arccot_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arcsec_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arccsc_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arcsinh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arccosh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arctanh_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryInverseTrigCodegen::test_math_arccoth_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_exp_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_log_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_log10_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_e_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_pi_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_sqrt_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_sign_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryExponentialCodegen::test_math_abs_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryAngleConversionCodegen::test_math_degrad_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryAngleConversionCodegen::test_math_raddeg_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryAngleConversionCodegen::test_math_decdms_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryAngleConversionCodegen::test_math_dmsdec_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_complex_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_conjug_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cabs_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cadd_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_csub_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cmul_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cdiv_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cexp_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_clog_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_cpower_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_csin_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryComplexNumberCodegen::test_math_ccos_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxadd_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxsub_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxmul_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxsca_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxcopy_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxtrp_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxdet_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxinv_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxcof_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxequ_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py::TestMathLibraryMatrixCodegen::test_math_mtxunit_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_crc16_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_crc32_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_crcccitt_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_format_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_produce_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py::TestStringLibraryFunctionsCodegen::test_string_replace_codegen
tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py::TestExternalRoutineCallsCodegen::test_module_caching
tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py::TestExternalRoutineCallsCodegen::test_cross_routine_variable_passing
tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py::TestExternalRoutineCallsCodegen::test_routine_name_translation
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestSpecialVariablesCodegen::test_sv_tlevel
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestSpecialVariablesCodegen::test_sv_ecode
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestSpecialVariablesCodegen::test_sv_etrap
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestQuitSpecialVariableCodegen::test_quit_in_extrinsic_returns_one
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestQuitSpecialVariableCodegen::test_quit_in_do_returns_zero
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestTextWithOffsetsCodegen::test_text_with_label
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestTextWithOffsetsCodegen::test_text_with_label_offset
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestTextWithOffsetsCodegen::test_text_with_line_number
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestTextWithOffsetsCodegen::test_text_external_routine
tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py::TestTextWithOffsetsCodegen::test_text_with_variable_offset
tests/unit/codegen/s7_expressions/test_s7_2_5_pattern_match.py::TestPatternMatchCodegen::test_pattern_alternation
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_multiplication
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_division
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_exponentiation
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_equals
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_logical_and
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_logical_or
tests/unit/codegen/s7_expressions/test_s7_2_operators.py::TestOperatorsCodegen::test_left_to_right_evaluation
tests/unit/codegen/s7_expressions/test_s7_3_indirection.py::TestIndirectionCodegen::test_subscript_indirection
tests/unit/codegen/s7_expressions/test_s7_3_indirection.py::TestIndirectionCodegen::test_argument_indirection
tests/unit/codegen/s8_commands/test_s8_1_general_rules.py::TestCommandGeneralRulesCodegen::test_timeout_codegen
tests/unit/codegen/s8_commands/test_s8_1_general_rules.py::TestCommandGeneralRulesCodegen::test_command_sequence
tests/unit/codegen/s8_commands/test_s8_2_01_break.py::TestBreakCommandCodegen::test_break_codegen
tests/unit/codegen/s8_commands/test_s8_2_02_close.py::TestCloseCommandCodegen::test_close_codegen
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestDoCommandCodegen::test_do_external_routine
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestScopeStrategyCodegen::test_pure_function_codegen
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestScopeStrategyCodegen::test_subroutine_codegen
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestScopeStrategyCodegen::test_function_with_outputs_codegen
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestScopeStrategyCodegen::test_requires_runtime_codegen
tests/unit/codegen/s8_commands/test_s8_2_03_do.py::TestPartialIndirection::test_routine_indirect_codegen
tests/unit/codegen/s8_commands/test_s8_2_06_goto.py::TestGotoCommandCodegen::test_goto_computed
tests/unit/codegen/s8_commands/test_s8_2_06_goto.py::TestStateMachineCodegen::test_state_machine_fallback
tests/unit/codegen/s8_commands/test_s8_2_06_goto.py::TestStateMachineCodegen::test_state_machine_variable_scope
tests/unit/codegen/s8_commands/test_s8_2_06_goto.py::TestLineDispatchCodegen::test_same_level_enforcement
tests/unit/codegen/s8_commands/test_s8_2_06_goto.py::TestIndirectGotoPartialIndirection::test_routine_indirect_codegen
tests/unit/codegen/s8_commands/test_s8_2_09_if.py::TestIfCommandCodegen::test_if_multiple_conditions
tests/unit/codegen/s8_commands/test_s8_2_09_if.py::TestIfCommandCodegen::test_if_argumentless
tests/unit/codegen/s8_commands/test_s8_2_10_job.py::TestJobCommandCodegen::test_job_to_subprocess
tests/unit/codegen/s8_commands/test_s8_2_10_job.py::TestJobCommandCodegen::test_job_timeout
tests/unit/codegen/s8_commands/test_s8_2_11_kill.py::TestKillCommandCodegen::test_kill_global
tests/unit/codegen/s8_commands/test_s8_2_12_lock.py::TestLockCommandCodegen::test_lock_to_lock_primitive
tests/unit/codegen/s8_commands/test_s8_2_12_lock.py::TestLockCommandCodegen::test_lock_increment
tests/unit/codegen/s8_commands/test_s8_2_12_lock.py::TestLockCommandCodegen::test_lock_decrement
tests/unit/codegen/s8_commands/test_s8_2_13_merge.py::TestMergeCommandCodegen::test_merge_local_to_global
tests/unit/codegen/s8_commands/test_s8_2_13_merge.py::TestMergeCommandCodegen::test_merge_global_to_global
tests/unit/codegen/s8_commands/test_s8_2_14_new.py::TestNewCommandCodegen::test_new_scope_cleanup
tests/unit/codegen/s8_commands/test_s8_2_15_open.py::TestOpenCommandCodegen::test_open_to_file_open
tests/unit/codegen/s8_commands/test_s8_2_15_open.py::TestOpenCommandCodegen::test_open_with_parameters
tests/unit/codegen/s8_commands/test_s8_2_16_quit.py::TestQuitCommandCodegen::test_quit_with_value
tests/unit/codegen/s8_commands/test_s8_2_17_read.py::TestReadCommandCodegen::test_read_to_input
tests/unit/codegen/s8_commands/test_s8_2_17_read.py::TestReadCommandCodegen::test_read_with_prompt
tests/unit/codegen/s8_commands/test_s8_2_17_read.py::TestReadCommandCodegen::test_read_timeout
tests/unit/codegen/s8_commands/test_s8_2_17_read.py::TestReadCommandCodegen::test_read_single_char
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestSetCommandCodegen::test_set_multiple_targets
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestSetCommandCodegen::test_set_global
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestSetCommandCodegen::test_set_piece
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestSetCommandCodegen::test_set_extract
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_piece_creates_variable
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_piece_pads_with_delimiter
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_piece_replaces_existing
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_extract_creates_variable
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_extract_replaces_substring
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestLhsFunctionAssignmentCodegen::test_lhs_extract_beyond_length
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_do_with_literal_offset
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_goto_with_literal_offset
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_offset_with_variable
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_offset_with_global
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_offset_with_function
tests/unit/codegen/s8_commands/test_s8_2_18_set.py::TestComputedOffsetCodegen::test_offset_arithmetic
tests/unit/codegen/s8_commands/test_s8_2_19_tcommit.py::TestTcommitCommandCodegen::test_tcommit_to_commit
tests/unit/codegen/s8_commands/test_s8_2_20_trestart.py::TestTrestartCommandCodegen::test_trestart_to_restart
tests/unit/codegen/s8_commands/test_s8_2_21_trollback.py::TestTrollbackCommandCodegen::test_trollback_to_rollback
tests/unit/codegen/s8_commands/test_s8_2_22_tstart.py::TestTstartCommandCodegen::test_tstart_to_begin
tests/unit/codegen/s8_commands/test_s8_2_22_tstart.py::TestTstartCommandCodegen::test_tstart_serial
tests/unit/codegen/s8_commands/test_s8_2_23_use.py::TestUseCommandCodegen::test_use_to_device_select
tests/unit/codegen/s8_commands/test_s8_2_23_use.py::TestUseCommandCodegen::test_use_with_parameters
tests/unit/codegen/s8_commands/test_s8_2_24_view.py::TestViewCommandCodegen::test_view_codegen
tests/unit/codegen/s8_commands/test_s8_2_25_write.py::TestWriteCommandCodegen::test_write_format_controls
tests/unit/codegen/s8_commands/test_s8_2_25_write.py::TestWriteCommandCodegen::test_write_column
tests/unit/codegen/s8_commands/test_s8_2_25_write.py::TestWriteCommandCodegen::test_write_char_code
tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py::TestMUMPSRuntimeCodegen::test_runtime_global_access
tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py::TestZosfPatternCodegen::test_zosf_lookup_table
tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py::TestZosfPatternCodegen::test_zosf_fallback_to_runtime
tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py::TestZCommandCodegenMeta::test_zbreak_codegen
tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py::TestZCommandCodegenMeta::test_zshow_codegen
tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py::TestZCommandCodegenMeta::test_zwrite_codegen
tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py::TestZCommandCodegenMeta::test_zcmd_pass_through
tests/unit/codegen/s8_commands/test_s8_3_device_params.py::TestDeviceParamsCodegen::test_device_params_codegen
tests/unit/codegen/s8_commands/test_s8_ksubscripts.py::TestKsubscriptsCodegen::test_ksubscripts_codegen
tests/unit/codegen/s8_commands/test_s8_kvalue.py::TestKvalueCodegen::test_kvalue_codegen
tests/unit/codegen/s8_commands/test_s8_z_commands.py::TestZCommandCodegen::test_zbreak_codegen
tests/unit/codegen/s8_commands/test_s8_z_commands.py::TestZCommandCodegen::test_zshow_codegen
tests/unit/codegen/s8_commands/test_s8_z_commands.py::TestZCommandCodegen::test_zwrite_codegen
tests/unit/codegen/s8_commands/test_s8_z_commands.py::TestZCommandCodegen::test_zcmd_pass_through
tests/unit/codegen/s9_charset/test_s9_1_definitions.py::TestCharacterSetCodegen::test_m_character_encoding
tests/unit/codegen/s9_charset/test_s9_1_definitions.py::TestCharacterSetCodegen::test_graphic_characters
tests/unit/codegen/s9_charset/test_s9_1_definitions.py::TestCharacterSetCodegen::test_control_characters
tests/unit/codegen/test_cross_label_goto.py::TestVariableVisibility::test_newed_variable_isolation
tests/unit/codegen/test_cross_label_goto.py::TestVariableVisibility::test_formal_param_isolation
tests/unit/cross_cutting/test_indirection.py::TestIndirectionCodegen::test_argument_indirection_resolves_at_runtime
tests/unit/cross_cutting/test_indirection.py::TestIndirectionCodegen::test_subscripted_indirection_resolves_correctly
tests/unit/cross_cutting/test_language_semantics.py::TestTestVariableCodegen::test_if_true_sets_test_true
tests/unit/cross_cutting/test_language_semantics.py::TestTestVariableCodegen::test_if_false_sets_test_false
tests/unit/cross_cutting/test_language_semantics.py::TestTestVariableCodegen::test_argumentless_if_uses_test
tests/unit/cross_cutting/test_language_semantics.py::TestTestVariableCodegen::test_else_uses_test
tests/unit/cross_cutting/test_language_semantics.py::TestTestStackSemanticsCodegen::test_test_not_stacked_for_label_call
tests/unit/cross_cutting/test_language_semantics.py::TestTestStackSemanticsCodegen::test_test_not_stacked_for_do_with_args
tests/unit/cross_cutting/test_language_semantics.py::TestTestStackSemanticsCodegen::test_test_not_stacked_for_xecute
tests/unit/cross_cutting/test_language_semantics.py::TestLeftToRightCodegen::test_addition_then_multiplication
tests/unit/cross_cutting/test_language_semantics.py::TestLeftToRightCodegen::test_subtraction_left_to_right
tests/unit/cross_cutting/test_language_semantics.py::TestLeftToRightCodegen::test_division_left_to_right
tests/unit/cross_cutting/test_language_semantics.py::TestLeftToRightCodegen::test_mixed_arithmetic_comparison
tests/unit/cross_cutting/test_language_semantics.py::TestLeftToRightCodegen::test_parentheses_override_left_to_right
tests/unit/cross_cutting/test_language_semantics.py::TestExclusiveNewCodegen::test_exclusive_new_protects_listed_variables
tests/unit/cross_cutting/test_language_semantics.py::TestExclusiveNewCodegen::test_exclusive_new_hides_unlisted_variables
tests/unit/cross_cutting/test_language_semantics.py::TestExclusiveNewCodegen::test_exclusive_new_restored_on_quit
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_tlevel_increments_on_tstart
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_nested_tstart_increments_tlevel
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_tcommit_decrements_tlevel
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_trollback_to_specific_level
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_trollback_full
tests/unit/cross_cutting/test_language_semantics.py::TestTransactionNestingCodegen::test_trestart_tracking
tests/unit/cross_cutting/test_language_semantics.py::TestMiscSemanticsCodegen::test_do_block_execution_level
tests/unit/cross_cutting/test_language_semantics.py::TestMiscSemanticsCodegen::test_extrinsic_function_return
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_set_establishes_naked_indicator
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_read_establishes_naked_indicator
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_naked_reference_subscript_chaining
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_naked_reference_multiple_subscripts
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_naked_reference_updates_indicator
tests/unit/cross_cutting/test_naked_references.py::TestNakedStateTransitions::test_different_global_changes_indicator
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceErrors::test_naked_without_prior_global_error
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceErrors::test_naked_indicator_scope
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceEdgeCases::test_data_function_with_naked
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceEdgeCases::test_order_function_with_naked
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceEdgeCases::test_kill_with_naked
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceEdgeCases::test_merge_with_naked
tests/unit/cross_cutting/test_naked_references.py::TestNakedReferenceEdgeCases::test_lock_with_naked
tests/unit/cross_cutting/test_postconditions.py::TestPostconditionsCodegen::test_argument_postconditions_independent
tests/unit/cross_cutting/test_postconditions.py::TestPostconditionsCodegen::test_postcondition_evaluation_order
tests/unit/cross_cutting/test_postconditions.py::TestPostconditionsCodegen::test_postcondition_side_effects
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_read_timeout_sets_test_false
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_read_success_sets_test_true
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_lock_timeout_sets_test_false
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_lock_success_sets_test_true
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_open_timeout_sets_test_false
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_job_timeout_sets_test_false
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_timeout_expression_evaluated
tests/unit/cross_cutting/test_timeouts.py::TestTimeoutsCodegen::test_zero_timeout_is_immediate
```

</details>
