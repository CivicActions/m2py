#!/usr/bin/env python3
"""Scan VistA-VEHU-M routines and report transpilation success/failure metrics.

Usage:
    uv run python utils/scan_vista.py [--output-dir DIR] [--source-dir DIR]

Defaults:
    --source-dir  VistA-VEHU-M
    --output-dir  tmp/baseline-scan
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

from m2py.cli.transpile import transpile_sources


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


def run_scan(source_dir: Path, output_dir: Path, batch_size: int = 2000) -> dict:
    """Run transpilation scan and return metrics.

    Processes in batches to avoid OOM with large corpora.
    """
    print(f"Discovering .m files in {source_dir}...", flush=True)
    m_files = discover_m_files(source_dir)
    total = len(m_files)
    print(f"Found {total:,} .m files", flush=True)

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

    n_batches = (len(sources) + batch_size - 1) // batch_size
    print(
        f"Transpiling {len(sources):,} routines in {n_batches} batches of {batch_size}...",
        flush=True,
    )
    t0 = time.time()

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(sources))
        batch = sources[start:end]

        items = [(src, name) for src, name, _ in batch]
        results = transpile_sources(items)

        for (src, name, path), (code, error) in zip(batch, results):
            if error is None:
                successes.append(name)
            else:
                failures.append({"routine": name, "path": str(path), "error": error})
                cat = categorize_error(error)
                error_categories[cat] += 1
                error_details.setdefault(cat, []).append(name)

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
    print(f"Rate:      {report['success_rate_pct']}%")
    print(f"Time:      {report['transpile_time_secs']}s")
    print()
    print("Top error categories:")
    for cat, count in sorted(report["error_categories"].items(), key=lambda x: -x[1])[
        :15
    ]:
        print(f"  {count:>5,}  {cat}")
    print("=" * 60)


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
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    report = run_scan(source_dir, output_dir)
    write_report(report, output_dir)
    print_summary(report)


if __name__ == "__main__":
    main()
