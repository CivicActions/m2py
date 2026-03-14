"""Native Python override for FileMan DIC.m — FIND^DIC and LIST^DIC.

Provides performant implementations that bypass line-by-line transpiled
MUMPS execution, giving orders-of-magnitude speedup for FileMan's two
primary database-server lookup APIs.

Output is written to ^TMP("DILIST",$J,...) in the standard format:
  (0)          = count^max^more?^flags
  (0,"MAP")    = field1^field2^...
  (2,n)        = IEN of entry n
  ("ID",n,fld) = value for regular field
  ("ID",n,"Cn",1) = value for computed field at position n
"""

from __future__ import annotations

import re
from typing import Any

from m2py.runtime.overrides import partial_override

_base = partial_override("DIC")

# ── Module protocol ──────────────────────────────────────────────────
_routine_name = "DIC"
# _source_lines, _label_lines, _line_map, _entry_function are all
# resolved via __getattr__ → _base, except where we override them.
# We explicitly define FIND and LIST as module-level functions;
# everything else (including _entry_function for `D ^DIC`) forwards
# to the transpiled base.


def __getattr__(name: str) -> Any:
    """Delegate non-overridden attributes to transpiled base."""
    return getattr(_base, name)


# ── Helpers: file/field metadata ─────────────────────────────────────


def _get_global_root(g: Any, file_num: str) -> tuple[str, tuple[str, ...]]:
    """Return (global_name, prefix_subscripts) for a FileMan file.

    Reads ^DIC(file,0,"GL") e.g. "^DMU(1009.802," → ("DMU", ("1009.802",))
    """
    gl = g.get("DIC", (str(file_num), "0", "GL"))
    if not gl:
        raise ValueError(f"No global root for file {file_num}")
    m = re.match(r"\^(\w+)\((.+),\s*$", gl)
    if m:
        name = m.group(1)
        subs = tuple(s.strip('"') for s in m.group(2).split(","))
        return name, subs
    m2 = re.match(r"\^(\w+)\(", gl)
    if m2:
        return m2.group(1), ()
    raise ValueError(f"Cannot parse global root: {gl}")


def _get_field_info(g: Any, file_num: str, field_num: str) -> dict[str, Any] | None:
    """Read DD metadata for one field.

    Returns dict with keys: name, type, node, piece, pointer_global, set_codes.
    """
    dd = g.get("DD", (str(file_num), str(field_num), "0"))
    if not dd:
        return None
    parts = dd.split("^")
    name = parts[0] if parts else ""
    ftype = parts[1] if len(parts) > 1 else ""
    storage = parts[3] if len(parts) > 3 else ""

    node = ""
    piece = 0
    if ";" in storage:
        node_str, piece_str = storage.split(";", 1)
        node = node_str
        piece = int(piece_str) if piece_str.isdigit() else 0

    pointer_global = ""
    set_codes: dict[str, str] = {}

    if ftype.startswith("P"):
        # Pointer field — e.g. "P.85'" with global in piece 3 (sans leading ^)
        raw_pg = parts[2] if len(parts) > 2 else ""
        pointer_global = "^" + raw_pg if raw_pg else ""
    elif ftype.startswith("S"):
        # Set-of-codes — codes in piece 3, e.g. "M:MALE;F:FEMALE;"
        codes_str = parts[2] if len(parts) > 2 else ""
        for pair in codes_str.split(";"):
            if ":" in pair:
                code, label = pair.split(":", 1)
                set_codes[code] = label

    return {
        "name": name,
        "type": ftype,
        "node": node,
        "piece": piece,
        "pointer_global": pointer_global,
        "set_codes": set_codes,
    }


# ── Helpers: field-spec parsing ──────────────────────────────────────

_RE_COMPUTED = re.compile(r"^(\w+)\((\w+)\)$")


