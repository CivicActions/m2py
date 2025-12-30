#!/usr/bin/env python3
"""Validate Issue #1: Silent Parse Errors behavior."""

from m2py.parser.line_parser import parse_line_content, parse_commands_from_line
from m2py.parser import MUMPSParser

# Test 1: Valid line
print("=== Test 1: Valid line ===")
result = parse_line_content("S X=1 W X")
print(f"parse_line_content('S X=1 W X'): {result}")
print(f"Type: {type(result)}")

# Test 2: Invalid syntax
print("\n=== Test 2: Invalid syntax ===")
result = parse_line_content("S X=!@#$%^&*")
print(f"parse_line_content('S X=!@#$%^&*'): {result}")

# Test 3: Parse commands from invalid line
print("\n=== Test 3: parse_commands_from_line with invalid ===")
result = parse_commands_from_line("S X=!@#$%^&*")
print(f"parse_commands_from_line('S X=!@#$%^&*'): {result}")

# Test 4: Parse full routine with one bad line
print("\n=== Test 4: Full routine with invalid line ===")
source = """ROUTINE
 S X=1
 S Y=@#$INVALID
 S Z=3
 Q
"""
parser = MUMPSParser()
try:
    routine = parser.parse(source, filename="test.m")
    print("Routine parsed successfully!")
    print(f"Labels: {[lbl.name for lbl in routine.labels]}")
    for label in routine.labels:
        print(f"  Label '{label.name}' has {len(label.body.statements)} statements")
        for i, stmt in enumerate(label.body.statements):
            print(f"    Statement {i}: {type(stmt).__name__}")
except Exception as e:
    print(f"Parse error: {e}")

# Test 5: What does line 3 look like when parsed alone?
print("\n=== Test 5: What happens to the invalid line? ===")
result = parse_commands_from_line("S Y=@#$INVALID")
print(f"'S Y=@#$INVALID' -> {result}")

# Test 6: Another common error - unbalanced parens
print("\n=== Test 6: Unbalanced parens ===")
result = parse_commands_from_line('S X=$P(A,"^",1')  # Missing closing paren
print(f"'S X=$P(A,\"^\",1' -> {result}")

# Test 7: Unknown command
print("\n=== Test 7: Unknown command ===")
result = parse_commands_from_line("FOOBAR X=1")
print(f"'FOOBAR X=1' -> {result}")
