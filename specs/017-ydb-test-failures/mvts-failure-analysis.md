# MVTS Test Failure Analysis

Research results for 14 failing MVTS test suites. Each section contains the MUMPS source, root cause analysis, and recommended fix.

---

## 1. V3FOR (passes=7/15, 1 unexpected fail)

### Test Structure
- **V3FOR.m** (driver): calls `D ^V3FOR1` and `D ^V3FOR2`
- **V3FOR1.m**: 7 tests (III-298 through III-304) — argumentless FOR command part 1
- **V3FOR2.m**: 8 tests (III-305 through III-312) — argumentless FOR command part 2
- **V3FOREX.m**: helper for external GOTO from FOR scope
- Total: **15 VEXAMINE calls** → 15 expected passes

### Unexpected Fail: III-305 (ABSN 30305)
**"XECUTE command argument has duplicated argumentless FOR"**

MUMPS source (V3FOR2.m test 1):
```mumps
 S ^VCOMP="",E=0
 x "for  s ^VCOMP=^VCOMP_"" f"",E=E+1,N=0 q:E=4  f  s N=N+1,^VCOMP=^VCOMP_N q:N>4"
 S ^VCORR=" f12345 f12345 f12345 f"
```

This XECUTE string contains **two nested argumentless FOR loops**:
1. Outer `for` sets `^VCOMP=^VCOMP_" f"`, increments E, quits when E=4
2. Inner `f` iterates N=1..5, appending N, quits when N>4

**COMPUTED=" f12345"** vs **CORRECT=" f12345 f12345 f12345 f"** — only one iteration of the outer FOR runs. The outer argumentless FOR inside XECUTE is not looping back.

**Root cause**: Argumentless FOR inside XECUTE likely breaks after the first iteration because the QUIT from the inner FOR is being misinterpreted as quitting the outer FOR scope as well, or the XECUTE'd code isn't properly establishing nested FOR scopes.

### 8 Missing Passes
The 7 passes come from V3FOR1 tests (III-298 through III-304). All 8 tests in V3FOR2 appear to fail or not produce PASS markers. Many V3FOR2 tests also involve:
- **III-306**: `FOR` scope has XECUTE with argumentless FOR inside
- **III-307**: Nested `FOR` with params inside argumentless FOR
- **III-308**: `IF` command inside argumentless FOR
- **III-309**: Subroutine with argumentless FOR (GOTO to end)
- **III-310**: Nested FOR with internal GOTO
- **III-311**: Nested FOR with external GOTO
- **III-312**: Deeply nested FOR

All V3FOR2 tests involve complex argumentless FOR patterns (nested FORs, XECUTE within FOR, GOTO within FOR scopes). The likely root cause is that once test III-305 errors/misbehaves, subsequent tests in V3FOR2 may also fail due to corrupted global state or the transpiled module crashing.

**Root cause category**: Argumentless FOR inside XECUTE, and nested argumentless FOR scoping.

---

## 2. V3NST1 (passes=5/6, 1 unexpected fail)

### Unexpected Fail: III-339 (ABSN 30339)
**"1 level of DO, and 29 levels of XECUTE"**

MUMPS source (V3NST1.m test 3):
```mumps
 S A="X B",B="X C",C="X D",D="X E",E="X F",F="X G",G="X H",H="X I"
 S I="X J",J="X K",K="X L",L="X M",M="X N",N="X O",O="X P",P="X Q"
 S Q="X R",R="X S",S="X T",T="X U",U="X V",V="X W",W="X X",X="X Y"
 S Y="X Z",Z="X A1",A1="X A2",A2="X A3"
 S ZZ=0,A3="S ZZ=ZZ+1 S ^VCOMP=^VCOMP_ZZ"
 X A3,A2,A1,Z,Y,X,W,V,U,T,S,R,Q,P,O,N,M,L,K,I,J,H,G,F,E,D,C,B,A
 S ^VCORR="1234567891011121314151617181920212223242526272829"
```

