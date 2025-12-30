"""Test script to validate grammar/analyzer findings.

Run with: uv run python utils/test_parse_failures.py
"""

from m2py.parser import MUMPSParser

parser = MUMPSParser()

print("=" * 60)
print("Finding 1: HALT abbreviation 'H' not recognized")
print("=" * 60)

# Test HALT with full spelling
test_halt = "LABEL1 HALT\n"
result = parser.parse(test_halt)
stmts = result.labels[0].body.statements if result.labels else []
print(f"'HALT' -> {len(stmts)} statements:", [type(s).__name__ for s in stmts])

# Test HALT with H abbreviation (no args)
test_h = "LABEL2 H\n"
result = parser.parse(test_h)
stmts = result.labels[0].body.statements if result.labels else []
print(
    f"'H' (should be HALT) -> {len(stmts)} statements:",
    [type(s).__name__ for s in stmts],
)

# Test HANG with H abbreviation (with args)
test_hang = "LABEL3 H 5\n"
result = parser.parse(test_hang)
stmts = result.labels[0].body.statements if result.labels else []
print(f"'H 5' (HANG) -> {len(stmts)} statements:", [type(s).__name__ for s in stmts])

print()
print("=" * 60)
print("Finding 2: JOB indirection not analyzed correctly")
print("=" * 60)

# Test DO with indirection
test_do_ind = "LABEL4 D @VAR\n"
result = parser.parse(test_do_ind)
if result.labels and result.labels[0].body.statements:
    stmt = result.labels[0].body.statements[0]
    call = stmt.targets[0] if hasattr(stmt, "targets") and stmt.targets else None
    print(f"'D @VAR' -> {type(stmt).__name__}")
    if call:
        # MCall uses call_type and indirection
        print(
            f"  indirection: {type(call.indirection).__name__ if hasattr(call, 'indirection') and call.indirection else None}"
        )
else:
    print("'D @VAR' -> No statements")

# Test JOB with indirection
test_job_ind = "LABEL5 J @VAR\n"
result = parser.parse(test_job_ind)
if result.labels and result.labels[0].body.statements:
    stmt = result.labels[0].body.statements[0]
    target = stmt.targets[0] if hasattr(stmt, "targets") and stmt.targets else None
    print(f"'J @VAR' -> {type(stmt).__name__}")
    if target:
        # MJobTarget has call attribute which is MCall
        call = target.call if hasattr(target, "call") else None
        if call:
            print(
                f"  call.indirection: {type(call.indirection).__name__ if hasattr(call, 'indirection') and call.indirection else None}"
            )
else:
    print("'J @VAR' -> No statements")

print()
print("=" * 60)
print("Finding 3: Silent parse failures")
print("=" * 60)

# Test invalid command
test_invalid = "LABEL6 NOTACOMMAND 123\n"
result = parser.parse(test_invalid)
stmts = result.labels[0].body.statements if result.labels else []
print(f"'NOTACOMMAND 123' -> {len(stmts)} statements (silently ignored)")

# Test SET without args (invalid syntax)
test_set_no_args = "LABEL7 SET\n"
result = parser.parse(test_set_no_args)
stmts = result.labels[0].body.statements if result.labels else []
print(f"'SET' (no args, invalid) -> {len(stmts)} statements (silently ignored)")

print()
print("=" * 60)
print("Summary of Issues Found:")
print("=" * 60)
print("1. HALT abbreviation 'H' doesn't parse - grammar fix needed")
print("2. JOB indirection doesn't set label_is_indirect - analyzer fix needed")
print("3. Invalid syntax is silently ignored - error tracking needed")
