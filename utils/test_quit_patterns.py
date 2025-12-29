#!/usr/bin/env python
"""Test script to debug QuitCommand parsing issues."""

import re

from m2py.parser.parser import MUMPSParser

# Simplified patterns - only match UNAMBIGUOUS command starts
PATTERNS = {
    "SET": r"[Ss][Ee][Tt][ \t:]",
    "WRITE": r"[Ww][Rr][Ii][Tt][Ee][ \t:]",
    "READ": r"[Rr][Ee][Aa][Dd][ \t:]",
    "IF": r"[Ii][Ff][ \t:]|[Ii][Ff]$",
    "ELSE": r"[Ee][Ll][Ss][Ee]",
    "FOR": r"[Ff][Oo][Rr][ \t:]",
    "GOTO": r"[Gg][Oo][Tt][Oo][ \t:]",
    "DO": r"[Dd][Oo][ \t:]",
    "QUIT": r"[Qq][Uu][Ii][Tt]",
    "NEW": r"[Nn][Ee][Ww][ \t:]",
    "KILL": r"[Kk][Ii][Ll][Ll][ \t:]",
    "BREAK": r"[Bb][Rr][Ee][Aa][Kk]",
    "JOB": r"[Jj][Oo][Bb][ \t:]",
    "OPEN": r"[Oo][Pp][Ee][Nn][ \t:]",
    "CLOSE": r"[Cc][Ll][Oo][Ss][Ee][ \t:]",
    "USE": r"[Uu][Ss][Ee][ \t:]",
    "HANG": r"[Hh][Aa][Nn][Gg][ \t:]",
    "HALT": r"[Hh][Aa][Ll][Tt]",
    "LOCK": r"[Ll][Oo][Cc][Kk][ \t:]",
    "MERGE": r"[Mm][Ee][Rr][Gg][Ee][ \t:]",
    "VIEW": r"[Vv][Ii][Ee][Ww][ \t:]",
    "XECUTE": r"[Xx][Ee][Cc][Uu][Tt][Ee][ \t:]",
    "POSTCOND": r"[SsWwRrIiFfGgDdQqNnKkBbJjOoCcUuLlMmVvXxEeHh]:",
}

test_strings = ["S=1", "X S Y=1", "S=1,Y=2", "X", "X=1", "S Y=1", "S:0 X"]
print("Testing CommandWithArg patterns (simplified):")
for s in test_strings:
    print(f"\n  Input: '{s}'")
    any_match = False
    for name, pattern in PATTERNS.items():
        match = re.match(pattern, s)
        if match:
            any_match = True
            print(f"    MATCH {name}: '{match.group()}'")
    if not any_match:
        print("    NO MATCH - This would be treated as QUIT's value!")

print("\n\n=== Testing actual parsing ===")

parser = MUMPSParser()

test_cases = [
    (" Q S=1\n", "QUIT with value S=1 (comparison expression)"),
    (" Q X S Y=1\n", "QUIT X then SET Y=1"),
    (" Q S=1,Y=2\n", "QUIT with value S=1,Y=2 (comparison expressions)"),
    (" Q S\n", "QUIT with value S"),
    (" Q  S Y=1\n", "QUIT with no value, then SET Y=1"),
]

for code, expected in test_cases:
    print(f"\n  Input: '{code}'")
    print(f"  Expected: {expected}")
    try:
        routine = parser.parse(code)
        # Get statements from first label's body
        if routine.labels:
            label = routine.labels[0]
            if hasattr(label, "body") and label.body:
                stmts = (
                    label.body.statements if hasattr(label.body, "statements") else []
                )
                stmt_names = [type(s).__name__ for s in stmts]
                print(f"  Result: {stmt_names}")
                # Check for QUIT return value
                for stmt in stmts:
                    if type(stmt).__name__ == "MQuitStatement":
                        if hasattr(stmt, "value") and stmt.value:
                            from m2py.codegen.expr import _generate_expr

                            value = _generate_expr(stmt.value)
                            print(f"  QUIT value: {value}")
                        else:
                            print("  QUIT: no return value")
            else:
                print("  Result: No body found")
        else:
            print("  Result: No labels found")
    except Exception as e:
        import traceback

        print(f"  ERROR: {e}")
        traceback.print_exc()
