"""Stub implementation of GT.M/YDB %RSEL utility.

%RSEL selects M routines matching a pattern and stores them in the %ZR
local variable. In m2py, there are no on-disk M routines to discover,
so this stub KILLs %ZR (leaving it undefined) and returns — matching
the behavior of a YDB system where no routines match the search pattern.

Entry points:
    SILENT^%RSEL(pattern, label) — non-interactive routine selection
    %RSEL — interactive (prompts user) — stub does nothing

Output variables:
    %ZR — local array of matched routines (empty after stub execution)

Reference: YDB Programmer's Guide, %RSEL utility
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m2py.runtime import MUMPSRuntime

_routine_name = "%RSEL"
_source_lines: list[str] = []
_label_lines: dict[str, int] = {"RSEL": 0, "SILENT": 1}


def SILENT(_rt: "MUMPSRuntime", *args, _scope=None, _start_offset=0) -> None:
    """Non-interactive routine selection.

    SILENT^%RSEL(pattern, label) searches for routines matching pattern.
    In m2py there are no on-disk M routines, so %ZR is KILLed (empty).

    Args:
        _rt: Runtime instance
        *args: (pattern, label) — pattern is a routine name/wildcard,
               label is "SRC", "OBJ", or "CALL"
        _scope: Variable scope dictionary
        _start_offset: Line offset for GOTO support
    """
    if _scope is None:
        _scope = {}
    # KILL %ZR — ensure it's undefined (no routines found)

    _scope.pop("_pct_ZR", None)


def _pct_RSEL(_rt: "MUMPSRuntime", *args, _scope=None, _start_offset=0) -> None:
    """Interactive %RSEL entry point (stub — does nothing).

    In interactive mode, %RSEL prompts for routine patterns.
    In m2py this is a no-op since there are no on-disk routines.
    """
    if _scope is None:
        _scope = {}
    _scope.pop("_pct_ZR", None)


# Module-level _entry_function for D ^%RSEL calls
_entry_function = _pct_RSEL