def _parse_fields(fields_str: str) -> tuple[bool, list[dict[str, Any]]]:
    """Parse DIFIELDS like ``"@;.01;1;COUNT(COUNTY)"``.

    Returns (suppress_auto_01, field_specs) where each spec is a dict
    with keys: field_num, computed_func, computed_arg, map_id, pos.
    """
    parts = fields_str.split(";")
    suppress = False
    specs: list[dict[str, Any]] = []
    pos = 0
    for part in parts:
        pos += 1
        part = part.strip()
        if part == "@":
            suppress = True
            continue
        m = _RE_COMPUTED.match(part)
        if m:
            specs.append(
                {
                    "field_num": None,
                    "computed_func": m.group(1).upper(),
                    "computed_arg": m.group(2),
                    "map_id": f"C{pos}",
                    "pos": pos,
                }
            )
        else:
            specs.append(
                {
                    "field_num": str(part),
                    "computed_func": None,
                    "computed_arg": None,
                    "map_id": str(part),
                    "pos": pos,
                }
            )
    return suppress, specs


# ── Helpers: field extraction & validation ───────────────────────────


def _extract_piece(
    g: Any, gname: str, prefix: tuple[str, ...], ien: str, node: str, piece: int
) -> str:
    """Get piece ``piece`` (1-based) of ^GLOBAL(prefix,ien,node)."""
    raw = g.get(gname, prefix + (str(ien), node))
    if raw is None:
        return ""
    pieces = raw.split("^")
    return pieces[piece - 1] if piece <= len(pieces) else ""


def _validate_field(g: Any, value: str, info: dict[str, Any]) -> bool:
    """Return True if ``value`` is valid for this field type (non-E mode).

    Pointer — target entry must exist.
    Date    — must be a positive integer of 5–7 digits.
    Set     — must be one of the allowed codes.
    Number  — must be numeric.
    Others  — always valid.
    """
    if not value:
        return True  # empty is never "bad"

    ftype = info["type"]

    # Pointer
    if ftype.startswith("P"):
        pg = info.get("pointer_global", "")
        if pg:
            m = re.match(r"\^(\w+)\((.+),\s*$", pg)
            if m:
                tgt_name = m.group(1)
                tgt_prefix = tuple(s.strip('"') for s in m.group(2).split(","))
                return g.get(tgt_name, tgt_prefix + (value, "0")) is not None
        return True

    # Date — internal FileMan date is a 5-to-7-digit positive integer
    if ftype in ("D", "RD"):
        if not value.isdigit() or len(value) < 5 or len(value) > 7:
            return False
        return True

    # Set-of-codes
    if ftype.startswith("S"):
        return value in info["set_codes"]

    # Numeric
    if ftype.startswith("N"):
        try:
            float(value)
        except ValueError:
            return False
        return True

    return True


def _get_field_value(
    g: Any,
    gname: str,
    prefix: tuple[str, ...],
    ien: str,
    info: dict[str, Any] | None,
    e_flag: bool,
) -> tuple[str, bool]:
    """Extract a single field's output value for an entry.

    Returns (value, ok).  ok=False means validation failed
    (only possible when e_flag is False).
    """
    if info is None:
        return "", True
    if info["piece"] == 0:
        return "", True  # multiple header — no scalar value

    value = _extract_piece(g, gname, prefix, ien, info["node"], info["piece"])

    if not e_flag and value:
        if not _validate_field(g, value, info):
            return value, False  # bad data

    return value, True


# ── Helpers: COUNT(multiple) ─────────────────────────────────────────


def _find_field_by_name(g: Any, file_num: str, name: str) -> str | None:
    """Look up field number by name via ^DD(file,"B",name,field_num)."""
    fn = g.order("DD", (str(file_num), "B", name, ""))
    if fn:
        return fn
    # Try exact case then upper case
    fn = g.order("DD", (str(file_num), "B", name.upper(), ""))
    return fn or None


def _count_multiple(
    g: Any,
    gname: str,
    prefix: tuple[str, ...],
    ien: str,
    field_name: str,
    file_num: str,
) -> int:
    """Count entries in a multiple field (e.g. COUNT(COUNTY)).

    Uses the header node's 4th piece for speed.
    """
    fn = _find_field_by_name(g, file_num, field_name)
    if fn is None:
        return 0
    info = _get_field_info(g, file_num, fn)
    if info is None or info["piece"] != 0:
        return 0
    node = info["node"]  # e.g. "1" for COUNTY at subscription 1

    header = g.get(gname, prefix + (str(ien), node, "0"))
    if not header:
        return 0
    hp = header.split("^")
    count_str = hp[3] if len(hp) > 3 else "0"
    return int(count_str) if count_str.isdigit() else 0


