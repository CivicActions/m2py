# Research: VistA-VEHU-M Transpilation Fixes

**Feature**: 024-vista-transpilation-fixes | **Date**: 2026-02-17

## Source

This research is primarily derived from [specs/vista-transpilation-failures.md](vista-transpilation-failures.md) — a full scan of 39,304 VistA-VEHU-M routines. Supplemented with codebase analysis of modification points.

---

## 1. ParenExpr Unwrapping Gaps

**Decision**: Add a defensive `ParenExpr` handler in `generate_expr()` (codegen) AND audit the semantic analyzer to find contexts where `_analyze_ParenExpr` is bypassed.

**Rationale**: The root cause is that some code paths skip semantic analysis (e.g., certain argument positions in commands that directly pass textX nodes to codegen). A defensive handler in codegen ensures no `ParenExpr` ever causes a `NotImplementedError`, while the analyzer audit fixes the root cause per Constitution Principle III (Strict Layer Separation).

**Alternatives Considered**:
- Codegen-only fix: Quick but masks analyzer gaps. Rejected as sole fix because it violates layer separation (codegen shouldn't need to handle raw textX nodes).
- Analyzer-only fix: Correct but risky — hard to guarantee every code path is covered. Could leave edge cases.
- Both (chosen): Defense-in-depth. Codegen fallback + analyzer fixes.

**Modification Points**:
- `src/m2py/codegen/expressions.py` L222: Add `ParenExpr` isinstance check before the `else: raise NotImplementedError` fallthrough
- `src/m2py/analysis/semantic_analyzer.py` L573-579: `_analyze_ParenExpr` unwraps correctly; need to audit callers that bypass the analyzer dispatch

---

## 2. f-string Nested Quote Incompatibility (Python 3.10)

**Decision**: Replace f-strings that embed single-quoted Python expressions with string concatenation using `+` operator.

**Rationale**: Python 3.10 does not support nested matching quotes in f-strings (PEP 701 only in 3.12+). The m2py target is Python 3.10. String concatenation is universally compatible and equally readable in generated code.

**Alternatives Considered**:
- `.format()` calls: Verbose for generated code; harder to read in codegen source. Rejected.
- Double-quoted f-strings: Would require all inner expressions to use single quotes — can't guarantee this. Rejected.
- Target Python 3.12+: Would reduce user base. Rejected per spec assumption.
- String concatenation with `+` (chosen): Simple, universally compatible, clear intent.

**Modification Points**:
- `src/m2py/codegen/indirection.py` L575: `f"f'({{_format_subscript({all_subs[0]})}})'"` → `"'(' + _format_subscript(" + all_subs[0] + ") + ')'"`
- `src/m2py/codegen/indirection.py` L578: Same pattern for multi-subscript case
- Audit all other f-string sites in `src/m2py/codegen/` for similar patterns

---

## 3. Empty Indented Block in TRAMPOLINE

**Decision**: When an IF block's body would be empty because its only statement is a GOTO (converted to `return` in TRAMPOLINE), include the `return` statement inside the if block body.

**Rationale**: The GOTO-to-return conversion currently places the return statement after the if block, leaving the if body empty. The correct fix is to include conditional GOTOs as part of the if body, not separate from it. Inserting `pass` would suppress the error but leave dead code.

**Alternatives Considered**:
- Insert `pass`: Masks the real issue (the return should be inside the if). Rejected.
- Include return in if body (chosen): Correct semantics — the GOTO was conditional, so the return should be too.

**Modification Points**:
- `src/m2py/codegen/statements.py` — TRAMPOLINE GOTO handling around L3282-3935: Ensure that when a GOTO is the last/only statement in an IF block, the generated `return` is emitted inside the `if:` block at the correct indentation level

---

## 4. `>=` and `<=` Operators

**Decision**: Add `>=` and `<=` as binary operator cases in `_generate_binary_op()`, mapping them to negated comparisons.

**Rationale**: These are YottaDB extensions (ANSI MUMPS uses `'<` for ≥ and `'>` for ≤). The parser already accepts them. The negated comparison equivalence is semantically exact. The existing `'<` and `'>` handlers already implement this pattern at L731-736.

**Alternatives Considered**:
- Normalize in parser/analyzer to `'<`/`'>`: Would require grammar changes. More invasive than needed. Rejected.
- Add to codegen dispatch (chosen): Minimal change, follows existing pattern exactly.

**Modification Points**:
- `src/m2py/codegen/expressions.py` L725-736: Add two `elif` branches after the existing `'>` handler:
  - `>=` → `int(not m_compare(left, "<", right))` (same as `'<`)
  - `<=` → `int(not m_compare(left, ">", right))` (same as `'>`)

---

## 5. SET $X / SET $Y

**Decision**: Add `$X` and `$Y` to the SET special variable dispatcher in codegen, backed by new runtime setter methods.

**Rationale**: `$X` and `$Y` are cursor position special variables (ANSI MUMPS §8.2.20.4). The runtime already tracks device position via `_current_device.x_pos` and `.y_pos`. Read access works (getters exist at runtime/__init__.py L2707-2724). Only the SET path is missing.

**Alternatives Considered**:
- No-op SET: Would lose cursor tracking fidelity. VistA actively uses `S $Y=0` to reset page counters. Rejected.
- Direct device attribute assignment in codegen: Violates runtime encapsulation. Rejected.
- Runtime setter methods (chosen): Clean API, matches existing pattern for $ETRAP etc.

**Modification Points**:
- `src/m2py/codegen/statements.py` L1104: Add `elif` for `$X`/`$Y` before the `else: raise NotImplementedError`
- `src/m2py/runtime/__init__.py`: Add `set_x(value)` and `set_y(value)` methods to `MRuntime`

---

## 6. LHS $EXTRACT 1-Argument Form

**Decision**: When `$EXTRACT` has 1 argument on the LHS, default start=1 and end=1 (replace first character).

**Rationale**: `S $E(X)="Z"` is standard MUMPS shorthand for `S $E(X,1,1)="Z"`. The existing handler at L1478 raises `ValueError` for <2 args. The fix is a simple default-value case addition.

**Alternatives Considered**:
- Normalize in analyzer: Could expand 1-arg to 3-arg form during analysis. More complex than needed. Rejected.
- Default in codegen handler (chosen): Minimal change, matches how the runtime `m_set_extract` already works.

**Modification Points**:
- `src/m2py/codegen/statements.py` L1478: Change from `if len(args) < 2: raise ValueError` to `if len(args) == 1: start=1, end=1; elif len(args) == 2: ...`

---

## 7. Computed/Indirected GOTO

**Decision**: For `G @expr` in TRAMPOLINE strategy, generate code that evaluates the expression at runtime and dispatches to the resolved label function via a dispatch table.

**Rationale**: Computed GOTOs like `G @$S(%=1:"A",%=2:"B",1:"C")` resolve to label names at runtime. TRAMPOLINE already has label functions. The trampoline dispatcher can accept the label name string as a return value and look it up in its dispatch table.

**Alternatives Considered**:
- Static analysis of all possible targets: Not feasible — `$SELECT` can produce arbitrary label names. Rejected.
- Runtime eval of generated Python: Security risk and complexity. Rejected.
- Return label name string to trampoline dispatcher (chosen): The dispatcher already maps label names to functions. Returning the string lets it look up the right function.

**Modification Points**:
- `src/m2py/codegen/statements.py` — computed GOTO handler: Generate code that evaluates the indirection expression to get a label name string, then return it as the trampoline target
- Runtime may need a helper to parse label+offset from evaluated expressions

---

## 8. Tuple SET with $PIECE/$EXTRACT Targets

**Decision**: Extend `_generate_single_assignment_with_preeval_subs()` in the tuple SET handler to support `MIntrinsicFunction` targets by delegating to existing `_generate_lhs_piece()` and `_generate_lhs_extract()` handlers.

**Rationale**: The existing LHS handlers work perfectly for single-target SET. Tuple SET just needs to evaluate the shared value once, then pass it to each target's handler.

**Alternatives Considered**:
- Duplicate LHS logic in tuple handler: Violates DRY. Rejected.
- Delegate to existing handlers (chosen): Reuse proven code. The shared value is already pre-evaluated in the tuple handler.

**Modification Points**:
- `src/m2py/codegen/statements.py` L1061: Before the `else: raise NotImplementedError`, add `elif isinstance(target, MIntrinsicFunction)` branch routing to `_generate_lhs_piece` or `_generate_lhs_extract`

---

## 9. ZLINK/ZLOAD

**Decision**: Add ZLOAD dispatch to codegen (aliasing to the existing ZLINK handler), which generates `_rt.zlink()` or `pass`.

**Rationale**: ZLINK is already handled (L6688-6710). ZLOAD has an ASG node (`MZLoadStatement`) but no codegen dispatch entry. The semantics are similar enough to share the same handler. VistA uses ZLOAD primarily for `$TEXT` access.

**Alternatives Considered**:
- Separate ZLOAD handler with different semantics: Unnecessary — VistA usage is identical to ZLINK. Rejected.
- Alias to existing handler (chosen): Minimal change.

**Modification Points**:
- `src/m2py/codegen/statements.py` L811-812: Add `elif isinstance(stmt, MZLoadStatement)` routing to `_generate_zlink()`
- Import `MZLoadStatement` in codegen if not already imported

---

## 10. RecursionError

**Decision**: Increase `sys.setrecursionlimit()` during transpilation. Use `5000` (default is 1000).

**Rationale**: The deeply nested VistA routines (PSXRECV, PSDCOSD, etc.) have very long lines with deeply nested function calls. The recursive `generate_expr()` and analyzer traversals hit the 1000-deep default. Increasing to 5000 is safe for transpilation (not runtime). An iterative rewrite would be ideal but is high complexity for 26 routines.

**Alternatives Considered**:
- Iterative traversal rewrite: High complexity, high risk of regressions. Rejected for now.
- Per-routine limit adjustment: Complex to implement. Rejected.
- Global limit increase during transpilation (chosen): Simple, safe, proven approach.

**Modification Points**:
- `src/m2py/cli/` or top-level transpilation entry point: Set `sys.setrecursionlimit(5000)` before transpilation, restore afterward

---

## 11. NEW Indirection in TRAMPOLINE

**Decision**: Implement `NEW @VAR` in TRAMPOLINE by using the routine state's `_locals` dictionary to dynamically save/restore the named variable.

**Rationale**: TRAMPOLINE uses `RoutineState` with a shared `_locals` dict. Dynamic NEW of a variable named by `@VAR` requires: (1) evaluate VAR to get the variable name string, (2) save the current value from `_locals`, (3) delete it from `_locals`, (4) restore on scope exit. This matches how `_rt.execute_new_indirection()` works for SIMPLE_FUNCTIONS (L4834).

**Alternatives Considered**:
- Reject with error (current behavior): Blocks 17 VistA routines including 7 FileMan core files. Rejected.
- Generate inline code (chosen): Use the same runtime method (`_rt.execute_new_indirection()`) but adapted for TRAMPOLINE's state model.

**Modification Points**:
- `src/m2py/codegen/statements.py` L4843: Replace `raise NotImplementedError` with code that calls a runtime method adapted for TRAMPOLINE scope management

---

## 12. IRIS Vendor Functions — Implementation Details

### 12a. $REPLACE

**Decision**: Implement as `m_replace(string, search, replace, start=1, count=-1, case=0)` in `runtime/helpers.py`.

**Rationale**: The 3-arg form maps directly to Python `str.replace()`. Start/count/case need a small wrapper. IRIS semantics are well-documented and validated.

**Modification Points**:
- `src/m2py/runtime/helpers.py`: New function `m_replace()`
- `src/m2py/codegen/expressions.py`: Add `$REPLACE`/`$R` to intrinsic function dispatch

### 12b. $ZBOOLEAN

**Decision**: Implement as `m_zboolean(arg1, arg2, op)` with a 16-entry dispatch using Python bitwise operators.

**Rationale**: For integers: use `&`, `|`, `^`, `~` directly. For strings: iterate characters applying per-character bitwise ops on ASCII values. The truth table is fully defined and validated against IRIS.

**Modification Points**:
- `src/m2py/runtime/helpers.py`: New function `m_zboolean()`
- `src/m2py/codegen/expressions.py`: Add `$ZBOOLEAN`/`$ZB` to intrinsic function dispatch

### 12c. $ZV/$ZVERSION

**Decision**: Return `"M2PY for Python 1.0 (Build 1)"` as a read-only special variable. `$ZVERSION(1)` returns 3 (UNIX).

**Rationale**: VistA platform-detection checks `$ZV["GT.M"` or `$ZV["IRIS"`. Returning "M2PY" allows VistA code to detect the runtime. The string format follows IRIS conventions.

**Modification Points**:
- `src/m2py/runtime/__init__.py`: Add `zversion()` property to `MRuntime`
- `src/m2py/codegen/expressions.py`: Add `$ZV`/`$ZVERSION` to special variable reader

### 12d. $ZF

**Decision**: Implement `$ZF(-1)` and `$ZF(-2)` via `subprocess.run()`/`subprocess.Popen()`. Implement `$ZF(-100)` via `subprocess.run()` with flag parsing. Stub VMS variants.

**Rationale**: `-1` (sync) and `-2` (async) are straightforward subprocess calls. `-100` is more structured with flags for shell mode, quoting, etc. VMS variants are dead code in VistA (guarded by `$ZV["VMS"` which won't match "M2PY").

**Modification Points**:
- `src/m2py/runtime/helpers.py`: New function `m_zf(code, *args)`
- `src/m2py/codegen/expressions.py`: Add `$ZF` to intrinsic function dispatch

### 12e. $ZA

**Decision**: Stub as 0 in runtime. Track TCP connection state (bit 13) when TCP device support is active.

**Modification Points**:
- `src/m2py/runtime/__init__.py`: Add `za()` property returning `self._za` (default 0)

### 12f. $ZR/$ZREFERENCE

**Decision**: Track last global reference in runtime, exposed as `$ZR`/`$ZREFERENCE`.

**Modification Points**:
- `src/m2py/runtime/__init__.py`: Add `zreference()` property, `set_zreference()` setter
- `src/m2py/runtime/globals.py`: Update global get/set/kill to call `_rt.set_zreference()`

### 12g. $NAMESPACE

**Decision**: Settable and NEW-able runtime variable, default "VISTA".

**Modification Points**:
- `src/m2py/runtime/__init__.py`: Add `namespace()` property, `set_namespace()` setter
- `src/m2py/codegen/statements.py`: Add `$NAMESPACE` to SET special variable handler

### 12h. $ZU Dispatch

**Decision**: Implement `m_zu(code, *args)` dispatch table for the ~12 VistA-used codes.

**Modification Points**:
- `src/m2py/runtime/helpers.py`: New function `m_zu(code, *args)`
- `src/m2py/codegen/expressions.py`: Add `$ZU` to intrinsic function dispatch

### 12i. $ZC/$ZCALL and $VIEW/$V Stubs

**Decision**: Return empty string and log warning.

**Modification Points**:
- `src/m2py/runtime/helpers.py`: `m_zcall_stub()`, `m_view_func_stub()`
- `src/m2py/codegen/expressions.py`: Add dispatch entries

---

## 13. Miscellaneous Fixes

### Device Control Mnemonics (WRITE /command)

**Decision**: Generate `_rt.device_control(command, args)` call. The runtime handler is a no-op for unrecognized mnemonics.

**Modification Points**:
- `src/m2py/codegen/statements.py`: WRITE handler — add case for `/command` format
- `src/m2py/runtime/devices.py`: Add `device_control()` method

### SET $ZINTERRUPT, $ZERR, $ZSOURCE

**Decision**: Add to SET special variable dispatcher.

**Modification Points**:
- `src/m2py/codegen/statements.py` L1104: Add elif branches for these three special variables

### $DEVICE, $REFERENCE, $ZGBLDIR Readers

**Decision**: Add to special variable reader in codegen.

**Modification Points**:
- `src/m2py/codegen/expressions.py`: Add to `_generate_special_variable()` dispatch
- `src/m2py/runtime/__init__.py`: Add properties with default values

### External C Functions ($&)

**Decision**: Generate `_rt.external_call_stub(name, args)` which logs a warning and returns "".

**Modification Points**:
- `src/m2py/codegen/expressions.py`: `_generate_external_function()` — handle `$&` prefix
- `src/m2py/runtime/__init__.py`: Add `external_call_stub()` method

### UnaryPrefixedExpr

**Decision**: Add defensive handler in `generate_expr()` (same approach as ParenExpr).

**Modification Points**:
- `src/m2py/codegen/expressions.py` L222: Add isinstance check before the NotImplementedError fallthrough

### Non-UTF-8 Encoding

**Decision**: Use `errors='replace'` or try Latin-1 fallback when opening `.m` files.

**Modification Points**:
- File reading code in CLI or parser entry point: Add encoding fallback

### Limitations Documentation

**Decision**: Add LIM-017 for partial IRIS/Caché support. Update LIM-012 if needed.

**Modification Points**:
- `src/m2py/limitations.py`: Add new `LIM-017` entry documenting IRIS support scope
- Run `utils/rebuild_docs.py` to regenerate `docs/limitations.md`
