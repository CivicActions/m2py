"""pytest plugin for M-Unit integration tests.

Provides session-scoped fixtures for runtime, baseline data, and the M-Unit
framework.  Registers a ``pytest_collect_file`` hook so that TestList files
inside the VistA dependency directory are automatically discovered.

Manual MASH Utilities configs are built here because that package has no
TestList file — its test routines are hard-coded.

Includes a ``MumpsAutoImporter`` meta-path finder that auto-transpiles MUMPS
routines from VistA-M on first import, so deep dependency chains (like
DMUFINIT → DIKZ → DILF → DIQGU → …) resolve without enumerating every
routine.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import logging
import os
import sys
from pathlib import Path

import pytest

from .lib.adapter import (
    MUnitCollector,
    _load_routine,
    load_mash_routines,
    load_package_routines,
)
from .lib.models import BaselineData, TestRoutineConfig
from .lib.parser import parse_testlist

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

# Repository root (tests/functional/munit → 3 levels up)
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Baselines shipped with the repo (not downloaded)
_BASELINES_DIR = Path(__file__).resolve().parent / "baselines"
_BASELINE_FILE = _BASELINES_DIR / "osehravista-baseline.json"
_GLOBALS_DIR = _BASELINES_DIR / "globals"

# VistA dependencies — downloaded by setup_deps.py into .vista-deps/ (or
# overridden via VISTA_DEPS_DIR).  Individual dirs can also be overridden.
_VISTA_DEPS = Path(os.environ.get("VISTA_DEPS_DIR", str(_REPO_ROOT / ".vista-deps")))
_VISTA_M_DIR = Path(os.environ.get("VISTA_M_DIR", str(_VISTA_DEPS / "VistA-M")))
_VISTA_DIR = Path(os.environ.get("VISTA_DIR", str(_VISTA_DEPS / "VistA")))

# Derived paths within VistA-M
_VISTA_M_PACKAGES_DIR = _VISTA_M_DIR / "Packages"
_VISTA_M_KERNEL_DIR = _VISTA_M_PACKAGES_DIR / "Kernel" / "Routines"
_VISTA_M_FILEMAN_DIR = _VISTA_M_PACKAGES_DIR / "VA FileMan" / "Routines"
_VISTA_M_FILEMAN_GLOBALS_DIR = _VISTA_M_PACKAGES_DIR / "VA FileMan" / "Globals"
_VISTA_M_MXML_DIR = _VISTA_M_PACKAGES_DIR / "M XML Parser" / "Routines"
_VISTA_M_MASH_DIR = _VISTA_M_PACKAGES_DIR / "MASH Utilities" / "Routines"

# VistA (OSEHRA) — contains TestList files for Tier 2+ packages
_VISTA_SUBMODULE = _VISTA_DIR

# Self-test routine names (%utt1–%utt7 + %uttcovr)
_MASH_TEST_ROUTINES = [
    "%utt1",
    "%utt2",
    "%utt3",
    "%utt4",
    "%utt5",
    "%utt6",
    "%utt7",
    "%uttcovr",
]

# FileMan Testing/MUnit directory (OSEHRA test fixtures: DMUFINIT chain, etc.)
_FM_TESTING_DIR = _VISTA_SUBMODULE / "Packages" / "VA FileMan" / "Testing" / "MUnit"


# ---------------------------------------------------------------------------
# Auto-importer: transpile MUMPS routines on demand
# ---------------------------------------------------------------------------

# Explicit filename → routine-name overrides for %-prefix routines
# where the MUMPS routine name differs from the file stem.
_FILENAME_OVERRIDES: dict[str, str] = {
    "DIDT": "%DT",
    "DIDTC": "%DTC",
    "DIRCR": "%RCR",
    "ZOSVGTM": "%ZOSV",
    "DINVGTM": "%ZOSV2",
    "ZISHGTM": "%ZISH",
}


class MumpsAutoImporter(importlib.abc.MetaPathFinder):
    """sys.meta_path finder that auto-transpiles MUMPS routines.

    When Python tries ``import DIQGU`` and the module isn't already in
    ``sys.modules``, this finder searches the configured VistA-M source
    directories for a matching ``.m`` file.  If found, it transpiles and
    registers the module — handling the entire transitive dependency chain
    lazily.

    This replaces the need to enumerate every possible FileMan/Kernel
    dependency in ``_register_fileman_dependencies()``.
    """

    def __init__(self, search_dirs: list[Path]) -> None:
        self._index: dict[str, Path] = {}  # module_name → .m path
        self._failed: set[str] = set()  # modules that failed transpilation
        for d in search_dirs:
            if d.is_dir():
                for m_file in d.glob("*.m"):
                    stem = m_file.stem
                    # Register under stem name (most routines)
                    self._index[stem] = m_file
                    # For %-prefix overrides, also register the _pct_ form
                    if stem in _FILENAME_OVERRIDES:
                        mumps_name = _FILENAME_OVERRIDES[stem]
                        py_name = "_pct_" + mumps_name[1:]
                        self._index[py_name] = m_file
        logger.debug(
            "MumpsAutoImporter indexed %d routines from %d dirs",
            len(self._index),
            len(search_dirs),
        )

    # -- Modern importlib protocol (find_spec / create_module / exec_module) --

    def find_spec(self, fullname: str, path=None, target=None):
        """Return a ModuleSpec if we have a matching .m file."""
        if fullname in self._failed:
            return None
        if fullname in sys.modules:
            return None
        if fullname not in self._index:
            return None
        return importlib.util.spec_from_loader(fullname, loader=self)

    def create_module(self, spec):
        """Use default module creation semantics."""
        return None

    def exec_module(self, module):
        """Transpile and execute the MUMPS routine into *module*."""
        fullname = module.__name__
        m_file = self._index.get(fullname)
        if m_file is None:
            raise ImportError(fullname)

        # Determine the MUMPS routine name
        stem = m_file.stem
        if stem in _FILENAME_OVERRIDES:
            routine_name = _FILENAME_OVERRIDES[stem]
        else:
            routine_name = stem

        try:
            _load_routine(m_file, routine_name)
            logger.info("Auto-loaded %s from %s", routine_name, m_file.name)
            # _load_routine populated sys.modules[fullname] with the real
            # module object; copy its attributes into *module* so the import
            # system's reference stays valid.
            real = sys.modules.get(fullname)
            if real is not None and real is not module:
                module.__dict__.update(real.__dict__)
        except Exception:
            self._failed.add(fullname)
            logger.debug(
                "Auto-load failed for %s (%s) — skipping",
                fullname,
                m_file.name,
                exc_info=True,
            )
            raise ImportError(fullname) from None


# Singleton; installed once by _install_auto_importer()
_auto_importer: MumpsAutoImporter | None = None


def _install_auto_importer() -> None:
    """Install the MUMPS auto-importer on sys.meta_path (idempotent)."""
    global _auto_importer
    if _auto_importer is not None:
        return
    _auto_importer = MumpsAutoImporter(
        [
            _VISTA_M_FILEMAN_DIR,
            _VISTA_M_KERNEL_DIR,
            _FM_TESTING_DIR,
        ]
    )
    sys.meta_path.append(_auto_importer)
    logger.info("Installed MumpsAutoImporter on sys.meta_path")


# ---------------------------------------------------------------------------
# M XML Parser dependencies — transpiled from VistA-M real MUMPS source
# ---------------------------------------------------------------------------


def _try_load_routine(source_path: Path, routine_name: str) -> bool:
    """Try to transpile and load a routine, logging on failure.

    Returns True on success, False on failure.
    """
    import sys

    if routine_name in sys.modules:
        return True
    # For %-prefixed routines, also check the Python module name
    if routine_name.startswith("%"):
        py_name = "_pct_" + routine_name[1:]
        if py_name in sys.modules:
            return True
    if not source_path.exists():
        logger.warning("Source not found for %s: %s", routine_name, source_path)
        return False
    try:
        _load_routine(source_path, routine_name)
        logger.info("Loaded %s from %s", routine_name, source_path)
        return True
    except Exception:
        logger.exception("Failed to load %s from %s", routine_name, source_path)
        return False


def _register_xml_parser_dependencies() -> None:
    """Load external dependencies needed by the M XML Parser routines.

    Most dependencies are transpiled from real MUMPS source in VistA-M.

    Load order respects dependency chains:

    1. **VA FileMan** (from VistA-M):
       - DDIOL — text output (pure MUMPS, self-contained)
       - DII — OS label sets DISYS from ``^%ZOSF("OS")``/``^DD("OS")``
       - DIDTC (=%DTC) — ``NOW`` converts ``$HOROLOG`` to FileMan date
       - DICRW — ``DT`` entry calls ``NOW^%DTC`` + ``OS^DII``
       - DIALOG — ``BLD`` reads ``^DI(.84)``; no-ops when data missing

    2. **Kernel** (from VistA-M):
       - XLFSTR — string utilities (``$$UP``, ``$$LOW``)
       - XUSCLEAN — keepalive (``TOUCH`` = simple global SET)
       - %ZOSV — GT.M OS utilities (``$$RETURN``, ``DEVOK``)
       - %ZISH — host file control (Python impl, see below)

    3. **M XML Parser library** (from VistA-M) — loaded by
       ``mxml_library`` fixture separately.
    """
    # --- VA FileMan routines ---
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DDIOL.m", "DDIOL")
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DII.m", "DII")
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DIDTC.m", "%DTC")
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DICRW.m", "DICRW")
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DIALOG.m", "DIALOG")

    # --- Kernel routines ---
    _try_load_routine(_VISTA_M_KERNEL_DIR / "XLFSTR.m", "XLFSTR")
    _try_load_routine(_VISTA_M_KERNEL_DIR / "XUSCLEAN.m", "XUSCLEAN")
    _try_load_routine(_VISTA_M_KERNEL_DIR / "ZOSVGTM.m", "%ZOSV")

    # %ZISH — Python implementation because ZISHGUX.m's FTG→READNXT
    # internal call uses ZEXCEPT scoping that the trampoline codegen
    # doesn't support yet (READNXT gets its own RoutineState, so %ZA
    # set by READNXT is invisible to FTG's scope).
    import sys
    from .lib import zish_impl

    sys.modules["_pct_ZISH"] = zish_impl


def _register_fileman_dependencies() -> None:
    """Load external dependencies needed by the VA FileMan test routines.

    Extends the XML Parser dependency set with the auto-importer so that
    any FileMan or Kernel routine referenced at runtime is transpiled and
    loaded on demand.  Only %-prefix routines (where filename ≠ routine
    name) need explicit pre-loading.

    1. **All XML Parser deps** — shared base (DDIOL, DII, %DTC, DICRW, etc.)
    2. **Auto-importer** — handles all remaining FileMan/Kernel/Testing deps
    3. **%-prefix routines** — explicitly pre-loaded because the auto-importer
       needs the mapping (DIDT→%DT, DIRCR→%RCR)
    """
    # First load the shared XML Parser deps (includes %ZISH Python impl)
    _register_xml_parser_dependencies()

    # Install the auto-importer for lazy on-demand transpilation
    _install_auto_importer()

    # Pre-load %-prefix routines where filename ≠ routine name
    # (the auto-importer handles these too via _FILENAME_OVERRIDES,
    # but pre-loading ensures they're available before any DO ^%DT call)
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DIDT.m", "%DT")
    _try_load_routine(_VISTA_M_FILEMAN_DIR / "DIRCR.m", "%RCR")


def _load_dialog_globals(rt) -> int:
    """Load ^DI(.84) DIALOG entries for M XML Parser errors into the runtime.

    The MXML Parser uses BLD^DIALOG to look up error severity for each parse
    error.  Without the ^DI(.84) data, BLD^DIALOG returns without setting
    DIMSG or DIHELP, so MXMLPRSE.ERROR defaults ALL errors to severity 2
    (fatal).  This immediately sets EOD=-1, killing the parse — and then
    blocks the ENDDOCUMENT callback (``Q:EOD<0`` in CBK^MXMLPRS0), so
    SUCCESS never becomes 1 and $$EN^MXMLDOM returns 0.

    With proper data loaded, warnings (type 2→DIMSG) and informational
    messages (type 3→DIHELP) get severity 1 or 0 and don't abort parsing.

    Only entries 9500001–9500049 (M XML Parser package) are loaded.

    Returns:
        Number of global nodes loaded.
    """
    import io

    from m2py.runtime.zwr import import_zwr

    zwr_path = _VISTA_M_FILEMAN_GLOBALS_DIR / "0.84+DIALOG.zwr"
    if not zwr_path.exists():
        logger.warning("DIALOG .zwr file not found — XML parse may fail")
        return 0

    # Filter to only lines containing "9500" (M XML Parser DIALOG entries)
    # to avoid loading the entire DIALOG global.
    filtered_lines: list[str] = []
    with open(zwr_path) as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped.startswith("^") and "9500" in stripped:
                filtered_lines.append(stripped)

    if not filtered_lines:
        logger.warning("No M XML Parser DIALOG entries found")
        return 0

    stream = io.StringIO("\n".join(filtered_lines) + "\n")
    count = import_zwr(rt.globals, stream)
    logger.info("Loaded %d DIALOG global entries for M XML Parser", count)
    return count


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def munit_baseline() -> BaselineData | None:
    """Load the committed osehravista baseline from disk."""
    if _BASELINE_FILE.exists():
        return BaselineData.from_json(_BASELINE_FILE)
    logger.warning("Baseline file not found: %s", _BASELINE_FILE)
    return None


@pytest.fixture(scope="session")
def munit_runtime():
    """Shared MUMPSRuntime for all M-Unit test executions."""
    from m2py.runtime import MUMPSRuntime

    runtime = MUMPSRuntime()
    runtime._capture_output = True
    return runtime


@pytest.fixture(scope="session")
def fileman_bootstrap(munit_runtime):
    """Bootstrap FileMan globals into the runtime (Tier 3).

    Imports ``^DD`` (data dictionary) and ``^DIC`` (file list) into
    ``munit_runtime.globals`` via ``import_zwr()``.

    Data sources (checked in order):
    1. ``baselines/globals/fileman.zwr`` — pre-captured combined file
    2. VistA-M ZWR globals — ``DD.zwr`` and ``1+FILE.zwr``
    3. Skip if neither is available

    Note: ``^%ZOSF`` is not loaded here because it requires a live
    MUMPS instance to generate (see ``utils/export_globals.py``).
    Loading the full ^DD (765K lines) takes a few seconds at session start.
    """
    from m2py.runtime.zwr import import_zwr

    total = 0

    # Option 1: pre-captured combined file
    combined = _GLOBALS_DIR / "fileman.zwr"
    if combined.exists():
        total += import_zwr(munit_runtime.globals, combined)
        logger.info("Loaded %d FileMan globals from combined fileman.zwr", total)
        _bootstrap_package_file(munit_runtime)
        _load_dmu_fixtures(munit_runtime)
        return munit_runtime

    # Option 2: VistA-M individual ZWR files
    dd_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "DD.zwr"
    dic_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "1+FILE.zwr"

    if not dd_zwr.exists() and not dic_zwr.exists():
        pytest.skip(
            "FileMan globals not available — need baselines/globals/fileman.zwr "
            "or VistA-M dependency"
        )

    if dd_zwr.exists():
        count = import_zwr(munit_runtime.globals, dd_zwr)
        total += count
        logger.info("Loaded %d nodes from DD.zwr", count)

    if dic_zwr.exists():
        count = import_zwr(munit_runtime.globals, dic_zwr)
        total += count
        logger.info("Loaded %d nodes from 1+FILE.zwr (^DIC)", count)

    # VistA-M's DD.zwr omits ^DD(.11,...) — the data dictionary for the
    # Index file (.11).  Without it, old-style cross-references (B, AC) on
    # the Index file don't fire when indexes are installed, so LOADALL^DIKC1
    # can't discover new-style indexes.  Load a supplement if available.
    dd_supplement = _GLOBALS_DIR / "fileman_dd_supplement.zwr"
    if dd_supplement.exists():
        count = import_zwr(munit_runtime.globals, dd_supplement)
        total += count
        logger.info("Loaded %d nodes from fileman_dd_supplement.zwr", count)

    # 0.11+INDEX.zwr contains pre-existing ^DD("IX",...) index entries and
    # ~1500 ^DD("IX","AC",rootfile,ien) runtime entries.  Without AC data,
    # INDEX^DIKC / LOADALL^DIKC1 cannot discover new-style cross-references
    # for data files.  This is the same data that a full VistA installation
    # would have — loading it brings the test environment closer to parity
    # with a real YDB instance.
    index_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "0.11+INDEX.zwr"
    if index_zwr.exists():
        count = import_zwr(munit_runtime.globals, index_zwr)
        total += count
        logger.info('Loaded %d nodes from 0.11+INDEX.zwr (^DD("IX",...))', count)

    # ^DI(.85) — Language file.  Provides locale-specific date/time
    # formatting code used by DD^%DT when DUZ("LANG")>1 (e.g. German).
    lang_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "0.85+LANGUAGE.zwr"
    if lang_zwr.exists():
        count = import_zwr(munit_runtime.globals, lang_zwr)
        total += count
        logger.info("Loaded %d nodes from 0.85+LANGUAGE.zwr (^DI(.85,...))", count)

    # ^DI(.84) — Dialog file.  Contains error/help text definitions used
    # by BLD^DIALOG.  Without it, FileMan error handling silently returns 0
    # (no error built), causing infinite loops in routines like DIDU that
    # rely on DIERR being set when an error is encountered.
    dialog_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "0.84+DIALOG.zwr"
    if dialog_zwr.exists():
        count = import_zwr(munit_runtime.globals, dialog_zwr)
        total += count
        logger.info("Loaded %d nodes from 0.84+DIALOG.zwr (^DI(.84,...))", count)

    logger.info("FileMan bootstrap complete: %d total global nodes", total)

    # Ensure Package file (9.4) has VA FileMan entry so $$VERSION^XPDUTL("DI")
    # returns "22.2".  DMUDIC00 gates its tests behind this version check.
    _bootstrap_package_file(munit_runtime)

    # Load DMUDIC00 test fixture data (files 1009.801/1009.802) if available.
    # This ZWR was captured from YDB running the real DMUFINIT chain — it
    # contains ^DD, ^DIC, and ^DMU entries for the Broken File and Shadow
    # State test fixtures, including all cross-reference indexes.
    _load_dmu_fixtures(munit_runtime)

    return munit_runtime


def _load_dmu_fixtures(rt) -> int:
    """Load DMUDIC00 test fixture globals (files 1009.801/1009.802).

    Returns the number of global nodes loaded.
    """
    from m2py.runtime.zwr import import_zwr

    dmu_zwr = _GLOBALS_DIR / "dmudic00_fixtures.zwr"
    if not dmu_zwr.exists():
        logger.info(
            "DMUDIC00 fixtures not found (%s) — DIC tests will rely on "
            "DMUFINIT transpilation (likely to fail)",
            dmu_zwr,
        )
        return 0

    count = import_zwr(rt.globals, dmu_zwr)
    logger.info("Loaded %d DMUDIC00 fixture nodes (files 1009.801/1009.802)", count)
    return count


def _bootstrap_package_file(rt) -> None:
    """Seed minimal ^DIC(9.4,...) data for VA FileMan (IEN 13).

    XPDUTL's VERSION function looks up the package namespace ("DI") via the
    "C" cross-reference, then reads the VERSION node.  Without these two
    globals, $$VERSION^XPDUTL("DI") returns "" and any routine that gates
    on FileMan's version (e.g. DMUDIC00) silently skips all tests.
    """
    g = rt.globals
    # Cross-reference: ^DIC(9.4,"C","DI",13)=""
    g.set("DIC", ("9.4", "C", "DI", "13"), "")
    # Version: ^DIC(9.4,13,"VERSION")=22.2
    g.set("DIC", ("9.4", "13", "VERSION"), "22.2")
    # Header node (needed if any code does $D(^DIC(9.4,13,0)))
    g.set("DIC", ("9.4", "13", "0"), "VA FILEMAN^DI^FM INIT")
    logger.info("Bootstrapped Package file: ^DIC(9.4,13) = VA FileMan 22.2")


@pytest.fixture(scope="session")
def clinical_bootstrap(fileman_bootstrap):
    """Bootstrap clinical globals into the runtime (Tier 4).

    Extends ``fileman_bootstrap`` with clinical package globals
    (``^DPT``, ``^SC``, ``^AUPNPROB``, ``^GMPL*``, ``^SD*``, ``^DG*``).

    Reads from ``baselines/globals/clinical_*.zwr`` files if available.
    Skips if no clinical baseline files are present.
    """
    from m2py.runtime.zwr import import_zwr

    clinical_files = sorted(_GLOBALS_DIR.glob("clinical_*.zwr"))
    if not clinical_files:
        pytest.skip(
            "Clinical globals not available — need baselines/globals/clinical_*.zwr"
        )

    total = 0
    for zwr_file in clinical_files:
        count = import_zwr(fileman_bootstrap.globals, zwr_file)
        total += count
        logger.info("Loaded %d nodes from %s", count, zwr_file.name)

    logger.info("Clinical bootstrap complete: %d total global nodes", total)
    return fileman_bootstrap


@pytest.fixture(scope="session")
def munit_framework(munit_runtime):
    """Transpile and load the full MASH Utilities suite (framework + self-tests).

    This must run once per session before any M-Unit test execution so that
    cross-routine calls resolve correctly.
    """
    if not _VISTA_M_MASH_DIR.is_dir():
        pytest.skip(f"MASH Utilities directory not found: {_VISTA_M_MASH_DIR}")

    modules = load_mash_routines(_VISTA_M_MASH_DIR)
    if "%ut" not in modules:
        pytest.skip("Failed to load %ut framework")

    # Register XTMUNIT as an alias for %ut.  In VistA, XTMUNIT was the
    # package-namespaced (Toolkit) name for %ut.  FileMan test routines
    # (DMUDIC00, DMUDTC00, etc.) reference EN^XTMUNIT.
    ut_mod = modules["%ut"]
    sys.modules["XTMUNIT"] = ut_mod

    return modules


@pytest.fixture(scope="session")
def mxml_library(munit_framework, munit_runtime):
    """Load M XML Parser library routines from VistA-M.

    Returns dict mapping routine name → module.  Requires the M-Unit
    framework to be loaded first (for cross-routine call resolution).

    Loads external Kernel/FileMan dependencies first (transpiled from
    VistA-M real MUMPS source), then parser library routines.  Also loads
    ^DI(.84) DIALOG global data so that BLD^DIALOG can classify error
    severity correctly — without this, all XML parse errors are fatal.
    """
    if not _VISTA_M_MXML_DIR.is_dir():
        pytest.skip(f"M XML Parser library not found: {_VISTA_M_MXML_DIR}")

    # Register Kernel/FileMan dependencies before loading parser routines
    _register_xml_parser_dependencies()

    # Load ^DI(.84) DIALOG data for XML Parser error severity classification.
    # Without this, BLD^DIALOG can't determine severity, all errors become
    # fatal, and $$EN^MXMLDOM always returns 0.
    _load_dialog_globals(munit_runtime)

    # Load all M XML Parser library routines from VistA-M
    modules = load_package_routines(_VISTA_M_MXML_DIR)

    return modules


@pytest.fixture(scope="session")
def fileman_library(munit_framework, fileman_bootstrap):
    """Load VA FileMan dependency routines and test init routines.

    Requires the M-Unit framework to be loaded first, and FileMan globals
    (``^DD``, ``^DIC``) to be bootstrapped from ZWR files.

    Loads:
    - All FileMan/Kernel dependency routines (DIC, DIQ, %DT, etc.)
    - DMUFINIT chain (test fixture installation routines)
    - %ZISH Python implementation
    """
    _register_fileman_dependencies()


@pytest.fixture(scope="session")
def mash_configs() -> list[TestRoutineConfig]:
    """Build TestRoutineConfig objects for each MASH Utilities self-test routine.

    MASH Utilities has no TestList file, so configs are built manually.
    """
    configs = []
    for routine_name in _MASH_TEST_ROUTINES:
        # %utt1 → filename %utt1.m or utt1.m (VistA-M stores both forms)
        stem = routine_name.lstrip("%")
        # Prefer %-prefixed filename, fall back to bare stem
        source_path = _VISTA_M_MASH_DIR / f"{routine_name}.m"
        if not source_path.exists():
            source_path = _VISTA_M_MASH_DIR / f"{stem}.m"

        configs.append(
            TestRoutineConfig(
                routine_name=routine_name,
                package_name="MASH Utilities",
                invocation=f'D EN^%ut("{routine_name}")',
                source_path=str(source_path),
                tier=1,
            )
        )
    return configs


# ---------------------------------------------------------------------------
# Backend-aware test skipping
# ---------------------------------------------------------------------------


def _get_backend_name() -> str:
    """Get the current backend name from environment."""
    import os

    return os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory").lower()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip tests marked for backends that aren't active.

    Tests decorated with @pytest.mark.backend_yottadb will only run when
    M2PY_GLOBAL_BACKEND=yottadb, and similarly for other backends.
    """
    current = _get_backend_name()

    for item in items:
        for marker_name in ("backend_yottadb", "backend_iris", "backend_inmemory"):
            if marker_name in item.keywords:
                required_backend = marker_name.replace("backend_", "")
                if current != required_backend:
                    item.add_marker(
                        pytest.mark.skip(
                            reason=f"requires {required_backend} backend "
                            f"(current: {current})"
                        )
                    )


