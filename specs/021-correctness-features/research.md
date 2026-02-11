# Research: Phase 3 — Correctness Fixes & New Features

**Date**: 2026-02-10
**Branch**: `021-correctness-features`

## Phase 1 + Phase 2 Deliverable Status

All Phase 1 and Phase 2 deliverables are assumed complete and merged to `main`
before Phase 3 begins:

| Deliverable | Location | Status |
|---|---|---|
| `core/values.py` | `src/m2py/core/values.py` | ✅ Phase 1 |
| `core/parsing.py` | `src/m2py/core/parsing.py` | ✅ Phase 1 |
| `core/tokenizer.py` | `src/m2py/core/tokenizer.py` | ✅ Phase 1 |
| `codegen/exceptions.py` | `src/m2py/codegen/exceptions.py` | ✅ Phase 1 |
| `codegen/var_access.py` | `src/m2py/codegen/var_access.py` | ✅ Phase 2 |
| `MScope.walk_statements()` | `src/m2py/asg/elements.py` | ✅ Phase 1 |
| Indirection template | `src/m2py/codegen/indirection.py` | ✅ Phase 2 |

---

## Track A: Error Handling (F-03, F-09, F-08)

### Current Infrastructure Audit

**$ETRAP/$ECODE — Partially implemented:**

| Component | File | Lines | Status |
|---|---|---|---|
| `_ecode` / `_etrap` storage | `runtime/__init__.py` | L1611–1614 | ✅ Initialized to `""` |
| `ecode()` / `etrap()` getters | `runtime/__init__.py` | L2450–2503 | ✅ Working |
| `set_ecode()` / `set_etrap()` | `runtime/__init__.py` | L2467–2503 | ✅ Working |
| `_exception_to_ecode()` | `runtime/__init__.py` | L2522–2577 | ✅ Maps M9, M6, M4, M28, M26, M13, M1, M44, Z150373210 |
| `_handle_etrap()` | `runtime/__init__.py` | L2579–2619 | ⚠️ Basic: runs $ETRAP, checks $ECODE clear. Missing stack-level tracking for unwinding. |
| NEW $ETRAP codegen | `codegen/statements.py` | L4758–4790 | ✅ Uses `NewScopeManager.new_special_var()` |
| NEW $ESTACK | `codegen/statements.py` | L4784–4786 | ❌ Stubbed as no-op |
| SIMPLE_FUNCTIONS try/except | `codegen/routine.py` | L597–651 | ✅ `except Exception → _handle_etrap(_e, _scope)` |
| TRAMPOLINE try/except | `codegen/routine.py` | L872–943 | ✅ Same pattern |

**Key gap**: `_handle_etrap()` triggers $ETRAP but does NOT track at which stack level
$ETRAP was set. MUMPS requires QUIT from error trap to unwind to the setter's level.
The current implementation runs the trap code but has no level-aware unwinding.

**$ZTRAP/$ZSTATUS/$ZPOSITION — Not implemented:**

| Component | Status |
|---|---|
| Grammar parsing | ✅ ZTRAP, ZSTATUS, ZPOSITION recognized in SVARNAME regex |
| Codegen read | ❌ Falls through to `raise NotImplementedError` |
| Codegen SET | ❌ Falls through to `raise NotImplementedError` |
| Runtime storage | ❌ No `_ztrap`, `_zstatus`, `_zposition` fields |

**$STACK — Partially implemented:**

| Component | File | Lines | Status |
|---|---|---|---|
| `_stack_level: int` | `runtime/__init__.py` | L1593–1594 | ✅ Counter only |
| `stack_level()` accessor | `runtime/__init__.py` | L2424–2430 | ✅ Returns integer |
| `push_frame()` / `pop_frame()` | `runtime/__init__.py` | L2621–2628 | ⚠️ Increment/decrement only — no frame metadata |
| `$STACK(n,"info")` | — | — | ❌ Not implemented |
| DO block increment | `codegen/statements.py` | L4008 | ✅ `_rt._stack_level += 1` |

**Key gap**: push/pop only track depth (integer). Need to store per-frame
`(routine, label, offset, mcode)` tuples for $STACK(n,"PLACE") etc.

### MUMPS Standard Semantics (verified)

**$ECODE format** (ANSI §107.059): Always `,Lecode,` — codes prefixed M (MDC), U (user),
Z (implementation). Non-empty = error active. SET to `""` clears. Invalid value → M101.

