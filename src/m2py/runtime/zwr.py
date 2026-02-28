"""ZWR (ZWRITE) format import/export for MUMPS global data.

ZWR is the standard MUMPS global interchange format used by GT.M/YDB
and InterSystems Caché/IRIS.  This module provides parsing, serialization,
and bulk import/export of ZWR data into any ``GlobalStorageBackend``.

ZWR line format::

    ^GLOBAL(sub1,"sub2",sub3)="value with ""escaped"" quotes"

Special encodings in values:
- Doubled quotes ``""`` represent a literal ``"`` character
- ``$C(n)`` or ``$CHAR(n)`` encodes non-printable characters
- String concatenation ``_`` joins quoted segments and ``$C()`` calls

Subscripts:
- Numeric subscripts are unquoted: ``^G(1,2,3)``
- String subscripts are quoted: ``^G("A","B")``
- Mixed: ``^G(1,"A",2)``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, TextIO, Union

if TYPE_CHECKING:
    from m2py.runtime.globals import GlobalStorageBackend

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Match a ZWR line: ^NAME(subscripts)="value"  or  ^NAME="value"
# NOTE: We no longer use a single regex to split subscripts from value
# because the old greedy `(.+)` pattern failed when values contained
# `)=` sequences (e.g. cross-reference SET code with indirection).
# Instead, _split_zwr_line() scans character-by-character with quote-
# state tracking to locate the correct `)=` boundary.
_ZWR_GLOBAL_RE = re.compile(r"^\^([A-Za-z%][\w]*)")

# $C(n) or $CHAR(n) — for decoding non-printable characters in values
_DOLLAR_C_RE = re.compile(r"\$C(?:HAR)?\((\d+(?:,\d+)*)\)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_zwr_line(line: str) -> tuple[str, str | None, str] | None:
    """Split a ZWR line into ``(global_name, raw_subscripts, raw_value)``.

    Unlike a simple regex, this scanner tracks quote-state so that ``)``
    and ``=`` characters *inside* quoted subscripts are not mistaken for
    the subscript/value boundary.

    Returns ``None`` if *line* is not valid ZWR format.
    """
    # --- global name ---
    m = _ZWR_GLOBAL_RE.match(line)
    if not m:
        return None
    global_name = m.group(1)
    i = m.end()
    n = len(line)

    if i >= n:
        return None  # need at least '=' after the name

    # --- optional subscripts ---
    if line[i] == "(":
        i += 1  # skip '('
        sub_start = i
        in_quote = False
        while i < n:
            ch = line[i]
            if in_quote:
                if ch == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        i += 2  # doubled-quote escape
                    else:
                        in_quote = False
                        i += 1
                else:
                    i += 1
            else:
                if ch == '"':
                    in_quote = True
                    i += 1
                elif ch == ")":
                    raw_subs = line[sub_start:i]
                    i += 1  # skip ')'
                    break
                else:
                    i += 1
        else:
            return None  # unmatched '('

        if i >= n or line[i] != "=":
            return None
        i += 1  # skip '='
        return (global_name, raw_subs, line[i:])

    elif line[i] == "=":
        i += 1  # skip '='
        if i >= n:
            return None  # empty value
        return (global_name, None, line[i:])

    return None


def _parse_subscripts(raw: str) -> list[str]:
    """Parse the subscript portion of a ZWR reference.

    Handles quoted strings (with doubled-quote escaping) and
    unquoted numeric subscripts.

    Examples::

        '1,2,3'           -> ['1', '2', '3']
        '"A","B"'         -> ['A', 'B']
        '1,"A",2'         -> ['1', 'A', '2']
        '"say ""hi""..."' -> ['say "hi"...']
    """
    subs: list[str] = []
    i = 0
    n = len(raw)

    while i < n:
        # Skip whitespace/comma
        while i < n and raw[i] in (" ", ","):
            i += 1
        if i >= n:
            break

        if raw[i] == '"':
            # Quoted subscript — scan for matching close quote
            i += 1  # skip opening quote
            parts: list[str] = []
            while i < n:
                if raw[i] == '"':
                    if i + 1 < n and raw[i + 1] == '"':
                        # Doubled quote → literal "
                        parts.append('"')
                        i += 2
                    else:
                        # End of quoted subscript
                        i += 1
                        break
                else:
                    parts.append(raw[i])
                    i += 1
            subs.append("".join(parts))
        else:
            # Unquoted subscript (numeric) — collect until comma or end
            start = i
            while i < n and raw[i] != ",":
                i += 1
            subs.append(raw[start:i].strip())

    return subs


def _decode_zwr_value(raw: str) -> str:
    """Decode a ZWR value expression.

    ZWR values use MUMPS string syntax:
    - Quoted strings: ``"hello"`` → ``hello``
    - Doubled quotes: ``""`` inside a quoted string → ``"``
    - ``$C(n)`` / ``$CHAR(n)`` → ``chr(n)``
    - ``$C(n1,n2,...)`` → ``chr(n1) + chr(n2) + ...``
    - Concatenation: ``"str"_$C(10)_"more"`` joins segments

    Args:
        raw: The raw value expression from a ZWR line (everything after ``=``).

    Returns:
        The decoded string value.
    """
    raw = raw.strip()
    result: list[str] = []
    i = 0
    n = len(raw)

    while i < n:
        # Skip whitespace
        while i < n and raw[i] == " ":
            i += 1
        if i >= n:
            break

        if raw[i] == "_":
            # Concatenation operator — skip it
            i += 1
            continue

        if raw[i] == '"':
            # Quoted string segment
            i += 1  # skip opening quote
            while i < n:
                if raw[i] == '"':
                    if i + 1 < n and raw[i + 1] == '"':
                        # Doubled quote → literal "
                        result.append('"')
                        i += 2
                    else:
                        # End of quoted segment
                        i += 1
                        break
                else:
                    result.append(raw[i])
                    i += 1
            continue

        if raw[i] == "$":
            # Check for $C() or $CHAR()
            m = _DOLLAR_C_RE.match(raw, i)
            if m:
                codes = m.group(1).split(",")
                for code in codes:
                    result.append(chr(int(code.strip())))
                i = m.end()
                continue

        # Unexpected character — include literally (best-effort)
        result.append(raw[i])
        i += 1

    return "".join(result)


def _encode_zwr_value(value: str) -> str:
    """Encode a string value for ZWR output.

    All printable ASCII characters (32–126) go into a quoted string
    with ``"`` doubled.  Non-printable characters are emitted as
    ``$C(n)`` joined by ``_``.

    Args:
        value: The string value to encode.

    Returns:
        ZWR-encoded value expression (always includes outer quotes
        for the printable portions).
    """
    if not value:
        return '""'

    segments: list[str] = []
    current_str: list[str] = []

    def _flush_str() -> None:
        if current_str:
            inner = "".join(current_str).replace('"', '""')
            segments.append(f'"{inner}"')
            current_str.clear()

    for ch in value:
        code = ord(ch)
        if 32 <= code <= 126:
            current_str.append(ch)
        else:
            _flush_str()
            segments.append(f"$C({code})")

    _flush_str()

    return "_".join(segments) if segments else '""'


def _format_subscript(sub: str) -> str:
    """Format a single subscript for ZWR output.

    Numeric subscripts (canonical MUMPS numbers) are unquoted.
    Everything else is quoted with doubled internal quotes.

    Args:
        sub: The subscript string.

    Returns:
        Formatted subscript for ZWR output.
    """
    # Check if this is a canonical MUMPS number
    # Canonical: no leading zeros (except "0" itself or ".NNN"), no trailing
    # zeros after decimal, no leading +, optional leading -
    if _is_canonical_number(sub):
        return sub
    # String subscript — quote it
    return '"' + sub.replace('"', '""') + '"'


def _is_canonical_number(s: str) -> bool:
    """Test whether *s* is a canonical MUMPS number.

    Canonical MUMPS numbers:
    - Integers: ``0``, ``1``, ``-1``, ``123``
    - Decimals: ``.5``, ``1.5``, ``-.5`` (no trailing zeros)
    - NOT canonical: ``01``, ``1.0``, ``+1``, ``1.50``
    """
    if not s:
        return False
    # Try to parse as a number and check canonical form
    try:
        if "." in s:
            f = float(s)
            # Rebuild canonical form
            if f == 0:
                canonical = "0"  # ".0" → "0" in MUMPS? No, ".0" is not canonical
            elif abs(f) < 1:
                # Values like .5 or -.5
                sign = "-" if f < 0 else ""
                # Format without leading zero
                formatted = f"{abs(f):.20f}".rstrip("0")
                if formatted.endswith("."):
                    formatted = formatted[:-1]
                # Remove leading zero
                if formatted.startswith("0"):
                    formatted = formatted[1:]
                canonical = sign + formatted
            else:
                sign = "-" if f < 0 else ""
                formatted = f"{abs(f):.20f}".rstrip("0")
                if formatted.endswith("."):
                    formatted = formatted[:-1]
                canonical = sign + formatted
            return s == canonical
        else:
            n = int(s)
            return s == str(n)
    except (ValueError, OverflowError):
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_zwr_line(line: str) -> tuple[str, list[str], str]:
    """Parse a single ZWR-format line into components.

    Args:
        line: A ZWR line like ``^GLOBAL("sub1","sub2")="value"``.

    Returns:
        Tuple of ``(global_name, subscripts, value)`` where
        ``global_name`` includes the leading caret (e.g. ``"^DD"``),
        ``subscripts`` is a list of string subscript values, and
        ``value`` is the decoded string value.

    Raises:
        ValueError: If the line is not valid ZWR format.
    """
    line = line.strip()
    parts = _split_zwr_line(line)
    if parts is None:
        raise ValueError(f"Invalid ZWR line: {line!r}")

    global_name, raw_subs, raw_value = parts
    name = "^" + global_name
    subscripts = _parse_subscripts(raw_subs) if raw_subs else []
    value = _decode_zwr_value(raw_value)

    return (name, subscripts, value)


def parse_zwr_stream(stream: TextIO) -> Iterator[tuple[str, list[str], str]]:
    """Iterate parsed ZWR entries from a file or stream.

    Skips blank lines, comment lines (starting with ``;``), and ZWR
    header lines (typically the first two lines of a GT.M/YDB export).

    Args:
        stream: File-like text object with ZWR-format lines.

    Yields:
        Tuples of ``(global_name, subscripts, value)`` for each data line.

    Raises:
        ValueError: On malformed data lines (fail-fast).
    """
    seen_data = False
    for line_no, line in enumerate(stream, 1):
        line = line.rstrip("\n").rstrip("\r")
        # Skip blank lines
        if not line or line.isspace():
            continue
        # Skip comment lines
        if line.startswith(";"):
            continue
        # Non-^ lines: allowed as headers before the first data line,
        # but treated as malformed once data has started.
        if not line.startswith("^"):
            if seen_data:
                raise ValueError(f"Line {line_no}: unexpected non-data line: {line!r}")
            continue
        seen_data = True
        try:
            yield parse_zwr_line(line)
        except ValueError as e:
            raise ValueError(f"Line {line_no}: {e}") from e


def serialize_zwr_node(global_name: str, subscripts: list[str], value: str) -> str:
    """Produce a single ZWR-format line.

    Args:
        global_name: Global name with caret (e.g. ``"^DD"``).
        subscripts: List of subscript strings.
        value: The node value.

    Returns:
        ZWR-format string like ``^DD("sub")="value"``.
    """
    if subscripts:
        formatted_subs = ",".join(_format_subscript(s) for s in subscripts)
        ref = f"{global_name}({formatted_subs})"
    else:
        ref = global_name
    encoded_value = _encode_zwr_value(value)
    return f"{ref}={encoded_value}"


def import_zwr(
    backend: GlobalStorageBackend,
    source: Union[Path, TextIO],
) -> int:
    """Import ZWR data into a global storage backend.

    Args:
        backend: Any ``GlobalStorageBackend`` implementation.
        source: Path to a ZWR file, or an open text stream.

    Returns:
        Number of nodes imported.
    """
    count = 0

    if isinstance(source, Path):
        with open(source, errors="replace") as f:
            for name, subs, value in parse_zwr_stream(f):
                # Backend expects name without caret
                bare_name = name[1:] if name.startswith("^") else name
                backend.set(bare_name, tuple(subs), value)
                count += 1
    else:
        for name, subs, value in parse_zwr_stream(source):
            bare_name = name[1:] if name.startswith("^") else name
            backend.set(bare_name, tuple(subs), value)
            count += 1

    return count


def export_zwr(
    backend: GlobalStorageBackend,
    global_names: list[str],
    dest: Union[Path, TextIO],
) -> int:
    """Export globals from a backend to ZWR format.

    Args:
        backend: Source ``GlobalStorageBackend``.
        global_names: List of global names to export (with or without
            leading ``^``, e.g. ``["^DD", "^DIC"]`` or ``["DD", "DIC"]``).
        dest: Path to write ZWR output, or an open text stream.

    Returns:
        Number of nodes exported.
    """
    count = 0

    def _write_stream(stream: TextIO) -> int:
        nonlocal count
        for raw_name in global_names:
            bare_name = raw_name.lstrip("^")
            display_name = f"^{bare_name}"
            # Traverse all nodes using $QUERY equivalent
            _export_tree(backend, bare_name, display_name, stream)
        return count

    def _export_tree(
        backend: GlobalStorageBackend,
        bare_name: str,
        display_name: str,
        stream: TextIO,
    ) -> None:
        """Walk an entire global tree via $QUERY and write ZWR lines."""
        nonlocal count
        # Start by checking if the root node has a value
        root_val = backend.get(bare_name, (), update_naked=False)
        if root_val is not None:
            line = serialize_zwr_node(display_name, [], root_val)
            stream.write(line + "\n")
            count += 1

        # Use $QUERY to traverse all subscripted nodes in order
        ref = backend.query(bare_name, ("",))
        while ref:
            # Parse the reference string: ^NAME(sub1,sub2,...)
            subs, val = _parse_query_ref(backend, bare_name, ref)
            if val is not None:
                line = serialize_zwr_node(display_name, subs, val)
                stream.write(line + "\n")
                count += 1
            # Get next node
            ref = backend.query(bare_name, tuple(subs))

    if isinstance(dest, Path):
        with open(dest, "w") as f:
            _write_stream(f)
    else:
        _write_stream(dest)

    return count


def _parse_query_ref(
    backend: GlobalStorageBackend,
    bare_name: str,
    ref: str,
) -> tuple[list[str], str | None]:
    """Parse a $QUERY reference and retrieve the value.

    Args:
        backend: The storage backend.
        bare_name: Global name without caret.
        ref: A full reference like ``^DD(2,"NAME")``.

    Returns:
        Tuple of (subscripts, value).
    """
    # ref is like ^DD(2,"NAME") — strip the ^NAME( prefix and trailing )
    prefix = f"^{bare_name}("
    if not ref.startswith(prefix) or not ref.endswith(")"):
        return [], None
    inner = ref[len(prefix) : -1]
    subs = _parse_subscripts(inner)
    value = backend.get(bare_name, tuple(subs), update_naked=False)
    return subs, value
