# Comprehensive Expected-Fails Audit

All tests with `expected_fails` or `skip_reason` in `suite_definitions.py`, verified by
running each routine through m2py and comparing actual vs expected PASS/FAIL counts.

**Key discovery**: MVTS tests use files from `tests/functional/mvts/inref/` (NOT
`YDBTest/mugj/inref/`). The MVTS versions use `D ^VEXAMINE` with numeric test IDs and
`D MANPF*^VEXAMINE` for interactive operator tests. MUGJ versions use internal `D EXAMINER`
with "I-xxx" format IDs.

---

## Summary

| Category | Routines | Fails | Description |
|----------|----------|-------|-------------|
| OPERATOR | 7 | 29 | MANPF visual tests — permanently unfixable in automation |
| FIXABLE | 11 | 72 | Real test failures from unimplemented features |
| STALE | 2 | 4 | Expected fails that are now 0 — remove |
| SKIP-VALID | 3 | — | Cannot run in automation (BREAK/HANG/READ) |
| SKIP-UNSKIPPABLE | 3 | — | Can be unskipped with expected_passes/fails |
| SKIP-STALE | 1 | — | All tests withdrawn, skip unnecessary |

**Total expected_fails configured**: 105
**Total verified actual fails**: 101 (4 are stale)
**Total tests gained by unskipping**: +62 passes, +3 fails

---

## OPERATOR Tests (Permanently Unfixable) — 29 fails

These all use `D MANPF*^VEXAMINE` which prompts the human operator via READ. Without
keyboard input, VEXAMINE records a FAIL. No way to fix in automated testing.

| Routine | Suite | Passes | Fails | Verified | What the operator tests check |
|---------|-------|--------|-------|----------|-------------------------------|
| V1WR | VV1 | 0 | 4 | ✅ | 4 WRITE format visual checks |
| V1PRSET | VV1 | 0 | 4 | ✅ | 4 SET/KILL visual checks |
| V1FC | VV1 | 0 | 15 | ✅ | 15 format control visual checks (6+3+6 across V1FC1-3) |
| V1PC | VV1 | 18 | 2 | ✅ | 2 postcondition WRITE visual checks (V1PCA I-712.1/2) |
| V1SVH | VV1 | 1 | 1 | ✅ | 1 $HOROLOG date/time visual check |
| V1MAX | VV1 | 3 | 1 | ✅ | 1 max line length WRITE visual check |
| V2LCC1 | VV2 | 10 | 2 | ✅ | 2 lowercase command WRITE visual checks |

**No action needed** — these are correctly configured.

---

## FIXABLE Tests (Implementation Gaps) — 72 fails

These are automated `D ^VEXAMINE` tests that fail due to missing features. All verified
to produce the exact number of expected fails.

### By Feature Area

#### $TEXT function — 11 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V3TEXT | VV3 | 37 | 9 | 30252-30276 | `$TEXT(label^routine)` — external routine source lookup |
| V2FN2 | VV2 | 13 | ~~2~~ **0** | — | **STALE** — $TEXT fixes now pass all 13 tests |

#### NEW command — 35 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V3NEW | VV3 | 121 | 35 | 30971-31063 | `NEW @expr` indirection, exclusive NEW nesting, NEW with QUIT-with-value |

#### MERGE command — 17 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V4MERGE | VV4 | 51 | 17 | 40553-40612 | Subscripted MERGE, indirection in MERGE, global↔global |

#### $PRINCIPAL / Device I/O — 2 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V4PRIN | VV4 | 2 | 2 | 40745-40746 | OPEN/USE/CLOSE device I/O + JOB in tests 3-4 |

#### DO with Parameters — 2 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V3DWP | VV3 | 4 | 2 | 31083-31084 | Subscripted indirection `@IX@(1)`, $TEST preservation |

#### $NAME / $QSUBSCRIPT — 3 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V4NAME | VV4 | 93 | 2 | 40294, 40326 | $NAME edge cases |
| V4QSUB | VV4 | 112 | 1 | 40453 | $QSUBSCRIPT edge case |

#### Other — 4 fails
| Routine | Suite | Passes | Fails | Fail IDs | Specific gap |
|---------|-------|--------|-------|----------|-------------|
| V3FOR | VV3 | 7 | 1 | 30305 | Argumentless FOR with GOTO/QUIT interaction |
| V3NST1 | VV3 | 5 | 1 | 30339 | Deep nesting (30 levels FOR+DO+XECUTE) |
| V3INDNM | VV3 | 4 | 1 | 30381 | Name-level indirection with $ORDER |
| V4SORT | VV4 | 86 | 1 | 40079 | Sort-after operator (`]]`) |

### Priority for fixing (by ROI)

1. **V3NEW** (35 fails) — NEW command is core; many tests likely share root causes
2. **V4MERGE** (17 fails) — MERGE is critical for VistA data operations
3. **V3TEXT** (9 fails) — `$TEXT(label^routine)` external refs
4. **V4NAME + V4QSUB** (3 fails) — likely small edge cases
5. **V3DWP** (2 fails) — subscripted indirection
6. **Remaining singles** (4 fails) — V3FOR, V3NST1, V3INDNM, V4SORT

---

## STALE Expected Fails (Need Removing) — 4 bogus fails

These routines have `expected_fails` configured but now produce 0 fails.
The underlying issues have been fixed.

