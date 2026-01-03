#!/usr/bin/env python3
"""
Verify VistA-M MUMPS file parsing capability.

This script tests M2PY's ability to parse VistA-M MUMPS source files,
verifying backward compatibility with legacy MUMPS syntax.

Usage:
    uv run python utils/verify_vista_parse.py [OPTIONS]

Options:
    --sample N      Parse N random files (default: 100)
    --all           Parse all VistA-M files (slow, ~34k files)
    --verbose       Show per-file results
    --file PATH     Parse a specific file
    --package NAME  Parse all files in a specific package

Exit codes:
    0: All files parsed successfully
    1: Some files failed to parse
    2: No files found or configuration error
"""

import argparse
import random
import sys
import time
from pathlib import Path
from typing import Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
VISTA_M_DIR = PROJECT_ROOT / "VistA-M" / "Packages"


def discover_mumps_files(
    package: Optional[str] = None,
    sample_size: Optional[int] = None,
) -> list[Path]:
    """Discover MUMPS source files in VistA-M directory.

    Args:
        package: If specified, only include files from this package.
        sample_size: If specified, return a random sample of this size.

    Returns:
        List of Path objects to MUMPS source files.
    """
    if not VISTA_M_DIR.exists():
        print(f"Error: VistA-M directory not found: {VISTA_M_DIR}", file=sys.stderr)
        return []

    search_path = VISTA_M_DIR
    if package:
        # Find package directory (may have spaces)
        candidates = list(VISTA_M_DIR.glob(f"*{package}*"))
        if not candidates:
            print(f"Error: Package not found: {package}", file=sys.stderr)
            return []
        search_path = candidates[0]
        print(f"Using package directory: {search_path.name}")

    all_files = list(search_path.rglob("*.m"))

    if sample_size and len(all_files) > sample_size:
        return random.sample(all_files, sample_size)

    return all_files


def parse_file(filepath: Path, verbose: bool = False) -> tuple[bool, Optional[str]]:
    """Parse a single MUMPS file.

    Args:
        filepath: Path to the MUMPS file.
        verbose: If True, print success messages.

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        # Add src to path if needed
        src_path = PROJECT_ROOT / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        # Import here to ensure proper path setup
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse_file(str(filepath))

        if verbose:
            label_count = len(routine.labels) if hasattr(routine, "labels") else 0
            print(f"  ✓ {filepath.name}: {label_count} labels")

        return True, None

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        return False, error_msg


def main() -> int:
    """Main entry point."""
    arg_parser = argparse.ArgumentParser(
        description="Verify VistA-M MUMPS file parsing capability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    arg_parser.add_argument(
        "--sample",
        type=int,
        default=100,
        help="Number of random files to parse (default: 100)",
    )
    arg_parser.add_argument(
        "--all",
        action="store_true",
        help="Parse all VistA-M files (~34k files)",
    )
    arg_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-file results",
    )
    arg_parser.add_argument(
        "--file",
        type=str,
        help="Parse a specific file path",
    )
    arg_parser.add_argument(
        "--package",
        type=str,
        help="Parse all files in a specific package",
    )
    args = arg_parser.parse_args()

    print("=" * 60)
    print("VistA-M MUMPS Parsing Verification")
    print("=" * 60)
    print()

    # Handle single file mode
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 2

        print(f"Parsing single file: {filepath.name}")
        success, error = parse_file(filepath, verbose=True)
        if success:
            print("\n✓ File parsed successfully")
            return 0
        else:
            print(f"\n✗ Parse failed: {error}")
            return 1

    # Discover files
    sample_size = None if args.all else args.sample
    files = discover_mumps_files(package=args.package, sample_size=sample_size)

    if not files:
        print("Error: No MUMPS files found", file=sys.stderr)
        return 2

    print(f"Found {len(files)} MUMPS files to parse")
    print()

    # Parse files
    start_time = time.time()
    successes = 0
    failures: list[tuple[Path, str]] = []

    for i, filepath in enumerate(files, 1):
        if args.verbose or (i % 100 == 0):
            print(f"Progress: {i}/{len(files)} files...", end="\r")

        success, error = parse_file(filepath, verbose=args.verbose)
        if success:
            successes += 1
        else:
            failures.append((filepath, error or "Unknown error"))

    elapsed = time.time() - start_time

    # Report results
    print()
    print("-" * 60)
    print("Results")
    print("-" * 60)
    print(f"Total files:    {len(files)}")
    print(f"Parsed OK:      {successes} ({100 * successes / len(files):.1f}%)")
    print(f"Parse failures: {len(failures)} ({100 * len(failures) / len(files):.1f}%)")
    print(f"Time elapsed:   {elapsed:.2f} seconds")
    print(f"Files/second:   {len(files) / elapsed:.1f}")
    print()

    # Show failures if any
    if failures:
        print("Failed files:")
        for filepath, error in failures[:20]:  # Show first 20
            relative_path = filepath.relative_to(PROJECT_ROOT)
            print(f"  ✗ {relative_path}")
            print(f"    {error}")

        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more failures")

        print()
        print("✗ VERIFICATION FAILED")
        return 1

    print("✓ ALL FILES PARSED SUCCESSFULLY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