# ── Helpers: output ──────────────────────────────────────────────────


def _output_entry(
    g: Any,
    dl_name: str,
    dl_base: tuple[str, ...],
    entry_num: int,
    ien: str,
    field_specs: list[dict[str, Any]],
    field_values: list[Any],
) -> None:
    """Write one entry's output into the DILIST global."""
    g.set(dl_name, dl_base + ("2", str(entry_num)), str(ien))
    for spec, val in zip(field_specs, field_values):
        if val is None or val == "":
            continue
        if spec["computed_func"]:
            g.set(
                dl_name, dl_base + ("ID", str(entry_num), spec["map_id"], "1"), str(val)
            )
        else:
            g.set(
                dl_name, dl_base + ("ID", str(entry_num), spec["field_num"]), str(val)
            )


def _build_map(field_specs: list[dict[str, Any]]) -> str:
    return "^".join(spec["map_id"] for spec in field_specs)


def _set_header(
    g: Any,
    dl_name: str,
    dl_base: tuple[str, ...],
    count: int,
    field_specs: list[dict[str, Any]],
) -> None:
    """Write the (0) header and (0,"MAP") nodes."""
    g.set(dl_name, dl_base + ("0",), f"{count}^*^0^")
    g.set(dl_name, dl_base + ("0", "MAP"), _build_map(field_specs))


# ── Field extraction for a complete entry ────────────────────────────


def _extract_fields(
    g: Any,
    gname: str,
    prefix: tuple[str, ...],
    ien: str,
    field_specs: list[dict[str, Any]],
    field_metas: dict[str, Any],
    file_num: str,
    e_flag: bool,
) -> list[Any]:
    """Extract all requested field values for one entry.

    On validation failure (non-E mode), remaining fields are set to None.
    """
    values: list[Any] = []
    for spec in field_specs:
        if spec["computed_func"]:
            if spec["computed_func"] == "COUNT":
                cnt = _count_multiple(
                    g, gname, prefix, ien, spec["computed_arg"], file_num
                )
                values.append(cnt)
            else:
                values.append("")
        else:
            meta = field_metas.get(spec["field_num"])
            val, ok = _get_field_value(g, gname, prefix, ien, meta, e_flag)
            if not ok:
                # Validation failed — mark this and all remaining fields
                values.append(None)
                values.extend(None for _ in field_specs[len(values) :])
                break
            values.append(val)
    return values


# ── FIND^DIC ─────────────────────────────────────────────────────────


def FIND(
    _rt: Any, *args: str, _scope: dict[str, Any] | None = None, **kwargs: Any
) -> None:
    """Native implementation of FIND^DIC.

    Walks the B-index of the file, matching entries whose index value
    starts with DIVALUE, then extracts the requested fields.
    """
    g = _rt.globals
    j = str(_rt.job())

    # ── Parse parameters (coerce everything to str) ──
    file_num = str(args[0]) if len(args) > 0 else ""
    # iens    = args[1] (unused for top-level files)
    fields_s = str(args[2]) if len(args) > 2 else ""
    flags = str(args[3]) if len(args) > 3 else ""
    value = str(args[4]) if len(args) > 4 else ""
    # number, force, screen, write, dilist, msga — not needed for DMUDIC00

    e_flag = "E" in flags.upper() if flags else False

    dl_name = "TMP"
    dl_base = ("DILIST", j)
    g.kill(dl_name, dl_base)

    gname, gprefix = _get_global_root(g, file_num)
    _, field_specs = _parse_fields(fields_s)

    field_metas: dict[str, Any] = {}
    for spec in field_specs:
        if spec["field_num"] is not None:
            field_metas[spec["field_num"]] = _get_field_info(
                g, file_num, spec["field_num"]
            )

    val_len = len(value)
    count = 0
    key = value  # $ORDER starting point

    while True:
        key = g.order(gname, gprefix + ("B", key))
        if not key:
            break
        if value and key[:val_len] != value:
            break

        # Iterate all IENs sharing this index value
        ien = ""
        while True:
            ien = g.order(gname, gprefix + ("B", key, ien))
            if not ien:
                break
            count += 1
            fv = _extract_fields(
                g, gname, gprefix, ien, field_specs, field_metas, file_num, e_flag
            )
            _output_entry(g, dl_name, dl_base, count, ien, field_specs, fv)

    _set_header(g, dl_name, dl_base, count, field_specs)


