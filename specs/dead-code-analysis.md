# Dead Code Analysis — Functional Test Coverage Gaps

Generated from functional test coverage run (`tests/functional/` only, 301 tests).
Overall coverage: 70% (3698 uncovered lines out of 14054 statements).

Each section identifies code NOT exercised by any functional test, with a determination
of whether it is live, dead, or deferred.

## Dead Code Removal Status

**✅ COMPLETE** — All identified dead code has been removed. 5582 tests pass (0 failures, 0 xfail, 0 skipped).

### Removals by module:

| Module | Lines Removed | Key Items |
|--------|--------------|-----------|
| parser/ | ~55 | `classify_for_patterns`, `ForPatternResult`, defensive guards, unused functions |
| analysis/ | ~185 | `RoutineAnalysisCache` (143 lines), `_push_scope`/`_pop_scope`, unused convenience functions |
| asg/ | ~38 | `MParseError.__str__`, `MScope.add_statement`, `has_body`/`has_then_scope`, unused properties |
| codegen/ | ~215 | `_generate_single_assignment_with_preeval` (75 lines), `_expr_references_vars` (29 lines), intrinsic guards, unused methods |
| core/ | ~145 | `VarRef` class (36 lines), `resolve_to_argument_list` (49 lines), `data`/`_data_subscripted`, unused functions |
| runtime/ | ~79 | `YottaDBGlobalStorage` stub, `IRISGlobalStorage` stub, `InMemory.incr`, `InMemory.kill_all`, dead branches |
| **Total** | **~682** | (excludes ~35 lines TYPE_CHECKING/Protocol stubs retained by design) |

### Items found to be LIVE during removal (originally marked DEAD):
- `codegen/__init__.py` `generate_python` name fallback — used by `execute_mumps` test fixtures
- `runtime/helpers.py` `m_format_output` float formatting — Python `**` with negative exponents produces floats
- `runtime/helpers.py` `_mumps_collation_key` final str() fallback — retained as safety net

## Decision Key

| Decision | Meaning |
|----------|---------|
| **LIVE** | Required by MUMPS spec or has clear runtime purpose; just not tested by functional suite |
| **DEAD** | No MUMPS input can reach this code, no callers in production, or no effect on output |
| **REMOVED** | Dead code successfully removed |
| **DEFERRED** | Limitation documented in limitations.md; partial implementation is correct |

---

## Summary

| Section | Uncovered (P1) | Removed (P1+P2) | Dead (P3) | LIVE | DEFERRED |
|---------|----------------|-----------------|-----------|------|----------|
| parser/ | 240 | ~55 | 0 | ~185 | ~3 |
| analysis/ | 814 | ~185 | ~51 | ~304 | ~325 |
| asg/ | 64 | ~38 | 0 | ~20 | ~6 |
| codegen/ | 1136 | ~215 | ~87 | ~891 | ~30 |
| core/ | 322 | ~145 | ~3 | ~177 | ~5 |
| runtime/ | 1122 | ~79 | ~38 | ~1043 | 0 |
| **Total** | **3698** | **~682** | **~179** | **~2620** | **~369** |

**Bottom line: ~682 lines removed (passes 1+2), ~179 lines identified for removal (pass 3),
~35 lines retained by design (TYPE_CHECKING/Protocol stubs), ~369 lines are deferred limitations.**

---

## parser/ (240 uncovered lines)

### `parser/parser.py` — 75% covered (94 uncovered lines)

#### `_structure_commands_with_bodies` — empty guard (L94) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Callers always pass non-empty lists from parsed MUMPS. The `analyze_command` filter removes None values, so the list is never empty at this call site.

```python
>>>   94 |     if not commands:
```

#### `_structure_do_blocks` — empty guard + do_line is None (L214, L245, L266→277) — 5 lines
**Decision**: ~~DEAD~~ REMOVED
L214 and L245 are empty-list guards that callers never trigger. L266→277 is a branch where `line_number` is None on the DO statement, but line_numbers are always set during parsing.

```python
>>>  214 |     if not statements:
        ...
>>>  245 |     if not current_block:
        ...
>>>  266 |     if do_line is None:
```

#### `_build_label` — no commands fallback (L816) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Branch where `parsed_content` has no `commands` attribute. textX `LineContent` always has a `commands` attribute per the grammar.

```python
>>>  816 |         commands = []
```

#### `classify_for_patterns` + `classify_for_patterns_from_file` (L868-953) — ~50 lines
**Decision**: ~~DEAD~~ REMOVED
Public API methods for FOR loop classification. Not called by any production transpiler pipeline. Only used for ad-hoc analysis tooling.

```python
>>>  868 |     def classify_for_patterns(self, source: str) -> dict[str, list[dict]]:
        ...
>>>  942 |     def classify_for_patterns_from_file(self, file_path: str) -> dict[str, list[dict]]:
```

#### `_find_argumentless_do_for_dot_lines` — IF/ELSE/direct DO (L169-210) — ~20 lines
**Decision**: LIVE
Handles `I cond D` + dot-lines, `E D` + dot-lines, and direct argumentless DO patterns. Valid MUMPS patterns confirmed reachable.

#### `_structure_commands_with_bodies` — ELSE branch (L127→131) — 2 lines
**Decision**: LIVE
Handles `E W x S y` pattern. Reachable but functional tests only cover ELSE with single body commands.

#### `_set_line_number_recursive` — else_scope (L71-72) — 2 lines
**Decision**: LIVE
Handles ELSE statements with sub-scopes.

#### `parse()` — exception handlers (L543-562) — ~10 lines
**Decision**: LIVE
TextXSyntaxError and generic Exception handlers. Defensive but reachable for malformed inputs.

#### `parse_file()` — optional analysis flags (L618-623) — 6 lines
**Decision**: LIVE
`analyze_variables=True` and `compute_signatures=True` options. Used by tooling.

#### `_mark_unreachable_statements` — generic body scope (L408) — 1 line
**Decision**: LIVE

#### `MUMPSParser.__init__` — FileNotFoundError (L478) — 1 line
**Decision**: LIVE

#### `analyze_variables` — transitive edge cases (L1067-1075) — 3 lines
**Decision**: LIVE

### `parser/textx_classes.py` — 68% covered (95 uncovered lines)

#### `_get_function_arg_list` — old format path (L130-133) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
Old `args.args` format no longer produced by textX grammar; superseded by first+rest pattern.

```python
>>>  130 |         elif hasattr(args, "args") and args.args:
>>>  131 |             for arg in args.args:
>>>  132 |                 if arg is not None:
>>>  133 |                     result.append(_unwrap_expr(arg))
```

#### `_unwrap_function_args_with_passing_mode` — defensive else (L234) — 1 line
**Decision**: ~~DEAD~~ REMOVED

```python
>>>  234 |                 pass  # Shouldn't happen
```

#### `NumericLiteral.__init__` — ValueError (L296-299) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
textX regex for NUMBER ensures value is always valid.

```python
>>>  296 |         except (ValueError, ArithmeticError):
>>>  297 |             self.decimal_value = Decimal(0)
>>>  298 |             self.int_value = 0
>>>  299 |             self.is_integer = True
```

#### `StringLiteral.__init__` — no-quotes branch (L322) — 1 line
**Decision**: ~~DEAD~~ REMOVED
textX STRING_VALUE rule always produces quoted strings.

#### `_unwrap_zwrite_subscripts` — defensive branches (L413, L444-453) — ~12 lines
**Decision**: ~~DEAD~~ REMOVED
Guards and fallback branches unreachable from textX grammar structure.

#### `SelectFunction.__init__` — no args branch (L617→624) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `FunctionArgs.args` — None rest_item (L846) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `get_command_classes` (L901) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Defined but never called by any code.

#### `get_class_for_rule` (L918-920) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Defined but never called by any code.

#### Other textx_classes.py uncovered — ~65 lines
**Decision**: LIVE
Valid MUMPS syntax handlers: `_unwrap_expr` None check, `_get_function_arg_list` empty placeholder, `_unwrap_function_args` byref/indirect/omitted variants, `ZWriteNakedGlobal`, `AnySpecialVariable`, `TextFunction` label indirection, `ExtrinsicFunction` routine indirection, `Indirection` name_subscripts, `get_expression_classes`.

### `parser/line_parser.py` — 39% covered (45 uncovered lines)

#### `_get_command_metamodel` (L43-46) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
Function defined but never called anywhere in production source.