This test creates a chain: `X A` → `X B` → `X C` → ... → `X A3` which does `S ZZ=ZZ+1 S ^VCOMP=^VCOMP_ZZ`. The XECUTE line `X A3,A2,A1,...,A` executes A3 first (ZZ=1), then A2 which executes A3 (ZZ=2), etc. Each comma-delimited argument executes its chain, producing 29 total iterations.

**Root cause**: 29 levels of nested XECUTE is testing the maximum nesting depth. The issue could be:
1. Stack depth limitation in m2py's XECUTE implementation
2. Variable scoping issue — XECUTE uses the same variable namespace, so `X A` when A="X B" should recursively execute, but the intermediate variables (A through Z, A1-A3) get overwritten in the chain
3. The XECUTE with comma-separated arguments (`X A3,A2,...,A`) may not be handling each argument correctly as independent XECUTE operations

Note: The XECUTE line has 29 comma-separated arguments. Each one triggers a chain of variable-driven XECUTEs. Total XECUTE depth is 29 (one per comma argument, each going one level deep since each variable just says "X <next>").

---

## 3. V3INDNM (passes=4/5, 1 unexpected fail)

### Unexpected Fail: III-30381 (ABSN 30381)
**"Indirection of naked reference"**

MUMPS source (V3INDNM.m test 3):
```mumps
 D NEXT S ^VCOMP=""
 S A="^(2)",B="^(22,"""")",C="^(44)"
 S ^VCOMP=$O(^V1A(""))_" "_$O(@A)_" "_$O(@B)_" "_$O(@C)
 S ^VCORR="0 22 44 66"
```

Where NEXT sets up: `^V1A(0)=0, ^V1A(1)=1, ^V1A(22,66)=2266, ^V1A(22,44,66)=224466, ^V1A(100)=100, etc.`

The test expects:
1. `$O(^V1A(""))` → "0" (first subscript of ^V1A)
2. `$O(@A)` where A=`^(2)` → naked reference from ^V1A, so `$O(^V1A(2))` → "22"
3. `$O(@B)` where B=`^(22,"")` → naked from ^V1A, so `$O(^V1A(22,""))` → "44"
4. `$O(@C)` where C=`^(44)` → naked from ^V1A(22,...), so `$O(^V1A(22,44))` → "66"

**Root cause**: Indirection of naked references (`@"^(2)"`) requires combining indirection with the naked indicator. The `@A` where A contains a naked reference (`^(2)`) must resolve using the current naked indicator set by the previous global access. This is an interaction between two complex features: name indirection + naked references.

---

## 4. V3DWP (passes=4/6, 2 unexpected fails)

### Unexpected Fail: III-1083 (ABSN 31083)
**"indirection" with DO parameter passing**

MUMPS source (V3DWP.m test 5):
```mumps
 S IX="X",IY="@IY(1)",IY(1)="Y"
 d A0^V3DWPE(.@IX,.@IY,@IX@(1),.W,@IX,@IY)
 S ^VCORR="11X 1X1 1Y 0 1X1 0 10 1W123 1X 1Y 0/"
```

This tests `DO` with parameter passing where the parameters use **indirection**:
- `.@IX` → `.X` (pass X by reference, since IX="X")
- `.@IY` → `.@IY(1)` → `.Y` (two-level indirection, pass Y by reference)
- `@IX@(1)` → `X(1)` (subscripted indirection, pass X(1) by value)
- `.W` → pass W by reference
- `@IX` → `X` (pass X by value)
- `@IY` → `Y` (pass Y by value via two-level indirection)

**Root cause**: Complex indirection in DO parameter passing arguments. Specifically `@IX@(1)` (subscripted indirection), `.@IX` (by-reference via indirection), and `.@IY` (multi-level indirection for by-reference passing) are likely not handled by the codegen/runtime.

### Unexpected Fail: III-1084 (ABSN 31084)
**"$TEST value" with DO parameter passing**

