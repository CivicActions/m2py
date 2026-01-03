#!/usr/bin/env python3
"""Coverage audit script for spec-aligned unit tests.

Scans test files in tests/unit/{parser,asg,codegen}/ and reports coverage status
against MUMPS 1995 ANSI spec sections (§5-§9).

Usage:
    uv run python utils/audit_tests.py                          # Full report
    uv run python utils/audit_tests.py --section s7             # Filter by section
    uv run python utils/audit_tests.py --section s8_2_18        # Filter by subsection
    uv run python utils/audit_tests.py --output docs/coverage-matrix.md  # Save report

Exit codes:
    0 - All sections have test files
    1 - One or more sections missing test files
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# =============================================================================
# SPEC_SECTIONS - All §5-§9 sections from MUMPS 1995 ANSI Standard
# =============================================================================

SPEC_SECTIONS: dict[str, dict[str, str]] = {
    # §5 Metalanguage (informative - out of scope)
    "s5_metalanguage": {
        "s5_1_bnf_notation": "BNF Notation",
    },
    # §6 Routine Structure
    "s6_routine": {
        "s6_1_routine_head": "Routine Head",
        "s6_2_routine_body": "Routine Body (§6.2.1-6.2.5)",
        "s6_3_1_indirection": "Generic Indirection",
        "s6_3_1_transaction": "Transaction Processing",
        "s6_3_2_error_processing": "Error Processing",
        "s6_3_4_event_processing": "Event Processing (out-of-scope)",
        "s6_4_embedded_programs": "Embedded Programs (out-of-scope)",
    },
    # §7 Expressions
    "s7_expressions": {
        "s7_1_1_values": "Values",
        "s7_1_2_variables": "Variables (lvn, gvn, glvn)",
        "s7_1_3_ssvns": "Structured System Variables",
        "s7_1_4_literals": "Literals",
        "s7_1_5_intrinsic_functions": "Intrinsic Functions",
        "s7_1_6_extrinsic_functions": "Extrinsic Functions",
        "s7_1_7_special_variables": "Special Variables",
        "s7_2_operators": "Operators",
        "s7_2_5_pattern_match": "Pattern Match",
        "s7_3_indirection": "Indirection",
    },
    # §8 Commands
    "s8_commands": {
        "s8_1_general_rules": "General Rules",
        "s8_2_01_break": "BREAK",
        "s8_2_02_close": "CLOSE",
        "s8_2_03_do": "DO",
        "s8_2_04_else": "ELSE",
        "s8_2_05_for": "FOR",
        "s8_2_06_goto": "GOTO",
        "s8_2_07_halt": "HALT",
        "s8_2_08_hang": "HANG",
        "s8_2_09_if": "IF",
        "s8_2_10_job": "JOB",
        "s8_2_11_kill": "KILL",
        "s8_2_12_lock": "LOCK",
        "s8_2_13_merge": "MERGE",
        "s8_2_14_new": "NEW",
        "s8_2_15_open": "OPEN",
        "s8_2_16_quit": "QUIT",
        "s8_2_17_read": "READ",
        "s8_2_18_set": "SET",
        "s8_2_19_tcommit": "TCOMMIT",
        "s8_2_20_trestart": "TRESTART",
        "s8_2_21_trollback": "TROLLBACK",
        "s8_2_22_tstart": "TSTART",
        "s8_2_23_use": "USE",
        "s8_2_24_view": "VIEW (implementation-defined)",
        "s8_2_25_write": "WRITE",
        "s8_2_26_xecute": "XECUTE",
        "s8_2_27_zcommand": "Z-commands",
        "s8_2_28_rload": "RLOAD (out-of-scope)",
        "s8_2_29_rsave": "RSAVE (out-of-scope)",
        "s8_3_device_params": "Device Parameters",
        "s8_ksubscripts": "$KEY Subscripts",
        "s8_kvalue": "$KEY Value",
        "s8_event_processing": "Event Processing (out-of-scope)",
        "s8_then_command": "THEN (out-of-scope)",
        "s8_assign": "ASSIGN (out-of-scope)",
    },
    # §9 Character Set
    "s9_charset": {
        "s9_1_definitions": "Definitions",
    },
}

# Extensions (YottaDB Z-commands) - per-category as ASG only tests commands with semantic analysis
# Parser: All Z-commands (T145-T155f, T164b)
# ASG: Only commands with semantic analysis (T156-T159f, T164c)
# Codegen: All Z-commands (T160-T164o, T164d)

EXTENSION_PARSER: dict[str, str] = {
    "zbreak": "ZBREAK",
    "zcompile": "ZCOMPILE",
    "zcontinue": "ZCONTINUE",
    "zedit": "ZEDIT",
    "zfunctions": "Z-Functions (implementation-defined)",
    "zgoto": "ZGOTO",
    "zhalt": "ZHALT",
    "zhelp": "ZHELP",
    "zkill": "ZKILL/ZWITHDRAW",
    "zlink": "ZLINK",
    "zmessage": "ZMESSAGE",
    "zprint": "ZPRINT",
    "zshow": "ZSHOW",
    "zstep": "ZSTEP",
    "zsystem": "ZSYSTEM",
    "ztrigger": "ZTRIGGER",
    "zwrite": "ZWRITE",
    "zallocate": "ZALLOCATE/ZDEALLOCATE",
}

# ASG only tests Z-commands that have semantic analysis (classification, resolution)
EXTENSION_ASG: dict[str, str] = {
    "zbreak": "ZBREAK",
    "zedit": "ZEDIT",
    "zfunctions": "Z-Functions (implementation-defined)",
    "zgoto": "ZGOTO (ZGotoType classification)",
    "zhalt": "ZHALT",
    "zhelp": "ZHELP",
    "zkill": "ZKILL/ZWITHDRAW",
    "zlink": "ZLINK",
    "ztrigger": "ZTRIGGER",
    "zwrite": "ZWRITE",
    "zallocate": "ZALLOCATE/ZDEALLOCATE",
}

EXTENSION_CODEGEN: dict[str, str] = {
    "zbreak": "ZBREAK",
    "zcompile": "ZCOMPILE",
    "zcontinue": "ZCONTINUE",
    "zedit": "ZEDIT",
    "zfunctions": "Z-Functions (implementation-defined)",
    "zgoto": "ZGOTO",
    "zhalt": "ZHALT",
    "zhelp": "ZHELP",
    "zkill": "ZKILL/ZWITHDRAW",
    "zlink": "ZLINK",
    "zmessage": "ZMESSAGE",
    "zprint": "ZPRINT",
    "zshow": "ZSHOW",
    "zstep": "ZSTEP",
    "zsystem": "ZSYSTEM",
    "ztrigger": "ZTRIGGER",
    "zwrite": "ZWRITE",
    "zallocate": "ZALLOCATE/ZDEALLOCATE",
}

# Combined for report generation (union of all)
EXTENSION_SECTIONS: dict[str, dict[str, str]] = {
    "extensions/ydb": EXTENSION_PARSER,  # Use parser as the full list for display
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TestInfo:
    """Information about a single test function."""

    name: str
    markers: list[str] = field(default_factory=list)
    is_xfail: bool = False
    is_skip: bool = False
    is_stub: bool = False
    skip_reason: str | None = None
    xfail_reason: str | None = None


@dataclass
class FileInfo:
    """Information about a test file."""

    path: Path
    tests: list[TestInfo] = field(default_factory=list)
    total_count: int = 0
    passed_count: int = 0  # No xfail/skip
    stub_count: int = 0  # Has xfail with stub marker
    xfail_count: int = 0  # Has xfail but no stub marker
    skipped_count: int = 0  # Has skip

    def compute_counts(self) -> None:
        """Compute test counts from test list."""
        self.total_count = len(self.tests)
        self.passed_count = 0
        self.stub_count = 0
        self.xfail_count = 0
        self.skipped_count = 0

        for test in self.tests:
            if test.is_skip:
                self.skipped_count += 1
            elif test.is_stub and test.is_xfail:
                self.stub_count += 1
            elif test.is_xfail:
                self.xfail_count += 1
            else:
                self.passed_count += 1


@dataclass
class SectionStatus:
    """Coverage status for a spec section."""

    section_id: str
    section_name: str
    parser: FileInfo | None = None
    asg: FileInfo | None = None
    codegen: FileInfo | None = None
    notes: str = ""


TestCategory = Literal["parser", "asg", "codegen"]


# =============================================================================
# Test File Discovery
# =============================================================================


def scan_test_files(
    base_dir: Path, section_filter: str | None = None
) -> dict[TestCategory, dict[str, FileInfo]]:
    """Discover all test files in parser/, asg/, codegen/ directories.

    Args:
        base_dir: Base directory (tests/unit/)
        section_filter: Optional filter like "s7" or "s8_2_18"

    Returns:
        Dict mapping category -> section_id -> FileInfo
    """
    results: dict[TestCategory, dict[str, FileInfo]] = {
        "parser": {},
        "asg": {},
        "codegen": {},
    }

    for category in ("parser", "asg", "codegen"):
        category_dir = base_dir / category
        if not category_dir.exists():
            continue

        # Find all test_*.py files recursively
        for test_file in category_dir.rglob("test_*.py"):
            # Extract section ID from path
            # e.g., s8_commands/test_s8_2_18_set.py -> s8_2_18_set
            # e.g., extensions/ydb/test_zwrite.py -> extensions/ydb/zwrite
            rel_path = test_file.relative_to(category_dir)

            # Handle extensions differently
            if "extensions" in str(rel_path):
                # extensions/ydb/test_zwrite.py -> extensions/ydb/zwrite
                parts = list(rel_path.parts)
                if len(parts) >= 3:  # extensions/ydb/test_xxx.py
                    extension_type = f"{parts[0]}/{parts[1]}"  # extensions/ydb
                    test_name = test_file.stem.replace("test_", "")
                    section_id = f"{extension_type}/{test_name}"
                else:
                    continue
            else:
                # Standard spec section
                # s8_commands/test_s8_2_18_set.py -> s8_2_18_set
                test_name = test_file.stem.replace("test_", "")
                section_id = test_name

            # Apply section filter if specified
            if section_filter:
                if not section_id.startswith(section_filter):
                    continue

            file_info = FileInfo(path=test_file)
            results[category][section_id] = file_info  # type: ignore

    return results


# =============================================================================
# AST-based Marker Parsing
# =============================================================================


def parse_test_markers(file_path: Path) -> list[TestInfo]:
    """Parse pytest markers from a test file using AST.

    Args:
        file_path: Path to test file

    Returns:
        List of TestInfo objects for each test function
    """
    tests: list[TestInfo] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return tests

    # Walk AST looking for test functions and methods
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                test_info = _extract_test_info(node)
                tests.append(test_info)
        elif isinstance(node, ast.ClassDef):
            # Look for test methods in classes
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("test_"):
                        test_info = _extract_test_info(item)
                        tests.append(test_info)

    return tests


def _extract_test_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> TestInfo:
    """Extract test information from a function definition node."""
    test_info = TestInfo(name=node.name)

    for decorator in node.decorator_list:
        marker_name, reason = _parse_decorator(decorator)
        if marker_name:
            test_info.markers.append(marker_name)

            if marker_name == "xfail":
                test_info.is_xfail = True
                test_info.xfail_reason = reason
            elif marker_name == "skip":
                test_info.is_skip = True
                test_info.skip_reason = reason
            elif marker_name == "stub":
                test_info.is_stub = True

    return test_info


def _parse_decorator(
    decorator: ast.expr,
) -> tuple[str | None, str | None]:
    """Parse a decorator to extract pytest marker name and reason.

    Returns:
        Tuple of (marker_name, reason) or (None, None) if not a pytest.mark
    """
    # Handle @pytest.mark.xxx
    if isinstance(decorator, ast.Attribute):
        # @pytest.mark.stub (no call)
        if isinstance(decorator.value, ast.Attribute):
            if (
                isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "pytest"
                and decorator.value.attr == "mark"
            ):
                return decorator.attr, None
        return None, None

    # Handle @pytest.mark.xxx(...) or @pytest.mark.xxx(reason="...")
    if isinstance(decorator, ast.Call):
        func = decorator.func

        # @pytest.mark.xfail(reason="...") or @pytest.mark.skip(reason="...")
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Attribute):
                if (
                    isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "pytest"
                    and func.value.attr == "mark"
                ):
                    marker_name = func.attr
                    reason = _extract_reason_from_call(decorator)
                    return marker_name, reason

    return None, None


def _extract_reason_from_call(call: ast.Call) -> str | None:
    """Extract reason argument from a decorator call."""
    # Check keyword arguments for reason=
    for kw in call.keywords:
        if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
            return str(kw.value.value)

    # Check first positional argument (common for skip/xfail)
    if call.args and isinstance(call.args[0], ast.Constant):
        return str(call.args[0].value)

    return None


# =============================================================================
# Test Status Counting
# =============================================================================


def count_test_status(files: dict[TestCategory, dict[str, FileInfo]]) -> None:
    """Parse markers and compute test counts for all files.

    Modifies FileInfo objects in place with test information and counts.

    Args:
        files: Dict mapping category -> section_id -> FileInfo
    """
    for category in files:
        for section_id, file_info in files[category].items():
            file_info.tests = parse_test_markers(file_info.path)
            file_info.compute_counts()


# =============================================================================
# Report Generation
# =============================================================================


def _format_cell(file_info: FileInfo | None) -> str:
    """Format a cell value for a file's test status."""
    if file_info is None:
        return "❌ Missing"

    total = file_info.total_count
    passed = file_info.passed_count
    stub = file_info.stub_count
    xfail = file_info.xfail_count
    skipped = file_info.skipped_count

    if total == 0:
        return "⚠️ Empty"

    # All skipped = out of scope
    if skipped == total:
        return f"⏭️ Skip ({total})"

    # All passed = fully implemented
    if passed == total:
        return f"✅ {passed}/{total}"

    # Mix of statuses
    parts = []
    if passed > 0:
        parts.append(f"✅{passed}")
    if stub > 0:
        parts.append(f"🚧{stub}")
    if xfail > 0:
        parts.append(f"⚠️{xfail}")
    if skipped > 0:
        parts.append(f"⏭️{skipped}")

    return " ".join(parts) + f" ({total})"


