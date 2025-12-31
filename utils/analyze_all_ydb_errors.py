#!/usr/bin/env python3
"""Analyze all YDB test suites for parse errors.

Identifies files where parsing failures are masked by error-tolerant parsing.
"""

from pathlib import Path
from m2py.parser import MUMPSParser
from m2py.asg import MRoutine


def analyze_suite(suite_name: str, suite_dir: Path):
    """Analyze a single test suite for parse errors."""
    parser = MUMPSParser()

    files_with_errors = []
    files_clean = []

    for filepath in sorted(suite_dir.glob("*.m")):
        try:
            routine = parser.parse_file(filepath)
            if not isinstance(routine, MRoutine):
                print(f"ERROR: {filepath.name} - Did not return MRoutine")
                continue

            if routine.parse_errors:
                files_with_errors.append((filepath.name, routine.parse_errors))
            else:
                files_clean.append(filepath.name)
        except Exception as e:
            print(f"EXCEPTION: {filepath.name} - {type(e).__name__}: {e}")

    total = len(files_clean) + len(files_with_errors)
    if total == 0:
        return None, None

    success_rate = len(files_clean) / total * 100

    return {
        "suite": suite_name,
        "total": total,
        "clean": len(files_clean),
        "with_errors": len(files_with_errors),
        "success_rate": success_rate,
        "error_details": files_with_errors,
    }, files_with_errors


def main():
    base_dir = Path("tests/functional")

    # All test suites
    suites = [
        ("mugj", base_dir / "mugj" / "inref"),
        ("basic", base_dir / "basic_inref"),
        ("indirection", base_dir / "indirection_inref"),
        ("io", base_dir / "io_inref"),
        ("longname", base_dir / "longname_inref"),
        ("m_commands", base_dir / "m_commands_inref"),
        ("merge", base_dir / "merge_inref"),
        ("mvts", base_dir / "mvts_inref"),
        ("tp", base_dir / "tp_inref"),
        ("triggers", base_dir / "triggers_inref"),
        ("unicode", base_dir / "unicode_inref"),
    ]

    print("=" * 70)
    print("YDB Test Suite Parse Error Analysis")
    print("=" * 70)

    all_results = []

    for suite_name, suite_dir in suites:
        if not suite_dir.exists():
            print(f"\n{suite_name}: Directory not found ({suite_dir})")
            continue

        result, errors = analyze_suite(suite_name, suite_dir)
        if result:
            all_results.append(result)

    # Summary table
    print("\n" + "=" * 70)
    print("SUMMARY BY SUITE")
    print("=" * 70)
    print(f"{'Suite':<15} {'Total':<8} {'Clean':<8} {'Errors':<8} {'Success':<10}")
    print("-" * 70)

    for r in sorted(all_results, key=lambda x: x["success_rate"]):
        print(
            f"{r['suite']:<15} {r['total']:<8} {r['clean']:<8} {r['with_errors']:<8} {r['success_rate']:.1f}%"
        )

    # Detail errors for suites with <100% success
    print("\n" + "=" * 70)
    print("DETAILED ERRORS BY SUITE")
    print("=" * 70)

    for r in sorted(all_results, key=lambda x: x["success_rate"]):
        if r["with_errors"] == 0:
            continue

        print(f"\n### {r['suite'].upper()} ({r['with_errors']} files with errors)")
        print("-" * 50)

        for filename, errors in r["error_details"]:
            print(f"\n{filename}: {len(errors)} error(s)")
            for err in errors[:3]:  # Show first 3 errors per file
                content = err.line_content[:70] if err.line_content else "(no content)"
                print(f"  Line {err.line_number}: {content}")
            if len(errors) > 3:
                print(f"  ... and {len(errors) - 3} more errors")


if __name__ == "__main__":
    main()
