#!/usr/bin/env python3
"""Validate codegen tests against YottaDB.

This utility parses codegen test files to extract MUMPS source and expected output,
then runs each test case against YottaDB to verify the expected outputs are correct.

Usage:
    # Validate all codegen tests
    uv run python utils/validate_tests.py

    # Validate specific test file
    uv run python utils/validate_tests.py tests/unit/codegen/test_cross_label_goto.py

    # Validate test files matching a pattern
    uv run python utils/validate_tests.py tests/unit/codegen/s8_commands/test_s8_2_05_for.py

    # Show verbose output
    uv run python utils/validate_tests.py -v

    # Stop on first failure
    uv run python utils/validate_tests.py --fail-fast

    # Only show failures
    uv run python utils/validate_tests.py --failures-only

    # Dry run (just extract, don't run YDB)
    uv run python utils/validate_tests.py --dry-run
"""

import argparse
import ast
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


# ANSI colors for terminal output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def color(text: str, c: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{c}{text}{Colors.RESET}"


@dataclass
class TestCase:
    """Represents an extracted test case."""

    file_path: Path
    class_name: str | None
    method_name: str
    mumps_source: str
    expected_output: str
    line_number: int

    @property
    def full_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}::{self.method_name}"
        return self.method_name


def extract_string_value(node: ast.AST) -> str | None:
    """Extract string value from an AST node, handling string concatenation."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-string - can't easily extract
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        # String concatenation
        left = extract_string_value(node.left)
        right = extract_string_value(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def find_source_and_output(
    func_body: list[ast.stmt],
) -> tuple[str | None, str | None]:
    """Find source assignment and output assertion in function body.

    Handles patterns like:
        # Pattern 1: source variable
        source = '''...'''
        result = execute_mumps(source)
        assert result.output == "..."

        # Pattern 2: direct variable
        output = execute_mumps(source, runtime)
        assert output == "..."

        # Pattern 3: inline source
        result = execute_mumps("TEST\\n W 1\\n Q\\n")
        assert result.output == "1"
    """
    source_code = None
    expected_output = None
    inline_sources: dict[str, str] = {}  # Maps result variable names to inline sources

    for stmt in func_body:
        # Look for: source = """..."""
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "source":
                    source_code = extract_string_value(stmt.value)
                # Look for: result = execute_mumps("...")
                elif isinstance(target, ast.Name):
                    if isinstance(stmt.value, ast.Call):
                        func = stmt.value.func
                        if isinstance(func, ast.Name) and func.id == "execute_mumps":
                            if stmt.value.args:
                                inline_src = extract_string_value(stmt.value.args[0])
                                if inline_src:
                                    inline_sources[target.id] = inline_src

        # Look for: assert result.output == "..."
        # or: assert output == "..."
        if isinstance(stmt, ast.Assert):
            compare = stmt.test
            if isinstance(compare, ast.Compare) and len(compare.ops) == 1:
                if isinstance(compare.ops[0], ast.Eq):
                    left = compare.left
                    right = compare.comparators[0]

                    # Check for result.output == ...
                    if isinstance(left, ast.Attribute):
                        if left.attr == "output":
                            expected_output = extract_string_value(right)
                            # If we have an inline source for this result variable, use it
                            if isinstance(left.value, ast.Name):
                                var_name = left.value.id
                                if var_name in inline_sources and source_code is None:
                                    source_code = inline_sources[var_name]

                    # Check for output == ... (direct variable)
                    elif isinstance(left, ast.Name) and left.id == "output":
                        expected_output = extract_string_value(right)

    return source_code, expected_output


def extract_test_cases(file_path: Path) -> list[TestCase]:
    """Extract test cases from a Python test file.

    Looks for test methods that:
    1. Assign MUMPS source to a 'source' variable
    2. Call execute_mumps() with that source
    3. Assert result.output or output equals an expected string
    """
    test_cases = []

    try:
        source = file_path.read_text()
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return []

    # Only iterate over top-level nodes to avoid duplicates
    for node in tree.body:
        # Find test classes
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                    source_code, expected_output = find_source_and_output(item.body)
                    if source_code and expected_output is not None:
                        test_cases.append(
                            TestCase(
                                file_path=file_path,
                                class_name=class_name,
                                method_name=item.name,
                                mumps_source=source_code,
                                expected_output=expected_output,
                                line_number=item.lineno,
                            )
                        )

        # Find top-level test functions (not inside classes)
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            source_code, expected_output = find_source_and_output(node.body)
            if source_code and expected_output is not None:
                test_cases.append(
                    TestCase(
                        file_path=file_path,
                        class_name=None,
                        method_name=node.name,
                        mumps_source=source_code,
                        expected_output=expected_output,
                        line_number=node.lineno,
                    )
                )

    return test_cases


def run_ydb(source: str, timeout: int = 30) -> tuple[str, bool]:
    """Run MUMPS source through YottaDB via Docker.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds

    Returns:
        Tuple of (output, success)
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".m", delete=False) as f:
        f.write(source)
        temp_path = Path(f.name)

    try:
        # Get the first label name from the source
        entry_label = None
        for line in source.split("\n"):
            line_stripped = line.strip()
            if (
                line_stripped
                and not line_stripped.startswith(";")
                and not line.startswith(" ")
                and not line.startswith("\t")
            ):
                parts = line_stripped.split()
                if parts:
                    label = parts[0].split("(")[0]
                    entry_label = label
                    break

        if not entry_label:
            return "ERROR: No entry label found in source", False

        # Run YottaDB via Docker using the ydb image
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "-v",
            f"{temp_path}:/workspace/test.m:ro",
            "ydb",
            "test.m",
        ]

        result = subprocess.run(
            docker_cmd, capture_output=True, text=True, timeout=timeout
        )

        output = result.stdout
        if result.returncode != 0 and result.stderr:
            return f"ERROR: {result.stderr}", False

        return output.rstrip(), True

    except subprocess.TimeoutExpired:
        return "ERROR: YottaDB execution timed out", False
    except FileNotFoundError:
        return "ERROR: Docker not found. Is Docker installed and running?", False
    except Exception as e:
        return f"ERROR: {e}", False
    finally:
        temp_path.unlink(missing_ok=True)


