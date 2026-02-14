#!/usr/bin/env python3
"""Rebuild auto-generated documentation files.

Generates:
- docs/limitations.md - Known limitations and gaps

Usage:
    uv run python utils/rebuild_docs.py              # Generate limitations doc
    uv run python utils/rebuild_docs.py --quiet      # Suppress output

Exit codes:
    0 - Success
    1 - Error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to path for importing limitations
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from m2py.limitations import generate_limitations_md


def rebuild_limitations(project_root: Path, quiet: bool = False) -> bool:
    """Rebuild docs/limitations.md from limitations.py.

    Args:
        project_root: Path to project root
        quiet: Suppress output

    Returns:
        True on success
    """
    output_path = project_root / "docs" / "limitations.md"
    content = generate_limitations_md()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    if not quiet:
        print(f"Generated {output_path}")

    return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rebuild auto-generated documentation files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output messages",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    rebuild_limitations(project_root, args.quiet)

    return 0


if __name__ == "__main__":
    sys.exit(main())