**$ETRAP behavior** (ANSI §107.061, §106.012):
1. $ETRAP fires when $ECODE changes from empty to non-empty
2. QUIT from error trap unwinds to the stack level where $ETRAP was SET
3. `NEW $ETRAP` saves current value, initializes new level with **copy** (same value)
4. `SET $ETRAP` replaces without saving
5. Error during error processing → `TROLLBACK:$TLEVEL QUIT:$QUIT "" QUIT` (unwind + re-issue)

**$ETRAP↔$ZTRAP mutual exclusion** (YDB-specific):
- `SET $ETRAP=x` implicitly does `NEW $ZTRAP` (saves and clears $ZTRAP)
- `SET $ZTRAP=x` implicitly does `NEW $ETRAP` (saves and clears $ETRAP)
- Only one active at any stack level

**$STACK function** (ANSI §107.108):
| Call | Returns |
|---|---|
| `$STACK` (no args) | Current stack depth (integer) |
| `$STACK(-1)` | Highest level with non-empty ECODE (error snapshot depth) |
| `$STACK(0)` | Implementation-specific process start info |
| `$STACK(n)` | Frame type: `"DO"`, `"$$"`, `"XECUTE"`, `"ZINTR"`, `"TRIGGER"` |
| `$STACK(n,"PLACE")` | `LABEL+offset^ROUTINE` or `"@"` for XECUTE |
| `$STACK(n,"MCODE")` | Source line of M code at that level |
| `$STACK(n,"ECODE")` | Error codes at that level (if any) |

**$STACK snapshot behavior** (YDB extensions): During error handling ($ECODE non-empty),
$STACK() returns frozen snapshot data. Stack changes after error don't affect snapshot.
Snapshot resets only on `SET $ECODE=""`.

### YDB Verification

```
YDB> S $ZT="G ERR"
     W "BEFORE",!
     W UNDEFINED
     W "AFTER",!
     Q
ERR  W "$ZSTATUS=",$ZS,!
     W "$ZPOSITION=",$ZP,!
     Q

Output:
BEFORE
$ZSTATUS=150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: UNDEFINED
$ZPOSITION=ERR+1^test
```

- `$ZSTATUS` format: `errorcode,location^routine,%YDB-E-ERRNAME, Human message`
- `$ZPOSITION` after GOTO to ERR: shows current position `ERR+1^test` (NOT error origin)

```
YDB> W $STACK,!        → 0
     D SUB ... D SUB2
     $STACK → 2
     $STACK(0) → "-run TEST^test"
     $STACK(1) → "DO"
     $STACK(2) → "DO"
     $STACK(1,"PLACE") → "SUB+2^test"
     $STACK(2,"PLACE") → "SUB2+6^test"
```

```
YDB> $ETRAP fires on M6:
     S $ET="W ""ERR:""_$EC,!"
     W UNDEFINED
     → Output: "ERR:,M6,Z150373850,"
```

### Design Decisions

1. **Stack frame storage**: Add `_stack_frames: list[StackFrame]` to runtime where
   `StackFrame = namedtuple('StackFrame', ['frame_type', 'routine', 'label', 'offset', 'mcode'])`.
   Push on DO/XECUTE/$$, pop on QUIT/return.

2. **$ETRAP level tracking**: Store `_etrap_set_level: int` alongside `_etrap`. On
   error, if QUIT-from-trap, unwind to that level via exception.

3. **$ZTRAP dispatch**: If value matches `r'^[A-Z%][A-Z0-9]*(\^[A-Z%][A-Z0-9]*)?$'` (label
   ref), use GOTO semantics. Otherwise XECUTE.

4. **$STACK snapshot**: When $ECODE becomes non-empty, deep-copy `_stack_frames` to
   `_stack_snapshot`. Restore on `SET $ECODE=""`.

5. **Nested error handling**: Track `_in_error_handler: bool`. If error fires while
   `_in_error_handler` is True, execute `TROLLBACK:$TLEVEL QUIT:$QUIT "" QUIT`
   instead of $ETRAP.

---

## Track B: LOCK Indirection + TSTART Restart Variables (C-05, F-05)

### LOCK Indirection Current State

At `codegen/statements.py` L5327–5330:
```python
if lock_target.is_indirect:
    lines.append(f"{indent}# LOCK indirection not yet supported")
    continue
```

Silent skip. No error, no runtime behavior. 222 VistA files use LOCK with indirection.

