# Test Contracts: VistA-VEHU-M Transpilation Fixes

**Feature**: 024-vista-transpilation-fixes | **Date**: 2026-02-17

Each contract defines a MUMPS input, expected output (validated against YDB or IRIS), and the fix it validates. Tests should be implemented as pytest tests using m2py's transpile-and-execute pattern.

---

## Contract 1: ParenExpr Handling

**Validates**: FR-001 (ParenExpr codegen fallback)

```mumps
PAREN
 S X=3,Y=4
 S Z=(X+Y)*2
 W Z,!
 S A=((X+Y))
 W A,!
 Q
```

**Expected Output**: `14\n7\n`

**Test Strategy**: Transpile and execute. Also transpile `VistA-VEHU-M/Packages/Accounts Receivable/Routines/PRCACV10.m` — must not raise `NotImplementedError`.

---

## Contract 2: f-string Nested Quotes (Python 3.10)

**Validates**: FR-002 (no nested matching quotes in f-strings)

```mumps
FSTR1
 S Y="Y"
 S Y(1)="found"
 S X="1^2" I $D(@Y@($P(X,"^",1))) W "yes",!
 Q
```

**Expected Output**: `yes\n`

**Test Strategy**: Transpile, then `compile()` the generated Python on Python 3.10 — must not raise `SyntaxError`. Then execute and verify output.

---

## Contract 3: Empty Indented Block (TRAMPOLINE)

**Validates**: FR-003 (no empty if bodies)

```mumps
EMPTYB
 S X=1 I X G DONE
 W "not reached",!
DONE W "done",!
 Q
```

**Expected Output**: `done\n`

**Test Strategy**: Transpile (will use TRAMPOLINE due to GOTO). `compile()` must succeed. Execute and verify output.

---

## Contract 4: >= and <= Operators

**Validates**: FR-004

```mumps
CMPOP
 I 5>=3 W "5>=3:yes",!
 I 3>=5 W "3>=5:yes",!
 I 5>=5 W "5>=5:yes",!
 I 3<=5 W "3<=5:yes",!
 I 5<=3 W "5<=3:yes",!
 I 5<=5 W "5<=5:yes",!
 Q
```

**Expected Output**: `5>=3:yes\n5>=5:yes\n3<=5:yes\n5<=5:yes\n`

---

## Contract 5: SET $X and SET $Y

**Validates**: FR-005

```mumps
SETXY
 S $X=0 W $X,!
 S $Y=0 W $Y,!
 Q
```

**Expected Output**: `0\n0\n` (validated against YDB — WRITE updates $X/$Y after output, so SET $X=0 followed by W $X prints 0)

---

## Contract 6: LHS $EXTRACT 1-Argument

**Validates**: FR-006

```mumps
EXT1A
 S X="hello" S $E(X)="H" W X,!
 S X="abc" S $E(X)="Z" W X,!
 Q
```

**Expected Output**: `Hello\nZbc\n`

---

## Contract 7: Tuple SET with $PIECE Target

**Validates**: FR-007

```mumps
TUPLEP
 S X="A^B^C" S ($P(X,"^",2),Y)="Z" W X,!,Y,!
 Q
```

**Expected Output**: `A^Z^C\nZ\n`

---

## Contract 8: NEW Indirection (TRAMPOLINE)

**Validates**: FR-008

```mumps
NEWIND
 S X="hello"
 D SUB
 W X,!
 Q
SUB N @"X"
 S X="world"
 Q
```

**Expected Output**: `hello\n` (X is NEW'd indirectly, so the outer X is preserved)

---

## Contract 9: Computed GOTO

**Validates**: FR-009

```mumps
CGOTO
 S %=2 G @$S(%=1:"A",%=2:"B",1:"C")
A W "A",! Q
B W "B",! Q
C W "C",! Q
```

**Expected Output**: `B\n`

---

## Contract 10: RecursionError Prevention

**Validates**: FR-010

**Test Strategy**: Transpile `PSXRECV.m` from VistA-VEHU-M CMOP package. Must not raise `RecursionError`.

---

## Contract 11: ZLOAD Handling

**Validates**: FR-011

```mumps
ZLOAD1
 ZL "SOMEFILE"
 W "ok",!
 Q
```

**Expected Output**: `ok\n` (ZLOAD is a no-op stub)

---

## Contract 12: $REPLACE

**Validates**: FR-013

```mumps
REPL
 W $REPLACE("hello world","world","earth"),!
 W $REPLACE("aXbXc","X",""),!
 W $REPLACE("abc","","x"),!
 W $REPLACE("aXbXcXd","X","-",1,2),!
 W $REPLACE("Hello HELLO hello","hello","X",1,-1,1),!
 W $REPLACE("Hello World","o","0",5),!
 Q
```

**Expected Output**:
```
hello earth
abc
abc
a-b-cXd
X X X
0 W0rld
```

---

## Contract 13: $ZBOOLEAN

**Validates**: FR-014

```mumps
ZBOOL
 W $ZBOOLEAN(3,5,1),!
 W $ZBOOLEAN(3,5,6),!
 W $ZBOOLEAN(3,5,7),!
 W $ZBOOLEAN(5,5,12),!
 W $ZBOOLEAN(3,5,0),!
 W $ZBOOLEAN(3,5,15),!
 W $ZBOOLEAN("abcd","_",1),!
 Q
```

**Expected Output**: `1\n6\n7\n-6\n0\n-1\nABCD\n`

---

## Contract 14: $ZVERSION

**Validates**: FR-015

```mumps
ZVER
 W $L($ZV)>0,!
 Q
```

**Expected Output**: `1\n`

---

## Contract 15: $ZF(-1)

**Validates**: FR-016

```mumps
ZFM1
 S X=$ZF(-1,"echo test > /dev/null") W X,!
 Q
```

**Expected Output**: `0\n`

---

## Contract 16: $ZA

**Validates**: FR-017

```mumps
ZAST
 W $ZA,!
 Q
```

**Expected Output**: `0\n`

---

## Contract 17: $ZREFERENCE

**Validates**: FR-018

```mumps
ZREF
 S ^ZZTEST(1,2)="hello" W $ZR,!
 K ^ZZTEST
 Q
```

**Expected Output**: `^ZZTEST(1,2)\n`

---

## Contract 18: $NAMESPACE

**Validates**: FR-019

```mumps
NSPC
 W $NAMESPACE,!
 Q
```

**Expected Output**: `VISTA\n` (configurable)

---

## Contract 19: $ZU

**Validates**: FR-020

```mumps
ZU168
 W $L($ZU(168))>0,!
 Q
```

**Expected Output**: `1\n`

---

## Contract 20: UnaryPrefixedExpr

**Validates**: FR-026

**Test Strategy**: Transpile `VistA-VEHU-M/Packages/Consult Request Tracking/Routines/GMRCIAC2.m`. Line 227 contains `Q:'CRNR!('$T(@+ERR))` where `+ERR` is parsed as `UnaryPrefixedExpr` and leaks through to codegen in the `$TEXT` label indirection context. Must not raise `NotImplementedError`.

---

## Contract 21: Full VistA Scan

**Validates**: SC-001, SC-003, SC-004, SC-005

**Test Strategy**: Run the full VistA-VEHU-M transpilation scan (39,304 routines). Assert:
- Success rate ≥ 99%
- Zero SyntaxError failures
- Zero NotImplementedError failures (except MWAPI)
- Zero RecursionError failures
