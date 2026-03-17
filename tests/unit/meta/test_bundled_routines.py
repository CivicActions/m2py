"""Tests for bundled routine discovery and registration.

Verifies:
- MumpsAutoImporter._is_bundled_routine() detects bundled routines
- _register_bundled_routines() populates sys.modules for transpiled imports
"""

import sys


class TestBundledRoutineFallback:
    """Auto-importer resolves bundled routines from m2py.runtime.routines."""

    def test_is_bundled_routine_true_for_pct_rsel(self):
        """_is_bundled_routine returns True for _pct_RSEL."""
        from tests.functional.munit.conftest import MumpsAutoImporter

        assert MumpsAutoImporter._is_bundled_routine("_pct_RSEL")

    def test_is_bundled_routine_true_for_math(self):
        """_is_bundled_routine returns True for MATH."""
        from tests.functional.munit.conftest import MumpsAutoImporter

        assert MumpsAutoImporter._is_bundled_routine("MATH")

    def test_is_bundled_routine_false_for_nonexistent(self):
        """_is_bundled_routine returns False for nonexistent modules."""
        from tests.functional.munit.conftest import MumpsAutoImporter

        assert not MumpsAutoImporter._is_bundled_routine("_pct_NONEXISTENT")
        assert not MumpsAutoImporter._is_bundled_routine("FAKE_MODULE")


class TestRegisterBundledRoutines:
    """_register_bundled_routines() populates sys.modules."""

    def test_registers_pct_rsel(self):
        """_pct_RSEL is importable after registration."""
        from tests.functional.munit.conftest import _register_bundled_routines

        # Remove from sys.modules if already loaded
        sys.modules.pop("_pct_RSEL", None)
        _register_bundled_routines()
        assert "_pct_RSEL" in sys.modules
        mod = sys.modules["_pct_RSEL"]
        assert hasattr(mod, "SILENT")
        assert mod._routine_name == "%RSEL"

    def test_registers_math(self):
        """MATH is importable after registration."""
        from tests.functional.munit.conftest import _register_bundled_routines

        sys.modules.pop("MATH", None)
        _register_bundled_routines()
        assert "MATH" in sys.modules

    def test_idempotent(self):
        """Calling _register_bundled_routines twice is safe."""
        from tests.functional.munit.conftest import _register_bundled_routines

        _register_bundled_routines()
        mod1 = sys.modules.get("_pct_RSEL")
        _register_bundled_routines()
        mod2 = sys.modules.get("_pct_RSEL")
        assert mod1 is mod2