**Existing indirection pattern**: Other indirection functions (SET, KILL, NEW, etc.)
follow a pattern of `generate_*_indirection()` in `codegen/indirection.py` and
corresponding `*_indirected()` in `runtime/__init__.py`. Phase 2's
`_build_indirection_call()` template may be available.

### TSTART Restart Variables Current State

At `codegen/statements.py` L5176–5214:
```python
if node.restart_vars or node.restart_all:
    raise NotImplementedError("TSTART restart variables not yet supported")
```

**ASG model** (`asg/statements.py` L781–870): `MTStartStatement` has fields
`restart_vars: list` and `restart_all: bool` — already parsed from grammar.

**MUMPS Standard Semantics** (ANSI §108.053):
- `TSTART (A,B,C)` — saves A, B, C for **TRESTART** (not TROLLBACK for locals)
- `TSTART *` — saves ALL current locals; marks as exclusive (no new vars after restart)
- Empty parens `TSTART ()` — restartable but no local restore
- No parens `TSTART` — not restartable

**Critical YDB finding**: In YDB, TSTART restart vars are for **TRESTART** (automatic
transaction restart on concurrency conflicts), NOT for TROLLBACK. TROLLBACK restores
globals only. Local variables are restored only on TRESTART.

**YDB verification**:
```
YDB> S X=1,Y=2 TS (X) S X=99,Y=99 TRO W "X=",X," Y=",Y,!
→ X=99 Y=99   (locals NOT restored by TROLLBACK)
```

This means FR-024 in the spec ("On TROLLBACK, the specified variables MUST be restored")
may need correction. VistA's usage pattern (`TS (vars)`) is about automatic restart
protection, not manual TROLLBACK restore. However, implementing the snapshot/restore
mechanism is still needed for TRESTART support.

### Design Decisions

1. **LOCK indirection**: Follow existing pattern. `generate_lock_indirection()` emits
   `_rt.lock_indirected(expr, lockop, timeout_expr)`. Runtime resolves the name and
   delegates to existing `lock()`/`unlock()`.

2. **TSTART restart vars**: Implement snapshot at TSTART time. Store in
   `_transaction_local_snapshots: list[dict]` (one per $TLEVEL). For TRESTART,
   restore. For TROLLBACK, only globals are restored (matching YDB). The spec's
   FR-024 should be updated to clarify TRESTART vs TROLLBACK semantics.

---

## Track C: Standalone Functions + Compliance (F-10, F-11, F-14)

### $ZDATE Current State

Listed in `Z_FUNCTIONS_UNIMPLEMENTED` frozenset at `codegen/expressions.py` L97.
Raises `NotImplementedError` when encountered.

**YDB $ZDATE format codes** (verified):

| Code | Meaning | Example |
|---|---|---|
| `MM` | 2-digit month | `08` |
| `DD` | 2-digit day | `16` |
| `YY` | 2-digit year | `22` |
| `YYYY` / `YEAR` | 4-digit year | `2022` |
| `MON` | 3-letter month abbreviation | `AUG` |
| `DAY` | Day-of-week abbreviation | `TUE` |
| `24` | 24-hour hour | `12` |
| `12` | 12-hour hour | `12` |
| `60` | Minutes | `35` |
| `SS` | Seconds | `56` |
| `AM` | AM/PM indicator | `PM` |

Default format: `"MM/DD/YY"`. Max 64 chars.

Literal separators allowed: `+ - . , / : ; *` and space.

**YDB verification**:
```
$ZD(66337)            → "08/16/22"
$ZD(66337,"YYYY-MM-DD") → "2022-08-16"
$ZD(66337,"DD MON YEAR") → "16 AUG 2022"
```

**$HOROLOG base date**: Day 1 = December 31, 1840 (ANSI standard).
66337 days from 1840-12-31 = August 16, 2022.

### ZSYSTEM Current State

At `codegen/statements.py` L856–857:
```python
raise NotImplementedError("LIM-015: ZSYSTEM command not supported")
```

ASG analysis already handles `MZSystemStatement` (semantic_analyzer.py L2413).
Implementation is straightforward: emit `subprocess.run(cmd, shell=True)`.

### ZLINK Current State

**Already fully implemented.** `zlink()` in `runtime/__init__.py` L2272–2301 uses
`importlib.import_module()`. Codegen in `codegen/statements.py` L6356–6382 emits
`_rt.zlink(routine_expr)`.

No Phase 3 work needed for ZLINK (FR-035 is already satisfied).