def _get_section_notes(section_id: str) -> str:
    """Get notes for a section based on its characteristics."""
    if "out-of-scope" in section_id or section_id in (
        "s5_1_bnf_notation",
        "s6_3_4_event_processing",
        "s6_4_embedded_programs",
        "s8_event_processing",
        "s8_then_command",
        "s8_assign",
        "s8_2_28_rload",
        "s8_2_29_rsave",
    ):
        return "Out of scope"

    if "implementation-defined" in section_id or section_id in (
        "s8_2_24_view",
        "zfunctions",
    ):
        return "Implementation-defined"

    return ""


def generate_report(
    files: dict[TestCategory, dict[str, FileInfo]],
    section_filter: str | None = None,
) -> str:
    """Generate a markdown coverage report.

    Args:
        files: Dict mapping category -> section_id -> FileInfo
        section_filter: Optional filter string

    Returns:
        Markdown formatted report string
    """
    lines = []
    lines.append("# Test Coverage Matrix")
    lines.append("")
    lines.append(
        "Auto-generated by `utils/audit_tests.py`. Shows coverage of MUMPS 1995 ANSI spec sections."
    )
    lines.append("")
    lines.append("## Legend")
    lines.append("")
    lines.append("- ✅ Implemented (tests pass)")
    lines.append("- 🚧 Stub (xfail, pending implementation)")
    lines.append("- ⚠️ XFail (needs investigation)")
    lines.append("- ⏭️ Skipped (out of scope or implementation-defined)")
    lines.append("- ❌ Missing (no test file)")
    lines.append("- ⚠️ Empty (file exists but no tests)")
    lines.append("")

    # Standard spec sections
    lines.append("## Standard Spec Sections (§5-§9)")
    lines.append("")
    lines.append("| Section | Parser | ASG | Codegen | Notes |")
    lines.append("|---------|--------|-----|---------|-------|")

    for section_group, subsections in SPEC_SECTIONS.items():
        for section_id, section_name in subsections.items():
            # Apply filter
            if section_filter and not section_id.startswith(section_filter):
                continue

            parser_info = files["parser"].get(section_id)
            asg_info = files["asg"].get(section_id)
            codegen_info = files["codegen"].get(section_id)

            parser_cell = _format_cell(parser_info)
            asg_cell = _format_cell(asg_info)
            codegen_cell = _format_cell(codegen_info)
            notes = _get_section_notes(section_id)

            lines.append(
                f"| {section_id} | {parser_cell} | {asg_cell} | {codegen_cell} | {notes} |"
            )

    # Extension sections
    lines.append("")
    lines.append("## YottaDB Extensions")
    lines.append("")
    lines.append("| Extension | Parser | ASG | Codegen | Notes |")
    lines.append("|-----------|--------|-----|---------|-------|")

    for extension_group, commands in EXTENSION_SECTIONS.items():
        for cmd_id, cmd_name in commands.items():
            full_id = f"{extension_group}/{cmd_id}"

            # Apply filter
            if section_filter and not full_id.startswith(section_filter):
                continue

            parser_info = files["parser"].get(full_id)
            asg_info = files["asg"].get(full_id)
            codegen_info = files["codegen"].get(full_id)

            parser_cell = _format_cell(parser_info)
            # ASG only expects certain extensions - show N/A for others
            if cmd_id in EXTENSION_ASG:
                asg_cell = _format_cell(asg_info)
            else:
                asg_cell = "— N/A"
            codegen_cell = _format_cell(codegen_info)
            notes = _get_section_notes(cmd_id)

            lines.append(
                f"| {cmd_id} | {parser_cell} | {asg_cell} | {codegen_cell} | {notes} |"
            )

    # Summary statistics
    lines.append("")
    lines.append("## Summary")
    lines.append("")

    total_sections = 0
    covered_sections = 0
    total_tests = 0
    passed_tests = 0
    stub_tests = 0

    for category in ("parser", "asg", "codegen"):
        for file_info in files[category].values():
            total_sections += 1
            if file_info.total_count > 0:
                covered_sections += 1
            total_tests += file_info.total_count
            passed_tests += file_info.passed_count
            stub_tests += file_info.stub_count

    lines.append(f"- **Total test files**: {total_sections}")
    lines.append(f"- **Files with tests**: {covered_sections}")
    lines.append(f"- **Total test functions**: {total_tests}")
    lines.append(f"- **Implemented tests**: {passed_tests}")
    lines.append(f"- **Stub tests**: {stub_tests}")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Exit Code Logic
