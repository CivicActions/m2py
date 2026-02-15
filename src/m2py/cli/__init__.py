"""Command-line interface for M2PY.

Entry point: ``m2py.cli:main``

Usage::

    m2py <PATH> [PATH ...] [-o OUTPUT_DIR] [-v] [--no-format]
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from m2py.cli.transpile import transpile_paths


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the m2py CLI."""
    parser = argparse.ArgumentParser(
        prog="m2py",
        description="Transpile MUMPS .m files to Python.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="MUMPS .m files or directories to transpile (directories searched recursively)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default=None,
        help="Output directory (mirrors input structure). Default: write alongside input.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Print detailed progress to stderr.",
    )
    parser.add_argument(
        "--no-format",
        action="store_true",
        default=False,
        help="Skip ruff lint-fix and formatting on generated output.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for m2py.

    Parses arguments, calls :func:`transpile_paths`, prints a summary to
    stderr, and returns an exit code (0 = all OK, 1 = failures).

    Args:
        argv: Command-line arguments. ``None`` means ``sys.argv[1:]``.

    Returns:
        0 if all files transpiled successfully, 1 otherwise.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    summary = transpile_paths(
        args.paths,
        output_dir=args.output,
        no_format=args.no_format,
        verbose=args.verbose,
    )

    # Print summary to stderr
    if summary.total == 0:
        print("No .m files found.", file=sys.stderr)
        return 1

    if summary.all_ok:
        print(
            f"Transpiled {summary.succeeded}/{summary.total} files",
            file=sys.stderr,
        )
    else:
        print(
            f"Transpiled {summary.succeeded}/{summary.total} files "
            f"({summary.failed} failed)",
            file=sys.stderr,
        )
        # List errors for failed files
        for result in summary.results:
            if not result.success:
                print(
                    f"  ERROR: {result.input_path.name} — {result.error}",
                    file=sys.stderr,
                )

    return 0 if summary.all_ok else 1
