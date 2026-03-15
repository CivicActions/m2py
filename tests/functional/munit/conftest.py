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
    _load_routine,
    load_mash_routines,
    load_package_routines,
)
from .lib.models import BaselineData, TestRoutineConfig

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
_VISTA_M_SCHEDULING_DIR = _VISTA_M_PACKAGES_DIR / "Scheduling" / "Routines"
_VISTA_M_REGISTRATION_DIR = _VISTA_M_PACKAGES_DIR / "Registration" / "Routines"

# VistA-VEHU-M — contains additional routines not in VistA-M (e.g. SDMAPI*)
_VEHU_M_DIR = _REPO_ROOT / "VistA-VEHU-M"
_VEHU_M_PACKAGES_DIR = _VEHU_M_DIR / "Packages"
_VEHU_M_SCHEDULING_DIR = _VEHU_M_PACKAGES_DIR / "Scheduling" / "Routines"
_VEHU_M_REGISTRATION_DIR = _VEHU_M_PACKAGES_DIR / "Registration" / "Routines"

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

# Native Python overrides directory — .py files here replace transpiled routines
_OVERRIDES_DIR = Path(__file__).resolve().parent / "overrides"

# Scheduling Testing/MUnit directory (Tier 4b test routines)
_SCHED_TESTING_DIR = _VISTA_SUBMODULE / "Packages" / "Scheduling" / "Testing" / "MUnit"

# Registration Testing/MUnit directory (Tier 4c test routines)
_REG_TESTING_DIR = _VISTA_SUBMODULE / "Packages" / "Registration" / "Testing" / "MUnit"

# Problem List Testing/MUnit directory (Tier 5 test routines)
_PROBLEM_LIST_TESTING_DIR = (
    _VISTA_SUBMODULE / "Packages" / "Problem List" / "Testing" / "MUnit"
)

