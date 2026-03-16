"""Tier 4c: Registration test routine (1 routine, 10 assertions).

Transpiles the Registration test routine via m2py, executes it through
``EN^%ut``, and verifies a clean pass.

- **ZZDGPTCO1** (10 assertions): patient combine via ``CHKCUR^DGPTCO1``

Dependencies (``DGPTCO1``, ``DICRW``, ``DIE``) are auto-loaded from VistA-M
via the ``MumpsAutoImporter`` and ``registration_library`` session fixture in
conftest.py.  ZZDGPTCO1's STARTUP calls ``DT^DICRW`` to set today's date,
which triggers the ``ADDREC`` path in ``CHKCUR^DGPTCO1`` — this exercises
the full FileMan ``DIE`` / ``UPDATE^DIE`` edit chain.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.helpers import assert_munit_pass, make_test_config, vista_testing_dir

_TESTING_DIR = vista_testing_dir("Registration")

# ---------------------------------------------------------------------------
# TestList routine (from VistA/Packages/Registration/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

ROUTINES = ["ZZDGPTCO1"]


@pytest.mark.slow
@pytest.mark.munit
@pytest.mark.usefixtures("registration_library")
class TestRegistration:
    """Run Registration test routines through the transpiled M-Unit framework."""

    @pytest.mark.parametrize("routine_name", ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one Registration test routine."""
        config = make_test_config(
            routine_name,
            package_name="Registration",
            tier=4,
            testing_dir=_TESTING_DIR,
        )
        result = transpile_and_execute(config, munit_runtime)
        assert_munit_pass(result, routine_name)