MUMPS source (V3DWP.m test 6):
```mumps
 S ^VCOMP=""
 D T^V3DWPE("a","b")
 S ^VCOMP=^VCOMP_" "_$T_" "
 S ^VCOMP=^VCOMP_$d(X) I $D(X)#10=1 S ^VCOMP=^VCOMP_X
 S ^VCOMP=^VCOMP_$d(Y) I $D(Y)#10=1 S ^VCOMP=^VCOMP_Y
 S ^VCORR="1a1b 0 0 1X0"
```

V3DWPE `T(X,Y)` does:
```mumps
T(X,Y) ;
 S ^VCOMP=^VCOMP_$d(X) I $D(X)#10=1 S ^VCOMP=^VCOMP_X
 S ^VCOMP=^VCOMP_$d(Y) I $D(Y)#10=1 S ^VCOMP=^VCOMP_Y
 i 0
 S ^VCOMP=^VCOMP_" "_$T
 K Y
 S X="x",Y="y"
 Q
```

The `i 0` sets $TEST=0. Then `^VCOMP_" "_$T` appends " 0". After returning from T, the caller checks `$T`. Expected: " 0 " (the caller's $TEST should be preserved across DO with params, not affected by the `i 0` inside). Expected output "1a1b 0 0 1X0": `$T` after return = 0, then `$d(X)=1, X="X"` (unchanged, since formal params are separate), `$d(Y)=0` (Y was KILLed inside T but that was the formal param).

**Root cause**: `$TEST` value is not correctly preserved/restored across DO with parameter passing. The `i 0` inside the called subroutine sets $TEST=0, and the caller should see $TEST=0 after the call (since $TEST propagates back). The issue is likely that after subroutine return, $TEST isn't being set correctly, OR the formal parameter handling is incorrect (affecting the output that arrives at the FAIL check).

---

## 5. V1PC (passes=18/20, 2 unexpected fails)

### Unexpected Fails: I-712.1 (ABSN 11711), I-712.2 (ABSN 11712)
**"Postcondition contains = operator (by OPERATOR)"** and **"Postcondition contains lvn (by OPERATOR)"**

MUMPS source (V1PCA.m):
```mumps
712 W !,"I-712  WRITE command"
7121 S ^ABSN="11711",^ITEM="I-712.1  Postcondition contains = operator (by OPERATOR)"
 ...
 W !,"       Following two lines should be identical:"
 W !,"   Postcondition pass  "
 WRITE:1=1 !,"   Postcondition pass  " W:1=2 !,"** Postcondition FAIL  "
 WRITE:1=2 !,"** Postcondition FAIL  "
 D MANPF1^VEXAMINE I $D(RES)=1 I RES="AGAIN" G 712

7122 S ^ABSN="11712",^ITEM="I-712.2  Postcondition contains lvn (by OPERATOR)"
 ...
 W !,"       Following two lines should be identical:"
 W !,"   lvn PASS  "
 S PC=2 W:PC=1 !,"** lvn FAIL  " W:PC=2 !,"   lvn PASS  "
 D MANPF1^VEXAMINE I $D(RES)=1 I RES="AGAIN" G 7122
```

These are **"by OPERATOR" tests** — they call `D MANPF1^VEXAMINE` which requires manual operator input (Y/N) to confirm the visual output matches. In automated testing, there's no operator, so `MANPF1^VEXAMINE` produces a `** FAIL` marker (or `*FAILO*`).

**Root cause**: These are **operator tests** that cannot pass in automation. The `expected_passes` for V1PC should account for this. Currently V1PC has `expected_passes=20` but gets 18 passes + 2 operator fails. Fix: set `expected_passes=18, expected_fails=2`.

---

## 6. V4MERGE (passes=51 vs expected 36, 17 unexpected fails)

### Overall Issue
The `expected_passes=36` is wrong — V4MERGE actually has many more tests. There are 18 sub-files (V4MERGE1 through V4MERGEI), each containing 3-4 tests.

### Failing Tests Pattern
All 17 failing test IDs: 40553, 40554, 40557, 40558, 40559, 40560, 40567, 40568, 40569, 40580, 40587, 40591, 40592, 40597, 40598, 40599, 40612

These are distributed across:
- **V4MERGE3**: 40553 (lvn1 $d=10, lvn2 $d=0), 40554 (lvn1 $d=10, lvn2 $d=1)
- **V4MERGE4**: 40557-40560 (lvn1 $d=11, lvn2 $d=0/1/10/11)
- **V4MERGE6**: 40567-40568 (lvn $d=1, gvn $d=10/11)
- **V4MERGE7**: 40569 (lvn $d=10, gvn $d=0)
- **V4MERGE9**: 40580 (gvn $d=0, lvn $d=11)
- **V4MERGEB**: 40587 (gvn $d=10, lvn $d=10)
- **V4MERGEC**: 40591-40592 (gvn $d=11, lvn $d=10/11)
- **V4MERGEE**: 40597-40599 (gvn1 $d=1, gvn2 $d=0/1/10)
- **V4MERGEI**: 40612 (indirection in MERGE)

Example failing test (V4MERGE3 test 1, ABSN 40553):
```mumps
 S A("A",1)="A1 ",A("A",1,1)="A11 "
 M A("A")=B(1,1)
 S X=$$^V4MERE("A"),Y=$$^V4MERE("B"),^VCOMP=X_"/"_Y
 S ^VCORR="A1:A1 A11:A11 /"
```
Setup: `A("A",1)="A1 "`, `A("A",1,1)="A11 "`. B is undefined ($d=0). MERGE A("A")=B(1,1) should **do nothing** since B(1,1) has $d=0. Result should still show A's existing data.

**Root cause**: MERGE implementation issues:
1. `expected_passes` is wrong (should be ~68, not 36)
2. The V4MERE helper uses `@V@(subscripts)` pattern — subscripted indirection with `@V@(1)` etc. This is the same subscripted indirection syntax that fails elsewhere
3. MERGE with $DATA=0 source may be incorrectly clearing the destination, or MERGE with $DATA=10 (descendants only) may not handle the "no root node" case correctly

**Fix**: Update `expected_passes` to correct value (51+17=68). Then fix MERGE implementation and/or the `@V@(subs)` subscripted indirection in V4MERE.

---

## 7. V4GET2 (passes=61/64, 3 fails)

### Failing Tests
- **40192** (IV-192): `$g(C(1,2,3,4,5,6,7,8,9,10),1E25)` → COMPUTED="1E+25", CORRECT="10000000000000000000000000"
- **40193** (IV-193): `$g(@"AA",-1E-25)` → similar large number formatting
- **40225** (IV-225): `$g(^VV,1E-25)` → CORRECT=".0000000000000000000000001"

Source for 40192 (V4GET23.m test 2):
```mumps
 S ^VCOMP=$g(C(1,2,3,4,5,6,7,8,9,10),1E25)
 S ^VCORR="10000000000000000000000000"
```

**Root cause**: Large number formatting. `1E25` should be formatted as `"10000000000000000000000000"` (MUMPS canonical form), not `"1E+25"` (Python scientific notation). The `$GET` second argument (default value) is being returned as-is in Python's scientific notation format rather than being converted through `m_str()` which should produce MUMPS canonical form.

Similarly `-1E-25` should format as `"-.0000000000000000000000001"`.

**Fix**: Ensure `$GET`'s default value expression goes through `m_str()` for canonical MUMPS number formatting before being returned.

---

## 8. V4QLEN (passes=51/59)

### 8 Missing Passes
All 8 missing tests are **commented out with "MVTS LOCAL CHANGE"** in the source files:

| File | Tests Commented Out | Reason |
|------|-------------------|--------|
| V4QLEN1.m | IV-342, IV-345 | "Current requirement is for canonic input" |
| V4QLEN2.m | IV-349, IV-350, IV-353 | "Current requirement is for canonic input" |
| V4QLEN5.m | IV-372 | "Current requirement is for canonic input" |
| V4QLEN6.m | IV-379, IV-380 | "Current requirement is for canonic input" |

These tests were disabled because GT.M/YDB requires canonical input to $QLENGTH. The tests use non-canonical subscript formats that the standard doesn't require.

**Fix**: Reduce `expected_passes` from 59 to 51. These tests are intentionally commented out in the MVTS suite and will never produce PASS markers.

---

## 9. V4QSUB (passes=112/116, 1 fail)

### 1 Unexpected Fail: IV-453 (ABSN 40453)
**"namevalue contains extrinsic function"**

MUMPS source (V4QSUB8.m test 5):
```mumps
 S D="DDD"
 S ^VCOMP=$QS($$ZZZ(123,.D),1)
 S ^VCORR="123"
```
Where `ZZZ(%1,%2)` returns `$NAME(@%2@(%1))`:
```mumps
ZZZ(%1,%2) ;
 Q $NAME(@%2@(%1))
```

So `$$ZZZ(123,.D)` passes D="DDD" by reference. Inside ZZZ, `%2` is a reference to D (="DDD"). `@%2@(%1)` = `@D@(123)` = `DDD(123)`. `$NAME(DDD(123))` = `"DDD(123)"`. Then `$QS("DDD(123)",1)` should return `"123"`.

**Root cause**: The extrinsic function `$$ZZZ` uses pass-by-reference (`.D`) and subscripted indirection (`@%2@(%1)`). This is the same `@var@(subs)` pattern that fails in V3DWP. The function either fails to execute or returns empty string.

### 3 Missing Passes (4 → 116-112=4, but we see only 1 fail)
3 of the 4 missing passes are **commented out with "MVTS LOCAL CHANGE"**:
- V4QSUB6.m test 7 (IV-438): subscript contains `"` characters
- V4QSUB13.m test 6 (IV-495): subscript contains a `"` character
- V4QSUB7.m test 2 (IV-441): namevalue contains gvn

**Fix**: Reduce `expected_passes` from 116 to 113 (3 commented out). Then fix `@var@(subs)` indirection for test 40453.

---

## 10. V4RAND (passes=0/1)

### Test Structure
The only test in V4RAND.m (IV-680) is **entirely commented out** with "MVTS LOCAL CHANGE":

```mumps
;**MVTS LOCAL CHANGE**
 ; Value that can fit in an int4 is the maximum we support for $Random argument
; 10/2001 SE
1 ;W !,"IV-680  intexpr is 15 digits ( maximum range )"
 ;S ^ABSN="40680",^ITEM="IV-680  intexpr is 15 digits ( maximum range )"
 ...
```

The test uses `$R(999999999999999)` which exceeds YDB's int4 limit.

**Fix**: Set `expected_passes=0`. The test is intentionally disabled. Or skip the test entirely.

---

## 11. V4MAX (passes=5/7)

### 2 Missing Passes
Both missing tests are **commented out with "MVTS LOCAL CHANGE"** in V4MAX2.m:
- **IV-758**: "50 levels subscript of local variable" — GT.M only supports 31 subscripts
- **IV-759**: "50 levels subscript of global variable" — GT.M only supports 31 subscripts

The active tests are:
- V4MAX1: 3 tests (IV-753, IV-754, IV-755) — numeric range 10^-25 to 10^25
- V4MAX2: 2 tests (IV-756, IV-757) — 15-digit subscripts

**Fix**: Set `expected_passes=5`. The 2 missing tests are intentionally disabled.

---

## 12. V4SSUB (passes=7/9)

### 2 Missing Passes
Both missing tests are **commented out with "MVTS LOCAL CHANGE"** in V4SSUB2.m:
- **IV-767**: "Total number of local variable subscripts is 79" — GT.M only allows 31 subscripts
- **IV-768**: "Total number of global variable subscripts is 78" — GT.M only allows 31 subscripts

Active tests: V4SSUB1 has 4 tests (IV-760 to IV-763), V4SSUB2 has 3 active tests (IV-764 to IV-766).

**Fix**: Set `expected_passes=7`. The 2 missing tests are intentionally disabled.

---

## 13. V2FN2 (passes=13/15)

### Test Structure
V2FN2 has 14 standard tests (II-79 through II-90, II-95.1, II-95.2) = 14 VEXAMINE calls.
But test II-95.2 (ABSN 20096) has special handling via `EXAMINE2`:

```mumps
952 S ^ABSN="20096",^ITEM="II-95.2  ls has multi spaces"
 S ^VCOMP="" S ^VCOMP=$t(T95)_"*"_$TEXT(T95+1)
 S ^VCORR="T95 S A=1   ;$TEXT* S B=2   ;$TEXT+1"
 S ^VCORRN="T95       S A=1   ;$TEXT*                   S B=2   ;$TEXT+1" D EXAMINE2

T95       S A=1   ;$TEXT
                   S B=2   ;$TEXT+1
```

`EXAMINE2` checks first if `^VCORR=^VCOMP` (normalized form). If match, calls `^VEXAMINE` (PASS). If not, checks `^VCORRN=^VCOMP` (with original multi-spaces). If that matches, goes to `FAIL90` — which writes `** FAIL90` (not `** FAIL`).

The `** FAIL90` marker means: "the implementation preserved multi-spaces in $TEXT output" — it's a known implementation-specific behavior, not a real failure. The marker `FAIL90` is different from the `** FAIL` pattern the test harness looks for.

### Analysis
- 14 VEXAMINE calls, but `expected_passes=15` is wrong
- 13 passes suggests test II-95.2 matches `^VCORRN` (multi-space form) and goes to FAIL90, which outputs `** FAIL90` — this doesn't match the `PASS\s+\d+` pattern (so no PASS), and doesn't match `\*\* FAIL\s+(\d+)` either (because it says "FAIL90" not "FAIL  20096")
- 1 other test also isn't producing PASS — likely II-95.1 (ABSN 20095) which also involves `$TEXT` with multi-space lines

**Root cause**: `$TEXT` is returning lines with original multi-space formatting. The VCORR uses normalized single-space form. So the test doesn't match VCORR, doesn't match VCORRN either, and both miss.

Wait — re-reading: test 95.1 uses `^VCORR="V2FN2*V2FN2"` which is `$t(+0)_"*"_$TEXT(+00.987)` — this returns the first line of the routine. If $TEXT(+0) works, it should pass. The issue is likely that `expected_passes=15` is wrong (should be 14 max, since there are only 14 VEXAMINE calls).

Actually, looking at the VV2 suite definitions: `RoutineDefinition("VV2FN2", "VV2FN2", expected_passes=14)` vs MVTS suite: `RoutineDefinition("9---V2FN2", "V2FN2", expected_passes=15)`. The VV2 version expects 14. So the MVTS expected count of 15 is wrong.

**Fix**: Set `expected_passes=13`. Account for 1 FAIL90 marker (not a real fail, just implementation-specific $TEXT behavior). Or `expected_passes=14` if the $TEXT normalization issue is fixed.

---

## 14. V3TEXT (passes=37/46, 9 unexpected fails)

### Test Structure
- **V3TEXT1.m**: 16 tests (III-252 through III-267) — `$TEXT(^routineref)` and `$TEXT(dlabel^routineref)`
- **V3TEXT2.m**: 19 tests (III-268 through III-286) — `$TEXT(dlabel+intexpr^routineref)`
- **V3TEXT3.m**: 11 tests (III-287 through III-297) — existence checks and value examination
- Total: **46 VEXAMINE calls**

### 9 Failing Tests

All failures involve accessing `$TEXT` in **external routines** or using **indirection** in routine/label references:

| ABSN | Test | Description | Root Cause |
|------|------|-------------|------------|
| 30252 | III-252 | `$TEXT(^V3TEXTA)` — routineref is a routinename | `$TEXT` with external routine `^routinename` not implemented |
| 30253 | III-253 | `$text(^V3TEXTA8)` — routinename has 8 chars | Same: external `$TEXT` |
| 30254 | III-254 | `$T(^@ROU)` where ROU="V3TEXTA" — indirection in routinename | External `$TEXT` + indirection |
| 30255 | III-255 | `$t(^V3TEXTB)` — label doesn't match routinename on 1st line | External `$TEXT` (V3TEXTB's first line has no label matching the routine name) |
| 30259 | III-259 | `$T(@A("ABC")^V3TEXTA8)` — dlabel has indirection | External `$TEXT` + label indirection |
| 30260 | III-260 | `$T(@^V3TEXT(12)^@^V3TEXT)` — both dlabel and routineref have indirection | External `$TEXT` + double indirection |
| 30269 | III-269 | `$T(A+2^@A)` where A="V3TEXTA" — routineref has indirection | External `$TEXT` + routineref indirection |
| 30271 | III-271 | `$T(@@A(1,2,3)+3^V3TEXTA)` — dlabel has double indirection | External `$TEXT` + multi-level indirection |
| 30276 | III-276 | `$T(@ABC(1)+--2^V3TEXTA)` — dlabel has indirection | External `$TEXT` + label indirection |