```python
>>>   43 | def _get_command_metamodel():
```

#### `classify_for_command` — empty param_types (L238) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### Other line_parser.py uncovered — ~39 lines
**Decision**: LIVE
Error branches, parse error fallbacks, subscripted var handling. All valid paths.

### `parser/exceptions.py` — 68% covered (6 uncovered lines)
**Decision**: LIVE
`__str__` methods on exception classes.

---

## analysis/ (814 uncovered lines)

### `analysis/semantic_analyzer.py` — 59% covered (515 uncovered lines)

#### Z-command handlers — LIM-015 (L2287-2706) — ~260 lines
**Decision**: DEFERRED
All Z-command analysis handlers for: ZTSTART, ZTCOMMIT, ZWRITE subscript types, ZBREAK, ZSTEP, ZGOTO, ZKILL, ZWITHDRAW, ZHALT, ZHELP, ZALLOCATE, ZDEALLOCATE, ZLOAD, ZLINK, ZPRINT, ZSYSTEM, ZMESSAGE, ZTRIGGER, ZCOMPILE, ZEDIT, ZCONTINUE, and their sub-handlers. Documented as LIM-015.

#### KSUBSCRIPTS/KVALUE handlers — LIM-016 (L1494-1569) — ~65 lines
**Decision**: DEFERRED

#### `_push_scope` / `_pop_scope` (L2831-2848) — 18 lines
**Decision**: ~~DEAD~~ REMOVED
Scope tracking infrastructure built but never called from any production code path.

```python
>>>  2831 |     def _push_scope(self, scope_type: str = "block") -> None:
        ...
>>>  2845 |     def _pop_scope(self) -> None:
```

#### Other semantic_analyzer.py uncovered — ~170 lines
**Decision**: LIVE
Valid MUMPS feature handlers: expression analysis for external functions, indirection direct subscripts, device control params, argument analysis, FOR indirection, GOTO/DO postconditions, indirect chains, HANG multi-args, LOCK, CLOSE/USE/OPEN device params, JOB indirection, VIEW args, TSTART compound params, TRESTART, TROLLBACK, LabelRef analysis, variable tracking, `unwrap_expression`, `analyze_statement`.

### `analysis/variables.py` — 73% covered (186 uncovered lines)

#### `RoutineAnalysisCache` class (L198-340) — 143 lines
**Decision**: ~~DEAD~~ REMOVED
Entire class is never instantiated in production code. No callers exist.

```python
>>>  198 | class RoutineAnalysisCache:
>>>  199 |     """Cache for routine analysis results.
        ...
>>>  340 |         return self._signatures
```

#### `get_def_use_chains` (L1060-1067) — 8 lines
**Decision**: ~~DEAD~~ REMOVED
Debug/analysis utility with no production callers.

```python
>>>  1060 | def get_def_use_chains(
```

#### Other variables.py uncovered — ~35 lines
**Decision**: LIVE
Edge case branches with production callers: `_label_has_new_statements`, `_routine_has_argumentless_kill`, `_routine_has_name_indirection_on_locals`, expression variable extraction, `compute_transitive_inputs/outputs`, `bind_parameters`, `check_requires_runtime_scope`.

### `analysis/resolver.py` — 68% covered (25 uncovered lines)

#### `get_unresolved_calls` (L178-191) — 14 lines
**Decision**: ~~DEAD~~ REMOVED
Utility function with no production callers.

#### `get_external_calls` (L203-216) — 14 lines
**Decision**: ~~DEAD~~ REMOVED
Utility function with no production callers.

#### `_collect_globals_from_node` (L254) — 1 line
**Decision**: LIVE

### `analysis/for_analysis.py` — 71% covered (47 uncovered lines)
**Decision**: LIVE (all)
Valid MUMPS FOR analysis: indirection loop vars, SET/READ/KILL modifications in loop body, nested scope traversal, by-ref detection with signatures, QUIT context analysis.

### `analysis/goto_analysis.py` — 84% covered (30 uncovered lines)
**Decision**: LIVE (all)
Valid MUMPS GOTO patterns: same-routine reference, unresolved targets, offset direction, multi-loop exit, cross-label detection, DO with offset, external GOTO, fall-through.

### `analysis/pattern_compiler.py` — 90% covered (11 uncovered lines)
**Decision**: LIVE (all)
Pattern edge cases and error handling.

---

## asg/ (64 uncovered lines)

### `asg/elements.py` — 56% covered (55 uncovered lines)

#### `MParseError.__str__` (L41-44) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
Never called in production code.

#### `MScope.add_statement` (L166-168) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Parser directly sets `.statements` list. Only used in unit test fixtures.

#### `walk_statements` — else_scope branch (L189) — 1 line
**Decision**: ~~DEAD~~ REMOVED
No ASG statement type defines `else_scope`.

#### `MRoutine.get_text_line` (L374-376) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Codegen `$TEXT` uses `source_lines` directly on the runtime state.

#### `MRoutine.get_text_at_label` (L390-393) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
No production caller in codegen or analysis.

#### `ASGElement.to_dict` / `_serialize_value` (L84-150) — ~35 lines
**Decision**: LIVE
Called by `parser.py:424` (`dump_ast_json`).

#### `has_explicit_exit` — all-unreachable branch (L258-264) — 2 lines
**Decision**: LIVE

#### `MRoutine.get_label` (L353-356) — 4 lines
**Decision**: LIVE
Called from `goto_analysis.py`, `variables.py`.

### `asg/expressions.py` — 98% covered (2 uncovered lines)

#### `MActualParameter.is_byref` (L385) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Codegen uses `arg.passing_mode == PassingMode.BY_REFERENCE` directly.

#### `MActualParameter.is_omitted` (L390) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Codegen uses `arg.passing_mode == PassingMode.OMITTED` directly.

### `asg/statements.py` — 99% covered (2 uncovered lines)

#### `MKSubscriptsStatement.is_kill_all` (L419) — 1 line
**Decision**: DEFERRED (LIM-016)

#### `MKValueStatement.is_kill_all` (L445) — 1 line
**Decision**: DEFERRED (LIM-016)

### `asg/type_helpers.py` — 74% covered (5 uncovered lines)

#### `has_body` (L44) — 1 line
**Decision**: ~~DEAD~~ REMOVED
TypeGuard function with zero production callers.

#### `has_then_scope` (L58) — 1 line
**Decision**: ~~DEAD~~ REMOVED
TypeGuard function with zero production callers.

#### `get_body_scope` / `get_then_scope` — non-MScope branches (L72-74, L88-90) — 2 lines
**Decision**: ~~DEAD~~ REMOVED
Defensive branches that never trigger.

#### `get_else_scope` body (L107-109) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
No ASG statement type defines `else_scope`.

---

## codegen/ (1136 uncovered lines)

### `codegen/statements.py` — 70% covered (727 uncovered lines)

#### `_subscript_needs_pre_eval` (L963-979) — 17 lines
**Decision**: ~~DEAD~~ REMOVED
Helper never called. `_generate_tuple_set` pre-evaluates ALL subscripts unconditionally.

```python
>>>  963 | def _subscript_needs_pre_eval(
>>>  964 |     subscripts: list[str], target_vars: set[str]
>>>  965 | ) -> bool:
```

#### `_expr_references_vars` (L992-1020) — 29 lines
**Decision**: ~~DEAD~~ REMOVED
Only called by `_subscript_needs_pre_eval` which is dead.

```python
>>>  992 | def _expr_references_vars(expr_str: str, var_names: set[str]) -> bool:
```

#### `_generate_single_assignment_with_preeval` (L1027-1101) — 75 lines
**Decision**: ~~DEAD~~ REMOVED
Old tuple-SET implementation superseded by `_generate_single_assignment_with_preeval_subs`. No callers.

```python
>>> 1027 | def _generate_single_assignment_with_preeval(
```

#### Z-command `isinstance` branches (L789-812) — ~24 lines
**Decision**: DEFERRED (LIM-015)
12 `isinstance` branches raising `NotImplementedError` for Z-commands.

#### KSUBSCRIPTS/KVALUE branches (L813-817) — 5 lines
**Decision**: DEFERRED (LIM-016)

