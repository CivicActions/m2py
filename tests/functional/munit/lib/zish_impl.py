"""Python implementation of %ZISH (GT.M/Unix Host File Control).

Provides the entry points used by the M XML Parser test suite:

- ``$$DEFDIR`` — default directory (with trailing ``/``)
- ``$$GTF``    — global to file (write global data to host file)
- ``$$FTG``    — file to global (read host file into global)
- ``$$DEL``    — delete host file(s)
- ``OPEN``     — open a host file (used internally by GTF/FTG)
- ``CLOSE``    — close a host file

Why a Python implementation instead of transpiling ZISHGUX.m?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ZISHGUX.m transpiles successfully, but the FTG→READNXT internal DO
call uses the ``; ZEXCEPT: %ZA`` pattern to share ``%ZA`` between
FTG's scope and READNXT's scope.  In the current trampoline-mode
codegen, internal DO calls get their own RoutineState, so ZEXCEPT
variables are not shared back to the caller — ``%ZA`` stays local
to READNXT and FTG raises ``KeyError: '_pct_ZA'``.

Once the codegen adds scope-sync for internal DO calls in trampoline
routines, this file can be replaced by the transpiled ZISHGUX.m.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from m2py.runtime import MArray, MUMPSRuntime
from m2py.codegen.helpers import m_str, m_num
from m2py.runtime.helpers import m_qlength, m_qsubscript


# ---------------------------------------------------------------------------
# Module metadata (matches transpiled module format)
# ---------------------------------------------------------------------------

_routine_name = "%ZISH"
_label_lines = {
    "%ZISH": 0,
    "OPEN": 8,
    "CLOSE": 55,
    "DEL": 61,
    "DEFDIR": 173,
    "FTG": 254,
    "GTF": 294,
    "READNXT": 285,
    "MGTF": 314,
    "EOF": 238,
    "MAKEREF": 241,
}
_source_lines = ["%ZISH ;ISF/AC,RWF,VEN/SMH - Python implementation"]
_line_map: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _val(x: Any) -> str:
    """Extract string value from an MArray or scalar."""
    if isinstance(x, MArray):
        return m_str(x.value) if x.value is not None else ""
    return m_str(x) if x is not None else ""


def _get_default_dir(rt: MUMPSRuntime, _scope: dict) -> str:
    """Resolve default directory, mimicking DEFDIR logic."""
    # Try ^XTV(8989.3,1,"DEV") first field
    try:
        raw = rt._globals.get("^XTV", ("8989.3", "1", "DEV"))
        if raw:
            dev = m_str(raw).split("^")[0]
            if dev:
                if not dev.endswith("/"):
                    dev += "/"
                return dev
    except Exception:
        pass

    # Fallback to cwd
    cwd = os.getcwd()
    if not cwd.endswith("/"):
        cwd += "/"
    return cwd


def _parse_name_ref(name_ref: str) -> Tuple[str, List[str]]:
    """Parse a $NAME reference like '^TMP(12345,1)' into ('TMP', ['12345','1']).

    Note: the caret is stripped because the runtime globals API uses bare names
    (e.g. 'TMP' not '^TMP').
    """
    ql = int(m_num(m_qlength(name_ref)))
    subs = []
    for i in range(1, ql + 1):
        subs.append(m_str(m_qsubscript(name_ref, i)))
    # Extract base name: everything before the first '('
    paren = name_ref.find("(")
    base = name_ref[:paren] if paren >= 0 else name_ref
    # Strip leading caret — runtime globals API uses bare names
    if base.startswith("^"):
        base = base[1:]
    return base, subs


def _open_host_file(
    rt: MUMPSRuntime,
    directory: str,
    filename: str,
    mode: str,
) -> Tuple[bool, str]:
    """Open a host file.  Returns (success, filepath)."""
    filepath = directory + filename

    mode = (mode or "R").upper()
    if "A" in mode:
        params = ["append", "nowrap", "stream"]
    elif "W" in mode:
        params = ["newversion", "nowrap", "stream"]
    else:
        params = ["readonly"]

    try:
        ok = rt.open_device(filepath, params, 0)
        return (bool(ok), filepath)
    except Exception:
        return (False, filepath)


def _close_host_file(rt: MUMPSRuntime, filepath: str) -> None:
    """Close a host file device."""
    try:
        rt.close_device(filepath)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def DEFDIR(rt: MUMPSRuntime, DF=None, _scope: Optional[Dict[str, Any]] = None) -> str:
    """``$$DEFDIR^%ZISH(DF)`` — Return default directory with trailing ``/``."""
    _scope = _scope if _scope is not None else {}
    df = _val(DF)
    if not df:
        df = _get_default_dir(rt, _scope)
    if not df.endswith("/"):
        df += "/"
    return df


def GTF(
    rt: MUMPSRuntime,
    _pct_ZX1=None,
    _pct_ZX2=None,
    _pct_ZX3=None,
    _pct_ZX4=None,
    _scope: Optional[Dict[str, Any]] = None,
) -> int:
    """``$$GTF^%ZISH(globalref, subscript, directory, filename)`` — Global to file.

    Writes global data to a host file, one line per node.

    Args:
        _pct_ZX1: $NAME of global reference (e.g. "^TMP(12345,1)")
        _pct_ZX2: incrementing subscript position
        _pct_ZX3: host file directory
        _pct_ZX4: host file name

    Returns:
        1 on success, 0 on failure.
    """
    _scope = _scope if _scope is not None else {}

    glo_name = _val(_pct_ZX1)
    sub_pos = int(m_num(_val(_pct_ZX2)))
    directory = _val(_pct_ZX3)
    filename = _val(_pct_ZX4)

    if not directory:
        directory = _get_default_dir(rt, _scope)

    # Open file for writing
    ok, filepath = _open_host_file(rt, directory, filename, "W")
    if not ok:
        return 0

    try:
        rt.use_device(filepath, None)

        # Parse global reference: "^TMP(12345,1)" with sub_pos=2
        # means iterate ^TMP(12345,1,sub) for sub in $ORDER
        base, base_subs = _parse_name_ref(glo_name)

        # Build the parent subscripts up to sub_pos-1
        parent_subs = tuple(base_subs[: sub_pos - 1])

        # Iterate using $ORDER at the incrementing subscript level
        sub = ""
        while True:
            all_subs = parent_subs + (sub,)
            sub = m_str(rt._globals.order(base, all_subs))
            if not sub:
                break

            node_subs = parent_subs + (sub,)

            # Only write if node has a value ($DATA = 1 or 11)
            d = rt._globals.data(base, node_subs)
            if d in (1, 11):
                val = rt._globals.get(base, node_subs)
                if val is not None:
                    rt.write(m_str(val))
                    rt.write_newline()

        _close_host_file(rt, filepath)
        return 1
    except Exception:
        _close_host_file(rt, filepath)
        return 0


def FTG(
    rt: MUMPSRuntime,
    _pct_ZX1=None,
    _pct_ZX2=None,
    _pct_ZX3=None,
    _pct_ZX4=None,
    _pct_ZX5=None,
    _scope: Optional[Dict[str, Any]] = None,
) -> int:
    """``$$FTG^%ZISH(directory, filename, globalref, subscript)`` — File to global.

    Reads host file lines into a global array.

    Args:
        _pct_ZX1: host file directory
        _pct_ZX2: host file name
        _pct_ZX3: $NAME reference including starting subscript
        _pct_ZX4: increment subscript position

    Returns:
        1 on success, 0 on failure.
    """
    _scope = _scope if _scope is not None else {}

    directory = _val(_pct_ZX1)
    filename = _val(_pct_ZX2)
    glo_ref = _val(_pct_ZX3)
    inc_sub = int(m_num(_val(_pct_ZX4)))

    if not directory:
        directory = _get_default_dir(rt, _scope)

    # Open file for reading
    ok, filepath = _open_host_file(rt, directory, filename, "R")
    if not ok:
        return 0

    try:
        rt.use_device(filepath, None)

        # Parse global reference: e.g. "^TMP(12345,2,1)"
        base, base_subs = _parse_name_ref(glo_ref)

        # Build parent subs from base_subs up to inc_sub-1
        parent_subs = list(base_subs[: inc_sub - 1])

        # Starting value for the incrementing subscript
        if len(base_subs) >= inc_sub:
            line_num = int(m_num(base_subs[inc_sub - 1]))
        else:
            line_num = 1

        # Read lines from file into global
        while True:
            try:
                val, _term = rt.read_line_timeout(0)
                eof = rt.zeof()
            except Exception:
                break

            if eof:
                break

            # Set ^base(parent_subs, line_num)
            node_subs = tuple(parent_subs) + (str(line_num),)
            rt._globals.set(base, node_subs, val)
            line_num += 1

        _close_host_file(rt, filepath)
        return 1
    except Exception:
        _close_host_file(rt, filepath)
        return 0


def DEL(
    rt: MUMPSRuntime,
    _pct_ZX1=None,
    _pct_ZX2=None,
    _scope: Optional[Dict[str, Any]] = None,
) -> int:
    """``$$DEL^%ZISH(directory, array)`` — Delete file(s).

    Args:
        _pct_ZX1: directory path
        _pct_ZX2: $NAME of array containing filenames as subscripts

    Returns:
        1 on success, 0 on failure.
    """
    _scope = _scope if _scope is not None else {}

    directory = _val(_pct_ZX1)
    array_ref = _val(_pct_ZX2)

    if not directory:
        directory = _get_default_dir(rt, _scope)

    # Resolve the array — it may be a local or global
    base, subs = _parse_name_ref(array_ref)
    success = True

    if base.startswith("^"):
        # Global array — shouldn't reach here (_parse_name_ref strips caret)
        pass
    else:
        # Local array
        from m2py.core.names import NameTranslator

        py_name = NameTranslator.to_python(base)
        arr = _scope.get(py_name)
        if isinstance(arr, MArray):
            # Navigate to subscript level
            target = arr
            for s in subs:
                child = target.get(s)
                if isinstance(child, MArray):
                    target = child
                else:
                    target = None
                    break

            if target is not None and isinstance(target, MArray):
                for sub in list(target._children.keys()):
                    filepath = directory + sub
                    try:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                    except OSError:
                        success = False

    return 1 if success else 0


def OPEN(
    rt: MUMPSRuntime,
    X1=None,
    X2=None,
    X3=None,
    X4=None,
    X5=None,
    X6=None,
    _scope: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """``OPEN^%ZISH`` — Open a host file."""
    _scope = _scope if _scope is not None else {}

    # Handle 3-parameter RPMS form
    if X4 is None:
        X4, X3, X2 = X3, X2, X1
        X1 = None

    directory = _val(X2)
    filename = _val(X3)
    mode = _val(X4) or "R"

    if not directory:
        directory = _get_default_dir(rt, _scope)

    ok, filepath = _open_host_file(rt, directory, filename, mode)
    if ok:
        _scope.setdefault("IO", MArray()).value = filepath
        _scope.setdefault("POP", MArray()).value = 0
    else:
        _scope.setdefault("POP", MArray()).value = 1

    if rt._in_extrinsic:
        return 1 if not ok else 0


def CLOSE(
    rt: MUMPSRuntime,
    X=None,
    _scope: Optional[Dict[str, Any]] = None,
) -> None:
    """``CLOSE^%ZISH`` — Close current HFS device."""
    _scope = _scope if _scope is not None else {}
    io = _scope.get("IO")
    if isinstance(io, MArray) and io.value:
        _close_host_file(rt, m_str(io.value))


def EOF(rt: MUMPSRuntime, X=None, _scope=None) -> str:
    """``$$EOF^%ZISH(X)`` — Return EOF flag (pass-through)."""
    return _val(X)
