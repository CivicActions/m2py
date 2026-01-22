#!/usr/bin/env python3
"""Categorize functional test failures by error type."""

import re
from pathlib import Path


def parse_failure_output(filepath: str) -> dict:
    """Parse pytest output and categorize failures."""
    content = Path(filepath).read_text()

    # Map test names to their error types
    test_errors = {}

    # Pattern to match test failures with errors
    # E   Failed: Routine X failed to execute: ErrorType: message
    execute_pattern = (
        r"E\s+Failed: Routine (\w+) failed to execute: (\w+(?:Error)?): (.+)"
    )

    # Pattern to match "No result for X" failures
    no_result_pattern = r"E\s+Failed: No result for (\w+)"

    # Pattern to match assertion errors (output mismatches)
    # FAILED tests/functional/test_*.py::TestClass::test_method[routine_name]
    failed_test_pattern = r"FAILED tests/functional/test_\w+\.py::\w+::\w+\[(\w+)\]"

    # Find all failed tests
    all_failed = set(re.findall(failed_test_pattern, content))

    # Find execution errors
    for match in re.finditer(execute_pattern, content):
        routine, error_type, message = match.groups()
        message = message.strip()
        test_errors[routine.lower()] = {
            "type": "execute_error",
            "error_class": error_type,
            "message": message,
        }

    # Find no result errors
    for match in re.finditer(no_result_pattern, content):
        routine = match.group(1)
        test_errors[routine.lower()] = {
            "type": "no_result",
            "error_class": "NoResult",
            "message": f"No result for {routine}",
        }

    # Find output mismatches (failures not in execute errors or no_result)
    for test in all_failed:
        key = test.lower()
        if key not in test_errors:
            test_errors[key] = {
                "type": "output_mismatch",
                "error_class": "AssertionError",
                "message": "Output does not match expected",
            }

    return test_errors


def categorize_errors(test_errors: dict) -> dict:
    """Categorize errors into groups."""
    categories = {
        # Category 1: Documented Limitations (xfail candidates)
        "LIM-015: ZSYSTEM/Z-commands": [],
        "LIM-015: $ZTRAP related": [],
        "LIM-015: Z-functions": [],
        # Category 2: TRAMPOLINE strategy limitations
        "TRAMPOLINE: Argumentless KILL": [],
        "TRAMPOLINE: Argumentless NEW": [],
        # Category 3: Other NotImplementedError (functional gaps)
        "FUNCTIONAL_GAP: Special Variables": [],
        "FUNCTIONAL_GAP: Intrinsic Functions": [],
        "FUNCTIONAL_GAP: Operators": [],
        "FUNCTIONAL_GAP: Expression Types": [],
        "FUNCTIONAL_GAP: SET Target Types": [],
        "FUNCTIONAL_GAP: LHS $PIECE": [],
        "FUNCTIONAL_GAP: UNRESOLVED GOTO": [],
        # Category 4: Code Generation Errors
        "CODEGEN: SyntaxError": [],
        # Category 5: External dependencies
        "EXTERNAL: No Result (external routines)": [],
        # Category 6: Output mismatches (behavioral bugs)
        "BEHAVIORAL: Output Mismatch": [],
    }

    for test, info in test_errors.items():
        msg = info["message"]
        error_class = info["error_class"]

        # LIM-015 explicit
        if "LIM-015: ZSYSTEM" in msg:
            categories["LIM-015: ZSYSTEM/Z-commands"].append(test)
        elif "$ZTRAP" in msg or "$zt" in msg:
            categories["LIM-015: $ZTRAP related"].append(test)
        elif "$ZVersion" in msg or "$ZPREVIOUS" in msg:
            categories["LIM-015: Z-functions"].append(test)
        elif "$ZPOSITION" in msg:
            categories["FUNCTIONAL_GAP: Special Variables"].append(test)
        # TRAMPOLINE limitations
        elif "Argumentless KILL not supported in TRAMPOLINE" in msg:
            categories["TRAMPOLINE: Argumentless KILL"].append(test)
        elif "Argumentless NEW not supported in TRAMPOLINE" in msg:
            categories["TRAMPOLINE: Argumentless NEW"].append(test)
        # Other special variables
        elif "Special variable" in msg:
            categories["FUNCTIONAL_GAP: Special Variables"].append(test)
        # Intrinsic functions
        elif "Intrinsic function" in msg:
            categories["FUNCTIONAL_GAP: Intrinsic Functions"].append(test)
        # Operators
        elif "Unsupported binary operator" in msg:
            categories["FUNCTIONAL_GAP: Operators"].append(test)
        # Expression types
        elif "Unsupported expression type" in msg:
            categories["FUNCTIONAL_GAP: Expression Types"].append(test)
        # SET target types
        elif "Unsupported SET target type" in msg:
            categories["FUNCTIONAL_GAP: SET Target Types"].append(test)
        # LHS $PIECE
        elif "LHS $PIECE" in msg:
            categories["FUNCTIONAL_GAP: LHS $PIECE"].append(test)
        # UNRESOLVED GOTO
        elif "UNRESOLVED GOTO" in msg:
            categories["FUNCTIONAL_GAP: UNRESOLVED GOTO"].append(test)
        # SyntaxError
        elif error_class == "SyntaxError":
            categories["CODEGEN: SyntaxError"].append(test)
        # No result
        elif info["type"] == "no_result":
            categories["EXTERNAL: No Result (external routines)"].append(test)
        # Output mismatch
        elif info["type"] == "output_mismatch":
            categories["BEHAVIORAL: Output Mismatch"].append(test)
        else:
            # Catch-all for uncategorized
            print(f"UNCATEGORIZED: {test} - {msg}")

    return categories