#### All other codegen/statements.py uncovered — ~577 lines
**Decision**: LIVE
TRAMPOLINE `uses_dynamic_locals` / `state_vars` branches (~150 lines), indirect FOR loop variants (~80 lines), multi-target indirect GOTO (~60 lines), LHS `$PIECE`/`$EXTRACT` indirection (~70 lines), MERGE indirection/extended-global paths (~50 lines), JOB indirect (~70 lines), Z-command implementations (ZWRITE/ZKILL/ZLINK/ZSHOW/ZGOTO/ZHALT/VIEW/BREAK) (~45 lines), various edge cases in NEW/KILL/QUIT/DO/SET/WRITE/READ (~52 lines).

### `codegen/expressions.py` — 78% covered (165 uncovered lines)

#### `_generate_literal` — else branch (L308-312) — 5 lines
**Decision**: ~~DEAD~~ REMOVED
Parser only produces STRING, INTEGER, DECIMAL literals.

#### `_generate_binary_op` — unsupported op (L794) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Parser normalizes all valid operators.

#### `_generate_unary_op` — unsupported op (L801-803) — 3 lines
**Decision**: ~~DEAD~~ REMOVED

#### `_generate_pattern_match` — no compiled_regex fallback (L866-867) — 2 lines
**Decision**: ~~DEAD~~ REMOVED
Analysis always compiles the regex.

#### Intrinsic function no-args guards (~18 lines) — scattered
**Decision**: ~~DEAD~~ REMOVED
Parser enforces minimum argument counts for all intrinsic functions: `$D()`, `$G()`, `$L()`, `$P(x)`, `$E()`, `$F(x)`, `$TR()/$TR(x)`, `$A()`, `$C()`, `$R()`, `$NA()`, `$QL()`, `$QS(x)`, `$J()/$J(x)`, `$RE()`, `$FN()/$FN(x)`, `$N()`.

Lines: L1141, L1241, L1882, L1924, L1967, L2009, L2050-2052, L2092, L2131, L2172, L2233, L2318, L2347, L2378-2380, L2413, L2445-2447, L2540

#### `_gen_select` — defensive guards (L1813-1840) — 5 lines
**Decision**: ~~DEAD~~ REMOVED
Parser produces well-formed MSelectArg.

#### `_generate_text` — label_indirect fallback (L1707) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Parser always creates MIndirection for `$T(@X)`.

#### SSVN branches (L513-543) — ~30 lines
**Decision**: DEFERRED
SYSTEM, DEVICE/CHARACTER, EVENT/WINDOW/DISPLAY (LIM-003), LIBRARY (LIM-011).

#### LIM-014 checks (L938-945, L965-967) — ~10 lines
**Decision**: DEFERRED

#### External function `$&name` (L1029-1032) — 4 lines
**Decision**: DEFERRED (LIM-015)

#### Extended globals (L490) — 1 line
**Decision**: DEFERRED

#### All other codegen/expressions.py uncovered — ~65 lines
**Decision**: LIVE
TRAMPOLINE/dynamic-locals paths for `$DATA`/`$ORDER`/`$QUERY`/`$NEXT`, `$STORAGE`/`$STACK`/`$QUIT`/`$TLEVEL`/`$ZJOB` special variables, complex indirection, `$NAME` naked global, `$NEXT` global/indirection, by-ref with omitted args.

### `codegen/indirection.py` — 77% covered (174 uncovered lines)

#### `_count_indirection_levels` / `_count_...with_subscripts` — None expr (L118, L123, L167, L177) — 4 lines
**Decision**: ~~DEAD~~ REMOVED
Parser always fills expression in indirection nodes.

#### `_generate_do_goto_indirection_string` — non-indirection fallback (L77) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Caller only passes indirection nodes.

#### All other codegen/indirection.py uncovered — ~169 lines
**Decision**: LIVE
Valid MUMPS indirection patterns: argument indirection with global source, complex expressions, name indirection (naked global, writes, kills), by-ref indirection, subscript indirection, merge indirection, function indirection, SET argument indirection, pattern indirection.

### `codegen/emitter.py` — 76% covered (7 uncovered lines)

#### `append` — no-lines branch (L93-98) — 6 lines
**Decision**: ~~DEAD~~ REMOVED

#### `get_code` — empty check (L107) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `get_lines` (L116) — 1 line
**Decision**: ~~DEAD~~ REMOVED
No production callers.

#### `current_indent` (L125) — 1 line
**Decision**: ~~DEAD~~ REMOVED
No production callers.

### `codegen/routine.py` — 91% covered (34 uncovered lines)

#### `get_scope_strategy_pattern` (L192-198) — 7 lines
**Decision**: ~~DEAD~~ REMOVED
Debug utility with no production callers.

```python
>>>  192 | def get_scope_strategy_pattern(routine: MRoutine) -> str:
```

#### `_generate_preamble` — auto-detect name fallback (L382-384) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Callers always provide a routine name.

#### Self-loop empty body (L710, L1306, L1312) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Parser always produces a body for self-loop labels.

#### `AnalysisNotCompleteError` / `validate_analysis_complete` (L29, L106-167) — ~35 lines
**Decision**: LIVE
Validation infrastructure.

#### Other codegen/routine.py uncovered — ~20 lines
**Decision**: LIVE

### `codegen/__init__.py` — 91% covered (6 uncovered lines)

#### `generate_python` — name fallback (L222-223) — 2 lines
**Decision**: LIVE

#### `_check_unsupported_gotos` — UNRESOLVED (L148, L152) — 2 lines
**Decision**: DEFERRED

#### Other — 2 lines
**Decision**: LIVE

### `codegen/helpers.py` — 89% covered (15 uncovered lines)

#### `m_str` — NaN/Infinity guard (L79) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `m_num` — no regex match (L207) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `m_num` — ValueError (L232-233) — 2 lines
**Decision**: ~~DEAD~~ REMOVED

#### `m_compare` — unsupported op (L539) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `m_format_output` — bool branch (L172) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### Other codegen/helpers.py uncovered — ~9 lines
**Decision**: LIVE

### `codegen/line_dispatch.py` — 81% covered (5 uncovered lines)

#### `generate_line_map` — label_line None (L73) — 1 line
**Decision**: ~~DEAD~~ REMOVED

#### `generate_line_map_code` — empty map (L103-104) — 2 lines
**Decision**: ~~DEAD~~ REMOVED

#### TYPE_CHECKING imports (L18-19) — 2 lines
**Decision**: DEAD (by design — do not remove)

### `codegen/shared_state.py` — 92% covered (3 uncovered lines)

#### `generate_state_imports` (L178) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Never called from production code.

#### TYPE_CHECKING import (L24) — 1 line
**Decision**: DEAD (by design — do not remove)

#### `generate_state_initialization` (L169) — 1 line
**Decision**: LIVE

---

## core/ (322 uncovered lines)

### `core/scope.py` — 46% covered (178 uncovered lines)

#### `VarRef` class (L51-86) — 36 lines
**Decision**: ~~DEAD~~ REMOVED
Never instantiated in production code. Zero callers.

```python
>>>   51 | @dataclass
>>>   52 | class VarRef:
```

#### `CurrentScope.get_subscripted` — non-MArray fallback (L228-252) — 25 lines
**Decision**: ~~DEAD~~ REMOVED
All variables are MArrays in practice. `hasattr(current, "__getitem__")`, `hasattr(current, "get")`, and else branches are unreachable.

#### `CurrentScope.data` + `_data_subscripted` (L578, L590-607) — 20 lines
**Decision**: ~~DEAD~~ REMOVED
Zero callers. `$DATA` uses `m_data()` from runtime helpers.

#### `CurrentScope._lookup` — locals_dict/state_locals branches (L643-668) — ~26 lines
**Decision**: ~~DEAD~~ REMOVED
`locals_dict` and `state_locals` are always None in production.

#### `CurrentScope._store` — locals_dict/state_locals fallbacks (L676-683) — 8 lines
**Decision**: ~~DEAD~~ REMOVED

#### `CurrentScope._delete` — locals_dict/state_locals branches (L690-696) — 7 lines
**Decision**: ~~DEAD~~ REMOVED

#### All other core/scope.py uncovered — ~56 lines
**Decision**: LIVE
`set`/`set_subscripted`/`exists`/`is_defined`/`get`/`kill` paths called via indirection runtime.

### `core/indirection.py` — 76% covered (113 uncovered lines)

#### `resolve_name_indirection` (L220) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Convenience method with zero external callers.

#### `resolve_argument_indirection` (L241) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Convenience method with zero external callers.