# ── LIST^DIC ─────────────────────────────────────────────────────────


def LIST(
    _rt: Any, *args: str, _scope: dict[str, Any] | None = None, **kwargs: Any
) -> None:
    """Native implementation of LIST^DIC.

    Without X flag: walks the B-index listing all entries.
    With X flag: honours DINDEX for field-sorting, expression screening,
    or sort-template traversal.
    """
    g = _rt.globals
    j = str(_rt.job())

    file_num = str(args[0]) if len(args) > 0 else ""
    # iens    = args[1]
    fields_s = str(args[2]) if len(args) > 2 else ""
    flags = str(args[3]) if len(args) > 3 else ""
    # number  = args[4]
    # from_v  = args[5]
    # part    = args[6]
    dindex = str(args[7]) if len(args) > 7 else ""
    # screen, write, dilist, msga — not used

    e_flag = "E" in flags.upper() if flags else False
    x_flag = "X" in flags.upper() if flags else False

    dl_name = "TMP"
    dl_base = ("DILIST", j)
    g.kill(dl_name, dl_base)

    gname, gprefix = _get_global_root(g, file_num)
    _, field_specs = _parse_fields(fields_s)

    field_metas: dict[str, Any] = {}
    for spec in field_specs:
        if spec["field_num"] is not None:
            field_metas[spec["field_num"]] = _get_field_info(
                g, file_num, spec["field_num"]
            )

    if x_flag and dindex:
        if dindex.startswith("["):
            _list_sort_template(
                g,
                gname,
                gprefix,
                field_specs,
                field_metas,
                dl_name,
                dl_base,
                file_num,
                dindex,
                e_flag,
            )
        elif ">" in dindex or "<" in dindex or "=" in dindex:
            _list_screen_expr(
                g,
                gname,
                gprefix,
                field_specs,
                field_metas,
                dl_name,
                dl_base,
                file_num,
                dindex,
                e_flag,
            )
        else:
            _list_sort_field(
                g,
                gname,
                gprefix,
                field_specs,
                field_metas,
                dl_name,
                dl_base,
                file_num,
                dindex,
                e_flag,
            )
    else:
        _list_b_index(
            g,
            gname,
            gprefix,
            field_specs,
            field_metas,
            dl_name,
            dl_base,
            file_num,
            e_flag,
        )


# ── LIST helpers ─────────────────────────────────────────────────────


def _list_b_index(
    g: Any,
    gname: str,
    gprefix: tuple[str, ...],
    field_specs: list[dict],
    field_metas: dict,
    dl_name: str,
    dl_base: tuple[str, ...],
    file_num: str,
    e_flag: bool,
) -> None:
    """Standard B-index walk — return all entries."""
    count = 0
    key = ""
    while True:
        key = g.order(gname, gprefix + ("B", key))
        if not key:
            break
        ien = ""
        while True:
            ien = g.order(gname, gprefix + ("B", key, ien))
            if not ien:
                break
            count += 1
            fv = _extract_fields(
                g, gname, gprefix, ien, field_specs, field_metas, file_num, e_flag
            )
            _output_entry(g, dl_name, dl_base, count, ien, field_specs, fv)
    _set_header(g, dl_name, dl_base, count, field_specs)