# Package routine directories used by Problem List dependencies
_VISTA_M_PROBLEM_LIST_DIR = _VISTA_M_PACKAGES_DIR / "Problem List" / "Routines"
_VISTA_M_CCR_DIR = _VISTA_M_PACKAGES_DIR / "Clinical Case Registries" / "Routines"
_VISTA_M_PCE_DIR = _VISTA_M_PACKAGES_DIR / "PCE Patient Care Encounter" / "Routines"
_VISTA_M_CLIN_REMINDERS_DIR = _VISTA_M_PACKAGES_DIR / "Clinical Reminders" / "Routines"
_VISTA_M_QUASAR_DIR = _VISTA_M_PACKAGES_DIR / "Quasar" / "Routines"
_VISTA_M_AICS_DIR = (
    _VISTA_M_PACKAGES_DIR / "Automated Information Collection System" / "Routines"
)
_VISTA_M_ODS_DIR = _VISTA_M_PACKAGES_DIR / "ODS" / "Routines"


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

    def __init__(
        self,
        search_dirs: list[Path],
        override_dirs: list[Path] | None = None,
    ) -> None:
        self._index: dict[str, Path] = {}  # module_name → .m path
        self._overrides: dict[str, Path] = {}  # module_name → .py override path
        self._failed: set[str] = set()  # modules that failed transpilation

        # Index override .py files first (higher priority than .m)
        for d in override_dirs or []:
            if d.is_dir():
                for py_file in d.glob("*.py"):
                    if py_file.name.startswith("_"):
                        continue  # skip __init__.py, __pycache__, etc.
                    self._overrides[py_file.stem] = py_file
        if self._overrides:
            logger.debug(
                "MumpsAutoImporter indexed %d overrides from %s",
                len(self._overrides),
                [str(d) for d in (override_dirs or [])],
            )

        # Index .m files
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
                    else:
                        # Auto-detect %-prefix routines by reading first line.
                        # Many Kernel routines have filename ZIS.m but start
                        # with %ZIS — register them under _pct_ZIS too.
                        try:
                            with open(m_file, "r", errors="replace") as fh:
                                first_line = fh.readline(200)
                            # First non-whitespace token before ; or whitespace
                            rname = (
                                first_line.split(";")[0].split()[0]
                                if first_line.strip()
                                else ""
                            )
                            if rname.startswith("%") and rname[1:] == stem:
                                py_name = "_pct_" + stem
                                self._index[py_name] = m_file
                        except Exception:
                            pass  # skip unreadable files
        logger.debug(
            "MumpsAutoImporter indexed %d routines from %d dirs (%d overrides)",
            len(self._index),
            len(search_dirs),
            len(self._overrides),
        )

    def add_dirs(self, dirs: list[Path]) -> None:
        """Extend the search index with additional directories."""
        added = 0
        for d in dirs:
            if not d.is_dir():
                continue
            for m_file in d.glob("*.m"):
                stem = m_file.stem
                if stem not in self._index:
                    self._index[stem] = m_file
                    added += 1
                if stem in _FILENAME_OVERRIDES:
                    mumps_name = _FILENAME_OVERRIDES[stem]
                    py_name = "_pct_" + mumps_name[1:]
                    if py_name not in self._index:
                        self._index[py_name] = m_file
                else:
                    try:
                        with open(m_file, "r", errors="replace") as fh:
                            first_line = fh.readline(200)
                        rname = (
                            first_line.split(";")[0].split()[0]
                            if first_line.strip()
                            else ""
                        )
                        if rname.startswith("%") and rname[1:] == stem:
                            py_name = "_pct_" + stem
                            if py_name not in self._index:
                                self._index[py_name] = m_file
                    except Exception:
                        pass
        if added:
            logger.debug("Auto-importer extended with %d new routines", added)

    # -- Modern importlib protocol (find_spec / create_module / exec_module) --

    def find_spec(self, fullname: str, path=None, target=None):
        """Return a ModuleSpec if we have a matching override or .m file."""
        if fullname in self._failed:
            return None
        if fullname in sys.modules:
            return None
        if fullname not in self._overrides and fullname not in self._index:
            return None
        return importlib.util.spec_from_loader(fullname, loader=self)

    def create_module(self, spec):
        """Use default module creation semantics."""
        return None

    def get_source_path(self, module_name: str) -> Path | None:
        """Return the .m source path for a routine, or None.

        Used by :func:`m2py.runtime.overrides.partial_override` to find
        the MUMPS source for transpilation when building a partial override.
        """
        return self._index.get(module_name)

    def exec_module(self, module):
        """Load an override or transpile the MUMPS routine into *module*."""
        fullname = module.__name__

        # --- Override fast path: load .py override directly ---
        py_override = self._overrides.get(fullname)
        if py_override is not None:
            try:
                from m2py.runtime.overrides import load_override

                override_mod = load_override(py_override, fullname)
                module.__dict__.update(override_mod.__dict__)
                logger.info(
                    "Loaded override for %s from %s", fullname, py_override.name
                )
                return
            except Exception:
                self._failed.add(fullname)
                logger.warning(
                    "Override load failed for %s (%s) — skipping",
                    fullname,
                    py_override.name,
                    exc_info=True,
                )
                raise ImportError(fullname) from None

        # --- Normal path: transpile .m source ---
        m_file = self._index.get(fullname)
        if m_file is None:
            raise ImportError(fullname)

        # Determine the MUMPS routine name
        stem = m_file.stem
        if stem in _FILENAME_OVERRIDES:
            routine_name = _FILENAME_OVERRIDES[stem]
        elif fullname.startswith("_pct_"):
            # Auto-detected %-prefix routine (e.g., _pct_ZIS → %ZIS)
            routine_name = "%" + fullname[5:]
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
            logger.warning(
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
        ],
        override_dirs=[_OVERRIDES_DIR],
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

    # %ZISH — transpiled from ZISHGUX.m (Host File Control for GT.M/YDB)
    _try_load_routine(_VISTA_M_KERNEL_DIR / "ZISHGUX.m", "%ZISH")
    _try_load_routine(_VISTA_M_KERNEL_DIR / "ZIS3.m", "%ZIS3")


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
    # First load the shared XML Parser deps (includes transpiled %ZISH)
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

    # Set ^XTV(8989.3,1,"DEV") to a writable temp directory so that
    # $$DEFDIR^%ZISH() returns a valid path for host file I/O.
    import tempfile

    dev_dir = tempfile.mkdtemp(prefix="munit_dev_") + "/"
    runtime.globals.set("XTV", ("8989.3", "1", "DEV"), dev_dir)

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

    Also bootstraps ``^%ZOSF`` (kernel OS-specific infrastructure)
    from ZOSFGUX.m values — see ``_bootstrap_zosf()``.
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
        _bootstrap_zosf(munit_runtime)
        _install_ac_xref_hook(munit_runtime.globals)
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

    # ^DD("FUNC") — Function file (.5).  Contains computed expression
    # functions (COUNT, TOTAL, MAXIMUM, etc.) used by DICOMP when parsing
    # sort expressions like "COUNT(COUNTY)".  Without this, BUILDNEW^DIBTED
    # cannot process sort template specs that use computed functions.
    func_zwr = _VISTA_M_FILEMAN_GLOBALS_DIR / "0.5+FUNCTION.zwr"
    if func_zwr.exists():
        count = import_zwr(munit_runtime.globals, func_zwr)
        total += count
        logger.info('Loaded %d nodes from 0.5+FUNCTION.zwr (^DD("FUNC",...))', count)

    logger.info("FileMan bootstrap complete: %d total global nodes", total)

    # Ensure Package file (9.4) has VA FileMan entry so $$VERSION^XPDUTL("DI")
    # returns "22.2".  DMUDIC00 gates its tests behind this version check.
    _bootstrap_package_file(munit_runtime)

    # Bootstrap ^%ZOSF kernel infrastructure (OS type, routine existence
    # test, UCI/PROD, terminal control, etc.).  Without this, FileMan
    # routines that X ^%ZOSF("TEST") or read ^%ZOSF("OS") will error.
    _bootstrap_zosf(munit_runtime)

    # ^DIBT(0) — Sort Template file header.  ^DIC LAYGO needs this to
    # allocate new IENs when creating sort templates (e.g. BUILDNEW^DIBTED).
    # We set a minimal header with IEN counter at 0 rather than loading the
    # full 15K-line 0.401+SORT TEMPLATE.zwr.
    munit_runtime.globals.set("DIBT", ("0",), "SORT TEMPLATE^.401I^0^0")

    # Install AC xref hook — environmental compensation needed by DMUFINIT.
    # When DMUDIC00's STARTUP calls D ^DMUFINIT, the DIFROM installer creates
    # new Index file (.11) entries via FILE^DICN + MERGE.  MERGE bypasses
    # cross-references, so the AC xref never fires.  This hook compensates
    # by creating ^DD("IX","AC",rootfile,ien) entries as indexes are written.
    # The same gap exists in native YottaDB (covered by pre-loaded AC data
    # from 0.11+INDEX.zwr); this hook covers dynamically-created entries.
    _install_ac_xref_hook(munit_runtime.globals)

    return munit_runtime