#### `resolve_to_argument_list` (L585-633) — 49 lines
**Decision**: ~~DEAD~~ REMOVED
Zero external callers.

```python
>>>  585 |     def resolve_to_argument_list(self, name: str, ...) -> list[str]:
```

#### `resolve_subscript_list` (L674-683) — 10 lines
**Decision**: ~~DEAD~~ REMOVED
Zero external callers.

```python
>>>  674 |     def resolve_subscript_list(self, name: str, ...) -> list[str]:
```

#### All other core/indirection.py uncovered — ~52 lines
**Decision**: LIVE
Various indirection resolution paths for valid MUMPS features.

### `core/names.py` — 65% covered (18 uncovered lines)

#### `is_valid_mumps_name` (L186-188) — 3 lines
**Decision**: ~~DEAD~~ REMOVED
Zero callers. `is_valid_varname` is used everywhere.

#### `translate` instance method (L251) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Zero callers.

#### `reverse` instance method (L255) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Zero callers.

#### `reverse_name` module function (L272) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Imported in `codegen/names.py` but never called.

#### Other names.py uncovered — 12 lines
**Decision**: LIVE
Python keyword escaping, `from_python()` reverse translation.

### `core/subscripts.py` — 82% covered (10 uncovered lines)

#### `canonicalize_numeric` — final `return str(n)` (L214) — 1 line
**Decision**: ~~DEAD~~ REMOVED
All types handled above. Unreachable.

#### `subscripts_equal` (L241) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Zero callers.

#### Other subscripts.py uncovered — 8 lines
**Decision**: LIVE
Canonicalization edge cases.

### `core/exceptions.py` — 73% covered (3 uncovered lines)
**Decision**: LIVE
`LVUNDEFError.__init__` — required by MUMPS spec.

---

## runtime/ (1122 uncovered lines)

### `runtime/__init__.py` — 58% covered (848 uncovered lines)
**Decision**: LIVE (all 848 lines)
Every uncovered function is either directly called by codegen-emitted code or transitively called by other live runtime methods. The uncovered lines are edge-case branches within live functions:
- Offset GOTO wrappers (G LABEL+N^ROUTINE state sync) — ~40 lines
- External call support (call_external_with_offset) — ~46 lines
- GOTO exception handler loop (run_with_goto_support) — ~132 lines
- Deep indirection (nested @, subscripted @, routine-qualified @) — ~249 lines
- Global variable operations — ~46 lines
- Error/exception handling branches — ~28 lines
- I/O device management (OPEN/CLOSE) — ~20 lines
- ZWRITE encoding/formatting — ~60 lines
- ZSHOW — ~22 lines
- ZLINK — ~20 lines
- JOB thread management — ~28 lines
- FOR loop runtime support — ~130 lines
- execute_mumps (XECUTE and runtime indirection) — ~86 lines
- Variable access (get_var/set_var/kill_var/merge_var/get_tree_var) — ~50 lines
- NEW push — ~6 lines

### `runtime/helpers.py` — 84% covered (84 uncovered lines)

#### TYPE_CHECKING imports (L31-32) — 2 lines
**Decision**: DEAD (by design — do not remove)

#### `_mumps_collation_key` — exception fallback (L119-120) — 2 lines
**Decision**: ~~DEAD~~ REMOVED
Logically unreachable after `is_canonical_numeric_string` validation.

#### `_mumps_collation_key` — non-str/int/float type (L125) — 1 line
**Decision**: LIVE
No other types reach this function.

#### `m_format_output` — bool branch (L172) — 1 line
**Decision**: ~~DEAD~~ REMOVED
Generated code never produces Python bools.

#### `m_format_output` — NaN/Inf Decimal (L184) — 1 line
**Decision**: ~~DEAD~~ REMOVED
MUMPS arithmetic can't produce NaN/Infinity.

#### `m_format_output` — float int check (L217) — 1 line
**Decision**: LIVE
All numerics are Decimal or str.

#### `m_format_output` — float formatting (L223-241) — 19 lines
**Decision**: LIVE
Float path unreachable.

#### All other runtime/helpers.py uncovered — ~57 lines
**Decision**: LIVE
`m_set_extract`, `m_data` subscript navigation, `m_order` direction coerce, `m_query` local, `_raise_select_false`, `m_qlength`/`m_qsubscript` parsing, `m_fnumber` comma/trailing-sign, `m_sorts_after`, `m_pattern_match` exception, `NewScopeManager`, `m_read_timeout`, `m_read_char`, `unwind_new_stack`. All called from generated code.

### `runtime/globals.py` — 71% covered (138 uncovered lines)

#### TYPE_CHECKING import (L33) — 1 line
**Decision**: DEAD (by design — do not remove)

#### Protocol `...` stubs — 26 lines (scattered L72-L437)
**Decision**: DEAD (by design — do not remove)
Protocol method `...` bodies are type-only declarations.

#### `InMemory.kill_all` (L636-637) — 2 lines
**Decision**: ~~DEAD~~ REMOVED
Zero callers in codegen or runtime.

#### `InMemory.incr` (L817-840) — 24 lines
**Decision**: ~~DEAD~~ REMOVED
Zero callers. `$INCREMENT` for globals is never generated.

```python
>>>  817 |     def incr(self, name: str, subscripts: tuple[str, ...], amount: str = "1") -> str:
```

#### `YottaDBGlobalStorage` class (L1189-1238) — ~12 lines
**Decision**: ~~DEAD~~ REMOVED
Stub class. All methods raise `NotImplementedError`.

#### `IRISGlobalStorage` class (L1356-1410) — ~12 lines
**Decision**: ~~DEAD~~ REMOVED
Stub class. All methods raise `NotImplementedError`.

#### All other runtime/globals.py uncovered — ~61 lines
**Decision**: LIVE
`InMemory` operations: kill edge case, data (return 11), naked indicator, order/query traversal, kill_node, lock/unlock, transactions, get_tlevel, SSVNs.

### `runtime/exceptions.py` — 33% covered (4 uncovered lines)
**Decision**: LIVE
`MRuntimeError.__init__` — called by `_raise_select_false()` and `$RANDOM` validation.

### `runtime/routines/MATH.py` — 0% covered (48 uncovered lines)
**Decision**: LIVE
All 13 `%SIN`, `%COS`, `%TAN`, etc. functions. Codegen resolves `$$%SIN^MATH` to these. No functional test calls `^MATH` yet.

---

## Dead Code Summary — All Candidates for Removal

### Total: ~717 lines

**Note**: TYPE_CHECKING imports and Protocol `...` stubs (~35 lines total) are dead at runtime by design and should NOT be removed. These are excluded from the actionable total.

### Actionable dead code: ~682 lines

| Category | Files | Lines |
|----------|-------|-------|
| **Unused utility functions** | parser, analysis, core | ~215 |
| **Dead infrastructure** (classes/methods never called) | analysis, core, codegen | ~250 |
| **Unreachable defensive branches** (grammar guarantees) | parser, codegen, runtime | ~100 |
| **Superseded code** (replaced by new implementation) | codegen | ~121 |
| **Stub backends** (placeholder classes) | runtime/globals | ~24 |

### Top 10 largest removable items:

| # | File | Item | Lines |
|---|------|------|-------|
| 1 | analysis/variables.py | `RoutineAnalysisCache` class | 143 |
| 2 | codegen/statements.py | `_generate_single_assignment_with_preeval` | 75 |
| 3 | core/indirection.py | `resolve_to_argument_list` | 49 |
| 4 | parser/parser.py | `classify_for_patterns` + `from_file` | 50 |
| 5 | core/scope.py | `VarRef` class | 36 |
| 6 | codegen/statements.py | `_expr_references_vars` | 29 |
| 7 | core/scope.py | `_lookup` locals_dict/state_locals branches | 26 |
| 8 | core/scope.py | `get_subscripted` non-MArray fallback | 25 |
| 9 | runtime/globals.py | `InMemory.incr` | 24 |
| 10 | runtime/helpers.py | `m_format_output` float formatting | 19 |

---

## Second Pass — Additional Dead Code Found

Ran functional test coverage again after the first round of removals. Total uncovered
lines went from 3698→3268 (430 lines removed from uncovered). The second pass inspected
all remaining uncovered sections (3+ contiguous lines) to identify items missed in the
first analysis.

### Coverage After First-Pass Removal

