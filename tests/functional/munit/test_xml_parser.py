"""Tier 2: M XML Parser test routines (MXMLBLD, MXMLTMPT, MXMLPATT, MXMLDOMT).

Transpiles each M XML Parser test routine via m2py, executes it through
``EN^%ut``, and classifies the result.

Test routines and their status:

- **MXMLBLD** (13 assertions): XML Builder — fully passing
- **MXMLTMPT** (49 assertions): XML Templates — fully passing.
  Dependencies loaded from VistA-M (MXMLTMP1, MXMLTMPL,
  DDIOL, DICRW, DIALOG, etc.)
- **MXMLPATT** (25 tests): XML Path — fully passing.
  Dependencies loaded (MXMLPATH, %ZOSV, DIALOG globals).
- **MXMLDOMT** (9 tests): XML DOM Parser — fully passing.
  File I/O via ``%ZISH`` provided by transpiled ZISHGUX.m.

Library routines are loaded from VistA-M via the
``mxml_library`` session fixture defined in conftest.py.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.helpers import assert_munit_pass, make_test_config, vista_testing_dir

_TESTING_DIR = vista_testing_dir("M XML Parser")

# ---------------------------------------------------------------------------
# TestList routines  (from VistA/Packages/M XML Parser/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

TIER2_ROUTINES = [
    "MXMLBLD",
    "MXMLTMPT",
    "MXMLPATT",
    "MXMLDOMT",
]

# Invocation patterns from the TestList file
_INVOCATIONS = {
    "MXMLBLD": "D TEST^MXMLBLD",
    "MXMLTMPT": "D TEST^MXMLTMPT",
    "MXMLPATT": "D TEST^MXMLPATT",
    "MXMLDOMT": "D ^MXMLDOMT",
}


@pytest.mark.slow
@pytest.mark.munit
@pytest.mark.usefixtures("mxml_library")
class TestMXMLParser:
    """Run M XML Parser test routines through the transpiled M-Unit framework."""

    @pytest.mark.parametrize("routine_name", TIER2_ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one M XML Parser test routine."""
        config = make_test_config(
            routine_name,
            package_name="M XML Parser",
            tier=2,
            testing_dir=_TESTING_DIR,
            invocation=_INVOCATIONS[routine_name],
        )
        result = transpile_and_execute(config, munit_runtime)
        assert_munit_pass(result, routine_name)
