#!/usr/bin/env python3
"""Scan VistA-VEHU-M routines and report transpilation success/failure metrics.

Usage:
    uv run python utils/scan_vista.py [--output-dir DIR] [--source-dir DIR]
    uv run python utils/scan_vista.py --update-reference  # Create reference JSON
    uv run python utils/scan_vista.py --limit 100         # Test with 100 files

Defaults:
    --source-dir  VistA-VEHU-M
    --output-dir  tmp/baseline-scan
    --reference   utils/scan_vista_reference.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from m2py.cli.transpile import transpile_sources_with_warnings

# Default reference file path
DEFAULT_REFERENCE = Path(__file__).parent / "scan_vista_reference.json"


def discover_m_files(source_dir: Path) -> list[Path]:
    """Recursively find all .m files under source_dir."""
    return sorted(source_dir.rglob("*.m"))


def read_sources(m_files: list[Path]) -> list[tuple[str, str, Path]]:
    """Read source code from all .m files.

    Returns list of (source_code, routine_name, path).
    """
    items: list[tuple[str, str, Path]] = []
    for p in m_files:
        try:
            source = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                source = p.read_text(encoding="latin-1")
            except Exception as e:
                print(f"WARNING: Cannot decode {p}: {e}", file=sys.stderr)
                continue
        except OSError as e:
            print(f"WARNING: Cannot read {p}: {e}", file=sys.stderr)
            continue
        routine_name = p.stem.upper()
        items.append((source, routine_name, p))
    return items


def categorize_error(error: str) -> str:
    """Extract a high-level error category from an error message."""
    # Match the exception class name at the start
    m = re.match(r"^(\w+(?:Error|Exception)):", error)
    if m:
        exc_class = m.group(1)
        # Further sub-categorize NotImplementedError
        if exc_class == "NotImplementedError":
            if "Special variable" in error:
                svn = re.search(r"Special variable \$(\w+)", error)
                return (
                    f"NotImplementedError: SVN ${svn.group(1)}"
                    if svn
                    else "NotImplementedError: SVN"
                )
            if "Unsupported expression type" in error:
                expr = re.search(r"Unsupported expression type: (\w+)", error)
                return (
                    f"NotImplementedError: ExprType {expr.group(1)}"
                    if expr
                    else "NotImplementedError: ExprType"
                )
            if "Unsupported SET target" in error:
                return "NotImplementedError: SET target"
            if "Unsupported statement type" in error:
                stmt = re.search(r"Unsupported statement type: (\w+)", error)
                return (
                    f"NotImplementedError: StmtType {stmt.group(1)}"
                    if stmt
                    else "NotImplementedError: StmtType"
                )
            if "Intrinsic function" in error:
                fn = re.search(r"Intrinsic function \$(\w+)", error)
                return (
                    f"NotImplementedError: Fn ${fn.group(1)}"
                    if fn
                    else "NotImplementedError: Fn"
                )
            if "not yet supported" in error:
                return f"NotImplementedError: {error.split(': ', 1)[1][:60]}"
            return f"NotImplementedError: {error.split(': ', 1)[1][:60]}"
        if exc_class == "UnsupportedFeatureError":
            return f"UnsupportedFeatureError: {error.split(': ', 1)[1][:60]}"
        return exc_class
    return "Unknown"


def run_scan(
    source_dir: Path,
    output_dir: Path,
    batch_size: int = 2000,
    limit: int | None = None,
) -> dict:
    """Run transpilation scan and return metrics.

    Processes in batches to avoid OOM with large corpora.
    Uses parallel execution with per-worker warning capture.

    Args:
        source_dir: Directory containing .m files
        output_dir: Output directory for reports
        batch_size: Number of files per batch
        limit: If set, only process this many files (for testing)
    """
    print(f"Discovering .m files in {source_dir}...", flush=True)
    m_files = discover_m_files(source_dir)
    total = len(m_files)
    print(f"Found {total:,} .m files", flush=True)

    if limit is not None and limit < total:
        print(f"Limiting to first {limit:,} files (--limit)", flush=True)
        m_files = m_files[:limit]
        total = limit

    print("Reading source files...", flush=True)
    t0 = time.time()
    sources = read_sources(m_files)
    t_read = time.time() - t0
    print(f"Read {len(sources):,} files in {t_read:.1f}s", flush=True)

    # Collect metrics incrementally
    successes: list[str] = []
    failures: list[dict] = []
    error_categories: Counter[str] = Counter()
    error_details: dict[str, list[str]] = {}
    all_warnings: list[dict] = []

    n_batches = (len(sources) + batch_size - 1) // batch_size
    print(
        f"Transpiling {len(sources):,} routines in {n_batches} batches of {batch_size} (parallel with warning capture)...",
        flush=True,
    )
    t0 = time.time()

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(sources))
        batch = sources[start:end]

        items = [(src, name) for src, name, _ in batch]
        # Use transpile_sources_with_warnings for parallel execution
        # with per-worker warning capture
        results = transpile_sources_with_warnings(items)

        for (_src, name, path), (code, error, routine_warnings) in zip(batch, results):
            if error is None:
                successes.append(name)
            else:
                failures.append({"routine": name, "path": str(path), "error": error})
                cat = categorize_error(error)
                error_categories[cat] += 1
                error_details.setdefault(cat, []).append(name)

            # Collect warnings from this routine
            for warn_msg in routine_warnings:
                # Try to extract routine name from warning message
                routine_match = re.search(r"routine (\w+)", warn_msg)
                routine = routine_match.group(1) if routine_match else name
                all_warnings.append(
                    {
                        "routine": routine,
                        "category": "UserWarning",
                        "message": warn_msg[:200],
                    }
                )
                # Also print to stderr for visibility
                print(f"  Warning: {warn_msg}", file=sys.stderr, flush=True)

        done = end
        pct = done / len(sources) * 100
        print(
            f"  Batch {batch_idx + 1}/{n_batches}: {done:,}/{len(sources):,} ({pct:.0f}%) - {len(successes):,} ok, {len(failures):,} err",
            flush=True,
        )

    t_transpile = time.time() - t0
    print(f"Transpilation completed in {t_transpile:.1f}s", flush=True)

    success_count = len(successes)
    failure_count = len(failures)
    success_rate = (success_count / total * 100) if total > 0 else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source_dir": str(source_dir),
        "total_routines": total,
        "total_read": len(sources),
        "succeeded": success_count,
        "failed": failure_count,
        "success_rate_pct": round(success_rate, 2),
        "transpile_time_secs": round(t_transpile, 1),
        "error_categories": dict(error_categories.most_common()),
        "error_category_routines": {
            k: sorted(v) for k, v in sorted(error_details.items())
        },
        "failures": failures,
        "warnings": all_warnings,
        "warning_count": len(all_warnings),
    }

    return report


def write_report(report: dict, output_dir: Path) -> None:
    """Write scan report files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full JSON report
    json_path = output_dir / "baseline-report.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Full report: {json_path}")

    # Human-readable summary
    summary_path = output_dir / "baseline-summary.md"
    with open(summary_path, "w") as f:
        f.write("# VistA-VEHU-M Baseline Transpilation Scan\n\n")
        f.write(f"**Date**: {report['timestamp']}\n")
        f.write(f"**Source**: {report['source_dir']}\n\n")
        f.write("## Summary\n\n")
        f.write("| Metric | Value |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Total routines | {report['total_routines']:,} |\n")
        f.write(f"| Succeeded | {report['succeeded']:,} |\n")
        f.write(f"| Failed | {report['failed']:,} |\n")
        f.write(f"| Success rate | {report['success_rate_pct']}% |\n")
        f.write(f"| Transpile time | {report['transpile_time_secs']}s |\n\n")
        f.write("## Error Categories\n\n")
        f.write("| Category | Count |\n")
        f.write("|----------|-------|\n")
        for cat, count in sorted(
            report["error_categories"].items(), key=lambda x: -x[1]
        ):
            f.write(f"| {cat} | {count:,} |\n")
        f.write("\n")

        # Per-category routine lists
        f.write("## Affected Routines by Category\n\n")
        for cat in sorted(report["error_category_routines"].keys()):
            routines = report["error_category_routines"][cat]
            f.write(f"### {cat} ({len(routines):,} routines)\n\n")
            # Show first 20 routines, then count remainder
            shown = routines[:20]
            f.write(", ".join(shown))
            if len(routines) > 20:
                f.write(f", ... and {len(routines) - 20} more")
            f.write("\n\n")

    print(f"Summary: {summary_path}")

    # Failure list (one per line, for diffing)
    failures_path = output_dir / "failures.txt"
    with open(failures_path, "w") as f:
        for item in sorted(report["failures"], key=lambda x: x["routine"]):
            f.write(f"{item['routine']}\t{item['error'][:120]}\n")
    print(f"Failure list: {failures_path}")