| Section | Uncovered (Before) | Uncovered (After) | Removed |
|---------|-------------------|-------------------|---------|
| parser/ | 240 | 175 | -65 |
| analysis/ | 814 | 770 | -44 |
| asg/ | 64 | 42 | -22 |
| codegen/ | 1136 | 1037 | -99 |
| core/ | 322 | 173 | -149 |
| runtime/ | 1122 | 1071 | -51 |
| **Total** | **3698** | **3268** | **-430** |

### New DEAD Code Found (~220 lines)

#### 1. `analysis/variables.py` L175-340 — `RoutineAnalysisCache` class (~166 lines)
**Decision**: DEAD — **REMOVED**
This class was identified for removal in pass 1 but was not actually removed.
It has zero production callers — only referenced in its own `ensure_analyzed()` method.
The `analyze_variables()` and `compute_all_signatures()` functions are used directly
instead. Entire class is dead infrastructure for IDE support that was never integrated.

```python
>>> 175 | class RoutineAnalysisCache:
>>> 176 |     """Cached analysis results for a routine with incremental update support."""
...
>>> 340 |         return self._signatures
```

#### 2. `analysis/semantic_analyzer.py` L1587-1590 — HANG legacy `seconds` attribute (4 lines)
**Decision**: DEAD — **REMOVED**
Grammar defines HangCommand with `args+=Expr[/,/]`, not `seconds`.
The `hasattr(cmd, "seconds")` check can never be true with the current textX grammar.
```python
>>>     elif hasattr(cmd, "seconds") and cmd.seconds:
>>>         stmt.duration = self.analyze(cmd.seconds, stmt)
>>>         if stmt.duration is not None:
>>>             stmt.durations.append(stmt.duration)
```

#### 3. `core/scope.py` L323-333 — `_exists_subscripted` dict fallback (11 lines)
**Decision**: DEAD — **REMOVED**
Fallback for non-MArray structures. Same pattern as `get_subscripted` non-MArray
fallback removed in pass 1. All variables are MArrays in practice.
```python
>>>     current = base
>>>     for sub in subscripts:
>>>         canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
>>>         if hasattr(current, "__contains__"):
...
```

#### 4. `core/scope.py` L379-396 — `_kill_subscripted` dict fallback (18 lines)
**Decision**: DEAD — **REMOVED**
Two blocks: dict navigation (L379-386) + final node deletion (L391-396).
Same dead pattern as #3. MArray `kill()` branch always handles the operation.
```python
>>>     current = base
>>>     for sub in subscripts[:-1]:
>>>         canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
>>>         if hasattr(current, "__getitem__"):
...
>>>     final_sub = SubscriptCanonicalizer.canonicalize(subscripts[-1])
>>>     if hasattr(current, "__delitem__"):
...
```

#### 5. `parser/line_parser.py` L144-170 — `detect_quit_after_for` function (27 lines)
**Decision**: DEAD — **REMOVED**
Exported in `parser/__init__.py` and `analysis/__init__.py` but has zero production
callers. Its only consumer `classify_for_patterns` was removed in pass 1.
```python
>>> 144 | def detect_quit_after_for(line_content: str) -> bool:
```

#### 6. `parser/line_parser.py` L173-190 — `extract_for_commands` function (18 lines)
**Decision**: DEAD — **REMOVED**
Same situation as #5 — exported but zero production callers.
```python
>>> 173 | def extract_for_commands(line_content: str) -> List[Any]:
```

#### 7. `parser/line_parser.py` L193-235 — `classify_for_command` function + helpers (43 lines)
**Decision**: DEAD — **REMOVED**
Same situation as #5/#6. Includes `ForParamType` enum used only by this function.
```python
>>> 193 | def classify_for_command(for_cmd) -> tuple:
```

### New DEFERRED Code Found (~52 lines)

#### Z-command analysis handlers in `analysis/semantic_analyzer.py` (LIM-015)

These should have been marked DEFERRED in the first pass but fell just
outside the documented range.

| Range | Function | Lines |
|-------|----------|-------|
| L2235-2238 | `_analyze_ZTStartCommand` | 4 |
| L2246-2248 | `_analyze_ZTCommitCommand` | 3 |
| L2714-2721 | `_analyze_ZBreakArg` | 8 |
| L2731-2733 | `_analyze_ZBreakClearAll` | 3 |
| L2741-2748 | `_analyze_ZBreakTarget` | 8 |
| L2754-2761 | `_analyze_ZGotoArg` | 8 |
| L2805-2818 | `_analyze_ZPrintArg` | 14 |

#### Z-command codegen dispatchers in `codegen/statements.py` (LIM-015)

| Range | Function | Lines |
|-------|----------|-------|
| L783-786 | ZGOTO/ZHALT dispatch | 4 |

### All Remaining Code is LIVE

All other uncovered sections (165 ranges, ~693 lines) are valid MUMPS feature code
that simply isn't exercised by the functional test suite. They are branches within
live functions covering: indirection code generation, SET $EXTRACT, FOR loop indirection,
GOTO restructuring, TRAMPOLINE by-ref handling, NEW/KILL, MERGE, WRITE/READ indirection,
XECUTE, JOB indirection, ZWRITE/ZKILL/ZLINK/ZGOTO/ZHALT, expressions, semantic analysis
of external functions, device controls, LOCK, VIEW, TSTART, and more.

### Second Pass Summary

| Category | Items | Lines |
|----------|-------|-------|
| **DEAD (missed in pass 1)** | 7 | ~220 |
| **DEFERRED (missed margin)** | 8 | ~52 |
| **LIVE** | 165 | ~693 |
| **TYPE_CHECKING (skip)** | 2 | ~7 |
| **Total new ranges** | 182 | ~972 |

**Actionable dead code: ~220 lines across 7 items.**

---

## Third Pass — Final Dead Code Sweep

Third functional coverage run after passes 1+2 removal (~902 lines removed total).
Examined all 353 uncovered ranges (3+ contiguous lines, 1513 total lines) plus small
gaps. Line numbers have shifted throughout, so all ranges were re-read at current
positions.

### Coverage After Passes 1+2

| Section | Uncovered | Ranges (3+) |
|---------|-----------|-------------|
| parser/ | 63 | 17 |
| analysis/ | 429 | 96 |
| asg/ | 28 | 6 |
| codegen/ | 473 | 110 |
| core/ | 23 | 7 |
| runtime/ | 497 | 117 |
| **Total** | **1513** | **353** |

### New DEAD Code Found (~179 lines)

#### 1. `analysis/semantic_analyzer.py` L134-169 — `SemanticScope` + `ScopeVariableInfo` classes (~36 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
These two `@dataclass` classes were infrastructure for scope-level variable tracking.
They were ONLY used by `_track_variable`, `_track_global`, `_track_label_call`, and
`self.current_scope`. Since `_push_scope`/`_pop_scope` were removed in pass 1,
`current_scope` is **always None** and never set. Both classes are unreachable.

```python
>>> 134 | @dataclass
>>> 135 | class SemanticScope:
...
>>> 153 | @dataclass
>>> 154 | class ScopeVariableInfo:
...
>>> 169 |     )  # Number of subscripts seen
```

#### 2. `analysis/semantic_analyzer.py` L2827-2838 — `_track_variable` body (~12 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
All call sites (14) and all 3 method definitions also removed. `current_scope` field
removed from `__init__`. Total ~80 lines removed for items 1-4 combined.
Body past the `if not self.current_scope: return` guard (L2824-2825). Since
`current_scope` is always None after `_push_scope` removal, the guard always
triggers and the body is unreachable. The 12 covered call sites (L223, L668, L820,
L829, L935, L1012, L1423, etc.) all immediately return.

```python
>>> 2824 |         if not self.current_scope:
>>> 2825 |             return
>>> 2827 |         if name not in self.current_scope.variables:
...
>>> 2838 |             info.is_newed = True
```

#### 3. `analysis/semantic_analyzer.py` L2843 — `_track_global` body (1 line)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
`if self.current_scope:` is always False. Body unreachable.

```python
>>> 2842 |         if self.current_scope:
>>> 2843 |             self.current_scope.globals_accessed.add(name)
```

#### 4. `analysis/semantic_analyzer.py` L2848-2849 — `_track_label_call` body (2 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
Same pattern — `if self.current_scope:` always False.

```python
>>> 2847 |         if self.current_scope:
>>> 2848 |             call_target = f"{label}^{routine}" if routine else label
>>> 2849 |             self.current_scope.labels_called.add(call_target)
```

