"""Command-line interface for m2py.

Entry point: ``m2py.cli:main``

Usage::

    m2py transpile <PATH> [PATH ...] [-o OUTPUT_DIR] [-v] [--no-format]
    m2py globals import <file.zwr> [--backend <type>]
    m2py globals export <file.zwr> [--globals '^DD,^DIC'] [--backend <type>]
"""

from __future__ import annotations

import sys
from typing import Optional, Sequence

import click

from m2py.cli.globals import globals_group
from m2py.cli.transpile import transpile_paths


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """m2py — MUMPS-to-Python transpiler and global data toolkit."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), err=True)


@cli.command()  # type: ignore[attr-defined]
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=False))
@click.option(
    "-o",
    "--output",
    "output_dir",
    default=None,
    type=click.Path(),
    help="Output directory (mirrors input structure). Default: write alongside input.",
)
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Print detailed progress."
)
@click.option(
    "--no-format",
    is_flag=True,
    default=False,
    help="Skip ruff lint-fix and formatting on generated output.",
)
def transpile(
    paths: tuple[str, ...],
    output_dir: str | None,
    verbose: bool,
    no_format: bool,
) -> None:
    """Transpile MUMPS .m files or directories to Python."""
    summary = transpile_paths(
        list(paths),
        output_dir=output_dir,
        no_format=no_format,
        verbose=verbose,
    )

    if summary.total == 0:
        click.echo("No .m files found.", err=True)
        sys.exit(1)

    if summary.all_ok:
        click.echo(
            f"Transpiled {summary.succeeded}/{summary.total} files",
            err=True,
        )
    else:
        click.echo(
            f"Transpiled {summary.succeeded}/{summary.total} files "
            f"({summary.failed} failed)",
            err=True,
        )
        for result in summary.results:
            if not result.success:
                click.echo(
                    f"  ERROR: {result.input_path.name} — {result.error}",
                    err=True,
                )
        sys.exit(1)


cli.add_command(globals_group, name="globals")  # type: ignore[attr-defined]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for m2py.

    Wraps the click CLI so it can be called programmatically from tests
    and from the ``[project.scripts]`` entry point.

    Args:
        argv: Command-line arguments. ``None`` means ``sys.argv[1:]``.

    Returns:
        0 on success, non-zero on failure.
    """
    try:
        cli(args=list(argv) if argv is not None else None, standalone_mode=False)  # type: ignore[call-arg]
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except click.exceptions.UsageError:
        return 2
    return 0
