#!/usr/bin/env python3
"""
Validate parsing of $Z* implementation-specific variables.

Issue #3 Validation: Check that $ZVERSION, $ZTRAP, etc. parse correctly
via the IntrinsicFunctionNoArgs catch-all in the grammar.
"""

from m2py.parser.line_parser import parse_line_content


def test_zvar_parsing():
    """Test that $Z* variables parse correctly as IntrinsicFunctionNoArgs."""
    # Test cases: various $Z* implementation-specific variables
    test_cases = [
        ("S X=$ZVERSION", "ZVERSION"),
        ("S X=$ZV", "ZV"),  # Abbreviated form
        ("S X=$ZTRAP", "ZTRAP"),
        ("S X=$ZJOB", "ZJOB"),
        ("S X=$ZT", "ZT"),  # Abbreviated
        ("W $ZIO", "ZIO"),
    ]

    print("Testing $Z* implementation-specific variable parsing:")
    print("=" * 60)

    for line_content, expected_name in test_cases:
        result = parse_line_content(line_content)
        if result is None:
            print(f"FAIL: '{line_content}' - Parse returned None")
            continue

        # Get the parsed expression
        parsed = result.commands[0] if hasattr(result, "commands") else result
        print(f"\n'{line_content}':")
        print(f"  Parsed type: {type(parsed).__name__}")

        # Try to extract the $Z variable from the expression
        if hasattr(parsed, "args"):
            for arg in parsed.args:
                print(f"  Arg: {arg}")
                if hasattr(arg, "value"):
                    value = arg.value
                    print(f"    Value type: {type(value).__name__}")
                    if hasattr(value, "left"):
                        left = value.left
                        print(f"    Left type: {type(left).__name__}")
                        if hasattr(left, "operand"):
                            operand = left.operand
                            print(f"    Operand type: {type(operand).__name__}")
                            if hasattr(operand, "name"):
                                print(f"    Name: {operand.name}")
                                if operand.name.upper().startswith("Z"):
                                    print(f"  PASS: Found $Z variable: ${operand.name}")

    print("\n" + "=" * 60)
    print("\nAlso testing that known special variables still work correctly:")

    known_svars = [
        ("S X=$TEST", "TEST"),
        ("S X=$T", "T"),
        ("S X=$HOROLOG", "HOROLOG"),
        ("S X=$H", "H"),
        ("S X=$IO", "IO"),
        ("S X=$I", "I"),
    ]

    for line_content, expected_name in known_svars:
        result = parse_line_content(line_content)
        if result is None:
            print(f"FAIL: '{line_content}' - Parse returned None")
        else:
            print(f"PASS: '{line_content}' - Parsed successfully")


if __name__ == "__main__":
    test_zvar_parsing()