**Note on `_track_*` methods**: The 3 method definitions themselves (signatures +
docstrings + guards) and their 14 call sites are technically wasted no-ops as well.
However, the call sites are scattered across 12+ handler methods. Removing all call
sites would be a larger refactor (~14 additional lines touched). The classes + bodies
are the primary dead code (~51 lines). Full removal of methods + call sites = ~80 lines.

#### 5. `core/scope.py` L274-276 — `set_subscripted` unreachable ValueError (3 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
The `else` branch of `if hasattr(current, "__getitem__")` can never trigger.
`current` is always an MArray: initialized as MArray at L249-254 (created if missing),
and each loop iteration sets `current` to either an existing MArray child or a newly
created MArray. MArray always has `__getitem__`.

```python
>>> 274 |             else:
>>> 275 |                 # Can't navigate further
>>> 276 |                 raise ValueError(f"Cannot set subscript on non-array value at {name}")
```

#### 6. `codegen/indirection.py` L2055-2098 — `generate_pattern_indirection` (44 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
Zero production callers. Pattern indirection (`X?@PAT`) is handled inline in
`codegen/expressions.py` via `m_pattern_match()`. This function was planned for
Spec 012 T060 but the implementation took a different route. Only referenced in
`__all__` (L2116) and tests.

```python
>>> 2055 | def generate_pattern_indirection(
>>> 2056 |     subject_expr: str,
...
>>> 2098 |         return f"(1 if {match_expr} is not None else 0)"
```

#### 7. `codegen/indirection.py` L1404-1424 — `generate_xecute_constant` stub (21 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
Stub that raises `NotImplementedError`. Zero production callers. XECUTE handling is
in `_generate_xecute` (statements.py). Planned for Spec 012 Phase 4 T024 but never
wired in. Also in `__all__` (L2111).

```python
>>> 1404 | def generate_xecute_constant(
...
>>> 1424 |     raise NotImplementedError("Constant XECUTE codegen not yet implemented")
```

#### 8. `codegen/indirection.py` L1427-1448 — `generate_xecute_dynamic` stub (22 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
Same situation as #7. Stub for Spec 012 Phase 5 T032. Zero production callers.
Also in `__all__` (L2112).

```python
>>> 1427 | def generate_xecute_dynamic(
...
>>> 1448 |     raise NotImplementedError("Dynamic XECUTE codegen not yet implemented")
```

