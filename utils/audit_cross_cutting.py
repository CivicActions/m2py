#!/usr/bin/env python3
"""Focused audit of cross-cutting tests for duplicates with spec-aligned tests.

This script identifies specific test functions and their assertion checks
that duplicate what exists in spec-aligned test files.
"""

import ast
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DuplicateCase:
    """A specific duplication case."""

    cross_cutting_file: str
    cross_cutting_test: str
    cross_cutting_checks: list[str]
    spec_aligned_file: str
    spec_aligned_test: str
    spec_aligned_checks: list[str]
    recommendation: str


def extract_checks_from_function(
    node: ast.FunctionDef, source_lines: list[str]
) -> list[str]:
    """Extract all assertion statements from a test function."""
    checks = []
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            try:
                # Get the line of the assertion
                if child.lineno and child.end_lineno:
                    assertion_lines = source_lines[child.lineno - 1 : child.end_lineno]
                    assertion = "\n".join(line.strip() for line in assertion_lines)
                    checks.append(assertion)
            except Exception:
                pass
    return checks


def extract_mumps_code(func_source: str) -> list[str]:
    """Extract MUMPS code patterns from function source."""
    patterns = []
    # Match various parse function calls
    for match in re.finditer(
        r'(?:parse_expression|analyze_routine|parser\.parse|analyze_first_command)\s*\(\s*["\']([^"\']+)["\']',
        func_source,
    ):
        patterns.append(match.group(1))
    return patterns


def analyze_test_file(filepath: Path) -> dict:
    """Analyze a test file and extract test function details."""
    with open(filepath) as f:
        content = f.read()
        source_lines = content.split("\n")

    tree = ast.parse(content)
    tests = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            func_source = ast.unparse(node)
            mumps_codes = extract_mumps_code(func_source)
            checks = extract_checks_from_function(node, source_lines)
            docstring = ast.get_docstring(node) or ""

            tests[node.name] = {
                "mumps_codes": mumps_codes,
                "checks": checks,
                "docstring": docstring,
                "line": node.lineno,
            }

    return tests