# =============================================================================


def check_coverage(
    files: dict[TestCategory, dict[str, FileInfo]],
) -> tuple[bool, list[str]]:
    """Check if all required sections have test files.

    Args:
        files: Dict mapping category -> section_id -> FileInfo

    Returns:
        Tuple of (all_covered, missing_sections)
    """
    missing: list[str] = []

    # Check standard sections
    for section_group, subsections in SPEC_SECTIONS.items():
        for section_id, section_name in subsections.items():
            # Check all three categories
            for category in ("parser", "asg", "codegen"):
                if section_id not in files[category]:
                    missing.append(f"{category}/{section_id}")

    # Check extension sections - use category-specific lists
    extension_by_category: dict[TestCategory, dict[str, str]] = {
        "parser": EXTENSION_PARSER,
        "asg": EXTENSION_ASG,
        "codegen": EXTENSION_CODEGEN,
    }

    for category, extensions in extension_by_category.items():
        for cmd_id in extensions:
            full_id = f"extensions/ydb/{cmd_id}"
            if full_id not in files[category]:
                missing.append(f"{category}/{full_id}")

    return len(missing) == 0, missing


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    """Main entry point for the audit script."""
    parser = argparse.ArgumentParser(
        description="Audit test coverage against MUMPS spec sections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--section",
        metavar="FILTER",
        help="Filter by section (e.g., s7, s8_2_18, extensions/ydb)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write report to file (e.g., docs/coverage-matrix.md)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress report output, only return exit code",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check coverage, don't generate report",
    )

    args = parser.parse_args()

    # Determine base directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    base_dir = project_root / "tests" / "unit"

    if not base_dir.exists():
        print(f"Error: Test directory not found: {base_dir}", file=sys.stderr)
        return 1

    # Scan test files
    files = scan_test_files(base_dir, args.section)

    # Parse markers and count test status
    count_test_status(files)

    # Check coverage
    all_covered, missing = check_coverage(files)

    if args.check_only:
        if not all_covered:
            print("Missing test files:", file=sys.stderr)
            for m in sorted(missing)[:20]:  # Show first 20
                print(f"  - {m}", file=sys.stderr)
            if len(missing) > 20:
                print(f"  ... and {len(missing) - 20} more", file=sys.stderr)
            return 1
        return 0

    # Generate report
    report = generate_report(files, args.section)

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        if not args.quiet:
            print(f"Report written to {output_path}")
    elif not args.quiet:
        print(report)

    # Return exit code based on coverage
    return 0 if all_covered else 1


if __name__ == "__main__":
    sys.exit(main())