#### 9. `runtime/__init__.py` L4792-4838 — `compile_pattern_indirect` method (~38 lines)
**Decision**: ~~DEAD~~ **REMOVED** (Pass 3)
Only designed to be called from generated code via `_rt.compile_pattern_indirect(...)`.
The codegen function that would emit such calls (`generate_pattern_indirection`, item #6)
is dead — no generated Python code ever calls this method. Only referenced from tests
and the dead codegen function.

```python
>>> 4792 |     def compile_pattern_indirect(self, pattern_str: str) -> str:
...
>>> 4838 |             ) from e
```

### New DEFERRED Code Found (~8 lines)

#### `parser/exceptions.py` L51-53 — `source_line` formatting in `MUMPSSyntaxError` (3 lines)
**Decision**: DEFERRED
No production caller passes `source_line=` to the constructor. The feature exists to
show source context in syntax errors but hasn't been wired up yet. Capability stub.

#### `core/scope.py` L116-118, L130-131 — strict_mode LVUNDEF raises (~5 lines)
**Decision**: DEFERRED
Only reachable when `self._strict_mode` is True. The sole production instantiation
uses default `strict_mode=False`. These exist for future LVUNDEF spec compliance (FR-025).

### All Remaining Ranges — LIVE

All other uncovered sections (338 ranges, ~1319 lines) are confirmed LIVE:

**parser/** (17 ranges, 63 lines): textX custom class constructors (ExtendedGlobalPipe,
ExtendedGlobalBracket, ZWriteGlobalPattern, ZWriteGlobal, ZWriteLocal, DeviceControl,
StructuredSystemVariable), encoding fallback, recursive DO/FOR nesting, label processing,
by-ref arg extraction, parse_file analysis flags.

**analysis/** (96 ranges, 429 lines): Z-command handlers (DEFERRED LIM-015, ~250 lines),
KSUBSCRIPTS/KVALUE (DEFERRED LIM-016, ~64 lines), plus FOR analysis (modification
detection, by-ref, signatures), GOTO analysis (unresolved targets, loop-exit, type
queries), variables (SSVN, indirection walk, bind_parameters, compute_transitive_outputs),
semantic analyzer (expression edge cases, SET/READ/IF/FOR/GOTO/DO handlers, LOCK, MERGE,
OPEN/CLOSE/USE, VIEW, TSTART, JOB, XECUTE).

**asg/** (6 ranges, 28 lines): `to_dict`/`_serialize_value` branches (position, set,
dataclass, source_lines), `get_label` body.

**codegen/** (107 ranges, 379 lines): expressions (intrinsic guards, SSVN dispatch,
$ORDER/$NEXT, extrinsic args), indirection (per-level subscripts, GlobalVariable/MVariable
branches, for-target, merge, data, query variants), routine (AnalysisNotCompleteError
validation guards), statements (Z-command handlers, indirect FOR, LHS $PIECE/$EXTRACT,
MERGE, JOB, GOTO restructuring, NEW/KILL, XECUTE, device I/O).

**core/** (4 ranges, 14 lines): `LVUNDEFError.__init__`, indirection NAME resolution,
recursive `@` resolution, escaped quote parsing.

**runtime/** (117 ranges, 497 lines): All edge-case branches within confirmed-live
functions (GOTO support, external calls, indirection, globals, I/O, ZWRITE, JOB,
FOR loops, XECUTE, variable access, NEW push, format output, SET extract, MATH
domain guards, lock/transaction management, SSVN).

### Third Pass Summary

| Category | Items | Lines |
|----------|-------|-------|
| ~~**DEAD (orphaned by prior removals)**~~ **REMOVED** | 9 | ~179 |
| **DEFERRED (new)** | 3 | ~8 |
| **LIVE** | 338 | ~1319 |
| **DEFERRED (carried from passes 1+2)** | ~10 | ~314 |
| **Total ranges analyzed** | ~360 | ~1513+ |

**All 9 dead code items removed. 3 tests exercising dead code also removed.
5818 tests passing (was 5821 before removal of 3 dead-code tests).**

Key insight: Most dead code in pass 3 was **orphaned by pass 1+2 removals** — the
scope tracking infrastructure (`SemanticScope`, `ScopeVariableInfo`, `_track_*` bodies)
became dead when `_push_scope`/`_pop_scope` were removed, and `compile_pattern_indirect`
became dead because `generate_pattern_indirection` was never wired into production.

---

## Fourth Pass — Deep Sweep for Missed Items

**Coverage baseline**: `uv run pytest tests/functional/ --cov=m2py --cov-report=json`
after pass 3 removals. 3086 lines uncovered across 1625 ranges.

**Strategy**: Instead of re-analyzing individual line ranges (which were already
examined in pass 3), this pass focused on:
1. Fully uncovered functions (entire functions with 0% coverage)
2. Contiguous uncovered blocks ≥ 5 lines not clearly addressed in passes 1-3
3. Functions with zero production callers (never imported/called from `src/m2py/`)

### Dead Code Found

#### 1. `analysis/variables.py` L1420-1498 — `compute_transitive_outputs` function (79 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Never imported or called from any production code in `src/m2py/`. Only referenced
in tests (`test_variable_analysis.py`) and documentation. Not exported from
`analysis/__init__.py`. The production pipeline uses `compute_transitive_inputs`
(a different function) via `codegen/__init__.py` L202.

```python
>>> 1420 | def compute_transitive_outputs(
>>> 1421 |     routine: MRoutine,
>>> 1422 | ) -> Dict[str, Set[str]]:
...
>>> 1498 |     return output_map
```

#### 2. `analysis/variables.py` L1360-1416 — `bind_parameters` function (57 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Only called from `compute_transitive_outputs` at L1472 (item #1 above), which is
itself dead. Not exported from `analysis/__init__.py`. Only referenced in tests.

```python
>>> 1360 | def bind_parameters(call: MCall, target_label: MLabel) -> List[ParameterBinding]:
...
>>> 1416 |     return bindings
```

#### 3. `analysis/variables.py` L113-135 — `ParameterBinding` dataclass (23 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Only used as the return type and construction target in `bind_parameters` (item #2
above), which is itself dead. Not exported from `analysis/__init__.py`.

```python
>>> 113 | class ParameterBinding:
>>> 114 |     """Links an actual parameter at a call site to a formal parameter.
...
>>> 135 |     caller_var_name: Optional[str] = None  # For BY_REFERENCE only
```

#### 4. `analysis/goto_analysis.py` L441-458 — `get_loop_exiting_gotos` function (18 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Zero production callers. Exported in `analysis/__init__.py` but never called from
any code in `src/m2py/`. Only referenced in tests (`test_goto_classifier.py`).
Public API that was designed but never consumed by the pipeline.

```python
>>> 441 | def get_loop_exiting_gotos(
>>> 442 |     routine: MRoutine,
>>> 443 | ) -> List[MGotoStatement]:
...
>>> 458 |     return result
```

#### 5. `analysis/goto_analysis.py` L460-477 — `get_gotos_by_type` function (18 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Same situation as #4. Exported but zero production callers. Only used in tests
(`test_goto_classifier.py`, `test_analysis_live_coverage.py`).

```python
>>> 460 | def get_gotos_by_type(routine: MRoutine, goto_type: GotoType) -> List[MGotoStatement]:
...
>>> 477 |     return result
```

#### 6. `runtime/__init__.py` L2851-2862 — `wait_for_jobs` method (12 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Zero production callers. Not emitted by any codegen function. Only called from tests
(`test_job_threading.py`, `test_runtime.py`). The JOB command generates `_rt.start_job()`
calls but never `_rt.wait_for_jobs()` — threads are fire-and-forget per MUMPS spec.

```python
>>> 2851 |     def wait_for_jobs(self, timeout: float | None = None) -> None:
>>> 2852 |         """Wait for all active JOB'd threads to complete.
...
>>> 2862 |             self._active_jobs = [t for t in self._active_jobs if t.is_alive()]
```

#### 7. `parser/parser.py` L400-413 — `dump_asg_json` function (14 lines)
**Decision**: ~~DEAD~~ **REMOVED**
Zero production callers. Exported from `parser/__init__.py` (L3, L13) but never
called from any code in `src/m2py/`. Debugging/inspection utility that has no
effect on the transpilation pipeline.

```python
>>> 400 | def dump_asg_json(
>>> 401 |     routine: MRoutine, include_position: bool = False, indent: int = 2
>>> 402 | ) -> str:
...
>>> 413 |     return json.dumps(routine.to_dict(include_position=include_position), indent=indent)
```

### New DEFERRED Code Found

#### `asg/elements.py` L62-145 — `to_dict` + `_serialize_value` methods (~84 lines)
**Decision**: DEFERRED
Only called from `dump_asg_json` (item #7 above), which is dead. However, these are
methods on the `ASGElement` base class, providing general-purpose debugging/inspection
capability. Removing them would eliminate a useful debugging surface. Classify as
low-priority dead code — keep for development tooling.

#### `parser/parser.py` L581-586 — `parse_file` convenience path (6 lines)
**Decision**: DEFERRED
The `compute_signatures` and `analyze_variables` parameters to `parse_file()` are
never used from production code (the pipeline calls `parser.analyze_variables()` and
`parser.compute_signatures()` separately). However, this is a public API convenience
path. The `compute_transitive=True` call on L584 also invokes the dead
`compute_transitive_outputs` code when `analyze_variables=True`. Keep as public API.

### All Remaining Ranges — LIVE

All other uncovered blocks were verified as LIVE edge-case branches within
confirmed-live functions. Key categories:

**Fully uncovered functions (all LIVE):**
- `runtime/routines/MATH.py` — All 9 `_pct_*` math functions are LIVE. Called via
  codegen dispatch (`MATH_FUNCTIONS_IMPLEMENTED`). Uncovered because functional tests
  don't exercise `$$%SIN^MATH()` etc., but 67 unit/codegen tests do.
- `runtime/__init__.py` `wrapped_func` inside `execute()` — LIVE. Functional tests
  use conftest's own equivalent wrapper; `execute()` is called from `validate.py`
  and unit tests.

**Edge-case branches (all LIVE):**
- `per_level_subscripts` blocks in `codegen/indirection.py` — Handle multi-level
  indirection `@X@(1,2)` patterns. Parser/analyzer fully wire these up.
- `_generate_do_target` byref branch — TRAMPOLINE strategy with by-ref args.
- `_evaluate_subscript` fallback — Defensive path for `runtime=None`.
- `_eval_simple_expr` arithmetic operators — Valid rare MUMPS patterns (`$D(x)-N`).
- `_restructure_forward_goto` — IF/GOTO restructuring (live, just rare).
- `_zwr_encode_string` — ZWRITE encoding (called from 3 live callers).
- `_exception_to_ecode` — Error handling (called from `_handle_etrap`).
- All Z-command handlers — DEFERRED (LIM-015, carried from passes 1-3).
- All KSUBSCRIPTS/KVALUE handlers — DEFERRED (LIM-016, carried from passes 1-3).

### Fourth Pass Summary

| Category | Items | Lines |
|----------|-------|-------|
| ~~**DEAD**~~ **REMOVED** | 7 | ~221 |
| **DEFERRED (new)** | 2 | ~90 |
| **LIVE** | all remaining | ~2775 |
| **Total ranges analyzed** | 1625 | ~3086 |

**All 7 dead code items removed. 26 tests exercising dead code also removed.
5792 tests passing (was 5818 before removal of 26 dead-code tests).**

Key insight: Pass 4 found dead code primarily in the form of **public API functions
that were designed/exported but never wired into the transpilation pipeline** — utility
query functions (`get_loop_exiting_gotos`, `get_gotos_by_type`), transitive output
analysis (`compute_transitive_outputs`, `bind_parameters`, `ParameterBinding`),
debugging utilities (`dump_asg_json`, `wait_for_jobs`). These weren't caught in
earlier passes because they're well-documented, exported, and tested — but have
zero production callers.

### Cumulative Dead Code Totals (All Passes)

| Pass | Items Removed | Lines Removed | Items Found | Lines Found |
|------|--------------|---------------|-------------|-------------|
| Pass 1 | 3 | ~682 | 3 | ~682 |
| Pass 2 | 7 | ~220 | 7 | ~220 |
| Pass 3 | 9 | ~179 | 9 | ~179 |
| Pass 4 | 7 | ~221 | 7 | ~221 |
| Pass 5 | 10+1 fix | ~179 | 13 | ~208 |
| **Total** | **37+1 fix** | **~1481** | **39** | **~1510** |

---

## Fifth Pass — Targeted Sweep for Orphaned and Write-Only Code

Coverage baseline: `tmp/coverage_pass5.json` (298 functional tests, post-pass-4 removal).
Strategy: Instead of re-scanning all uncovered blocks (which passes 1-4 exhaustively classified),
this pass focuses on three categories missed by earlier analysis:

1. **Code orphaned by pass 4 removals** — items whose only callers were removed
2. **Write-only fields and bookkeeping** — ASG fields set by analysis but never read by codegen/runtime
3. **Unused constants, exception classes, and utility functions** — defined but zero production callers

### Item 1: `_active_jobs` / `_active_jobs_lock` write-only bookkeeping (~4 lines)

`runtime/__init__.py` L1726-1727 (init) + L2820-2821 (append in `start_job`)

```python
# L1726-1727: Initialization
self._active_jobs: list[threading.Thread] = []
self._active_jobs_lock = threading.Lock()

# L2820-2821: In start_job()
with self._active_jobs_lock:
    self._active_jobs.append(thread)
```

With `wait_for_jobs` removed in pass 4, `_active_jobs` is **write-only** — threads are appended
but never read, joined, or iterated. Since threads are `daemon=True`, this is also a memory leak
(thread objects accumulate indefinitely without being garbage-collected).

**Decision**: ~~DEAD~~ **REMOVED** (~4 lines)

### Item 2: `to_dict` / `_serialize_value` on `ASGElement` (~82 lines) — UPGRADED FROM DEFERRED

`asg/elements.py` L62-144 (49 + 33 lines)

Previously deferred in pass 4 because `dump_asg_json` was the primary caller and it served as
debugging tooling. Now that `dump_asg_json` has been removed, these methods have **zero production
callers** — only test callers in `tests/unit/asg/test_elements.py`. The debugging rationale is
weakened since the serialization entrypoint no longer exists.

**Decision**: ~~DEAD~~ **REMOVED** (~82 lines, upgrade from DEFERRED)

### Item 3: `has_unstructured_goto` field + `_has_unstructured_gotos()` helper (~42 lines)

`asg/elements.py` L284 (field declaration)
`analysis/goto_analysis.py` L84 (writer: `routine.has_unstructured_goto = _has_unstructured_gotos(routine)`)
`analysis/goto_analysis.py` L441-480 (`_has_unstructured_gotos()` function, ~40 lines)

The field is **set by `classify_gotos()`** but **never read by codegen or runtime**. It was
superseded by `needs_trampoline` (which is the actual flag codegen uses for strategy selection).
No production code path reads `has_unstructured_goto`.

**Decision**: ~~DEAD~~ **REMOVED** (~42 lines: 1 field + 1 writer + 40-line helper function)

### Item 4: `global_refs` field + `_collect_global_refs()` collector (~36 lines)

`asg/elements.py` L286 (field declaration)
`analysis/resolver.py` L49 (writer: `routine.global_refs = list(_collect_global_refs(routine))`)
`analysis/resolver.py` L167-200 (`_collect_global_refs()` function, ~34 lines)

The field is **populated by `resolve_references()`** but **never read by codegen or runtime**.
The codegen generates global variable access directly from the ASG node types (`MGlobal`,
`MNakedGlobal`), not from a pre-collected list. Only tests read this field.

**Decision**: ~~DEAD~~ **REMOVED** (~36 lines: 1 field + 1 writer + 34-line collector + 46-line helper function)

### Item 5: `requires_runtime_eval` field — write-only (~4 lines)

`asg/elements.py` L285 (field on `MRoutine`)
`asg/expressions.py` L288 (field on `MIndirection`, hardcoded `True`)
`asg/statements.py` L594 (field on `MXecuteStatement`, hardcoded `True`)
`analysis/variables.py` L1117 (writer: `routine.requires_runtime_eval = any(...)`)

This field was a placeholder for future optimization — the intent was to skip runtime eval
setup for routines without indirection. However, codegen never reads it. The per-node fields
on `MIndirection` and `MXecuteStatement` are hardcoded to `True` and also never read.

**Decision**: ~~DEAD~~ **REMOVED** (~4 lines: 3 field declarations + 1 writer + 1 setter in textx_classes.py)

### Item 6: `result_type` field — unimplemented type tracking (~24 lines)

`asg/expressions.py` L47 (field on `MExpr`: `result_type: Optional[str] = None`)
`asg/expressions.py` L289 (field on `MIndirection`)
`parser/textx_classes.py` — 22 lines of `object.__setattr__(self, "result_type", None)` across
expression `__init_subclass__` methods

A placeholder for future type inference that was never implemented. Every setter initializes
it to `None`. No code in analysis, codegen, or runtime ever reads `result_type`.

**Decision**: ~~DEAD~~ **REMOVED** (~24 lines: 2 field declarations + 22 setter lines)

### Item 7: `indirection_levels` field on `MCall` — write-only (~5 lines)

`asg/elements.py` L370 (field declaration: `indirection_levels: int = 0`)
`analysis/semantic_analyzer.py` L1097, L1165, L1904, L2727 (4 writers)

Set by the semantic analyzer at 4 sites but **never read by codegen**. The codegen
recalculates indirection levels at emit time using its own `_count_indirection_levels()`
helper function in `codegen/indirection.py`. The ASG field is redundant.

**Decision**: ~~DEAD~~ **REMOVED** (~5 lines: 1 field + 4 writer lines)

### Item 8: `Z_COMMANDS_UNIMPLEMENTED` frozenset constant (~16 lines)

`codegen/statements.py` L123-138

A frozenset of 12 Z-command names that is defined but **never referenced** anywhere.
The actual Z-command handling uses `isinstance()` dispatch against individual statement
types (e.g., `isinstance(stmt, MZAllocateStatement)`), not this set.

**Decision**: ~~DEAD~~ **REMOVED** (~16 lines)

### Item 9: `NameTranslationError` exception class (~5 lines)

`codegen/__init__.py` L31-35 (class definition)
`codegen/__init__.py` L231 (`__all__` entry)

Exception class that is defined and exported but **never raised, caught, or imported**
by any code — production or test. Zero usage beyond definition.

**Decision**: ~~DEAD~~ **REMOVED** (~5 lines: class + `__all__` entry)

### Item 10: `get_expression_classes()` function (~7 lines)

`parser/textx_classes.py` L859-865

Returns a copy of `EXPRESSION_CLASSES` but is **never called**. The sibling function
`get_all_classes()` (which returns expressions + commands) is the one actually used
by the parser. This was likely an earlier API that `get_all_classes()` replaced.

**Decision**: LIVE — used by test helpers (tests/helpers/parsing.py and 8+ expression test files). Not dead.

### Item 11: `AssignmentTarget` type alias (~1 line)

`asg/expressions.py` L34

```python
AssignmentTarget = Union["MVariable", "MGlobal", "MNakedGlobal", "MIndirection"]
```

Type alias defined but never used in any type annotation or production code.

**Decision**: ~~DEAD~~ **REMOVED** (~1 line)

### Item 12: `UnsupportedFeatureError` duplicate class in `statements.py` (~9 lines)

`codegen/statements.py` L105-113

A local duplicate of the canonical `UnsupportedFeatureError` from `codegen/__init__.py`.
The canonical version inherits from `CodegenError`; this duplicate inherits from `Exception`.
It IS actively raised at L3536 and L3582 in `statements.py`, so it is **LIVE** — but it is
a **bug**: callers catching `CodegenError` won't catch this version. The fix is to import the
canonical class rather than maintain a duplicate.

**Decision**: ~~LIVE (bug)~~ **FIXED** — extracted CodegenError and UnsupportedFeatureError into codegen/exceptions.py; statements.py now imports the canonical class

### Item 13: `get_else_scope()` always-None function (~21 lines + 6 call sites)

`asg/type_helpers.py` L42-62

A helper that always returns `None` because MUMPS has no structural `ELSE` clause. It is
actively called by 6 sites in `analysis/goto_analysis.py` and `analysis/for_analysis.py`,
but every caller checks `if else_scope:` and skips when `None`. The function and all
calling code are functionally inert — they execute but never do anything.

**Decision**: DEFERRED — Removing requires updating 6 call sites across 2 files.
The function is architecturally intentional (future-proofing for potential ELSE scope
support). Low-priority cleanup.

### All Remaining Ranges — LIVE

All blocks identified in the pass 5 coverage scan that are not listed above were already
classified as LIVE in pass 4 analysis (edge-case branches, Z-command/KSUBSCRIPTS/KVALUE
handlers deferred under LIM-015/LIM-016, defensive error paths). No new LIVE→DEAD
reclassifications found.

### Fifth Pass Summary

| Category | Items | Lines |
|----------|-------|-------|
| ~~DEAD~~ **REMOVED** | 10 | ~179 |
| ~~LIVE (bug)~~ **FIXED** | 1 | ~9 (duplicate exception class) |
| **DEFERRED** | 1 | ~21 (get_else_scope() + call sites) |
| **Total** | 13 | ~216 |

Pass 5 findings fall into three categories:

1. **Orphaned by pass 4 removal** (items 1, 2): `_active_jobs` bookkeeping and
   `to_dict`/`_serialize_value` — both lost their only consumer when `wait_for_jobs`
   and `dump_asg_json` were removed.

2. **Write-only ASG fields** (items 3-7): Fields set by analysis passes but never
   read by codegen or runtime. These represent planned features (type tracking,
   indirection levels, global ref collection) that were partially implemented in
   analysis but never wired into code generation.

3. **Unused definitions** (items 8-11): Constants, exception classes, type aliases,
   and functions that were defined but never referenced.

### Cumulative Dead Code Totals (Updated)

| Pass | Items Removed | Lines Removed | Items Found | Lines Found |
|------|--------------|---------------|-------------|-------------|
| Pass 1 | 3 | ~682 | 3 | ~682 |
| Pass 2 | 7 | ~220 | 7 | ~220 |
| Pass 3 | 9 | ~179 | 9 | ~179 |
| Pass 4 | 7 | ~221 | 7 | ~221 |
| Pass 5 | 10+1 fix | ~179 | 13 | ~208 |
| **Total** | **37+1 fix** | **~1481** | **39** | **~1510** |
