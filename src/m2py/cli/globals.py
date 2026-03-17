"""CLI subcommands for ZWR global import/export.

Usage::

    m2py globals import <file.zwr> [--backend <type>]
    m2py globals export <file.zwr> [--globals '^DD,^DIC'] [--backend <type>]
"""

from __future__ import annotations

import sys
from pathlib import Path

import click


@click.group("globals", invoke_without_command=True)
@click.pass_context
def globals_group(ctx: click.Context) -> None:
    """Import/export MUMPS globals in ZWR format."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _get_backend(backend_name: str):  # noqa: ANN202
    """Create a GlobalStorageBackend from the backend name."""
    if backend_name == "sqlite":
        from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

        return SQLiteGlobalStorage()

    from m2py.runtime.globals import InMemoryGlobalStorage

    return InMemoryGlobalStorage()


@globals_group.command("import")
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--backend",
    default="inmemory",
    type=click.Choice(["inmemory", "sqlite"]),
    help="Global storage backend (default: inmemory).",
)
def globals_import(file: Path, backend: str) -> None:
    """Import a ZWR file into global storage."""
    from m2py.runtime.zwr import import_zwr

    storage = _get_backend(backend)
    try:
        count = import_zwr(storage, file)
    except ValueError as e:
        click.echo(f"Error parsing ZWR: {e}", err=True)
        sys.exit(1)

    click.echo(f"Imported {count} nodes from {file}", err=True)


@globals_group.command("export")
@click.argument("file", type=click.Path(path_type=Path))
@click.option(
    "--globals",
    "global_names",
    required=True,
    help="Comma-separated global names to export (e.g. '^DD,^DIC').",
)
@click.option(
    "--backend",
    default="inmemory",
    type=click.Choice(["inmemory", "sqlite"]),
    help="Global storage backend (default: inmemory).",
)
def globals_export(file: Path, global_names: str, backend: str) -> None:
    """Export globals to a ZWR file."""
    from m2py.runtime.zwr import export_zwr

    names = [n.strip() for n in global_names.split(",") if n.strip()]
    if not names:
        click.echo("Error: no global names specified.", err=True)
        sys.exit(1)

    storage = _get_backend(backend)
    try:
        count = export_zwr(storage, names, file)
    except ValueError as e:
        click.echo(f"Error exporting ZWR: {e}", err=True)
        sys.exit(1)

    click.echo(f"Exported {count} nodes to {file}", err=True)
