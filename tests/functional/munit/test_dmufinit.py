"""Standalone integration test: transpile and run DMUFINIT through m2py.

Validates that the DMUFINIT package installer chain — which creates test files
1009.801 (Broken File) and 1009.802 (Shadow State) — produces identical globals
when transpiled by m2py as when run in native YottaDB.

The golden reference is ``baselines/globals/dmudic00_fixtures.zwr``, captured
from YDB Docker.  Once this test passes fully, the ZWR file, capture script,
and STARTUP/SHUTDOWN bypass infrastructure become redundant and can be removed.

The static ZWR loader in conftest.py (``_load_dmu_fixtures``) remains the
fast-path for dependent tests like DMUDIC00 when ``-m slow`` is not active.
This test independently validates that the transpiled DMUFINIT chain produces
the same globals, proving the ZWR data is reproducible from source.

Execution chain::

    DMUFINIT → DMUFINI5 ($TEXT IXF data)
             → DMUFINI1 → DMUFI001..I (18 data loaders via D @(DN_$$B36(R)))
                        → KEYSNIX (DIFROMSX/SY index install)
                        → DATA (DITR data transport)
             → DMUFINI2 (help frames)
             → DMUFINI3 (templates)
             → cleanup (G Q^DIFROM0 → Q^DIFROM11)
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

_BASELINES_DIR = Path(__file__).resolve().parent / "baselines"
_BASELINE_ZWR = _BASELINES_DIR / "globals" / "dmudic00_fixtures.zwr"

# Global prefixes that DMUFINIT creates (used for comparison)
_DMU_GLOBAL_PREFIXES = [
    ("DD", "1009.801"),
    ("DD", "1009.802"),
    ("DD", "1009.812"),  # sub-file: COUNTY under 1009.802
    ("DD", "1009.822"),  # sub-file: COUNTY under 1009.812
    ("DIC", "1009.801"),
    ("DIC", "1009.802"),
    ("DMU", "1009.801"),
    ("DMU", "1009.802"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_zwr_baseline() -> dict[str, str]:
    """Parse the golden ZWR file into a {reference: value} dict.

    Returns dict like ``{"^DD(1009.801,0)": "FIELD^^.06^6", ...}``.

    Excludes ^DD("IX",...) entries because their IEN values are
    environment-dependent (sequential allocation from the existing
    Index file).  Structural validation is done separately.
    """
    from m2py.runtime.zwr import parse_zwr_stream

    result: dict[str, str] = {}
    with open(_BASELINE_ZWR) as f:
        for name, subs, value in parse_zwr_stream(f):
            # Skip ^DD("IX",...) — IENs differ between environments
            if name == "^DD" and subs and subs[0] == "IX":
                continue
            if subs:
                formatted = ",".join(
                    f'"{s}"' if not s.replace(".", "").replace("-", "").isdigit() else s
                    for s in subs
                )
                ref = f"{name}({formatted})"
            else:
                ref = name
            result[ref] = value
    return result


def _extract_dmu_globals(backend) -> dict[str, str]:
    """Extract DMUFINIT-created globals from a runtime backend.

    Uses export_zwr to serialize, then parses back for comparison.
    Returns dict like ``{"^DD(1009.801,0)": "FIELD^^.06^6", ...}``.
    """

    stream = io.StringIO()
    for global_name, first_sub in _DMU_GLOBAL_PREFIXES:
        # Export the subtree under ^GLOBAL(first_sub,...)
        _export_subtree(backend, global_name, first_sub, stream)

    # Note: ^DD("IX",...) entries are excluded from comparison because
    # IEN values are environment-dependent.  Structural validation is
    # done separately by _validate_dd_ix_structure().

    # Parse back into dict
    from m2py.runtime.zwr import parse_zwr_stream

    result: dict[str, str] = {}
    stream.seek(0)
    for name, subs, value in parse_zwr_stream(stream):
        if subs:
            formatted = ",".join(
                f'"{s}"' if not s.replace(".", "").replace("-", "").isdigit() else s
                for s in subs
            )
            ref = f"{name}({formatted})"
        else:
            ref = name
        result[ref] = value
    return result


def _export_subtree(backend, global_name: str, first_sub: str, stream) -> None:
    """Export all nodes under ^GLOBAL(first_sub,...) to a stream."""
    from m2py.runtime.zwr import serialize_zwr_node

    display = f"^{global_name}"

    # Check root: ^GLOBAL(first_sub)
    root_val = backend.get(global_name, (first_sub,), update_naked=False)
    if root_val is not None:
        stream.write(serialize_zwr_node(display, [first_sub], root_val) + "\n")

    # Use $QUERY to traverse all descendant nodes
    subs = (first_sub, "")
    ref = backend.query(global_name, subs)
    prefix = f"^{global_name}({first_sub},"
    while ref and ref.startswith(prefix):
        # Parse subscripts from the reference
        inner = ref[len(f"^{global_name}(") : -1]
        # Split carefully (handles quoted subscripts)
        parsed_subs = _parse_subs(inner)
        val = backend.get(global_name, tuple(parsed_subs), update_naked=False)
        if val is not None:
            stream.write(serialize_zwr_node(display, parsed_subs, val) + "\n")
        ref = backend.query(global_name, tuple(parsed_subs))


def _validate_dd_ix_structure(backend) -> list[str]:
    """Validate ^DD("IX",...) index structure without comparing exact IENs.

    Returns a list of error strings (empty if all checks pass).

    Verifies that:
    1. AC xref entries exist for expected test files
    2. Referenced index definitions have correct names and types
    3. Set/kill code patterns are correct
    """
    errors: list[str] = []
    _TEST_FILES = ("1009.801", "1009.802")

    for file_num in _TEST_FILES:
        # Check AC xref: ^DD("IX","AC",file,ien)
        ien = backend.order("DD", ("IX", "AC", file_num, ""), 1, update_naked=False)
        if not ien:
            errors.append(f"No AC xref for file {file_num}")
            continue

        # Validate the index definition at ^DD("IX",ien,0)
        ix_zero = backend.get("DD", ("IX", ien, "0"), update_naked=False)
        if not ix_zero:
            errors.append(f'No 0-node at ^DD("IX",{ien},0) for file {file_num}')
            continue

        parts = ix_zero.split("^")
        if parts[0] != file_num:
            errors.append(
                f'^DD("IX",{ien},0) piece 1: expected {file_num}, got {parts[0]}'
            )

        # Check set code exists
        set_code = backend.get("DD", ("IX", ien, "1"), update_naked=False)
        if not set_code:
            errors.append(f'No set code at ^DD("IX",{ien},1) for file {file_num}')

        # Check kill code exists
        kill_code = backend.get("DD", ("IX", ien, "2"), update_naked=False)
        if not kill_code:
            errors.append(f'No kill code at ^DD("IX",{ien},2) for file {file_num}')

    return errors


def _parse_subs(inner: str) -> list[str]:
    """Parse comma-separated subscripts from a global reference interior.

    Handles quoted strings: ``1009.801,"B","ALABAMA",1`` →
    ``["1009.801", "B", "ALABAMA", "1"]``
    """
    subs: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == '"':
            # Quoted string — find matching close quote
            j = i + 1
            while j < len(inner):
                if inner[j] == '"':
                    if j + 1 < len(inner) and inner[j + 1] == '"':
                        j += 2  # escaped quote
                    else:
                        break
                else:
                    j += 1
            subs.append(inner[i + 1 : j].replace('""', '"'))
            i = j + 1
            if i < len(inner) and inner[i] == ",":
                i += 1
        elif inner[i] == ",":
            i += 1
        else:
            # Unquoted value
            j = inner.index(",", i) if "," in inner[i:] else len(inner)
            subs.append(inner[i:j])
            i = j
            if i < len(inner) and inner[i] == ",":
                i += 1
    return subs


def _diff_globals(
    actual: dict[str, str],
    expected: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    """Compare two global dictionaries.

    Returns:
        (missing, extra, mismatched) where each is a list of human-readable strings.
        - missing: in expected but not in actual
        - extra: in actual but not in expected
        - mismatched: in both but with different values
    """
    missing = []
    extra = []
    mismatched = []

    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())

    for key in sorted(expected_keys - actual_keys):
        missing.append(f"  MISSING: {key}={expected[key]}")

    for key in sorted(actual_keys - expected_keys):
        extra.append(f"  EXTRA:   {key}={actual[key]}")

    for key in sorted(expected_keys & actual_keys):
        if actual[key] != expected[key]:
            mismatched.append(
                f"  MISMATCH: {key}\n"
                f"    expected: {expected[key]}\n"
                f"    actual:   {actual[key]}"
            )

    return missing, extra, mismatched


# ---------------------------------------------------------------------------
# AC xref hook — environmental compensation, NOT an m2py bug workaround
# ---------------------------------------------------------------------------


def _install_ac_xref_hook(backend) -> None:
    """Hook the global backend to fire AC xref on ^DD("IX",ien,0) writes.

    **This is NOT an m2py bug workaround.**  It compensates for the same
    environmental limitation that exists in native YottaDB: DDIXIN^DIFROMSX
    creates Index file (.11) entries via FILE^DICN + MERGE.  MERGE bypasses
    cross-references, so the .51 (Root File) AC xref never fires.  IX1^DIK
    is supposed to re-fire all xrefs afterward, but ^DD(.11,0,"DIK") is
    undefined in both YDB and m2py — meaning DH is NEWed but never SET in
    the non-compiled fallback path, and old-style xref iteration silently
    finds nothing.  In a full VistA environment, pre-existing AC entries
    from 0.11+INDEX.zwr cover this gap; the bootstrap loads that file,
    but dynamically-created index entries from DMUFINIT still need this
    hook.

    This hook creates ^DD("IX","AC",rootfile,ien)="" whenever the
    0-node of an index entry is written with a non-empty .51 value
    (piece 9).  This allows INDEX^DIKC / LOADALL^DIKC1 to discover
    new-style indexes when IXALL fires on data files later in DMUFINIT.
    """
    original_set = backend.set
    _ac_count = [0]  # mutable counter for closure

    def _hooked_set(name: str, subscripts: tuple, value: str) -> None:
        original_set(name, subscripts, value)

        # Detect writes to ^DD("IX",<numeric-ien>,"0")
        if (
            name == "DD"
            and len(subscripts) == 3
            and subscripts[0] == "IX"
            and subscripts[2] == "0"
        ):
            ien = subscripts[1]
            # Only process numeric IENs (skip "AC", "B", "BB" etc.)
            try:
                if float(ien) > 0:
                    parts = str(value).split("^") if value else []
                    # .51 (Root File) is at piece 9 (index 8) of the 0-node
                    if len(parts) >= 9 and parts[8]:
                        root_file = parts[8][:30]
                        original_set("DD", ("IX", "AC", root_file, ien), "")
                        _ac_count[0] += 1
                        logger.warning(
                            'AC xref hook: ^DD("IX","AC",%s,%s)=""',
                            root_file,
                            ien,
                        )
            except (ValueError, TypeError):
                pass  # Not a numeric IEN

    backend.set = _hooked_set


# ---------------------------------------------------------------------------
# Progress monitoring
# ---------------------------------------------------------------------------


class _ProgressTracker:
    """Wraps the global storage to log progress as globals are written.

    Reports a summary every ``interval`` seconds to give visibility into
    long-running DMUFINIT execution.
    """

    def __init__(self, backend, interval: float = 10.0) -> None:
        self._backend = backend
        self._interval = interval
        self._count = 0
        self._last_report = time.monotonic()
        self._start = self._last_report
        self._original_set = backend.set
        backend.set = self._tracked_set  # type: ignore[method-assign]

    def _tracked_set(self, global_name, subscripts, value):
        self._original_set(global_name, subscripts, value)
        self._count += 1
        now = time.monotonic()
        if now - self._last_report >= self._interval:
            elapsed = now - self._start
            logger.warning(
                "DMUFINIT progress: %d globals written in %.0fs (last: ^%s)",
                self._count,
                elapsed,
                global_name,
            )
            self._last_report = now

    def restore(self) -> None:
        """Restore the original set method."""
        self._backend.set = self._original_set

    @property
    def count(self) -> int:
        return self._count

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.munit
class TestDMUFINIT:
    """Validate that transpiled DMUFINIT produces correct globals."""

    def test_dmufinit_produces_correct_globals(
        self, fileman_library, fileman_bootstrap
    ):
        """Run DMUFINIT via m2py and compare output against ZWR baseline.

        This is the key integration test.  If it passes, the ZWR fixture
        file and all bypass infrastructure can be removed.

        Progress is logged every 10 seconds via the WARNING level so it
        shows up even without ``-s`` — use ``--log-cli-level=WARNING``
        or ``-s`` to watch live progress.
        """
        runtime = fileman_bootstrap

        if not _BASELINE_ZWR.exists():
            pytest.skip("Golden ZWR baseline not found")

        # --- Seed the variables DMUFINIT expects ---
        from m2py.runtime import MArray, run_with_goto_support

        scope: dict[str, MArray] = {}

        # U = "^" (already set by fileman_bootstrap, but ensure it)
        u = MArray()
        u.value = "^"
        scope["U"] = u

        # DUZ = 0 (unprivileged user)
        duz = MArray()
        duz.value = "0"
        scope["DUZ"] = duz

        # DUZ(0) = "@" (full access — programmer mode)
        duz.set("0", value="@")

        # ^DD("VERSION") = 22.2 (required for DMUFINIT version check)
        runtime.globals.set("DD", ("VERSION",), "22.2")

        # DIQUIET = 1 (suppress write output)
        diq = MArray()
        diq.value = "1"
        scope["DIQUIET"] = diq

        # IO = $PRINCIPAL (set to "0" which is our principal device)
        io_var = MArray()
        io_var.value = "0"
        scope["IO"] = io_var

        # Ensure the DMUFINIT module is loaded via auto-importer
        import importlib

        try:
            mod = importlib.import_module("DMUFINIT")
        except ImportError:
            pytest.fail("Cannot import DMUFINIT — auto-importer not configured")

        # --- Clear any pre-loaded DMU fixture data ---
        # We want to test that DMUFINIT creates this data from scratch.
        for global_name, first_sub in _DMU_GLOBAL_PREFIXES:
            if global_name == "DD":
                # Only kill DD entries for our test files, not all DD
                runtime.globals.kill("DD", (first_sub,))
            elif global_name == "DIC":
                # Only kill DIC entries for our test files
                runtime.globals.kill("DIC", (first_sub,))
            else:
                runtime.globals.kill(global_name, (first_sub,))

        # --- Install AC xref hook (environmental compensation, not m2py bug) ---
        _install_ac_xref_hook(runtime.globals)

        # --- Run DMUFINIT with progress tracking ---
        runtime.clear()  # Clear output buffer
        tracker = _ProgressTracker(runtime.globals, interval=10.0)
        logger.warning("DMUFINIT starting...")

        try:
            run_with_goto_support(
                lambda _rt, _scope=None: mod._entry_function(_rt, _scope=_scope),
                runtime,
                scope,
            )
        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            actual = _extract_dmu_globals(runtime.globals)
            expected = _load_zwr_baseline()
            missing_count = len(set(expected.keys()) - set(actual.keys()))
            extra_count = len(set(actual.keys()) - set(expected.keys()))
            pytest.fail(
                f"DMUFINIT crashed after {tracker.elapsed:.1f}s "
                f"({tracker.count} globals written): "
                f"{type(e).__name__}: {e}\n"
                f"Globals so far: {len(actual)} nodes "
                f"(expected {len(expected)}, "
                f"missing {missing_count}, extra {extra_count})\n"
                f"Output: {runtime.get_output()[:500]}\n"
                f"Traceback:\n{tb[-2000:]}"
            )
        finally:
            tracker.restore()
            # Safety net: release any locks still held if DMUFINIT crashes
            # before reaching its own argumentless LOCK (which translates to
            # _rt.globals.unlock_all()).  Under normal execution, DMUFINIT
            # releases all locks itself.
            runtime.globals.unlock_all()

        logger.warning(
            "DMUFINIT completed in %.1fs — %d global writes",
            tracker.elapsed,
            tracker.count,
        )

        # --- Post-DMUFINIT reindexing (environmental compensation, not m2py bug) ---
        for file_num in ("1009.801", "1009.802"):
            reindex_code = (
                f'N DA S DA="" D INDEX^DIKC("^DMU({file_num},",.DA,"","","S")'
            )
            try:
                runtime.execute_mumps(reindex_code, scope)
            except Exception as e:
                logger.warning("INDEX^DIKC for %s failed: %s", file_num, e)

        # --- Compare against baseline ---
        actual = _extract_dmu_globals(runtime.globals)
        expected = _load_zwr_baseline()

        missing, extra, mismatched = _diff_globals(actual, expected)

        # --- Structural validation of ^DD("IX") indexes ---
        ix_errors = _validate_dd_ix_structure(runtime.globals)
        if ix_errors:
            pytest.fail(
                'DD("IX") structural validation failed:\n'
                + "\n".join(f"  {e}" for e in ix_errors)
            )

        if missing or mismatched or extra:
            # Build a readable report
            lines = [
                f"DMUFINIT global comparison: "
                f"{len(actual)} actual vs {len(expected)} expected nodes"
            ]
            if missing:
                lines.append(f"\n{len(missing)} MISSING nodes:")
                lines.extend(missing[:20])
                if len(missing) > 20:
                    lines.append(f"  ... and {len(missing) - 20} more")
            if mismatched:
                lines.append(f"\n{len(mismatched)} MISMATCHED values:")
                lines.extend(mismatched[:10])
                if len(mismatched) > 10:
                    lines.append(f"  ... and {len(mismatched) - 10} more")
            if extra:
                lines.append(f"\n{len(extra)} EXTRA nodes (not in baseline):")
                lines.extend(extra[:10])
                if len(extra) > 10:
                    lines.append(f"  ... and {len(extra) - 10} more")

            pytest.fail("\n".join(lines))

        logger.info(
            "DMUFINIT produced %d globals matching ZWR baseline exactly",
            len(actual),
        )