| Routine | Suite | Expected | Actual | Action |
|---------|-------|----------|--------|--------|
| V4SVQ | VV4 | 28P/2F | **28P/0F** | Remove `expected_fails=2` |
| V2FN2 | VV2 | 13P/2F | **13P/0F** | Remove `expected_fails=2` |

---

## MUGJ Expected Fails — 1 fail

| Routine | Suite | Passes | Fails | Classification | Specific gap |
|---------|-------|--------|-------|---------------|-------------|
| VV2SS1 | MUGJ | 6 | 1 | FIXABLE | String subscript collation ordering ($ORDER through $C(32)-$C(126)) |

VV2SS1 tests string subscript ordering. The failing test (II-171 or II-172) checks
that `$ORDER` traverses subscripts `$C(32)` through `$C(126)` in the expected
ASCII collation sequence. The collation difference produces "49111111111-25..." vs expected.

---

## Skip Reasons Analysis

### Valid Skips (keep as-is)

| Routine | Suite | Skip Reason | Why valid |
|---------|-------|-------------|-----------|
| V1BR | VV1 | BREAK command enters debugger | BREAK literally halts execution waiting for ZGO resume |
| V3HANG | VV3 | HANG command causes test to sleep | Also uses `ZSHOW "*"` (YDB-specific) and `$$^difftime` (external); 75+ sec sleep |
| V4KEY | VV4 | Interactive READ ($KEY test) | All 3 tests require READ input or JOB process |

### Should Unskip (with expected_passes/fails)

| Routine | Suite | Current Skip Reason | Run Result | Recommended Config |
|---------|-------|--------------------|-----------|--------------------|
| **V1IDARG** | VV1 | LIM-ARG-INDIR | 18P/0F → crash | `expected_passes=18, expected_fails=0` |
| **V3QUERY** | VV3 | LIM-SUB-CANON | 44P/0F → crash | `expected_passes=44, expected_fails=0` |
| **V4JOB** | VV4 | JOB requires process | 0P/3F | `expected_passes=0, expected_fails=3` |

**V1IDARG details**: Currently skipped entirely (0 tests run). When run, 18 automated
tests pass covering IF/KILL/SET argument indirection (V1IDARG1-4), then crashes in
V1IDARG3 at test I-854 with `VarExpectedError: Invalid expression in indirection: '1)-'`.
The 9 operator tests in V1IDARG5 (WRITE argument indirection visual checks) would produce
9 additional MANPF fails. But since execution crashes before reaching them, expected_fails=0.
Skip reason should change to describe the actual crash, not the original assumption.

**V3QUERY details**: Currently skipped entirely (0 tests run). When run, 44 tests
pass covering $QUERY on local and global variables with string subscripts (V3Q1-4),
then crashes at start of V3Q5 with `VarExpectedError: '' is not a valid variable name`.
V3Q5 tests "Numeric interpretation of subscripts" — the crash is in subscript
canonicalization during $QUERY evaluation.

**V4JOB details**: All 3 tests use JOB to spawn processes and LOCK to synchronize.
JOB is fundamentally unsupported (requires OS-level process spawning). Converting
from skip to expected_fails makes the failure explicit rather than hidden.

### Stale Skip (could remove)

| Routine | Suite | Skip Reason | Reality |
|---------|-------|-------------|---------|
| V1HANG | VV1 | HANG causes sleep | All 16 tests marked `*WITHDR*` (withdrawn 1992); produces no PASS/FAIL output |

V1HANG is harmless to run (produces no test markers) but also provides no value.
Could unskip to reduce skip count, or keep as-is.

---

## Actionable Changes Summary

### Immediate (no code changes needed)

1. **Remove stale expected_fails**:
   - V4SVQ: `expected_fails=2` → remove (0 actual fails)
   - V2FN2: `expected_fails=2` → remove (0 actual fails)

2. **Unskip V1IDARG**: Remove skip_reason, set `expected_passes=18, expected_fails=0`
   - Gains: +18 test passes tracked

3. **Unskip V3QUERY**: Remove skip_reason, set `expected_passes=44, expected_fails=0`
   - Gains: +44 test passes tracked

4. **Unskip V4JOB**: Remove skip_reason, set `expected_passes=0, expected_fails=3`
   - Gains: +3 test fails explicitly tracked

### Future implementation work (by priority)

| Priority | Feature | Fails Fixed | Effort |
|----------|---------|------------|--------|
| 1 | NEW @expr indirection + exclusive NEW nesting | ~35 | Medium |
| 2 | MERGE subscripted + indirection | ~17 | Medium |
| 3 | $TEXT(label^routine) external refs | ~9 | Low-Medium |
| 4 | V1IDARG3 indirection parsing crash | +19 more passes | Low |
| 5 | V3Q5 $QUERY subscript canonicalization | +24 more passes | Low |
| 6 | $NAME/$QSUBSCRIPT edge cases | ~3 | Low |
| 7 | DO-with-params subscripted indirection | ~2 | Low |
| 8 | V3For/V3NST1/V3INDNM/V4SORT singles | ~4 | Low |
| 9 | $PRINCIPAL + device I/O | ~2 | High (new subsystem) |

**Total fixable fails**: 72 (plus VV2SS1's 1 in MUGJ)
**Total new passes from unskipping**: +62 (V1IDARG: 18, V3QUERY: 44)
