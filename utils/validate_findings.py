#!/usr/bin/env python
"""Validation script for MUMPS parser audit findings."""

from m2py.parser.parser import MUMPSParser

parser = MUMPSParser()


def test_parse(name: str, code: str, expected_success: bool = True):
    """Test if a MUMPS code snippet parses successfully."""
    full_code = (
        f" {code}\n" if not code.endswith("\n") else f" {code}"
    )  # Add line start space
    try:
        _result = parser.parse(full_code)
        if expected_success:
            print(f"✅ {name}: `{code}` -> parsed successfully")
            return True
        else:
            print(f"❌ {name}: `{code}` -> parsed (but expected failure)")
            return False
    except Exception as e:
        if expected_success:
            print(f"❌ {name}: `{code}` -> failed: {type(e).__name__}: {e}")
            return False
        else:
            print(f"✅ {name}: `{code}` -> failed as expected")
            return True


print("=" * 70)
print("FINDING 1: SET $X (Special Variable as LHS)")
print("=" * 70)

# Test SET $X - per spec, this should work
test_parse("SET $X=0", "S $X=0", expected_success=True)
test_parse("SET $Y=10", "S $Y=10", expected_success=True)
test_parse('SET $ECODE=",M1,"', 'S $EC=",M1,"', expected_success=True)
test_parse("SET $ETRAP=code", 'S $ET="G ERR"', expected_success=True)

# These should already work - $PIECE on LHS
test_parse("SET $P on LHS", 'S $P(X,"^",2)="val"', expected_success=True)
test_parse("SET $E on LHS", 'S $E(X,1,3)="ABC"', expected_success=True)

print()
print("=" * 70)
print("FINDING 2: TSTART with empty list")
print("=" * 70)

test_parse("TSTART no args", "TS", expected_success=True)
test_parse("TSTART with star", "TS *", expected_success=True)
test_parse("TSTART with vars", "TS (A,B)", expected_success=True)
test_parse("TSTART empty list", "TS ()", expected_success=True)  # This may fail

print()
print("=" * 70)
print("FINDING 3: OPEN with mnemonic spec")
print("=" * 70)

# Standard OPEN syntax that should work
test_parse("OPEN simple", "O 1", expected_success=True)
test_parse("OPEN with timeout", "O 1:5", expected_success=True)
test_parse("OPEN with params", "O 1:(param)", expected_success=True)
test_parse("OPEN with params+timeout", "O 1:(param):5", expected_success=True)

# With mnemonic spec
test_parse("OPEN with mnemonic", 'O 1:(param):5:"MNE"', expected_success=True)
test_parse("OPEN double colon mnemonic", 'O 1::"MNE"', expected_success=True)

print()
print("=" * 70)
print("FINDING 4: Structured System Variables (SSVs)")
print("=" * 70)

test_parse("SSV ^$DEVICE", "W ^$DEVICE", expected_success=True)
test_parse("SSV ^$JOB", "W ^$JOB(1)", expected_success=True)
test_parse("SSV ^$GLOBAL", "W ^$GLOBAL", expected_success=True)

print()
print("=" * 70)
print("FINDING 5: ISV $IOReference")
print("=" * 70)

# Check if $IOReference is in the grammar - it might not be standard
test_parse("ISV $IO (standard)", "W $IO", expected_success=True)
test_parse("ISV $IOR (extended?)", "W $IOR", expected_success=True)
test_parse("ISV $IOREFERENCE", "W $IOREFERENCE", expected_success=True)

print()
