"""Profile DMUDIC00 test execution: time each @TEST individually.

Usage:
    uv run python utils/profile_dmudic00.py

Runs the DMUDIC00 test routine with instrumentation that times each
@TEST entry and reports memory usage.  Helps identify which test(s)
are the bottleneck causing OOM in CI.
"""

from __future__ import annotations

import gc
import logging
import os
import resource
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_rss_mb() -> float:
    """Get current RSS in MB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main():
    # Ensure we're in the right directory
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)
    sys.path.insert(0, os.path.join(repo_root, "src"))
    # Add repo root so "tests" is importable as a package
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    print("=== DMUDIC00 Profiler ===")
    print(f"Initial RSS: {get_rss_mb():.1f} MB")

    # --- Phase 1: Bootstrap runtime ---
    t0 = time.monotonic()
    from m2py.runtime import MUMPSRuntime

    runtime = MUMPSRuntime()
    runtime._capture_output = True
    print(f"[{time.monotonic() - t0:.1f}s] Runtime created, RSS: {get_rss_mb():.1f} MB")

    # --- Phase 2: Load globals ---
    from pathlib import Path
    from m2py.runtime.zwr import import_zwr

    baselines_dir = (
        Path(repo_root) / "tests" / "functional" / "munit" / "baselines" / "globals"
    )
    vista_deps = Path(repo_root) / ".vista-deps"
    vista_m_fm_globals = vista_deps / "VistA-M" / "Packages" / "VA FileMan" / "Globals"

    # Load DD
    dd_zwr = vista_m_fm_globals / "DD.zwr"
    if dd_zwr.exists():
        count = import_zwr(runtime.globals, dd_zwr)
        print(f"  DD.zwr: {count} nodes, RSS: {get_rss_mb():.1f} MB")

    # Load DIC
    dic_zwr = vista_m_fm_globals / "1+FILE.zwr"
    if dic_zwr.exists():
        count = import_zwr(runtime.globals, dic_zwr)
        print(f"  1+FILE.zwr: {count} nodes")

    # Load INDEX
    index_zwr = vista_m_fm_globals / "0.11+INDEX.zwr"
    if index_zwr.exists():
        count = import_zwr(runtime.globals, index_zwr)
        print(f"  0.11+INDEX.zwr: {count} nodes")

    # Load DIALOG
    dialog_zwr = vista_m_fm_globals / "0.84+DIALOG.zwr"
    if dialog_zwr.exists():
        count = import_zwr(runtime.globals, dialog_zwr)
        print(f"  0.84+DIALOG.zwr: {count} nodes")

    # Load LANGUAGE
    lang_zwr = vista_m_fm_globals / "0.85+LANGUAGE.zwr"
    if lang_zwr.exists():
        count = import_zwr(runtime.globals, lang_zwr)
        print(f"  0.85+LANGUAGE.zwr: {count} nodes")

    # DD supplement
    dd_supp = baselines_dir / "fileman_dd_supplement.zwr"
    if dd_supp.exists():
        count = import_zwr(runtime.globals, dd_supp)
        print(f"  fileman_dd_supplement.zwr: {count} nodes")

    # DMU fixtures
    dmu_zwr = baselines_dir / "dmudic00_fixtures.zwr"
    if dmu_zwr.exists():
        count = import_zwr(runtime.globals, dmu_zwr)
        print(f"  dmudic00_fixtures.zwr: {count} nodes")

    print(f"[{time.monotonic() - t0:.1f}s] Globals loaded, RSS: {get_rss_mb():.1f} MB")

    # --- Phase 3: Bootstrap ^%ZOSF and Package file ---
    g = runtime.globals
    # Package file
    g.set("DIC", ("9.4", "C", "DI", "13"), "")
    g.set("DIC", ("9.4", "13", "VERSION"), "22.2")
    g.set("DIC", ("9.4", "13", "0"), "VA FILEMAN^DI^FM INIT")

    # ^%ZOSF bootstrap (from ZOSFGUX.m)
    zosf_entries = {
        "OS": "GT.M (Unix)^19",
        "TEST": 'I X]"",$T(^@X)]""',
        "UCI": 'S Y=^%ZOSF("PROD")',
        "UCICHECK": "S Y=1",
        "PROD": "VAH,ROU",
        "VOL": "ROU",
        "MGR": "VAH,ROU",
        "RM": "U $I:WIDTH=$S(X<256:X,1:0)",
        "TRAP": '$ZT="G "_X',
        "ERRTN": "^%ZTER",
        "UPPERCASE": 'S Y=$TR(X,"abcdefghijklmnopqrstuvwxyz","ABCDEFGHIJKLMNOPQRSTUVWXYZ")',
        "EOFF": "U $I:(NOECHO)",
        "EON": "U $I:(ECHO)",
        "TRMOFF": 'U $I:(TERMINATOR="")',
        "TMP": "/tmp/",
    }
    for key, value in zosf_entries.items():
        g.set("%ZOSF", (key,), value)

    print(
        f"[{time.monotonic() - t0:.1f}s] Bootstrap complete, RSS: {get_rss_mb():.1f} MB"
    )

    # --- Phase 4: Load routines ---
    from tests.functional.munit.lib.adapter import (
        _load_routine,
        load_mash_routines,
    )
    from tests.functional.munit.conftest import (
        _VISTA_M_MASH_DIR,
        _register_fileman_dependencies,
    )

    # Load mash utils
    modules = load_mash_routines(_VISTA_M_MASH_DIR)
    sys.modules["XTMUNIT"] = modules["%ut"]

    # Register FileMan deps (includes auto-importer)
    _register_fileman_dependencies()

    print(f"[{time.monotonic() - t0:.1f}s] Routines loaded, RSS: {get_rss_mb():.1f} MB")

    # --- Phase 5: Load DMUDIC00 and install AC xref hook ---
    from tests.functional.munit.conftest import _install_ac_xref_hook

    vista_dir = Path(os.environ.get("VISTA_DIR", str(vista_deps / "VistA")))
    testing_dir = vista_dir / "Packages" / "VA FileMan" / "Testing" / "MUnit"
    dmudic00_src = testing_dir / "DMUDIC00.m"

    _load_routine(dmudic00_src, "DMUDIC00")
    _install_ac_xref_hook(runtime.globals)
    test_module = sys.modules["DMUDIC00"]

    print(f"[{time.monotonic() - t0:.1f}s] DMUDIC00 loaded, RSS: {get_rss_mb():.1f} MB")

    # --- Phase 6: Run DMUDIC00 with timing ---
    from m2py.runtime import MArray, run_with_goto_support

    scope: dict[str, MArray] = {}
    _u = MArray()
    _u.value = "^"
    scope["U"] = _u

    runtime.clear()
    runtime.globals.unlock_all()

    print(f"\n{'=' * 60}")
    print("Starting DMUDIC00 execution...")
    print(f"{'=' * 60}")

    gc.collect()
    rss_before = get_rss_mb()
    t_start = time.monotonic()

    try:
        run_with_goto_support(
            test_module._entry_function,
            runtime,
            scope,
        )
    except Exception as e:
        print(
            f"\nEXCEPTION after {time.monotonic() - t_start:.1f}s: {type(e).__name__}: {e}"
        )

    t_end = time.monotonic()
    gc.collect()
    rss_after = get_rss_mb()

    output = runtime.get_output()
    print(f"\n{'=' * 60}")
    print(f"DMUDIC00 completed in {t_end - t_start:.1f}s")
    print(
        f"RSS: {rss_before:.1f} MB -> {rss_after:.1f} MB (delta: {rss_after - rss_before:.1f} MB)"
    )
    print(f"{'=' * 60}")
    print(f"\nOutput ({len(output)} chars):")
    print(output[:3000])
    if len(output) > 3000:
        print(f"... ({len(output) - 3000} more chars)")

    # Parse the output for test-by-test details
    from tests.functional.munit.lib.parser import parse_munit_output

    result = parse_munit_output(output, "DMUDIC00", "VA FileMan")
    print(
        f"\nParsed result: status={result.status}, tests={result.total_tests}, "
        f"failures={result.failures}, errors={result.errors}"
    )
    if result.failure_details:
        print("Failure details:")
        for d in result.failure_details:
            print(f"  {d.entry_tag}^{d.routine}: {d.kind} - {d.message}")


if __name__ == "__main__":
    main()