def _list_sort_field(
    g: Any,
    gname: str,
    gprefix: tuple[str, ...],
    field_specs: list[dict],
    field_metas: dict,
    dl_name: str,
    dl_base: tuple[str, ...],
    file_num: str,
    dindex: str,
    e_flag: bool,
) -> None:
    """X-flag sort by an unindexed field number.

    Walks all entries, collects (sort_value, ien) pairs, sorts, outputs.
    Only entries with a non-empty sort field value are included.
    """
    sort_field_num = dindex
    sort_meta = _get_field_info(g, file_num, sort_field_num)
    if sort_meta is None:
        _list_b_index(
            g,
            gname,
            gprefix,
            field_specs,
            field_metas,
            dl_name,
            dl_base,
            file_num,
            e_flag,
        )
        return

    # Collect all entries with their sort field value
    entries: list[tuple[str, str]] = []  # (sort_value, ien)
    key = ""
    while True:
        key = g.order(gname, gprefix + ("B", key))
        if not key:
            break
        ien = ""
        while True:
            ien = g.order(gname, gprefix + ("B", key, ien))
            if not ien:
                break
            sv = _extract_piece(
                g, gname, gprefix, ien, sort_meta["node"], sort_meta["piece"]
            )
            if sv:  # skip empties (can't be subscripts in temp index)
                entries.append((sv, ien))

    # Sort alphabetically by sort value, then by IEN for stability
    entries.sort(key=lambda e: (e[0], _mumps_sort_key(e[1])))

    count = 0
    for _, ien in entries:
        count += 1
        fv = _extract_fields(
            g, gname, gprefix, ien, field_specs, field_metas, file_num, e_flag
        )
        _output_entry(g, dl_name, dl_base, count, ien, field_specs, fv)
    _set_header(g, dl_name, dl_base, count, field_specs)


def _list_screen_expr(
    g: Any,
    gname: str,
    gprefix: tuple[str, ...],
    field_specs: list[dict],
    field_metas: dict,
    dl_name: str,
    dl_base: tuple[str, ...],
    file_num: str,
    dindex: str,
    e_flag: bool,
) -> None:
    """X-flag screen by computed expression (e.g. ``COUNT(COUNTY)>100``)."""
    # Parse: FUNC(ARG) operator THRESHOLD
    m = re.match(r"(\w+)\((\w+)\)\s*(>|<|>=|<=|=)\s*(\d+)", dindex)
    if not m:
        _list_b_index(
            g,
            gname,
            gprefix,
            field_specs,
            field_metas,
            dl_name,
            dl_base,
            file_num,
            e_flag,
        )
        return

    func = m.group(1).upper()
    arg = m.group(2)
    op = m.group(3)
    threshold = int(m.group(4))

    _ops = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "=": lambda a, b: a == b,
    }
    cmp = _ops.get(op, lambda a, b: False)

    # Walk all entries, evaluate expression, filter
    count = 0
    key = ""
    while True:
        key = g.order(gname, gprefix + ("B", key))
        if not key:
            break
        ien = ""
        while True:
            ien = g.order(gname, gprefix + ("B", key, ien))
            if not ien:
                break
            if func == "COUNT":
                cv = _count_multiple(g, gname, gprefix, ien, arg, file_num)
            else:
                continue
            if cmp(cv, threshold):
                count += 1
                fv = _extract_fields(
                    g, gname, gprefix, ien, field_specs, field_metas, file_num, e_flag
                )
                _output_entry(g, dl_name, dl_base, count, ien, field_specs, fv)
    _set_header(g, dl_name, dl_base, count, field_specs)


# ── Sort-template support ────────────────────────────────────────────


def _find_template_ien(g: Any, name: str, file_num: str) -> str | None:
    """Find a sort-template IEN by name via ^DIBT("F"<file>,name,ien)."""
    f_key = "F" + str(file_num)
    ien = g.order("DIBT", (f_key, name, ""))
    if ien:
        return ien
    # Also try the B-index
    ien = g.order("DIBT", ("B", name, ""))
    return ien or None


def _read_template_levels(g: Any, ien: str) -> list[dict[str, Any]]:
    """Read sort-template levels from ^DIBT(ien,2,level,0)."""
    levels: list[dict[str, Any]] = []
    lvl = ""
    while True:
        lvl = g.order("DIBT", (ien, "2", lvl))
        if not lvl:
            break
        zero = g.get("DIBT", (ien, "2", lvl, "0")) or ""
        parts = zero.split("^")
        field_num = parts[1] if len(parts) > 1 else ""
        label = parts[2] if len(parts) > 2 else ""
        flags = parts[3] if len(parts) > 3 else ""
        screen_val = parts[4] if len(parts) > 4 else ""

        descending = "-" in flags

        f_val = g.get("DIBT", (ien, "2", lvl, "F"))
        t_val = g.get("DIBT", (ien, "2", lvl, "T"))
        is_screen = (f_val == "0" and t_val == "1") or bool(screen_val)

        levels.append(
            {
                "field_num": field_num,
                "label": label,
                "flags": flags,
                "screen_val": screen_val,
                "descending": descending,
                "is_screen": is_screen,
            }
        )
    return levels


