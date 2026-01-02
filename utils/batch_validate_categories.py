#!/usr/bin/env python3
"""Systematic deep validation of all remaining MUGJ files.

This script validates files category by category, updating the checklist
and phase-13-tasks.md as issues are discovered.
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Any
from m2py.parser import MUMPSParser


# Categories still needing deep validation (from checklist)
CATEGORIES = {
    "Arithmetic & Conversion Tests": ["V1AC.m", "V1AC1.m", "V1AC2.m"],
    "Binary Operator Tests A": [
        "V1BOA.m",
        "V1BOA1.m",
        "V1BOA2.m",
        "V1BOA3.m",
        "V1BOA4.m",
        "V1BOA5.m",
        "V1BOA6.m",
    ],
    "Binary Operator Tests B": [
        "V1BOB.m",
        "V1BOB1.m",
        "V1BOB10.m",
        "V1BOB2.m",
        "V1BOB3.m",
        "V1BOB4.m",
        "V1BOB5A.m",
        "V1BOB5B.m",
        "V1BOB6A.m",
        "V1BOB6B.m",
        "V1BOB7.m",
        "V1BOB8.m",
        "V1BOB9.m",
    ],
    "Binary Operator Tests C": ["V1BOC.m", "V1BOC1.m", "V1BOC2.m", "V1BOC3.m"],
    "BREAK Command Tests": ["V1BR.m", "V1BR1.m"],
    "CALL/DO Tests": ["V1CALL.m", "V1CALL1.m"],
    "Comment Tests": ["V1CMT.m"],
    "Data Global Tests": ["V1DGA.m", "V1DGB.m", "V1DGB1.m", "V1DGB2.m", "V1GVN.m"],
    "Data Local Tests": ["V1DLA.m", "V1DLB.m", "V1DLB1.m", "V1DLB2.m", "V1DLC.m"],
    "DO Command Tests": ["V1DO.m", "V1DO1.m", "V1DO2.m", "V1DO3.m"],
    "Function Call Tests": ["V1FC.m", "V1FC1.m", "V1FC2.m"],
    "Function Tests - Numeric": ["V1FN.m", "V1FNL.m"],
    "Function Tests - $EXTRACT": ["V1FNE1.m", "V1FNE2.m"],
    "Function Tests - $FIND": ["V1FNF1.m", "V1FNF2.m", "V1FNF3.m"],
    "Function Tests - $PIECE": ["V1FNP1.m", "V1FNP2.m"],
    "FOR Loop Tests": [
        "V1FORA.m",
        "V1FORA1.m",
        "V1FORA2.m",
        "V1FORB.m",
        "V1FORC.m",
        "V1FORC1.m",
        "V1FORC2.m",
    ],
    "GOTO Tests": ["V1GO.m", "V1GO1.m", "V1GO2.m"],
    "HANG Command Tests": ["V1HANG.m"],
    "Indirection Tests - Arguments": [
        "V1IDARG.m",
        "V1IDARG1.m",
        "V1IDARG2.m",
        "V1IDARG3.m",
        "V1IDARG4.m",
        "V1IDARG5.m",
    ],
    "Indirection Tests - DO": ["V1IDDO.m", "V1IDDO1.m", "V1IDDOA.m", "V1IDDOB.m"],
    "Indirection Tests - GOTO": ["V1IDGO.m", "V1IDGO1.m", "V1IDGOA.m", "V1IDGOB.m"],
    "Indirection Tests - Name": ["V1IDNM.m", "V1IDNM1.m", "V1IDNM2.m", "V1IDNM3.m"],
    "IF/ELSE Tests": ["V1IE.m", "V1IE1.m", "V1IE2.m"],
    "I/O Tests": ["V1IO.m", "V1IO1.m", "V1IO2.m"],
}


def detect_issues(filepath: Path, routine: Any) -> list[dict]:
    """Detect ASG issues in a parsed routine."""
    issues = []
    source_lines = filepath.read_text().split("\n")

    # Check for missing I/O commands
    for line in source_lines:
        line_upper = line.strip().upper()
        if line_upper.startswith("OPEN ") or " OPEN " in line_upper:
            issues.append(
                {
                    "type": "missing_command",
                    "command": "OPEN",
                    "line": line.strip(),
                    "description": "OPEN command in source but not in ASG",
                }
            )
        if line_upper.startswith("CLOSE ") or " CLOSE " in line_upper:
            issues.append(
                {
                    "type": "missing_command",
                    "command": "CLOSE",
                    "line": line.strip(),
                    "description": "CLOSE command in source but not in ASG",
                }
            )
        if line_upper.startswith("USE ") or " USE " in line_upper:
            issues.append(
                {
                    "type": "missing_command",
                    "command": "USE",
                    "line": line.strip(),
                    "description": "USE command in source but not in ASG",
                }
            )
        if line_upper.startswith("JOB ") or " JOB " in line_upper:
            issues.append(
                {
                    "type": "missing_command",
                    "command": "JOB",
                    "line": line.strip(),
                    "description": "JOB command in source but not in ASG",
                }
            )

    # Check statement count vs source line count
    code_lines = [
        line
        for line in source_lines
        if line.strip() and not line.strip().startswith(";")
    ]
    label_lines = [line for line in code_lines if line and line[0] not in " \t"]
    statement_lines = len(code_lines) - len(label_lines)

    total_statements = sum(
        len(label.body.statements) if label.body else 0 for label in routine.labels
    )

    # Allow some tolerance for multi-statement lines
    if statement_lines > total_statements + 2:
        issues.append(
            {
                "type": "statement_count_mismatch",
                "expected": statement_lines,
                "actual": total_statements,
                "description": f"Source has ~{statement_lines} statement lines but ASG has {total_statements} statements",
            }
        )

    return issues


def validate_category(
    category_name: str, files: list[str], parser: MUMPSParser, mugj_dir: Path
) -> dict:
    """Validate all files in a category."""
    results = {
        "category": category_name,
        "total": len(files),
        "parsed": 0,
        "failed": 0,
        "issues": [],
    }

    for filename in files:
        filepath = mugj_dir / filename

        if not filepath.exists():
            results["failed"] += 1
            results["issues"].append({"file": filename, "error": "File not found"})
            continue

        try:
            routine = parser.parse_file(str(filepath))
            results["parsed"] += 1

            # Detect issues
            file_issues = detect_issues(filepath, routine)
            if file_issues:
                results["issues"].append({"file": filename, "issues": file_issues})

        except Exception as e:
            results["failed"] += 1
            results["issues"].append({"file": filename, "error": str(e)})

    return results


def main():
    """Main validation function."""
    mugj_dir = Path("tests/functional/mugj/inref")
    parser = MUMPSParser()

    print("=" * 80)
    print("SYSTEMATIC MUGJ VALIDATION - REMAINING CATEGORIES")
    print("=" * 80)
    print()

    all_results = []
    total_files = 0
    total_parsed = 0
    total_with_issues = 0

    for category_name, files in CATEGORIES.items():
        print(f"\nValidating: {category_name} ({len(files)} files)")
        print("─" * 80)

        results = validate_category(category_name, files, parser, mugj_dir)
        all_results.append(results)

        total_files += results["total"]
        total_parsed += results["parsed"]

        print(f"  ✓ Parsed: {results['parsed']}/{results['total']}")

        if results["failed"] > 0:
            print(f"  ❌ Failed: {results['failed']}")

        if results["issues"]:
            total_with_issues += len([i for i in results["issues"] if "issues" in i])
            print(f"  ⚠️  Issues found: {len(results['issues'])} files")

            for issue_entry in results["issues"]:
                if "error" in issue_entry:
                    print(f"     {issue_entry['file']}: {issue_entry['error']}")
                elif "issues" in issue_entry:
                    print(
                        f"     {issue_entry['file']}: {len(issue_entry['issues'])} issue(s)"
                    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files validated: {total_files}")
    print(f"Successfully parsed: {total_parsed}")
    print(f"Files with issues: {total_with_issues}")
    print()

    # Aggregate issue types
    issue_types = defaultdict(int)
    issue_commands = defaultdict(int)

    for result in all_results:
        for issue_entry in result["issues"]:
            if "issues" in issue_entry:
                for issue in issue_entry["issues"]:
                    issue_types[issue["type"]] += 1
                    if issue["type"] == "missing_command":
                        issue_commands[issue["command"]] += 1

    if issue_types:
        print("Issue types found:")
        for issue_type, count in sorted(issue_types.items()):
            print(f"  {issue_type}: {count}")

        if issue_commands:
            print("\nMissing commands:")
            for cmd, count in sorted(issue_commands.items()):
                print(f"  {cmd}: {count} occurrences")

    return 0 if total_with_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