@dataclass
class ValidationResult:
    """Result of validating a test case."""

    test_case: TestCase
    ydb_output: str
    ydb_success: bool
    matches: bool


def validate_test_case(test_case: TestCase, timeout: int = 30) -> ValidationResult:
    """Validate a single test case against YottaDB."""
    ydb_output, ydb_success = run_ydb(test_case.mumps_source, timeout)
    matches = ydb_success and ydb_output == test_case.expected_output
    return ValidationResult(
        test_case=test_case,
        ydb_output=ydb_output,
        ydb_success=ydb_success,
        matches=matches,
    )


def find_test_files(paths: list[Path]) -> list[Path]:
    """Find all test files from the given paths."""
    test_files = []
    for path in paths:
        if path.is_file():
            if path.name.startswith("test_") and path.suffix == ".py":
                test_files.append(path)
        elif path.is_dir():
            for test_file in path.rglob("test_*.py"):
                test_files.append(test_file)
    return sorted(set(test_files))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate codegen tests against YottaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("tests/unit/codegen")],
        help="Test files or directories to validate (default: tests/unit/codegen)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output"
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first failure"
    )
    parser.add_argument(
        "--failures-only", action="store_true", help="Only show failures"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Extract tests but don't run YDB"
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="YottaDB execution timeout in seconds (default: 30)",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Find test files
    test_files = find_test_files(args.paths)
    if not test_files:
        print("No test files found")
        return 1

    # Extract all test cases
    all_test_cases: list[TestCase] = []
    for test_file in test_files:
        cases = extract_test_cases(test_file)
        all_test_cases.extend(cases)

    if not all_test_cases:
        print("No test cases with source/output assertions found")
        return 1

    print(
        color(
            f"Found {len(all_test_cases)} test cases in {len(test_files)} files",
            Colors.BOLD,
        )
    )
    print()

    if args.dry_run:
        # Just show extracted tests
        for tc in all_test_cases:
            rel_path = (
                tc.file_path.relative_to(Path.cwd())
                if tc.file_path.is_relative_to(Path.cwd())
                else tc.file_path
            )
            print(color(f"📋 {rel_path}:{tc.line_number}", Colors.CYAN))
            print(f"   {tc.full_name}")
            print(color("   Source:", Colors.DIM))
            for line in tc.mumps_source.split("\n")[:5]:
                print(f"      {line}")
            if len(tc.mumps_source.split("\n")) > 5:
                print("      ...")
            print(color(f"   Expected: {repr(tc.expected_output)}", Colors.DIM))
            print()
        return 0

    # Run validation
    results: list[ValidationResult] = []
    passed = 0
    failed = 0
    errors = 0

    for i, tc in enumerate(all_test_cases, 1):
        rel_path = (
            tc.file_path.relative_to(Path.cwd())
            if tc.file_path.is_relative_to(Path.cwd())
            else tc.file_path
        )

        if args.verbose:
            print(f"[{i}/{len(all_test_cases)}] {tc.full_name}...", end=" ", flush=True)

        result = validate_test_case(tc, args.timeout)
        results.append(result)

        if not result.ydb_success:
            errors += 1
            status = color("ERROR", Colors.YELLOW)
        elif result.matches:
            passed += 1
            status = color("✓", Colors.GREEN)
        else:
            failed += 1
            status = color("✗", Colors.RED)

        if args.verbose:
            print(status)

        # Show details for failures/errors
        if (
            not result.matches
            and not args.failures_only
            or (args.failures_only and not result.matches)
        ):
            if not args.verbose:
                print(f"{status} {rel_path}:{tc.line_number} {tc.full_name}")

            if not result.ydb_success:
                print(color(f"   YDB Error: {result.ydb_output}", Colors.YELLOW))
            else:
                print(f"   Expected: {repr(tc.expected_output)}")
                print(f"   YDB gave: {repr(result.ydb_output)}")

                if args.verbose:
                    print(color("   Source:", Colors.DIM))
                    for line in tc.mumps_source.split("\n"):
                        print(f"      {line}")
            print()

        if args.fail_fast and not result.matches:
            print(color("\nStopping due to --fail-fast", Colors.YELLOW))
            break

    # Summary
    print(color("=" * 60, Colors.BOLD))
    print(color("SUMMARY", Colors.BOLD))
    print(color("=" * 60, Colors.BOLD))
    print(f"  Total:  {len(results)}")
    print(color(f"  Passed: {passed}", Colors.GREEN))
    if failed:
        print(color(f"  Failed: {failed}", Colors.RED))
    if errors:
        print(color(f"  Errors: {errors}", Colors.YELLOW))

    if args.json:
        import json

        json_results = []
        for r in results:
            json_results.append(
                {
                    "file": str(r.test_case.file_path),
                    "class": r.test_case.class_name,
                    "method": r.test_case.method_name,
                    "line": r.test_case.line_number,
                    "mumps_source": r.test_case.mumps_source,
                    "expected": r.test_case.expected_output,
                    "ydb_output": r.ydb_output,
                    "ydb_success": r.ydb_success,
                    "matches": r.matches,
                }
            )
        print("\n" + json.dumps(json_results, indent=2))

    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