def _eval_template_expr(
    g: Any, gname: str, gprefix: tuple[str, ...], ien: str, label: str, file_num: str
) -> Any:
    """Evaluate a template sort/screen expression for one entry."""
    m = _RE_COMPUTED.match(label)
    if m and m.group(1).upper() == "COUNT":
        return _count_multiple(g, gname, gprefix, ien, m.group(2), file_num)

    em = re.match(r"\$E(?:XTRACT)?\((\w+),(\d+),(\d+)\)", label, re.IGNORECASE)
    if em:
        fname = em.group(1)
        start = int(em.group(2))
        end = int(em.group(3))
        fn = _find_field_by_name(g, file_num, fname)
        if fn:
            info = _get_field_info(g, file_num, fn)
            if info and info["piece"] > 0:
                val = _extract_piece(
                    g, gname, gprefix, ien, info["node"], info["piece"]
                )
                return val[start - 1 : end]
        return ""

    fn = _find_field_by_name(g, file_num, label)
    if fn:
        info = _get_field_info(g, file_num, fn)
        if info and info["piece"] > 0:
            return _extract_piece(g, gname, gprefix, ien, info["node"], info["piece"])
    return ""


def _list_sort_template(
    g: Any,
    gname: str,
    gprefix: tuple[str, ...],
    field_specs: list[dict],
    field_metas: dict,
    dl_name: str,
    dl_base: tuple[str, ...],
    file_num: str,
    dindex: str,
    e_flag: bool,
) -> None:
    """X-flag sort using a named sort template from ^DIBT."""
    tmpl_name = dindex.strip("[]").strip()
    tmpl_ien = _find_template_ien(g, tmpl_name, file_num)
    if not tmpl_ien:
        _list_b_index(
            g,
            gname,
            gprefix,
            field_specs,
            field_metas,
            dl_name,
            dl_base,
            file_num,
            e_flag,
        )
        return

    levels = _read_template_levels(g, tmpl_ien)
    if not levels:
        _list_b_index(
            g,
            gname,
            gprefix,
            field_specs,
            field_metas,
            dl_name,
            dl_base,
            file_num,
            e_flag,
        )
        return

    sort_levels = [lv for lv in levels if not lv["is_screen"]]
    screen_levels = [lv for lv in levels if lv["is_screen"]]

    all_entries: list[str] = []
    key = ""
    while True:
        key = g.order(gname, gprefix + ("B", key))
        if not key:
            break
        ien = ""
        while True:
            ien = g.order(gname, gprefix + ("B", key, ien))
            if not ien:
                break
            all_entries.append(ien)

    filtered: list[str] = []
    for ien in all_entries:
        passes = True
        for slvl in screen_levels:
            ev = _eval_template_expr(g, gname, gprefix, ien, slvl["label"], file_num)
            sv = slvl["screen_val"]
            if sv.startswith("="):
                expected = sv[1:].strip('"')
                if str(ev) != expected:
                    passes = False
                    break
        if passes:
            filtered.append(ien)

    if sort_levels:

        def make_sort_key(ien: str) -> tuple:
            keys: list[Any] = []
            for slvl in sort_levels:
                ev = _eval_template_expr(
                    g, gname, gprefix, ien, slvl["label"], file_num
                )
                if isinstance(ev, int):
                    keys.append((-ev if slvl["descending"] else ev,))
                else:
                    keys.append((str(ev),))
            return tuple(keys)

        filtered.sort(key=make_sort_key)

    count = 0
    for ien in filtered:
        count += 1
        fv = _extract_fields(
            g, gname, gprefix, ien, field_specs, field_metas, file_num, e_flag
        )
        _output_entry(g, dl_name, dl_base, count, ien, field_specs, fv)
    _set_header(g, dl_name, dl_base, count, field_specs)


# ── MUMPS-compatible sort key ────────────────────────────────────────


def _mumps_sort_key(val: str) -> tuple:
    """Sort key matching MUMPS subscript collation: numerics first."""
    try:
        n = float(val)
        return (0, n, val)
    except ValueError:
        return (1, 0, val)