def _install_ac_xref_hook(backend) -> None:
    """Hook the global backend to fire AC xref on ^DD("IX",ien,0) writes.

    This is environmental compensation (not an m2py bug workaround).
    DDIXIN^DIFROMSX creates Index file (.11) entries via FILE^DICN + MERGE.
    MERGE bypasses cross-references, so the .51 (Root File) AC xref never
    fires.  In a full VistA environment, pre-existing AC entries from
    0.11+INDEX.zwr cover this gap; this hook covers dynamically-created
    index entries from DMUFINIT.

    Creates ^DD("IX","AC",rootfile,ien)="" whenever the 0-node of an
    index entry is written with a non-empty .51 value (piece 9).

    Idempotent — safe to call multiple times on the same backend.
    """
    if getattr(backend, "_ac_xref_hook_installed", False):
        return
    original_set = backend.set

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
            try:
                if float(ien) > 0:
                    parts = str(value).split("^") if value else []
                    # .51 (Root File) is at piece 9 (index 8) of the 0-node
                    if len(parts) >= 9 and parts[8]:
                        root_file = parts[8][:30]
                        original_set("DD", ("IX", "AC", root_file, ien), "")
            except (ValueError, TypeError):
                pass  # Not a numeric IEN

    backend.set = _hooked_set
    backend._ac_xref_hook_installed = True


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


