"""Support for native Python overrides of transpiled MUMPS routines.

Override files are plain Python modules that follow the same protocol as
transpiled code (``_routine_name``, ``_label_lines``, ``_line_map``,
``_source_lines``, ``_entry_function``, and label functions with
``(_rt, *args, _scope=None)`` signatures).

For partial overrides — where only some entry points are replaced — use
:func:`partial_override` to load the transpiled base and delegate
non-overridden labels automatically via module-level ``__getattr__``.
"""

from __future__ import annotations

import logging
import sys
import types
from pathlib import Path

logger = logging.getLogger(__name__)


def partial_override(routine_name: str) -> types.ModuleType:
    """Load the transpiled version of a routine for use as a partial-override base.

    Call this from an override module to get the transpiled fallback.
    Non-overridden labels are delegated to this base via ``__getattr__``.

    The transpiled module is registered under a private name so it doesn't
    shadow the override in ``sys.modules``.

    Args:
        routine_name: MUMPS routine name (e.g. ``"DIC"``).

    Returns:
        The transpiled module object.

    Raises:
        ImportError: If the routine cannot be transpiled.
    """
    # The override is already registered as the primary module.
    # We need to force-transpile the .m source under a private name.
    private_name = f"_m2py_base_{routine_name}"
    if private_name in sys.modules:
        return sys.modules[private_name]

    # Find the auto-importer on sys.meta_path — look for any finder that
    # has a get_source_path() method (duck-typing avoids importing test code).
    importer = None
    for finder in sys.meta_path:
        if hasattr(finder, "get_source_path"):
            importer = finder
            break

    if importer is None:
        raise ImportError(
            f"No MUMPS auto-importer installed — cannot load base for {routine_name}"
        )

    m_file = importer.get_source_path(routine_name)  # type: ignore[attr-defined]
    if m_file is None:
        raise ImportError(f"No .m source found for {routine_name}")

    # Import _load_routine lazily — it lives in the test adapter but is the
    # canonical way to transpile+register a routine.  Use the same import
    # path the auto-importer's exec_module uses.
    from tests.functional.munit.lib.adapter import _load_routine

    _, module = _load_routine(m_file, routine_name)

    # Re-register under the private name so future calls are instant
    sys.modules[private_name] = module
    # Restore the override as the primary module
    # (since _load_routine registers under routine_name too)
    override_mod = sys.modules.get(f"_m2py_override_{routine_name}")
    if override_mod is not None:
        sys.modules[routine_name] = override_mod

    return module


def _mumps_name_to_python_module(routine_name: str) -> str:
    """Convert a MUMPS routine name to its Python module name.

    MUMPS ``%``-prefixed routines become ``_pct_``-prefixed Python modules.
    """
    if routine_name.startswith("%"):
        return "_pct_" + routine_name[1:]
    return routine_name


def load_override(py_path: Path, routine_name: str) -> types.ModuleType:
    """Load a ``.py`` override file as a module.

    Compiles and executes the override file, registering it in
    ``sys.modules`` under both the routine name and the Python module
    name (handling ``%``-prefix translation).

    Args:
        py_path: Path to the ``.py`` override file.
        routine_name: MUMPS routine name this overrides.

    Returns:
        The loaded override module.
    """
    py_module_name = _mumps_name_to_python_module(routine_name)

    module = types.ModuleType(py_module_name)
    module.__file__ = str(py_path)

    # Register early so the override can be found during partial_override()
    sys.modules[f"_m2py_override_{routine_name}"] = module
    sys.modules[py_module_name] = module
    sys.modules[routine_name] = module

    code = py_path.read_text()
    exec(compile(code, str(py_path), "exec"), module.__dict__)  # noqa: S102

    logger.info("Loaded override %s from %s", routine_name, py_path.name)
    return module
