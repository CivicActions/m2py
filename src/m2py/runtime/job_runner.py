"""Entry point for JOB'd subprocess execution.

When MUMPSRuntime.start_job() creates a subprocess via subprocess.Popen,
the child process runs this module as its entry point. It:

1. Parses command-line arguments (routine, label, SQLite DB path, actuallist)
2. Creates a SQLiteGlobalStorage instance connected to the shared database
3. Creates a fresh MUMPSRuntime with independent local variables
4. Imports the transpiled routine module and runs the entry function
5. Ensures unlock_all() is called on exit (normal or abnormal)

Usage (invoked by MUMPSRuntime.start_job()):
    python -m m2py.runtime.job_runner --routine <name> --label <label> \\
        --db-path <sqlite_path> [--args <json_args>]
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys


def main() -> None:
    """Entry point for JOB'd child process."""
    parser = argparse.ArgumentParser(description="M2PY JOB subprocess runner")
    parser.add_argument("--routine", required=True, help="Routine module name")
    parser.add_argument("--label", required=True, help="Entry label name")
    parser.add_argument("--db-path", required=True, help="SQLite database path")
    parser.add_argument("--args", default="[]", help="JSON-encoded argument list")
    parser.add_argument("--output", default=None, help="Output file path for child I/O")
    parser.add_argument("--input", default=None, help="Input file path for child I/O")
    parser.add_argument(
        "--error", default=None, help="Error file path for child stderr"
    )
    args = parser.parse_args()

    # Parse actual list arguments
    actual_args = json.loads(args.args)

    # Create SQLite storage connected to shared database
    from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

    storage = SQLiteGlobalStorage(args.db_path)

    # Create child runtime with shared globals but independent locals
    from m2py.runtime import MUMPSRuntime

    rt = MUMPSRuntime(global_storage=storage)

    # Set child's $PRINCIPAL and $IO to indicate it's a JOB'd process
    child_device = f"/dev/null/{os.getpid()}"
    rt._principal = child_device
    # _io is a property that returns _current_device.name, so set the device name
    rt._current_device.name = child_device

    # Handle I/O redirection if specified
    # INPUT/OUTPUT/ERROR redirection for JOB'd processes
    if args.output:
        try:
            rt.open_device(args.output, ["NEWVERSION"], None)
            rt.use_device(args.output)
        except Exception:
            pass  # Silently ignore output redirection failures

    if args.input:
        try:
            rt.open_device(args.input, ["READONLY"], None)
            # INPUT sets the device for READ but doesn't USE it automatically
            # The child's principal READ will come from stdin which was redirected
            # at the Popen level. Device-level INPUT is for explicit USE.
        except Exception:
            pass

    try:
        # Import the routine module
        module = _import_routine(args.routine)
        if module is None:
            # Module not found — exit with failure code
            # (Must be outside try/except SystemExit to propagate correctly)
            storage.close()
            sys.exit(1)

        # Find the entry function
        entry_func = getattr(module, args.label, None)
        if entry_func is None or not callable(entry_func):
            storage.close()
            sys.exit(1)

        # Set routine context for $TEXT support
        rt._current_routine = args.routine
        source_lines = getattr(module, "_source_lines", None)
        if source_lines is not None:
            rt._current_source_lines = source_lines
        label_lines = getattr(module, "_label_lines", None)
        if label_lines is not None:
            rt._current_label_lines = label_lines

        # Run with goto support (handles GotoExternal for cross-routine control)
        # Pass actual_args to entry function
        # so JOB CHILD^ROUTINE(arg1,arg2) delivers values to CHILD(A,B)
        from m2py.runtime import run_with_goto_support

        run_with_goto_support(
            entry_func, rt, {}, _args=actual_args if actual_args else None
        )

    except SystemExit:
        pass  # HALT in child is normal
    except Exception:
        pass  # JOB'd routine errors shouldn't crash anything
    finally:
        # Release all locks held by this process
        rt._globals.unlock_all()
        # Close storage connection
        storage.close()


def _import_routine(routine_name: str) -> object | None:
    """Import a routine module by name.

    Tries several import strategies:
    1. Direct import by name
    2. Import with _pct_ prefix (for % routines)

    Args:
        routine_name: Module name to import

    Returns:
        Module object, or None if not found
    """
    try:
        return importlib.import_module(routine_name)
    except ImportError:
        pass

    try:
        return importlib.import_module(f"_pct_{routine_name}")
    except ImportError:
        pass

    return None


if __name__ == "__main__":
    main()