**Root cause**: **All 9 failures involve `$TEXT` with an external routine reference** (`^routinename`). The `$TEXT(label^routine)` form requires looking up source lines from a different routine file. This requires m2py to:
1. Have access to the source lines of external routines at runtime
2. Support indirection in routine name references for $TEXT
3. Support indirection in label references for $TEXT

The 37 passing tests use `$TEXT` with local references (`$T(+intexpr)`, `$T(label)` within the same routine) which work because `_source_lines` is available for the current routine.

**Fix**: Implement `$TEXT(entryref^routineref)` to look up source lines from other loaded routine modules. The modules already store `_source_lines` and `_label_lines`. A runtime helper could look up the module by name and retrieve its source.

---

## Summary: Root Cause Categories

### Category 1: Expected Pass Counts Wrong (easy fix)
Tests where `expected_passes` counts don't account for commented-out tests:
- **V4QLEN**: 59 → 51 (8 commented out with MVTS LOCAL CHANGE)
- **V4RAND**: 1 → 0 (test entirely commented out)
- **V4MAX**: 7 → 5 (2 commented out: 50-level subscripts)
- **V4SSUB**: 9 → 7 (2 commented out: 79/78-level subscripts)
- **V4QSUB**: 116 → 113 (3 commented out)
- **V2FN2**: 15 → 13 (only 14 VEXAMINE calls, 1 is FAIL90 behavior)
- **V4MERGE**: 36 → 68 (wrong initial count)
- **V1PC**: 20 → 18 + expected_fails=2 (operator tests)

