#!/usr/bin/env python3
"""Audit unit tests for duplicate or partially duplicate checks.

This utility scans test files to identify:
1. Duplicate MUMPS code snippets being tested
2. Duplicate assertion patterns
3. Tests that overlap with spec-aligned tests

Spec-aligned tests are identified by:
- File name containing section references (s6_, s7_, s8_)
- Docstrings containing § section references
"""

import ast
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TestCheck:
    """Represents a single test check (assertion)."""

    file: str
    test_class: str
    test_method: str
    line_no: int
    assertion_type: str  # e.g., "assert", "assert isinstance", "assert ==", etc.
    code_pattern: str  # The actual assertion code
    mumps_code: Optional[str] = None  # MUMPS code being tested if detectable
    is_spec_aligned: bool = False
    spec_section: Optional[str] = None


@dataclass
class TestPattern:
    """A pattern that may indicate duplicate tests."""

    pattern_type: str  # "mumps_code", "assertion", "variable_check"
    pattern_value: str
    checks: list[TestCheck] = field(default_factory=list)


def is_spec_aligned_file(filepath: str) -> bool:
    """Check if file is spec-aligned based on naming convention."""
    basename = os.path.basename(filepath)
    # Match patterns like test_s6_3_1_indirection.py, test_s7_2_operators.py
    return bool(re.search(r"test_s[567]_\d", basename))


