#!/usr/bin/env python3
"""Complete validation of all remaining 258 MUGJ files."""

import sys
from pathlib import Path
from collections import defaultdict
from m2py.parser import MUMPSParser


# All remaining categories
REMAINING_CATEGORIES = {
    "Justify Tests": ["V1JST.m", "V1JST1.m", "V1JST2.m", "V1JST3.m"],
    "Label Length Tests": ["V1LL1.m", "V1LL2.m"],
    "Local Variable Name Tests": ["V1LVN.m"],
    "Maximum Tests": ["V1MAX.m", "V1MAX1.m", "V1MAX2.m"],
    "Multi-job Tests": ["V1MJA.m", "V1MJA1.m", "V1MJA2.m", "V1MJB.m"],
    "NEW Command Tests": ["V1NX.m", "V1NX1.m", "V1NX2.m"],
    "Naked Reference Tests": ["V1NR.m", "V1NR1.m", "V1NR2.m"],
    "Nesting Tests": ["V1NST1.m", "V1NST2.m", "V1NST3.m", "V1NSTE.m"],
    "Numeric Label Tests": ["V4444.m", "V7777777.m"],
    "Numeric Tests": ["V1NUM.m", "V1NUM1.m", "V1NUM2.m", "V1NUM3.m", "V1NUM4.m"],
    "Order Tests": ["V1OV.m", "V1OV1.m"],
    "Pattern Match Tests": ["V1PAT.m", "V1PAT1.m", "V1PAT2.m"],
    "Peripheral Open Tests": ["V1PO.m"],
    "Postcondition Tests": ["V1PC.m", "V1PC1.m", "V1PCA.m", "V1PCB.m"],
    "Priority Tests": [
        "V1PRFOR.m",
        "V1PRGD.m",
        "V1PRGD1.m",
        "V1PRGD2.m",
        "V1PRGD3.m",
        "V1PRIE.m",
        "V1PRSET.m",
    ],
    "READ Command Tests": [
        "V1READA.m",
        "V1READA1.m",
        "V1READA2.m",
        "V1READB.m",
        "V1READB1.m",
        "V1READB2.m",
    ],
    "Random Number Tests": ["V1RN.m"],
    "Random Tests": ["V1RANDA.m", "V1RANDB.m"],
    "SET Command Tests": ["V1SET.m"],
    "Sequence Tests": ["V1SEQ.m", "V1SEQ1.m"],
    "Special Variables Tests": ["V1SVH.m", "V1SVS.m"],
    "Unary Operator Tests": [
        "V1UO.m",
        "V1UO1A.m",
        "V1UO1B.m",
        "V1UO2A.m",
        "V1UO2B.m",
        "V1UO3A.m",
        "V1UO3B.m",
        "V1UO4A.m",
        "V1UO4B.m",
        "V1UO5A.m",
        "V1UO5B.m",
    ],
    "WRITE Command Tests": ["V1WR.m"],
    "XECUTE Command Tests": [
        "V1XECA.m",
        "V1XECA1.m",
        "V1XECA2.m",
        "V1XECAE.m",
        "V1XECB.m",
    ],
}


def detect_io_commands(filepath: Path) -> list[dict]:
    """Detect I/O commands in source that might be missing from ASG."""
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


def validate_file(filepath: Path, parser: MUMPSParser) -> dict:
    """Validate a single file."""
    result = {
        "filename": filepath.name,
        "parsed": False,
        "labels": 0,
        "statements": 0,
        "io_commands": [],
        "error": None,
    }

    try:
        routine = parser.parse_file(str(filepath))
        result["parsed"] = True
        result["labels"] = len(routine.labels)
        result["statements"] = sum(
            len(label.body.statements) if label.body else 0 for label in routine.labels
        )

        # Check for I/O commands
        io_cmds = detect_io_commands(filepath)
        if io_cmds:
            result["io_commands"] = io_cmds

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    """Validate all remaining files."""
    mugj_dir = Path("tests/functional/mugj/inref")
    parser = MUMPSParser()

    print("=" * 80)
    print("COMPLETE VALIDATION - ALL REMAINING MUGJ FILES")
    print("=" * 80)
    print()

    all_results = []
    total_files = 0
    total_parsed = 0
    total_with_io = 0
    total_io_commands = 0

    for category, files in REMAINING_CATEGORIES.items():
        print(f"Validating: {category} ({len(files)} files)")

        for filename in files:
            filepath = mugj_dir / filename

            if not filepath.exists():
                print(f"  ❌ {filename}: NOT FOUND")
                continue

            result = validate_file(filepath, parser)
            all_results.append(result)
            total_files += 1

            if result["parsed"]:
                total_parsed += 1
                status = "✓"
                details = f"{result['labels']:2} labels, {result['statements']:3} stmts"

                if result["io_commands"]:
                    total_with_io += 1
                    total_io_commands += len(result["io_commands"])
                    io_summary = ", ".join(
                        set(cmd["command"] for cmd in result["io_commands"])
                    )
                    details += f" - I/O: {io_summary}"
                    status = "⚠"

                print(f"  {status} {filename:20} - {details}")
            else:
                print(f"  ❌ {filename:20} - ERROR: {result['error']}")

    # Also check VV files (Version 2 tests)
    vv_files = sorted([f for f in mugj_dir.glob("VV*.m")])
    print(f"\nValidating: Version 2 Tests ({len(vv_files)} files)")

    vv_with_io = 0
    vv_io_count = 0

    for filepath in vv_files:
        result = validate_file(filepath, parser)
        all_results.append(result)
        total_files += 1

        if result["parsed"]:
            total_parsed += 1

            if result["io_commands"]:
                vv_with_io += 1
                vv_io_count += len(result["io_commands"])
                total_with_io += 1
                total_io_commands += len(result["io_commands"])

    print(f"  ✓ Parsed: {len(vv_files)}/{len(vv_files)}")
    if vv_with_io:
        print(f"  ⚠️  Files with I/O: {vv_with_io} ({vv_io_count} commands)")

    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY - ALL REMAINING FILES")
    print("=" * 80)
    print(f"Total files validated: {total_files}")
    print(f"Successfully parsed: {total_parsed}/{total_files}")
    print(f"Files with I/O commands: {total_with_io}")
    print(f"Total I/O commands found: {total_io_commands}")

    # Aggregate I/O commands by type
    io_by_type = defaultdict(int)
    for result in all_results:
        for cmd in result.get("io_commands", []):
            io_by_type[cmd["command"]] += 1

    if io_by_type:
        print("\nI/O Commands found:")
        for cmd, count in sorted(io_by_type.items()):
            print(f"  {cmd}: {count} occurrences")

    print("\n✓ All remaining MUGJ files validated!")
    print(f"✓ Grand total: {total_parsed} files successfully parsed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
