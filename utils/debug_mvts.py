"""Debug script to see MVTS test output for specific test IDs."""

import sys

sys.path.insert(0, ".")
from tests.functional.test_mvts import _get_cached_modules
from m2py.runtime import MUMPSRuntime, run_with_goto_support


def run_suite(suite_name, test_ids):
    modules, errors = _get_cached_modules()
    if suite_name in errors:
        print(f"TRANSPILE ERROR for {suite_name}: {errors[suite_name]}")
        return
    module = modules.get(suite_name)
    if module is None:
        print(f"Module {suite_name} not available")
        return

    rt = MUMPSRuntime()
    rt._capture_output = True
    rt.clear()
    rt._current_routine = getattr(module, "_routine_name", suite_name)
    rt._current_source_lines = getattr(module, "_source_lines", [])
    rt._current_label_lines = getattr(module, "_label_lines", {})
    entry = getattr(module, suite_name, None)
    if not entry:
        print(f"No entry point for {suite_name}")
        return

    try:
        run_with_goto_support(entry, rt, {})
    except Exception as e:
        print(f"ERROR: {e}")

    output = rt.get_output()
    lines = output.split("\n")

    for tid in test_ids:
        for i, line in enumerate(lines):
            if tid in line:
                start = max(0, i - 1)
                end = min(len(lines), i + 6)
                print(f"\n=== Test {tid} (lines {start}-{end}) ===")
                for j in range(start, end):
                    print(f"  {j}: {repr(lines[j])}")
                break
        else:
            print(f"\n=== Test {tid}: NOT FOUND in output ===")


if __name__ == "__main__":
    print("=" * 60)
    print("V3DWP (tests 31083, 31084)")
    print("=" * 60)
    run_suite("V3DWP", ["31083", "31084"])

    print("\n" + "=" * 60)
    print("V4NAME18 (test 40294) and V4NAME25 (test 40326)")
    print("=" * 60)
    # V4NAME is actually composed of sub-routines; let's try the individual ones
    for suite in ["V4NAME18", "V4NAME25"]:
        run_suite(suite, ["40294", "40326"])

    print("\n" + "=" * 60)
    print("V4QSUB8 (test 40453)")
    print("=" * 60)
    run_suite("V4QSUB8", ["40453"])
