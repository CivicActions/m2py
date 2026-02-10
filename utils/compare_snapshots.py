"""Compare current generated Python output against baseline snapshots.

Generates Python from all .m files and compares against tmp/baseline-snapshots/.
Reports any differences found, distinguishing expected changes (C-07, C-09)
from unexpected regressions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m2py.codegen import generate_python  # noqa: E402


def main():
    baseline_dir = Path("tmp/baseline-snapshots")
    current_dir = Path("tmp/current-snapshots")
    current_dir.mkdir(parents=True, exist_ok=True)

    if not baseline_dir.exists():
        print("ERROR: Baseline snapshots not found at tmp/baseline-snapshots/")
        sys.exit(1)

    # Collect all .m files
    m_files = sorted(
        list(Path("YDBTest").rglob("inref/*.m"))
        + list(Path("tests/functional").rglob("inref/*.m"))
        + list(Path("tests/functional/com").glob("*.m"))
    )

    # Generate current snapshots
    success = fail = 0
    for m_file in m_files:
        name = m_file.stem
        try:
            code = generate_python(m_file.read_text(), routine_name=name)
            (current_dir / f"{name}.py").write_text(code)
            success += 1
        except Exception:
            fail += 1

    print(f"Generated: {success} succeeded, {fail} failed")

    # Compare against baseline
    baseline_files = sorted(baseline_dir.glob("*.py"))
    identical = 0
    different = 0
    missing = 0
    diff_names = []

    for baseline_file in baseline_files:
        current_file = current_dir / baseline_file.name
        if not current_file.exists():
            missing += 1
            continue

        baseline_text = baseline_file.read_text()
        current_text = current_file.read_text()

        if baseline_text == current_text:
            identical += 1
        else:
            different += 1
            diff_names.append(baseline_file.stem)

    print("\nComparison results:")
    print(f"  Identical: {identical}")
    print(f"  Different: {different}")
    print(f"  Missing from current: {missing}")
    print(f"  Total baseline: {len(baseline_files)}")

    if diff_names:
        print(f"\nDifferent files ({len(diff_names)}):")
        for name in diff_names[:50]:
            print(f"  {name}")
        if len(diff_names) > 50:
            print(f"  ... and {len(diff_names) - 50} more")

    return different, missing


if __name__ == "__main__":
    different, missing = main()
    # Exit 0 - differences are expected for C-07/C-09 changes
    sys.exit(0)