def print_summary(report: dict) -> None:
    """Print summary to stdout."""
    print("\n" + "=" * 60)
    print("BASELINE SCAN RESULTS")
    print("=" * 60)
    print(f"Total:     {report['total_routines']:,}")
    print(f"Succeeded: {report['succeeded']:,}")
    print(f"Failed:    {report['failed']:,}")
    print(f"Warnings:  {report.get('warning_count', 0):,}")
    print(f"Rate:      {report['success_rate_pct']}%")
    print(f"Time:      {report['transpile_time_secs']}s")
    print()
    print("Top error categories:")
    for cat, count in sorted(report["error_categories"].items(), key=lambda x: -x[1])[
        :15
    ]:
        print(f"  {count:>5,}  {cat}")
    print("=" * 60)


def create_reference(report: dict, reference_path: Path) -> None:
    """Create reference JSON file from scan results.

    The reference contains:
    - failed_routines: sorted list of routine names that failed
    - warning_routines: sorted list of unique routines with warnings
    - warning_messages: sorted list of unique warning messages
    """
    failed_routines = sorted(f["routine"] for f in report["failures"])
    warning_routines = sorted(set(w["routine"] for w in report.get("warnings", [])))
    warning_messages = sorted(set(w["message"] for w in report.get("warnings", [])))

    reference = {
        "description": "Reference baseline for VistA-VEHU-M transpilation scan",
        "created": report["timestamp"],
        "total_routines": report["total_routines"],
        "expected_failures": len(failed_routines),
        "expected_warnings": len(warning_messages),
        "failed_routines": failed_routines,
        "warning_routines": warning_routines,
        "warning_messages": warning_messages,
    }

    reference_path.parent.mkdir(parents=True, exist_ok=True)
    with open(reference_path, "w") as f:
        json.dump(reference, f, indent=2)
    print(f"\nReference file created: {reference_path}")
    print(f"  Failed routines: {len(failed_routines)}")
    print(f"  Warning routines: {len(warning_routines)}")
    print(f"  Unique warnings: {len(warning_messages)}")