# ---------------------------------------------------------------------------
# Test collection
# ---------------------------------------------------------------------------


def pytest_collect_file(parent, file_path):
    """Hook: discover OSEHRA TestList files in VistA dependency directory."""
    if file_path.name != "TestList":
        return None

    # Only process TestList files under a *MUnit* directory inside VistA/
    if "MUnit" not in str(file_path):
        return None

    # Derive package name from directory structure:
    # VistA/Packages/<PackageName>/Testing/MUnit/TestList
    parts = file_path.parts
    try:
        pkg_idx = parts.index("Packages")
        package_name = parts[pkg_idx + 1]
    except (ValueError, IndexError):
        return None

    configs = parse_testlist(str(file_path), package_name)
    if not configs:
        return None

    return MUnitCollector.from_parent(
        parent,
        name=f"munit_{package_name}",
        configs=configs,
        baseline=None,  # Will be patched in by the fixture if available
        runtime=None,  # Will be patched in by the fixture if available
    )


# ---------------------------------------------------------------------------
# Override parent conftest's per-test global cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_backend_globals():
    """Override parent conftest's _clean_backend_globals for M-Unit tests.

    The parent conftest (tests/conftest.py) calls kill_all() before every
    test to guarantee a clean slate.  This is correct for unit tests where
    each test creates its own data, but it's destructive for M-Unit
    functional tests because:

    - Session-scoped fixtures pre-load reference data (^DI(.84) Dialog
      entries, ^DD data dictionaries, ^DIC file lists) into the shared
      backend *once*.
    - kill_all() before each test wipes this reference data.
    - On InMemory backends, kill_all() operates on a separate storage
      instance so it's harmless.  On YDB/IRIS, it wipes the shared
      database, breaking routines that depend on the reference data
      (e.g., BLD^DIALOG needs ^DI(.84) for error severity classification).

    M-Unit tests manage their own isolation via the M-Unit framework and
    the transpile_and_execute adapter (output clear, unlock_all, I/O reset).

    We release all locks after each test as a safety net for test isolation.
    Routines like DMUFINIT acquire hundreds of incremental locks during
    execution and release them via argumentless LOCK at the end.  This
    teardown ensures clean isolation if a routine crashes before reaching
    its own lock-release code.
    """
    yield
    # Release any locks accumulated during this test.  Global data is
    # preserved (no kill_all), but stale locks must not carry over.
    import os

    backend_name = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")
    if backend_name in ("yottadb", "iris"):
        from m2py.runtime import get_global_storage

        try:
            get_global_storage(backend_name).unlock_all()
        except Exception:
            pass
