#!/usr/bin/env python3
"""Find all MUGJ files that have parse errors after parsing.

This script identifies files where UnknownCommand or other parsing failures
are being masked by error-tolerant parsing.
"""

from pathlib import Path
from m2py.parser import MUMPSParser
from m2py.asg import MRoutine


def analyze_mugj_parse_errors():
    """Analyze all MUGJ files for parse errors."""
    parser = MUMPSParser()
    mugj_dir = Path("tests/functional/mugj/inref")

    files_with_errors = []
    files_clean = []

    for filepath in sorted(mugj_dir.glob("*.m")):
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
            print(f"EXCEPTION: {filepath.name} - {e}")

    print(f"\n{'=' * 60}")
    print("MUGJ Parse Error Analysis")
    print(f"{'=' * 60}")
    print(f"\nClean files (0 parse errors): {len(files_clean)}")
    print(f"Files with parse errors: {len(files_with_errors)}")

    if files_with_errors:
        print(f"\n{'=' * 60}")
        print("FILES WITH PARSE ERRORS:")
        print(f"{'=' * 60}")

        for filename, errors in files_with_errors:
            print(f"\n{filename}: {len(errors)} error(s)")
            for i, err in enumerate(errors[:5]):  # Show first 5 errors
                content = err.line_content[:60] if err.line_content else "(no content)"
                print(f"  Line {err.line_number}: {content}...")
                msg = getattr(err, "error_message", None) or getattr(
                    err, "message", None
                )
                if msg:
                    print(f"    Error: {msg[:80]}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")

    return files_with_errors, files_clean


if __name__ == "__main__":
    analyze_mugj_parse_errors()