def compare_with_reference(report: dict, reference_path: Path) -> bool:
    """Compare scan results with reference and report differences.

    Returns True if results match reference (PASS), False otherwise (FAIL).
    """
    if not reference_path.exists():
        print(f"\n[SKIP] Reference file not found: {reference_path}")
        print("       Run with --update-reference to create it.")
        return True  # Don't fail if no reference exists

    with open(reference_path) as f:
        reference = json.load(f)

    print("\n" + "=" * 60)
    print("REFERENCE COMPARISON")
    print("=" * 60)

    # Extract current state
    current_failed = set(f["routine"] for f in report["failures"])
    current_warnings = set(w["message"] for w in report.get("warnings", []))

    ref_failed = set(reference.get("failed_routines", []))
    ref_warnings = set(reference.get("warning_messages", []))

    # Calculate differences
    new_failures = current_failed - ref_failed
    fixed_failures = ref_failed - current_failed
    new_warnings = current_warnings - ref_warnings
    fixed_warnings = ref_warnings - current_warnings

    is_pass = True

    # Report failure changes
    if new_failures:
        print(f"\n[REGRESSION] {len(new_failures)} new failures:")
        for r in sorted(new_failures)[:10]:
            print(f"  - {r}")
        if len(new_failures) > 10:
            print(f"  ... and {len(new_failures) - 10} more")
        is_pass = False

    if fixed_failures:
        print(f"\n[IMPROVEMENT] {len(fixed_failures)} failures fixed:")
        for r in sorted(fixed_failures)[:10]:
            print(f"  + {r}")
        if len(fixed_failures) > 10:
            print(f"  ... and {len(fixed_failures) - 10} more")
        # Fixed failures are OK, don't fail

    # Report warning changes
    if new_warnings:
        print(f"\n[REGRESSION] {len(new_warnings)} new warning types:")
        for w in sorted(new_warnings)[:5]:
            print(f"  - {w[:80]}")
        if len(new_warnings) > 5:
            print(f"  ... and {len(new_warnings) - 5} more")
        is_pass = False

    if fixed_warnings:
        print(f"\n[IMPROVEMENT] {len(fixed_warnings)} warning types resolved:")
        for w in sorted(fixed_warnings)[:5]:
            print(f"  + {w[:80]}")
        if len(fixed_warnings) > 5:
            print(f"  ... and {len(fixed_warnings) - 5} more")
        # Fixed warnings are OK, don't fail

    # Summary
    if (
        not new_failures
        and not fixed_failures
        and not new_warnings
        and not fixed_warnings
    ):
        print("\nNo changes from reference baseline.")

    print()
    if is_pass:
        print("[PASS] Results match or improve on reference baseline.")
    else:
        print("[FAIL] Results have regressions from reference baseline.")
    print("=" * 60)

    return is_pass


def main():
    parser = argparse.ArgumentParser(description="Scan VistA-VEHU-M transpilation")
    parser.add_argument(
        "--source-dir",
        default="VistA-VEHU-M",
        help="Directory containing .m files (default: VistA-VEHU-M)",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/baseline-scan",
        help="Output directory for results (default: tmp/baseline-scan)",
    )
    parser.add_argument(
        "--reference",
        default=str(DEFAULT_REFERENCE),
        help=f"Reference JSON file (default: {DEFAULT_REFERENCE})",
    )
    parser.add_argument(
        "--update-reference",
        action="store_true",
        help="Create/update reference JSON file from scan results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to first N files (for testing)",
    )
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reference_path = Path(args.reference).resolve()

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    report = run_scan(source_dir, output_dir, limit=args.limit)
    write_report(report, output_dir)
    print_summary(report)

    if args.update_reference:
        create_reference(report, reference_path)
    else:
        is_pass = compare_with_reference(report, reference_path)
        if not is_pass:
            sys.exit(1)


if __name__ == "__main__":
    main()