def main():
    test_errors = parse_failure_output("tmp/all_failures.txt")
    categories = categorize_errors(test_errors)

    print("=" * 70)
    print("FUNCTIONAL TEST FAILURE CATEGORIZATION")
    print("=" * 70)
    print()

    total = 0

    # Group categories by type
    xfail_count = 0
    xfail_categories = {}
    gap_count = 0
    gap_categories = {}
    other_count = 0
    other_categories = {}

    for cat, tests in categories.items():
        if not tests:
            continue
        count = len(tests)
        total += count

        if cat.startswith("LIM-015"):
            xfail_count += count
            xfail_categories[cat] = tests
        elif cat.startswith("TRAMPOLINE"):
            # These are architectural limitations, should be xfail
            xfail_count += count
            xfail_categories[cat] = tests
        elif cat.startswith("FUNCTIONAL_GAP"):
            gap_count += count
            gap_categories[cat] = tests
        else:
            other_count += count
            other_categories[cat] = tests

    print("SECTION 1: XFAIL CANDIDATES (Known Limitations)")
    print("-" * 70)
    for cat, tests in sorted(xfail_categories.items()):
        print(f"\n{cat} ({len(tests)} tests):")
        for t in sorted(tests):
            print(f"  - {t}")
    print(f"\n  SUBTOTAL: {xfail_count} tests")

    print()
    print("SECTION 2: FUNCTIONAL GAPS (Need Implementation)")
    print("-" * 70)
    for cat, tests in sorted(gap_categories.items()):
        print(f"\n{cat} ({len(tests)} tests):")
        for t in sorted(tests):
            print(f"  - {t}")
    print(f"\n  SUBTOTAL: {gap_count} tests")

    print()
    print("SECTION 3: OTHER FAILURES")
    print("-" * 70)
    for cat, tests in sorted(other_categories.items()):
        print(f"\n{cat} ({len(tests)} tests):")
        for t in sorted(tests):
            print(f"  - {t}")
    print(f"\n  SUBTOTAL: {other_count} tests")

    print()
    print("=" * 70)
    print(f"TOTAL: {total} tests categorized")
    print("=" * 70)


if __name__ == "__main__":
    main()