### LVUNDEF / strict_mode Current State

`core/scope.py` L38–53: `CurrentScope.__init__` accepts `strict_mode: bool = False`.
`core/scope.py` L85–86: `if self._strict_mode: raise LVUNDEFError(name)`.
`core/scope.py` L115–118: Same for subscripted access.

**Design decision**: Remove the `strict_mode` parameter entirely. Make the LVUNDEF
check unconditional (always raise). The `LVUNDEFError` exception class stays in
`core/exceptions.py` (L9–21) unchanged.

**Test impact**: Any test that currently relies on undefined locals returning empty
string will need to either:
1. Define the variable before accessing it, or
2. Expect a LVUNDEFError exception

**Constitution update**: §IV currently says "Undefined variables return empty string
(not exception)". This must be changed to "Undefined local variable access raises
LVUNDEFError (M6 error) per ANSI §7.2".

### Design Decisions

1. **$ZDATE implementation**: Pure Python function in `runtime/helpers.py`. Parse
   $HOROLOG into (year, month, day, hour, minute, second) using the ANSI base date
   (1840-12-31). Apply format codes via string replacement. Use Python's `datetime`
   module for day-of-week calculations.

2. **ZSYSTEM**: Emit `_rt.zsystem(cmd_expr)`. Runtime calls `subprocess.run(cmd, shell=True)`.
   Store exit code in `_zsystem_exit: int` for `$ZSYSTEM` ISV access.

3. **ZLINK**: Already done. Skip in Phase 3. ✅

4. **LVUNDEF**: Remove `strict_mode` conditional. Unconditional raise. Update constitution.
   Update broken tests.

---

## Track D: SVNs, SSVNs, Extended Globals (F-07, F-12, F-13)

### SSVNs Current State

| SSVN | Codegen | Runtime | Status |
|---|---|---|---|
| `^$GLOBAL` | `_rt.globals.ssvn_global()` | Backend method | ✅ Implemented |
| `^$JOB` | `_rt.globals.ssvn_job()` | Backend method | ⚠️ Returns "1" for current PID only |
| `^$LOCK` | `_rt.globals.ssvn_lock()` | Backend method | ✅ Implemented |
| `^$ROUTINE` | `_rt.globals.ssvn_routine()` | Backend method | ⚠️ Minimal |
| `^$SYSTEM` | Returns `'m2py'` inline | — | ❌ Stub |
| `^$DEVICE` | Returns `''` inline | — | ❌ Stub |
| `^$CHARACTER` | Returns `''` inline | — | ❌ Stub |
| `^$EVENT`, `^$WINDOW`, `^$DISPLAY` | NotImplementedError | — | ❌ MWAPI (LIM-003) |
| `^$LIBRARY` | NotImplementedError | — | ❌ LIM-011 |

The runtime methods (`ssvn_job`, `ssvn_routine`, etc.) exist in the global storage
backend but return minimal/stub data.

### YDB SVNs Current State

| SVN | Codegen | Status |
|---|---|---|
| `$ZJOB` | `_rt.zjob()` | ✅ Implemented — returns `_zjob` string |
| `$ZSEARCH` | — | ❌ Not implemented (limitations.py L374) |
| `$ZRO` | — | ❌ Not implemented (limitations.py L375) |
| `$ZMESSAGE` (function) | `Z_FUNCTIONS_UNIMPLEMENTED` | ❌ Not implemented |
| `ZMESSAGE` (command) | `NotImplementedError` (L850) | ❌ Not implemented |

### Extended Globals Current State

| Form | Codegen | Runtime | Status |
|---|---|---|---|
| `^[UCI,VOL]NAME` (bracket) | `_generate_extended_global_set()` L1540–1582 | Ignores environment | ⚠️ Partial (env ignored) |
| `^|"env"|NAME` (pipe) | Not in SET dispatch | — | ❌ Not handled |
| MERGE source | L4885–4891 | Ignores environment | ⚠️ Partial |
| MERGE destination | L5000–5013 | Ignores environment | ⚠️ Partial |
| $DATA, $ORDER, $GET, $QUERY | — | — | ❌ Not handled for extended refs |
| KILL | — | — | ❌ Not handled for extended refs |

Parser classes `ExtendedGlobalPipe` and `ExtendedGlobalBracket` exist in
`parser/textx_classes.py` L328–357.

### Design Decisions

