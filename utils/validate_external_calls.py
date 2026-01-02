#!/usr/bin/env python3
"""Validate all MUGJ files with external routine calls (T374)."""

import sys
import re
from pathlib import Path
from m2py.parser import MUMPSParser


def check_external_calls_in_file(filepath: Path) -> tuple[bool, list[str]]:
    """Check if all external calls in file have name='' not name=None.

    Returns:
        (success, errors): success=True if all calls correct, errors list of issues
    """
    try:
        parser = MUMPSParser()
        routine = parser.parse(filepath.read_text(), str(filepath.name))

        errors = []

        def check_call(call, location):
            """Check a single MCall object."""
            if call.routine is not None and call.name is None:
                errors.append(f"{location}: External call has name=None (should be '')")
            elif call.routine is not None and call.name == "":
                # This is correct
                pass

        # Check all labels
        for label in routine.labels:
            if not label.body or not label.body.statements:
                continue

            for i, stmt in enumerate(label.body.statements):
                stmt_type = stmt.__class__.__name__
                location = f"{label.name}+{i + 1}"

                # Check DO statements
                if stmt_type == "MDoStatement":
                    for target in stmt.targets:
                        check_call(target, f"{location} DO")

                # Check GOTO statements
                elif stmt_type == "MGotoStatement":
                    for target in stmt.targets:
                        check_call(target, f"{location} GOTO")

        return (len(errors) == 0, errors)

    except Exception as e:
        return (False, [f"Parse error: {str(e)}"])


def has_external_call(filepath: Path) -> bool:
    """Check if file contains external routine call syntax (^ROUTINE)."""
    content = filepath.read_text()
    # Match D ^ROUTINE or G ^ROUTINE or $$^ROUTINE
    return re.search(r"[DG]\s+\^[A-Z%]|\$\$\^[A-Z%]", content) is not None


def main():
    """Validate all MUGJ files with external routine calls."""
    mugj_dir = Path("/Users/owen.barton/workspace/m2py/tests/functional/mugj/inref")

    if not mugj_dir.exists():
        print(f"ERROR: MUGJ directory not found: {mugj_dir}")
        return 1

    # Find all .m files with external calls
    all_files = sorted(mugj_dir.glob("*.m"))
    affected_files = [f for f in all_files if has_external_call(f)]

    print(f"Found {len(all_files)} total MUMPS files")
    print(f"Validating {len(affected_files)} files with external routine calls...")
    print()

    passed_files = 0
    failed_files = 0

    for filepath in affected_files:
        success, errors = check_external_calls_in_file(filepath)

        if success:
            print(f"✓ {filepath.name}")
            passed_files += 1
        else:
            print(f"❌ {filepath.name}:")
            for error in errors:
                print(f"   {error}")
            failed_files += 1

    print()
    print("=" * 80)
    print("VALIDATION SUMMARY:")
    print(f"  Total files:   {len(affected_files)}")
    print(f"  ✓ Passed:      {passed_files}")
    print(f"  ❌ Failed:      {failed_files}")
    print("=" * 80)

    if failed_files > 0:
        return 1

    print()
    print(f"🎉 All {len(affected_files)} files validated successfully!")
    print("   External routine calls all have name='' (not None)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