def _bootstrap_zosf(rt) -> None:
    """Seed ^%ZOSF kernel infrastructure global.

    ^%ZOSF is normally populated by running ZOSFGUX (GT.M/Unix) at VistA
    installation time.  Values are MUMPS code strings that get XECUTE'd at
    runtime (e.g. ``X ^%ZOSF("TEST")`` checks if routine X exists).

    Without ^%ZOSF, FileMan routines that reference it either error out or
    take the wrong code path:
    - DII.m ``OS`` label reads ``^%ZOSF("OS")`` to set DISYS (system type)
    - DMUFINIT uses ``^%ZOSF("TEST")`` to check routine existence
    - DMUFINIS/DIINIS check ``^%ZOSF("UCI")`` / ``^%ZOSF("PROD")``
    - DDGLIBP uses ``^%ZOSF("RM")`` for terminal width

    Values sourced from ZOSFGUX.m (GT.M for Unix, the YDB-compatible
    variant).  Only entries referenced by FileMan and commonly-used Kernel
    routines are included — esoteric magtape/device entries are omitted.
    """
    # All values from ZOSFGUX.m Z-section $TEXT table, with "OS" from the
    # explicit SET after the table loop.
    #
    # Format: Each value is the literal string that VistA stores in the
    # global.  Many are MUMPS code intended for XECUTE (e.g. TEST, UCI,
    # TRAP).  Some are plain data values (e.g. OS, PROD, VOL, MGR, TMP).
    zosf_entries = {
        # --- Critical for FileMan ---
        # DII.m OS label: I $D(^%ZOSF("OS"))#2 S DISYS=+$P(^("OS"),"^",2)
        # DISYS=19 selects GT.M/Unix code paths throughout FileMan
        "OS": "GT.M (Unix)^19",
        # Routine existence test: I X]"",$T(^@X)]""
        # Used by DMUFINIT, DIINIT, DINTEG, DMUFINIS, etc.
        "TEST": 'I X]"",$T(^@X)]""',
        # UCI (User Class Identifier): S Y=^%ZOSF("PROD")
        # Referenced by DMUFINIS, DIINIS, DIDC, DMSQP6, DIDH1, DIWE4
        "UCI": 'S Y=^%ZOSF("PROD")',
        # UCI validation — always returns true (Y=1)
        "UCICHECK": "S Y=1",
        # Production UCI,VOL — referenced by UCI code above and DMUFINIS
        "PROD": "VAH,ROU",
        # Volume set name
        "VOL": "ROU",
        # Manager UCI,VOL
        "MGR": "VAH,ROU",
        # Terminal width: U $I:WIDTH=$S(X<256:X,1:0)
        # Referenced by DDGLIBP (FileMan screen library)
        "RM": "U $I:WIDTH=$S(X<256:X,1:0)",
        # Error trap setup: $ZT="G "_X
        "TRAP": '$ZT="G "_X',
        # Error routine name
        "ERRTN": "^%ZTER",
        # Uppercase conversion
        "UPPERCASE": 'S Y=$TR(X,"abcdefghijklmnopqrstuvwxyz",'
        '"ABCDEFGHIJKLMNOPQRSTUVWXYZ")',
        # --- I/O control ---
        "EOFF": "U $I:(NOECHO)",
        "EON": "U $I:(ECHO)",
        "TRMOFF": 'U $I:(TERMINATOR="")',
        "TRMON": "U $I:(TERMINATOR=$C(0,1,2,3,4,5,6,7,8,9,10,11,12,13,"
        "14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,127))",
        # --- Routine management ---
        # Routine load (used by LOAD command in FileMan)
        "LOAD": "D LOAD^%ZOSV2(X)",
        # Routine checksum — used by DINTEG
        "RSUM": 'S Y=0 F %=1,3:1 S %1=$T(+%^@X),%3=$F(%1," ") '
        'Q:\'%3  S %3=$S($E(%1,%3)\'=";":$L(%1),$E(%1,%3+1)=";":'
        "$L(%1),1:%3-2) F %2=1:1:%3 S Y=$A(%1,%2)*%2+Y",
        # Routine selection
        "RSEL": 'K ^UTILITY($J) D ^%RSEL S X="" '
        'X "F  S X=$O(%ZR(X)) Q:X=""""  '
        'S ^UTILITY($J,X)=""""" K %ZR',
        # --- Misc ---
        "TMP": "/tmp/",
        "XY": "S $X=DX,$Y=DY",
        "SAVE": "D SAVE^%ZOSV2(X)",
        "PROGMODE": "S Y=$$PROGMODE^%ZOSV()",
        "PRIORITY": "Q",
        "LPC": 'S Y=""',
        "MAXSIZ": "Q",
        "ETRP": "Q",
        "BRK": "U $I:(CENABLE)",
        "NBRK": "U $I:(NOCENABLE)",
        "TYPE-AHEAD": "U $I:(TYPEAHEAD)",
        "NO-TYPE-AHEAD": "U $I:(NOTYPEAHEAD)",
    }

    g = rt.globals
    for key, value in zosf_entries.items():
        g.set("%ZOSF", (key,), value)

    logger.info("Bootstrapped ^%%ZOSF with %d entries", len(zosf_entries))


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
    - %ZISH (transpiled from ZISHGUX.m)
    """
    _register_fileman_dependencies()


@pytest.fixture(scope="session")
def scheduling_library(munit_framework, fileman_bootstrap):
    """Load Scheduling and Registration dependency routines (Tier 4b).

    Extends the auto-importer with Scheduling, Registration, and VEHU-M
    directories so that SDK APIs (``SDAMA*``), management APIs
    (``SDMAPI*``), Registration utilities (``VADPT*``), and any other
    transitive dependencies resolve on demand.

    Requires:
    - M-Unit framework loaded (for cross-routine call resolution)
    - FileMan bootstrap (``^DD``, ``^DIC``) for routines that reference
      the data dictionary
    """
    # Expand the auto-importer with Scheduling, Registration, and VEHU-M
    # directories.  _install_auto_importer ensures the base importer exists;
    # add_dirs extends it with package-specific source trees.
    _install_auto_importer()
    _register_fileman_dependencies()
    assert _auto_importer is not None
    _auto_importer.add_dirs(
        [
            _VISTA_M_SCHEDULING_DIR,
            _VISTA_M_REGISTRATION_DIR,
            _SCHED_TESTING_DIR,
            _VEHU_M_SCHEDULING_DIR,
            _VEHU_M_REGISTRATION_DIR,
        ]
    )

    # Pre-load XLFDT, XLFSTR (Kernel utilities used by Scheduling tests)
    _try_load_routine(_VISTA_M_KERNEL_DIR / "XLFDT.m", "XLFDT")
    _try_load_routine(_VISTA_M_KERNEL_DIR / "XLFSTR.m", "XLFSTR")


@pytest.fixture(scope="session")
def registration_library(scheduling_library, munit_runtime):
    """Load Registration dependency routines (Tier 4c).

    Relies on ``scheduling_library`` which already extends the auto-importer
    with Registration and VEHU-M directories.  Adds the Registration MUnit
    testing directory so the ZZDGPTCO1 test routine resolves on import.

    Seeds ``^DG(45.86)`` (PTF CENSUS DATE) fixture data required by
    ZZDGPTCO1's ``GETDGIEN`` subroutine.  Record 22 is set as the active
    census date so that ``GETDGIEN`` returns 22 and ``NEWDGIEN`` = 23.
    """
    assert _auto_importer is not None
    _auto_importer.add_dirs([_REG_TESTING_DIR])

    # Kill ^DG(45.86) first to ensure clean state.  On backends with
    # persistent globals (YDB, IRIS) stale data from previous runs can
    # accumulate when TROLLBACK is skipped after an error inside
    # CHKCUR^DGPTCO1, causing phantom extra tests and cascading failures.
    g = munit_runtime.globals
    g.kill("DG", ("45.86",))

    # Seed ^DG(45.86) — ZZDGPTCO1 expects GETDGIEN to return 22.
    # GETDGIEN logic:
    #   S DGIEN=$S($D(^DG(45.86,+$O(^DG(45.86,"AC",1,0)),0)):+^(0),1:"")
    #   S DGIEN=$O(^DG(45.86,"B",+$G(DGIEN),0))
    # → needs AC,1 → IEN 22 → 0-node with +^(0)=22 → B,22,22
    g.set("DG", ("45.86", "0"), "PTF CENSUS DATE^45.86D^22^22")
    g.set("DG", ("45.86", "22", "0"), "22^^^1^")
    g.set("DG", ("45.86", "AC", "1", "22"), "")
    g.set("DG", ("45.86", "B", "22", "22"), "")


@pytest.fixture(scope="session")
def problem_list_library(scheduling_library, munit_runtime):
    """Load Problem List dependency routines (Tier 5).

    Extends the auto-importer with ALL VistA-VEHU-M package Routines
    directories.  ZZRGUTEX's STARTUP creates a patient via UPDATE^DIE which
    triggers cross-references spanning dozens of VistA packages (Income
    Verification Match, ODS, Scheduling, etc.).  Adding all package
    directories ensures every transitive dependency resolves on demand.

    Seeds minimal ``^SC`` (hospital location) and ``^VA(200,...)`` (user)
    globals so STARTUP's ``CHECKAV^XUSRB`` and clinic lookup work.
    """
    assert _auto_importer is not None

    # Add all VistA-VEHU-M package Routines directories plus the testing dir.
    all_package_routine_dirs = sorted(
        d
        for d in _VISTA_M_PACKAGES_DIR.iterdir()
        if d.is_dir() and (d / "Routines").is_dir()
    )
    _auto_importer.add_dirs(
        [_PROBLEM_LIST_TESTING_DIR] + [d / "Routines" for d in all_package_routine_dirs]
    )

    g = munit_runtime.globals

    # Load ICD, Lexicon, and Provider Narrative fixture data.
    # ZZRGUTEX uses ICD-10-CM code E23.0 (Hypopituitarism, IEN 503192)
    # and Lexicon term 7133461.  CREATE^GMPLUTL validates both via
    # $$ICDDATA^ICDXCODE and $D(^LEX(757.01,...)).  Without this data,
    # the validation fails with "Invalid ICD Diagnosis".
    from m2py.runtime.zwr import import_zwr

    pl_fixtures = _GLOBALS_DIR / "problem_list_fixtures.zwr"
    if pl_fixtures.exists():
        count = import_zwr(g, pl_fixtures)
        logger.info("Loaded %d Problem List fixture globals (ICD/LEX/AUTNPOV)", count)

    # OUTPUT^PXRMPROB calls $$CSYS^LEXU("10D") and $$CSDATA^LEXU("E23.0")
    # to populate clinical maintenance text.  The full Lexicon data (757.02,
    # 757.03) is now included in problem_list_fixtures.zwr.  NEW^GMPLSAVE
    # also calls $$IMPDATE^LEXU("10D") which reaches GET1^DIQ(757.03,30,11)
    # so ^DD(757.03) and ^DIC(757.03) metadata must be present.
    g.set("DD", ("757.03", "0"), "FIELD^^12^11")
    g.set(
        "DD",
        ("757.03", "11", "0"),
        'IMPLEMENTATION DATE^D^^2;1^S %DT="E" D ^%DT S X=Y K:X<1 X',
    )
    g.set("DD", ("757.03", "GL", "2", "1", "11"), "")
    g.set("DIC", ("757.03", "0"), "CODING SYSTEMS^757.03I")
    g.set("DIC", ("757.03", "0", "GL"), "^LEX(757.03,")

    # Seed ^SC — ZZRGUTEX STARTUP does:
    #   S GMPCLIN=$O(^SC("B","VISTA HEALTH CARE",""))_"^VISTA HEALTH CARE"
    # Needs a "B" cross-reference entry pointing to an IEN.
    # Piece 3 = "C" marks it as a clinic (LOCATION^GMPLUTL1 checks this).
    g.set("SC", ("1", "0"), "VISTA HEALTH CARE^^C")
    g.set("SC", ("B", "VISTA HEALTH CARE", "1"), "")

    # Seed ^VA(200,...) — CHECKAV^XUSRB does an access/verify code lookup.
    # CHECKAV^XUS uppercases the input, then hashes via $$EN^XUSHSH.
    # In the OSEHRA release, XUSHSH's KE subroutine is redacted (identity
    # function), so the "hash" is just the uppercase plaintext.
    #
    # Input: "fakedoc1;1Doc!@#$" → UP → "FAKEDOC1;1DOC!@#$"
    # Access = "FAKEDOC1", Verify = "1DOC!@#$"
    #
    # CHECKAV looks up: ^VA(200,"A",accessHash,IEN) for the "A" xref,
    # then checks $P(^VA(200,IEN,.1),"^",2) = verifyHash.
    g.set("VA", ("200", "0"), "NEW PERSON^200^1^1")
    g.set("VA", ("200", "1", "0"), "FAKEDOC,ONE^FD1")
    g.set("VA", ("200", "1", ".1"), "FAKEDOC1^1DOC!@#$")
    g.set("VA", ("200", "1", "2"), "FD1")
    g.set("VA", ("200", "B", "FAKEDOC,ONE", "1"), "")
    # Access code "A" cross-reference (hashed uppercase access code)
    g.set("VA", ("200", "A", "FAKEDOC1", "1"), "")
    # DUZ^XUS1A reads piece 17 of XOPT for division (DUZ(2)).
    # XOPT starts from ^XTV(8989.3,1,"XUS"), then overlays pieces 4-7,9,10,19
    # from ^VA(200,DUZ,200).  Piece 17 only comes from ^XTV.
    # Seed institution IEN 1 as the default division.
    # ^XTV piece 17 = division/institution IEN
    xus_val = "^" * 16 + "1"  # piece 17 = "1"
    g.set("XTV", ("8989.3", "1", "XUS"), xus_val)
    # ^DIC(4,1,...) — Institution file (for DUZ("AG") lookup)
    g.set("DIC", ("4", "0"), "INSTITUTION^4^1^1")
    g.set("DIC", ("4", "1", "0"), "TEST FACILITY^1")
    g.set("DIC", ("4", "1", "99"), "^^^^VA")

    # ^DIC(2,...) — Patient file header (needed by UPDATE^DIE for file 2)
    g.set("DIC", ("2", "0"), "PATIENT^2^0^0")
    g.set("DIC", ("2", "0", "GL"), "^DPT(")

    # ^DIC(9000011,...) — Problem file header (for AUPNPROB references)
    g.set("DIC", ("9000011", "0"), "PROBLEM^9000011^0^0")
    g.set("DIC", ("9000011", "0", "GL"), "^AUPNPROB(")

    # ^AUPNPROB(0) — File header for problem file.
    # NEWPROB^GMPLSAVE reads this: pieces 3=LAST IEN, 4=TOTAL count.
    g.set("AUPNPROB", ("0",), "PROBLEM^9000011^0^0")

    # ^GMPL(125.99,1,0) — Problem List site parameters.
    # Piece 2: verification (1=require),  Piece 5: sort order,
    # Piece 6: duplicate checking (1=on).  Keep simple defaults.
    g.set("GMPL", ("125.99", "1", "0"), "^1")

    # Person class data for provider validation.
    # $$ACTIVPRV^PXAPI → $$PRVCLASS^PXAPIUTL → $$GET^XUA4A72 → GETUE
    # checks ^VA(200,DUZ,"USC1",...) and ^USC(8932.1,...).
    # Without this, PROBLEM^PXCAPL and DIAG^PXCAPOV error with
    # "Provider is not active or valid".
    g.set("VA", ("200", "1", "USC1", "1", "0"), "1^3120101^")
    g.set("VA", ("200", "1", "USC1", "AD", "3120101", "1"), "")
    g.set("USC", ("8932.1", "1", "0"), "PHYSICIAN^MEDICAL^")

    # ^DD(9000011,...) — Data Dictionary for PROBLEM file.
    # FILE^DIE (EN^GMPLSAVE) needs ^DD to locate field storage (node;piece)
    # and validate SET-OF-CODES values.  $$EXTERNAL^DILFD also uses ^DD
    # to convert internal codes to external display (e.g. "A" → "ACTIVE").
    g.set("DD", ("9000011", "0"), "FIELD^^80300^39")
    g.set("DD", ("9000011", "0", "NM", "PROBLEM"), "")
    # .01 field (DIAGNOSIS) — VFILE^DIEFU checks ^DD(F,.01,0) piece 2 is
    # not empty; without this, FILE^DIE skips the entire file.
    g.set(
        "DD",
        ("9000011", ".01", "0"),
        "DIAGNOSIS^R*P80'^ICD9(^0;1^Q",
    )
    # STATUS field (.12): SET-OF-CODES A:ACTIVE;I:INACTIVE, stored node 0 piece 12
    g.set("DD", ("9000011", ".12", "0"), "STATUS^RS^A:ACTIVE;I:INACTIVE;^0;12^Q")
    # ACTIVE cross-reference trigger (fired by FILE^DIE on STATUS change)
    g.set("DD", ("9000011", ".12", "1", "0"), "^.1")
    g.set("DD", ("9000011", ".12", "1", "1", "0"), "9000011^ACTIVE^MUMPS")
    g.set(
        "DD",
        ("9000011", ".12", "1", "1", "1"),
        'S:$P(^AUPNPROB(DA,0),U,2) ^AUPNPROB("ACTIVE",+$P(^(0),U,2),X,DA)=""',
    )
    g.set(
        "DD",
        ("9000011", ".12", "1", "1", "2"),
        'K ^AUPNPROB("ACTIVE",+$P(^AUPNPROB(DA,0),U,2),X,DA)',
    )
    # CONDITION field (1.02): SET-OF-CODES, stored node 1 piece 2
    g.set(
        "DD",
        ("9000011", "1.02", "0"),
        "CONDITION^S^T:TRANSCRIBED;P:PERMANENT;H:HIDDEN;^1;2^Q",
    )
    # PRIORITY field (1.14): SET-OF-CODES, stored node 1 piece 14
    # Used by $$EXTERNAL^DILFD in OUTPUT^PXRMPROB
    g.set("DD", ("9000011", "1.14", "0"), "PRIORITY^S^A:ACUTE;C:CHRONIC;^1;14^Q")


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
            logger.debug("unlock_all failed in teardown", exc_info=True)