def find_duplicates():
    """Find duplicates between cross-cutting and spec-aligned tests."""
    tests_dir = Path("tests/unit")

    # Analyze cross-cutting tests
    cross_cutting_tests = {}
    for f in (tests_dir / "cross_cutting").glob("test_*.py"):
        cross_cutting_tests[f.name] = analyze_test_file(f)

    # Analyze spec-aligned tests
    spec_aligned_tests = {}
    for subdir in ["asg/s6_routine", "asg/s7_expressions", "asg/s8_commands"]:
        dir_path = tests_dir / subdir
        if dir_path.exists():
            for f in dir_path.glob("test_*.py"):
                spec_aligned_tests[str(f.relative_to(tests_dir))] = analyze_test_file(f)

    # Mapping of cross-cutting tests to their spec-aligned equivalents
    mappings = [
        {
            "cross_cutting": (
                "test_indirection.py",
                "test_name_indirection_in_set_target",
            ),
            "spec_aligned": (
                "asg/s7_expressions/test_s7_3_indirection.py",
                "test_indirection_in_set",
            ),
            "reason": "Both test SET @VAR=1 parsing with identical assertions",
        },
        {
            "cross_cutting": (
                "test_indirection.py",
                "test_subscripted_name_indirection",
            ),
            "spec_aligned": (
                "asg/s7_expressions/test_s7_3_indirection.py",
                "test_subscript_indirection",
            ),
            "reason": "Both test @X@(1,2) subscript indirection with same assertions",
        },
        {
            "cross_cutting": ("test_indirection.py", "test_chained_name_indirection"),
            "spec_aligned": (
                "asg/s7_expressions/test_s7_3_indirection.py",
                "test_nested_indirection",
            ),
            "reason": "Both test @@X nested indirection with same assertions",
        },
        {
            "cross_cutting": ("test_indirection.py", "test_pattern_indirection_basic"),
            "spec_aligned": (
                "asg/s7_expressions/test_s7_2_5_pattern_match.py",
                "test_pattern_indirection",
            ),
            "reason": "Both test X?@PAT pattern indirection",
        },
        {
            "cross_cutting": (
                "test_indirection.py",
                "test_subscripted_indirection_subscripts_resolved",
            ),
            "spec_aligned": (
                "asg/s6_routine/test_s6_3_1_indirection.py",
                "test_argument_indirection_resolution",
            ),
            "reason": "Both test @X@(1,2) subscript indirection ASG",
        },
        {
            "cross_cutting": (
                "test_indirection.py",
                "test_pattern_indirection_classified",
            ),
            "spec_aligned": (
                "asg/s6_routine/test_s6_3_1_indirection.py",
                "test_pattern_indirection_resolution",
            ),
            "reason": "Both test pattern indirection classification",
        },
        {
            "cross_cutting": (
                "test_postconditions.py",
                "test_command_postcondition_in_asg",
            ),
            "spec_aligned": (
                "asg/s8_commands/test_s8_1_general_rules.py",
                "test_postcondition_analysis",
            ),
            "reason": "Both test S:X=1 Y=2 postcondition ASG analysis",
        },
        {
            "cross_cutting": ("test_naked_references.py", "test_naked_reference_basic"),
            "spec_aligned": (
                "asg/s7_expressions/test_s7_1_2_variables.py",
                "test_naked_global_reference",
            ),
            "reason": "Both test ^(sub) naked reference ASG",
        },
    ]

    print("=" * 80)
    print("DUPLICATE TEST ANALYSIS REPORT")
    print("=" * 80)
    print()

    for mapping in mappings:
        cc_file, cc_test = mapping["cross_cutting"]
        sa_file, sa_test = mapping["spec_aligned"]
        reason = mapping["reason"]

        # Get test details if available
        cc_tests = cross_cutting_tests.get(cc_file, {})
        cc_info = cc_tests.get(cc_test, {})

        sa_tests = spec_aligned_tests.get(sa_file, {})
        sa_info = sa_tests.get(sa_test, {})

        print(f"DUPLICATE: {cc_file}::{cc_test}")
        print(f"  Duplicates: {sa_file}::{sa_test}")
        print(f"  Reason: {reason}")

        if cc_info.get("mumps_codes"):
            print(f"  Cross-cutting MUMPS: {cc_info['mumps_codes'][:2]}")
        if sa_info.get("mumps_codes"):
            print(f"  Spec-aligned MUMPS: {sa_info['mumps_codes'][:2]}")

        if cc_info.get("checks") and sa_info.get("checks"):
            # Find overlapping checks
            cc_checks = set(cc_info["checks"])
            sa_checks = set(sa_info["checks"])

            # Normalize for comparison
            def normalize(s):
                return re.sub(r"\s+", " ", s).strip()

            cc_normalized = {normalize(c) for c in cc_checks}
            sa_normalized = {normalize(c) for c in sa_checks}

            overlapping = cc_normalized & sa_normalized
            if overlapping:
                print(f"  Overlapping checks ({len(overlapping)}):")
                for check in list(overlapping)[:3]:
                    print(f"    - {check[:60]}...")

        print()

    print()
    print("=" * 80)
    print("RECOMMENDED ACTIONS")
    print("=" * 80)
    print()
    print("1. test_indirection.py - Most tests duplicate spec-aligned tests:")
    print(
        "   - TestNameIndirectionParser duplicates asg/s7_expressions/test_s7_3_indirection.py"
    )
    print(
        "   - TestPatternIndirectionParser duplicates asg/s7_expressions/test_s7_2_5_pattern_match.py"
    )
    print(
        "   - TestNameIndirectionASG duplicates asg/s6_routine/test_s6_3_1_indirection.py"
    )
    print(
        "   - TestPatternIndirectionASG duplicates asg/s6_routine/test_s6_3_1_indirection.py"
    )
    print()
    print("   RECOMMENDATION: Move unique cross-cutting checks to spec-aligned files,")
    print("   then delete duplicate test functions. Keep only tests that truly test")
    print("   cross-cutting behavior not covered by section-specific tests.")
    print()
    print("2. test_postconditions.py:")
    print(
        "   - test_command_postcondition_in_asg duplicates test_s8_1_general_rules.py::test_postcondition_analysis"
    )
    print(
        "   - Consider consolidating all postcondition ASG tests into s8_commands tests"
    )
    print()
    print("3. test_naked_references.py:")
    print(
        "   - test_naked_reference_basic duplicates test_s7_1_2_variables.py::test_naked_global_reference"
    )
    print("   - Keep naked reference sequence/dependency tests (truly cross-cutting)")
    print()


if __name__ == "__main__":
    find_duplicates()
