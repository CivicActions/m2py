#!/usr/bin/env python3
"""Coverage check utility for M2PY development.

Provides two metrics:
1. Overall test coverage (must stay ≥85%)
2. Transpilation readiness (parser/asg/analysis coverage from codegen tests only)

Usage:
    uv run python utils/coverage_check.py          # Both metrics
    uv run python utils/coverage_check.py overall  # Just overall coverage
    uv run python utils/coverage_check.py transpile # Just transpilation readiness
"""

import subprocess
import sys
import re


# Thresholds
OVERALL_COVERAGE_MIN = 85
TRANSPILE_BASELINE = 15  # Import overhead (0% progress)
TRANSPILE_TARGET = 85  # Full transpilation (100% progress)


def run_coverage(
    test_path: str, cov_paths: list[str], quiet: bool = True
) -> float | None:
    """Run pytest with coverage and extract the total percentage."""
    cmd = [
        "uv",
        "run",
        "pytest",
        test_path,
        "--cov-report=term-missing:skip-covered",
    ]
    if quiet:
        cmd.append("-q")

    for path in cov_paths:
        cmd.extend(["--cov", path])

    print(f"Running: {' '.join(cmd[:6])}...")
    sys.stdout.flush()

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse coverage from output - look for TOTAL line
    # Format: TOTAL   3853   2997   1956      7    15%
    for line in result.stdout.split("\n"):
        if line.startswith("TOTAL"):
            match = re.search(r"(\d+)%", line)
            if match:
                return float(match.group(1))

    # Fallback: look for coverage percentage in last lines
    for line in reversed(result.stdout.split("\n")):
        match = re.search(r"(\d+)%", line)
        if match:
            return float(match.group(1))

    print("Could not parse coverage output:")
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-500:])
    return None


def check_overall_coverage() -> tuple[bool, float | None]:
    """Check overall test coverage meets minimum threshold."""
    print("=" * 60)
    print("OVERALL TEST COVERAGE")
    print("=" * 60)

    coverage = run_coverage("tests/unit/", ["src/m2py"])

    if coverage is None:
        print("❌ FAILED: Could not measure coverage")
        return False, None

    passed = coverage >= OVERALL_COVERAGE_MIN
    status = "✅ PASS" if passed else "❌ FAIL"

    print(f"\nCoverage: {coverage:.0f}%")
    print(f"Minimum:  {OVERALL_COVERAGE_MIN}%")
    print(f"Status:   {status}")

    if not passed:
        print(f"\n⚠️  Coverage dropped below {OVERALL_COVERAGE_MIN}%!")
        print("   Review recent changes and add missing tests.")

    return passed, coverage


def check_transpilation_readiness() -> tuple[float | None, float | None]:
    """Check transpilation readiness (parser/asg coverage from codegen tests)."""
    print("\n" + "=" * 60)
    print("TRANSPILATION READINESS")
    print("=" * 60)

    coverage = run_coverage(
        "tests/unit/codegen/", ["src/m2py/parser", "src/m2py/asg", "src/m2py/analysis"]
    )

    if coverage is None:
        print("❌ FAILED: Could not measure coverage")
        return None, None

    # Normalize: 15% = 0% progress, 85% = 100% progress
    progress = (
        (coverage - TRANSPILE_BASELINE) / (TRANSPILE_TARGET - TRANSPILE_BASELINE) * 100
    )
    progress = max(0, min(100, progress))  # Clamp to 0-100

    print(f"\nParser/ASG/Analysis coverage: {coverage:.0f}%")
    print(f"Baseline (imports only):      {TRANSPILE_BASELINE}%")
    print(f"Target (full transpilation):  {TRANSPILE_TARGET}%")
    print(f"\n📊 TRANSPILATION PROGRESS: {progress:.1f}%")

    # Progress bar
    bar_width = 40
    filled = int(bar_width * progress / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"   [{bar}]")

    # Interpretation
    if progress < 10:
        print("\n   Status: Just getting started (mostly stubs)")
    elif progress < 30:
        print("\n   Status: Basic constructs working")
    elif progress < 60:
        print("\n   Status: Core language features implemented")
    elif progress < 90:
        print("\n   Status: Most syntax transpilable")
    else:
        print("\n   Status: Near-complete transpilation support!")

    return coverage, progress


def main():
    args = sys.argv[1:]

    if not args or "overall" in args or "all" in args:
        passed, overall_cov = check_overall_coverage()
    else:
        passed = True
        overall_cov = None

    if not args or "transpile" in args or "all" in args:
        _transpile_cov, progress = check_transpilation_readiness()
    else:
        progress = None

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if overall_cov is not None:
        status = "✅" if passed else "❌"
        print(
            f"{status} Overall coverage: {overall_cov:.0f}% (min: {OVERALL_COVERAGE_MIN}%)"
        )

    if progress is not None:
        print(f"📊 Transpilation progress: {progress:.1f}%")

    # Exit code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