1. **SSVN enhancement**: Improve `ssvn_job()` to use `os.kill(pid, 0)` for process
   checking. Improve `ssvn_routine()` to check `importlib.util.find_spec()` for
   routine existence. Keep `^$DEVICE`, `^$CHARACTER` as stubs (low VistA usage).

2. **$ZSEARCH**: Runtime method with iterator state. `_zsearch_results: list[str]`
   and `_zsearch_index: int`. First call does `glob.glob(pattern)`, stores results.
   Subsequent calls with empty string return next match.

3. **$ZMESSAGE**: Lookup table of common YDB error codes → messages. Can be generated
   from YDB documentation.

4. **Extended globals**: Add `namespace` parameter to global storage methods. Runtime
   stores namespace as key prefix: `"MYNS:GLOBALNAME"`. Codegen emits `_rt.globals.set(name, subs, value, namespace=expr)`.

---

## Track E: READ #maxlen (F-06)

### Current State

ASG parses `fixed_length` field on `MReadTarget` (asg/statements.py L112–140).
Codegen in `_generate_read_target()` (statements.py L5091–5174) does NOT check
for `target.fixed_length` — the value is silently ignored.

`$KEY` storage exists (`runtime/__init__.py` L1606–1607: `_key: str = ""`).
Accessor exists (`runtime/__init__.py` L2384–2394: `key()` returns `_key`).
Codegen read exists (`codegen/expressions.py` L592–594: `_rt.key()`).
But **no READ operation sets `_key`** — it remains empty string forever.

### MUMPS Standard Semantics (ANSI §108.045)

- `READ glvn#intexpr[:timeout]` — read at most `intexpr` characters
- If `intexpr ≤ 0` → error M18
- Input terminates on: terminator (e.g., Enter), n-th character, or timeout
- `$KEY` contains the control sequence that terminated the read, or empty string
  if maxlen was reached without a terminator

### YDB Verification

READ #maxlen with pipe was tested but returned empty (likely because YDB's piped
input behavior differs from terminal mode for character-counting). For m2py,
piped input implementation uses `sys.stdin.read(n)` which is straightforward.

### Design Decisions

1. **m_read_maxlen(n)**: For piped input, `sys.stdin.read(n)`. For interactive (future),
   character-at-a-time with termios. Phase 3 only implements piped/line-buffered input.

2. **$KEY setting**: After every READ, set `_rt._key` to the terminator character
   (newline if Enter, empty string if maxlen reached). This includes existing plain
   READ (which currently doesn't set $KEY).

3. **READ #0**: Return empty string immediately per spec edge case.

4. **m_read_maxlen_timeout(n, t)**: Combine `select()`-based timeout with character
   counting. Terminate on whichever comes first.

---

## Cross-Cutting Findings

### ZLINK Already Implemented

ZLINK is fully functional (codegen + runtime). FR-035 is already satisfied.
Phase 3 should mark this as no additional work needed, or remove from scope
to avoid confusion.

### TSTART Restart Vars ≠ TROLLBACK Restore

The spec (FR-024) says TROLLBACK restores specified variables. YDB testing shows
TROLLBACK only restores **globals**. Restart variables are for **TRESTART** (automatic
transaction restart on concurrency conflicts). The spec should be clarified, but
implementing the snapshot mechanism is still correct — it will be used by the TRESTART
path when that is eventually implemented.

For Phase 3, implement:
- Snapshot at TSTART time ✅
- Restore on TRESTART (if TRESTART is implemented, which involves TSTART keyword parsing)
- Do NOT restore locals on TROLLBACK (matches YDB)
- TROLLBACK still restores globals (already works)

### $ZDATE HOROLOG Day → Date Conversion

$HOROLOG day 1 = December 31, 1840 (not Jan 1, 1841 — verified by:
66337 days from Dec 31, 1840 = Aug 16, 2022, confirmed by `$ZD(66337)` → `"08/16/22"`).

Python implementation:
```python
from datetime import date, timedelta
BASE_DATE = date(1840, 12, 31)
target_date = BASE_DATE + timedelta(days=horolog_days)
```

### Tests Affected by Unconditional LVUNDEF

Any test that currently accesses an undefined local variable and expects empty string
will break. Need to audit test suite for this pattern. The fix is usually to either:
1. Add `SET VAR=""` before the access, or
2. Use `$GET(VAR)` (which returns "" for undefined without error), or
3. Update the test expectation to expect LVUNDEFError

This is the highest-risk change in Phase 3 from a test breakage perspective.