### Category 2: Argumentless FOR inside XECUTE
- **V3FOR**: Nested argumentless FOR in XECUTE string doesn't loop correctly
- Related to all 8 missing V3FOR2 tests

### Category 3: External $TEXT (`$TEXT(label^routine)`)
- **V3TEXT**: 9 fails, all involving `$TEXT` referencing external routines
- Needs runtime lookup of source lines from other loaded modules

### Category 4: Large Number Formatting
- **V4GET2**: 3 fails where `1E25` renders as `"1E+25"` instead of MUMPS canonical form
- `$GET` default value not going through `m_str()`

### Category 5: Subscripted Indirection (`@var@(subs)`)
- **V3DWP**: Test III-1083 uses `@IX@(1)`, `.@IX`, `.@IY` patterns
- **V4QSUB**: Test IV-453 uses `@%2@(%1)` in extrinsic function
- **V4MERGE**: V4MERE helper uses `@V@(subs)` throughout

### Category 6: Deep XECUTE Nesting
- **V3NST1**: 29 levels of XECUTE nesting

### Category 7: Naked Reference Indirection
- **V3INDNM**: `@"^(2)"` combining indirection with naked references

### Category 8: $TEST Preservation
- **V3DWP**: Test III-1084, $TEST not correctly set after DO with parameter passing
