#!/usr/bin/env python3
"""Find I/O commands in Version 2 test files."""

import sys
from pathlib import Path


def find_io_commands(filepath: Path) -> list[dict]:
    """Find I/O commands in source."""
    issues = []
    source_lines = filepath.read_text().split("\n")

    for line_num, line in enumerate(source_lines, 1):
        line_upper = line.strip().upper()
        # Skip comments
        if not line_upper or line_upper.startswith(";"):
            continue

        # Check for I/O commands
        for cmd in ["OPEN", "CLOSE", "USE", "JOB"]:
            if line_upper.startswith(f"{cmd} ") or f" {cmd} " in line_upper:
                issues.append({"line": line_num, "command": cmd, "text": line.strip()})

    return issues


def main():
    """Find I/O commands in VV files."""
    mugj_dir = Path("tests/functional/mugj/inref")
    vv_files = sorted([f for f in mugj_dir.glob("VV*.m")])

    print("=" * 80)
    print("VERSION 2 FILES WITH I/O COMMANDS")
    print("=" * 80)
    print()

    files_with_io = []

    for filepath in vv_files:
        io_cmds = find_io_commands(filepath)
        if io_cmds:
            files_with_io.append((filepath.name, io_cmds))
            print(f"{filepath.name}:")
            for cmd in io_cmds:
                print(f"  Line {cmd['line']:3}: {cmd['command']:5} - {cmd['text']}")
            print()

    print("=" * 80)
    print(f"Found {len(files_with_io)} Version 2 files with I/O commands")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
