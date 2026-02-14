"""Shared fixtures for runtime unit tests."""

import sys
import textwrap

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.sqlite_storage import SQLiteGlobalStorage


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary SQLite database path."""
    return str(tmp_path / "test_globals.db")


@pytest.fixture
def sqlite_storage(db_path):
    """Create a SQLiteGlobalStorage instance and clean up after test."""
    storage = SQLiteGlobalStorage(db_path)
    yield storage
    storage.close()


@pytest.fixture
def sqlite_rt(sqlite_storage):
    """Create a MUMPSRuntime backed by SQLiteGlobalStorage."""
    return MUMPSRuntime(global_storage=sqlite_storage)


@pytest.fixture
def job_routine_dir(tmp_path):
    """Create a temporary directory for JOB routine .py files.

    Inserts the directory into sys.path so that subprocess and parent
    can both import routines from it. Cleans up sys.path on teardown.

    Usage:
        def test_job(sqlite_rt, sqlite_storage, job_routine_dir):
            routine_file = job_routine_dir / "MYROUTINE.py"
            routine_file.write_text('''...''')
            sqlite_rt.start_job("entry", "MYROUTINE", [], None, None)
    """
    routine_dir = tmp_path / "routines"
    routine_dir.mkdir()
    sys.path.insert(0, str(routine_dir))
    yield routine_dir
    sys.path.remove(str(routine_dir))


def write_job_routine(
    routine_dir, routine_name, entry_body, *, label="entry", params="(_rt, _scope=None)"
):
    """Write a .py routine file to disk for JOB subprocess testing.

    Args:
        routine_dir: Path to the routines directory (from job_routine_dir fixture)
        routine_name: Module name (e.g., "JOBTST")
        entry_body: Python code for the entry function body (will be dedented)
        label: Function/label name (default "entry")
        params: Parameter signature (default "(_rt, _scope=None)")

    Returns:
        Path to the written .py file
    """
    body = textwrap.dedent(entry_body).strip()
    # Indent the body for the function (4 spaces)
    indented_body = "\n".join(
        f"    {line}" if line.strip() else "" for line in body.splitlines()
    )

    code = (
        f'_routine_name = "{routine_name}"\n'
        f"_source_lines = []\n"
        f"_label_lines = {{}}\n"
        f"\n"
        f"def {label}{params}:\n"
        f"{indented_body}\n"
    )

    routine_file = routine_dir / f"{routine_name}.py"
    routine_file.write_text(code)
    return routine_file


def wait_for_global(storage, name, subs=(), timeout=5.0):
    """Poll SQLiteGlobalStorage until a global value appears.

    Args:
        storage: SQLiteGlobalStorage instance
        name: Global variable name
        subs: Subscript tuple
        timeout: Maximum wait time in seconds

    Returns:
        The global value once it appears

    Raises:
        TimeoutError: If the value doesn't appear within timeout
    """
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        val = storage.get(name, subs)
        if val is not None:
            return val
        time.sleep(0.05)
    raise TimeoutError(f"Global ^{name}{subs} not set within {timeout}s")
