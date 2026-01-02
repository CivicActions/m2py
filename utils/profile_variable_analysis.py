#!/usr/bin/env python3
"""Profile variable analysis performance on MUMPS files.

Usage:
    uv run python utils/profile_variable_analysis.py [options]

Options:
    --mugj          Profile on MUGJ test files (default)
    --vista PATH    Profile on VistA-M files at PATH
    --largest N     Only profile N largest files (by line count)
    --detailed      Show per-file timing breakdown
    --summary       Show summary statistics only
"""

import argparse
import statistics
import time
from pathlib import Path
from typing import List, Tuple

from m2py.parser.parser import MUMPSParser


def get_file_line_count(filepath: Path) -> int:
    """Get line count of a file."""
    try:
        return len(filepath.read_text(encoding="utf-8", errors="replace").splitlines())
    except Exception:
        return 0


def find_mumps_files(directory: Path, largest_n: int = None) -> List[Path]:
    """Find all .m files in directory, optionally sorted by size."""
    files = list(directory.rglob("*.m"))

    if largest_n:
        # Sort by line count descending and take largest N
        files_with_counts = [(f, get_file_line_count(f)) for f in files]
        files_with_counts.sort(key=lambda x: x[1], reverse=True)
        files = [f for f, _ in files_with_counts[:largest_n]]

    return files


def profile_file(
    parser: MUMPSParser, filepath: Path
) -> Tuple[float, float, float, int, int]:
    """Profile parsing and analysis of a single file.

    Returns:
        Tuple of (parse_time, analyze_time, signature_time, line_count, label_count)
    """
    line_count = get_file_line_count(filepath)

    # Time parsing
    start = time.perf_counter()
    try:
        routine = parser.parse_file(filepath)
    except Exception:
        return (0, 0, 0, line_count, 0)
    parse_time = time.perf_counter() - start

    label_count = len(routine.labels)

    # Time variable analysis
    start = time.perf_counter()
    try:
        parser.analyze_variables(routine, compute_transitive=True)
    except Exception:
        return (parse_time, 0, 0, line_count, label_count)
    analyze_time = time.perf_counter() - start

    # Time signature computation
    start = time.perf_counter()
    try:
        parser.compute_signatures(routine)
    except Exception:
        return (parse_time, analyze_time, 0, line_count, label_count)
    signature_time = time.perf_counter() - start

    return (parse_time, analyze_time, signature_time, line_count, label_count)


def main():
    parser = argparse.ArgumentParser(
        description="Profile variable analysis performance"
    )
    parser.add_argument("--mugj", action="store_true", help="Profile MUGJ test files")
    parser.add_argument("--vista", type=str, help="Profile VistA-M files at PATH")
    parser.add_argument("--largest", type=int, help="Only profile N largest files")
    parser.add_argument(
        "--detailed", action="store_true", help="Show per-file breakdown"
    )
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    args = parser.parse_args()

    # Default to MUGJ if no path specified
    if args.vista:
        source_dir = Path(args.vista)
    else:
        source_dir = Path("tests/functional/mugj/inref")

    if not source_dir.exists():
        print(f"Error: Directory not found: {source_dir}")
        return 1

    # Find files
    files = find_mumps_files(source_dir, args.largest)
    print(f"Found {len(files)} .m files in {source_dir}")

    if not files:
        print("No files found!")
        return 1

    # Profile each file
    mumps_parser = MUMPSParser()
    results = []

    total_start = time.perf_counter()

    for i, filepath in enumerate(files):
        result = profile_file(mumps_parser, filepath)
        results.append((filepath, *result))

        if args.detailed and not args.summary:
            parse_t, analyze_t, sig_t, lines, labels = result
            total_t = parse_t + analyze_t + sig_t
            print(
                f"{filepath.name:40} {lines:5} lines {labels:4} labels "
                f"parse={parse_t * 1000:6.1f}ms analyze={analyze_t * 1000:6.1f}ms "
                f"sig={sig_t * 1000:6.1f}ms total={total_t * 1000:6.1f}ms"
            )

        # Progress indicator
        if not args.detailed and (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(files)} files...")

    total_elapsed = time.perf_counter() - total_start

    # Compute statistics
    parse_times = [r[1] for r in results]
    analyze_times = [r[2] for r in results]
    sig_times = [r[3] for r in results]
    line_counts = [r[4] for r in results]
    label_counts = [r[5] for r in results]
    total_times = [r[1] + r[2] + r[3] for r in results]

    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    print(f"\nFiles analyzed: {len(files)}")
    print(f"Total lines: {sum(line_counts):,}")
    print(f"Total labels: {sum(label_counts):,}")
    print(f"Total wall time: {total_elapsed:.2f}s")

    print("\n--- Timing Statistics (milliseconds) ---")
    print(
        f"{'Metric':<20} {'Mean':>10} {'Median':>10} {'Std Dev':>10} {'Max':>10} {'Total':>10}"
    )
    print("-" * 70)

    for name, times in [
        ("Parse", parse_times),
        ("Analyze", analyze_times),
        ("Signatures", sig_times),
        ("Total", total_times),
    ]:
        if times:
            mean = statistics.mean(times) * 1000
            median = statistics.median(times) * 1000
            stdev = statistics.stdev(times) * 1000 if len(times) > 1 else 0
            max_t = max(times) * 1000
            total = sum(times) * 1000
            print(
                f"{name:<20} {mean:>10.2f} {median:>10.2f} {stdev:>10.2f} {max_t:>10.2f} {total:>10.0f}"
            )

    # Find slowest files
    print("\n--- Top 10 Slowest Files (by total time) ---")
    sorted_results = sorted(results, key=lambda x: x[1] + x[2] + x[3], reverse=True)
    for filepath, parse_t, analyze_t, sig_t, lines, labels in sorted_results[:10]:
        total_t = parse_t + analyze_t + sig_t
        print(
            f"{filepath.name:40} {lines:5} lines {labels:4} labels "
            f"{total_t * 1000:8.2f}ms (parse={parse_t * 1000:.1f} analyze={analyze_t * 1000:.1f} sig={sig_t * 1000:.1f})"
        )

    # Find largest files
    print("\n--- Top 10 Largest Files (by line count) ---")
    sorted_by_lines = sorted(results, key=lambda x: x[4], reverse=True)
    for filepath, parse_t, analyze_t, sig_t, lines, labels in sorted_by_lines[:10]:
        total_t = parse_t + analyze_t + sig_t
        lines_per_sec = lines / total_t if total_t > 0 else 0
        print(
            f"{filepath.name:40} {lines:5} lines {labels:4} labels "
            f"{total_t * 1000:8.2f}ms ({lines_per_sec:.0f} lines/sec)"
        )

    # Check performance target (SC-005: 500-line routine in <2 seconds)
    print("\n--- Performance Target Check (SC-005) ---")
    files_over_500 = [
        (f, p + a + s, lines) for f, p, a, s, lines, lb in results if lines >= 500
    ]
    if files_over_500:
        all_under_2s = all(t < 2.0 for _, t, _ in files_over_500)
        max_time = max(t for _, t, _ in files_over_500)
        print(f"Files with 500+ lines: {len(files_over_500)}")
        print(f"Max analysis time for 500+ line file: {max_time * 1000:.2f}ms")
        print(f"All under 2 seconds: {'✅ YES' if all_under_2s else '❌ NO'}")
    else:
        print("No files with 500+ lines found in this set")

    return 0


if __name__ == "__main__":
    exit(main())