def extract_spec_section(docstring: str) -> Optional[str]:
    """Extract MUMPS spec section reference from docstring."""
    if not docstring:
        return None
    # Match patterns like (§7.3.1), §6.3.1, Section 7.2.5
    patterns = [
        r"§(\d+\.[\d.]+)",
        r"\(§(\d+\.[\d.]+)\)",
        r"Section\s+(\d+\.[\d.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, docstring)
        if match:
            return f"§{match.group(1)}"
    return None


def extract_mumps_code(source: str) -> list[str]:
    """Extract MUMPS code snippets from test source."""
    mumps_patterns = []

    # Pattern 1: parser.parse("...") or parse_routine("...")
    parse_calls = re.findall(r'parse(?:_routine)?\s*\(\s*["\']([^"\']+)["\']', source)
    mumps_patterns.extend(parse_calls)

    # Pattern 2: parse_expression("...")
    expr_calls = re.findall(r'parse_expression\s*\(\s*["\']([^"\']+)["\']', source)
    mumps_patterns.extend(expr_calls)

    # Pattern 3: analyze_routine("...")
    analyze_calls = re.findall(r'analyze_routine\s*\(\s*["\']([^"\']+)["\']', source)
    mumps_patterns.extend(analyze_calls)

    return mumps_patterns


def normalize_mumps(code: str) -> str:
    """Normalize MUMPS code for comparison."""
    # Remove leading label (TEST\n, etc.)
    code = re.sub(r"^[A-Z]+\\n\s*", "", code)
    # Remove trailing whitespace/newlines
    code = code.strip()
    # Normalize whitespace
    code = re.sub(r"\s+", " ", code)
    return code


class TestFileAnalyzer(ast.NodeVisitor):
    """Analyze a test file to extract test checks."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.relative_path = os.path.relpath(filepath, Path(__file__).parent.parent)
        self.checks: list[TestCheck] = []
        self.current_class = ""
        self.current_method = ""
        self.current_method_docstring = ""
        self.current_method_source = ""
        self.is_spec_file = is_spec_aligned_file(filepath)

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        if not node.name.startswith("test_"):
            return

        old_method = self.current_method
        old_docstring = self.current_method_docstring

        self.current_method = node.name
        self.current_method_docstring = ast.get_docstring(node) or ""

        # Extract the source code of the method
        try:
            with open(self.filepath, "r") as f:
                lines = f.readlines()
                start = node.lineno - 1
                end = node.end_lineno
                self.current_method_source = "".join(lines[start:end])
        except Exception:
            self.current_method_source = ""

        self.generic_visit(node)

        self.current_method = old_method
        self.current_method_docstring = old_docstring

    def visit_Assert(self, node):
        """Process an assert statement."""
        if not self.current_method:
            return

        # Get the assertion code as string
        try:
            code = ast.unparse(node)
        except Exception:
            code = f"assert @ line {node.lineno}"

        # Classify the assertion
        assertion_type = self._classify_assertion(node)

        # Extract MUMPS code if present in method
        mumps_codes = extract_mumps_code(self.current_method_source)

        check = TestCheck(
            file=self.relative_path,
            test_class=self.current_class,
            test_method=self.current_method,
            line_no=node.lineno,
            assertion_type=assertion_type,
            code_pattern=code,
            mumps_code=mumps_codes[0] if mumps_codes else None,
            is_spec_aligned=self.is_spec_file,
            spec_section=extract_spec_section(self.current_method_docstring),
        )
        self.checks.append(check)

    def _classify_assertion(self, node) -> str:
        """Classify the type of assertion."""
        test = node.test

        if isinstance(test, ast.Call):
            if isinstance(test.func, ast.Name):
                return f"assert {test.func.id}(...)"
            elif isinstance(test.func, ast.Attribute):
                return f"assert ...{test.func.attr}(...)"
        elif isinstance(test, ast.Compare):
            ops = [type(op).__name__ for op in test.ops]
            if "Eq" in ops:
                return "assert =="
            elif "Is" in ops or "IsNot" in ops:
                return "assert is/is not"
            elif "In" in ops or "NotIn" in ops:
                return "assert in/not in"
        elif isinstance(test, ast.Attribute):
            return f"assert .{test.attr}"
        elif isinstance(test, ast.UnaryOp):
            if isinstance(test.op, ast.Not):
                return "assert not ..."

        return "assert"


def analyze_test_file(filepath: str) -> list[TestCheck]:
    """Analyze a single test file."""
    try:
        with open(filepath, "r") as f:
            source = f.read()
        tree = ast.parse(source)
        analyzer = TestFileAnalyzer(filepath)
        analyzer.visit(tree)
        return analyzer.checks
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def find_duplicate_checks(checks: list[TestCheck]) -> dict[str, list[TestCheck]]:
    """Find checks that test the same MUMPS code."""
    by_mumps = defaultdict(list)

    for check in checks:
        if check.mumps_code:
            normalized = normalize_mumps(check.mumps_code)
            if normalized:
                by_mumps[normalized].append(check)

    # Filter to only duplicates (more than 1 check)
    return {k: v for k, v in by_mumps.items() if len(v) > 1}


def find_overlapping_assertion_patterns(
    checks: list[TestCheck],
) -> dict[str, list[TestCheck]]:
    """Find checks with similar assertion patterns checking same thing."""
    patterns = defaultdict(list)

    for check in checks:
        # Create a signature based on what's being checked
        # e.g., "isinstance(target, Indirection)" or "expression.name == 'X'"
        code = check.code_pattern

        # Normalize the assertion pattern
        # Remove specific values but keep structure
        normalized = re.sub(r"'[^']*'", "'...'", code)
        normalized = re.sub(r'"[^"]*"', '"..."', normalized)
        normalized = re.sub(r"\d+", "N", normalized)

        patterns[normalized].append(check)

    # Filter to duplicates with different test methods
    duplicates = {}
    for pattern, pattern_checks in patterns.items():
        # Group by unique test method
        unique_methods = set((c.test_class, c.test_method) for c in pattern_checks)
        if len(unique_methods) > 1:
            duplicates[pattern] = pattern_checks

    return duplicates


def categorize_duplicates(duplicates: dict[str, list[TestCheck]]) -> tuple[list, list]:
    """Categorize duplicates into spec-aligned and non-spec-aligned."""
    migration_candidates = []

    for key, checks in duplicates.items():
        spec_aligned = [c for c in checks if c.is_spec_aligned]
        non_spec = [c for c in checks if not c.is_spec_aligned]

        if spec_aligned and non_spec:
            migration_candidates.append(
                {
                    "pattern": key,
                    "spec_aligned": spec_aligned,
                    "non_spec": non_spec,
                }
            )

    return migration_candidates


def generate_report(all_checks: list[TestCheck], output_format: str = "text") -> str:
    """Generate a comprehensive report of duplicate checks."""
    lines = []

    # Summary
    lines.append("=" * 80)
    lines.append("TEST DUPLICATE AUDIT REPORT")
    lines.append("=" * 80)
    lines.append("")

    total_checks = len(all_checks)
    spec_aligned = sum(1 for c in all_checks if c.is_spec_aligned)
    non_spec = total_checks - spec_aligned

    lines.append(f"Total checks analyzed: {total_checks}")
    lines.append(f"  Spec-aligned checks: {spec_aligned}")
    lines.append(f"  Non-spec-aligned checks: {non_spec}")
    lines.append("")

    # Find duplicates by MUMPS code
    mumps_dups = find_duplicate_checks(all_checks)
    lines.append("-" * 80)
    lines.append(f"DUPLICATE MUMPS CODE TESTS ({len(mumps_dups)} patterns)")
    lines.append("-" * 80)

    migration_needed = []

    for mumps_code, checks in sorted(mumps_dups.items(), key=lambda x: -len(x[1])):
        # Check if there's a spec-aligned version
        has_spec = any(c.is_spec_aligned for c in checks)
        has_non_spec = any(not c.is_spec_aligned for c in checks)

        if has_spec and has_non_spec:
            migration_needed.append((mumps_code, checks))

    lines.append("")
    lines.append(
        f"MIGRATION CANDIDATES (spec-aligned + non-spec): {len(migration_needed)}"
    )
    lines.append("=" * 80)

    for mumps_code, checks in migration_needed:
        lines.append("")
        lines.append(f"MUMPS: {mumps_code[:60]}...")
        lines.append("-" * 40)

        for check in checks:
            marker = "✓ SPEC" if check.is_spec_aligned else "→ MIGRATE"
            lines.append(f"  {marker}: {check.file}")
            lines.append(f"         {check.test_class}.{check.test_method}()")
            if check.spec_section:
                lines.append(f"         Section: {check.spec_section}")

    # Find assertion pattern duplicates
    lines.append("")
    lines.append("=" * 80)
    lines.append("DUPLICATE ASSERTION PATTERNS (same check, different tests)")
    lines.append("=" * 80)

    pattern_dups = find_overlapping_assertion_patterns(all_checks)

    # Focus on patterns that have both spec and non-spec versions
    for pattern, checks in sorted(pattern_dups.items(), key=lambda x: -len(x[1]))[:30]:
        has_spec = any(c.is_spec_aligned for c in checks)
        has_non_spec = any(not c.is_spec_aligned for c in checks)

        if has_spec and has_non_spec:
            lines.append("")
            lines.append(f"Pattern: {pattern[:70]}")
            spec_checks = [c for c in checks if c.is_spec_aligned]
            nonspec_checks = [c for c in checks if not c.is_spec_aligned]

            lines.append(f"  Spec-aligned ({len(spec_checks)}):")
            for c in spec_checks[:3]:
                lines.append(f"    - {c.file}::{c.test_method}")

            lines.append(f"  Non-spec (migrate these) ({len(nonspec_checks)}):")
            for c in nonspec_checks:
                lines.append(f"    → {c.file}::{c.test_method}")

    return "\n".join(lines)


def main():
    """Run the audit."""
    tests_dir = Path(__file__).parent.parent / "tests" / "unit"

    print(f"Scanning test files in: {tests_dir}")
    print()

    all_checks = []

    # Walk the test directory
    for root, dirs, files in os.walk(tests_dir):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                filepath = os.path.join(root, file)
                checks = analyze_test_file(filepath)
                all_checks.extend(checks)

    print(f"Analyzed {len(all_checks)} assertions across test files")
    print()

    report = generate_report(all_checks)
    print(report)

    # Also save to file
    output_file = Path(__file__).parent.parent / "test_duplicate_audit.txt"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
