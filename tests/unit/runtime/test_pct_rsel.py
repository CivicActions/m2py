"""Tests for %RSEL stub routine.

Verifies that the bundled _pct_RSEL module provides a working stub for
GT.M/YDB's %RSEL routine selection utility. In m2py, no on-disk M routines
exist, so %RSEL should return an empty %ZR (matching YDB behavior when no
routines match the search pattern).
"""

from m2py.runtime import MUMPSRuntime, MArray


class TestRSELModule:
    """_pct_RSEL module has expected structure."""

    def test_module_importable(self):
        """_pct_RSEL can be imported from m2py.runtime.routines."""
        from m2py.runtime.routines import _pct_RSEL

        assert hasattr(_pct_RSEL, "SILENT")
        assert hasattr(_pct_RSEL, "_entry_function")

    def test_has_routine_name(self):
        """Module has _routine_name = '%RSEL'."""
        from m2py.runtime.routines import _pct_RSEL

        assert _pct_RSEL._routine_name == "%RSEL"

    def test_has_label_lines(self):
        """Module has _label_lines mapping."""
        from m2py.runtime.routines import _pct_RSEL

        assert "SILENT" in _pct_RSEL._label_lines

    def test_entry_function_is_pct_rsel(self):
        """_entry_function points to the main entry point."""
        from m2py.runtime.routines import _pct_RSEL

        assert _pct_RSEL._entry_function is _pct_RSEL._pct_RSEL


class TestSILENT:
    """SILENT^%RSEL kills %ZR and returns."""

    def test_silent_kills_pct_zr(self):
        """SILENT^%RSEL removes %ZR from scope."""
        from m2py.runtime.routines._pct_RSEL import SILENT

        rt = MUMPSRuntime()
        scope = {"_pct_ZR": MArray()}
        scope["_pct_ZR"]["foo"] = "bar"
        SILENT(rt, "NMSP*", "SRC", _scope=scope)
        assert "_pct_ZR" not in scope

    def test_silent_noop_when_no_zr(self):
        """SILENT^%RSEL handles missing %ZR gracefully."""
        from m2py.runtime.routines._pct_RSEL import SILENT

        rt = MUMPSRuntime()
        scope = {}
        SILENT(rt, "NMSP*", "SRC", _scope=scope)
        assert "_pct_ZR" not in scope

    def test_silent_with_no_args(self):
        """SILENT^%RSEL works with no arguments."""
        from m2py.runtime.routines._pct_RSEL import SILENT

        rt = MUMPSRuntime()
        SILENT(rt, _scope={})

    def test_silent_preserves_other_scope_vars(self):
        """SILENT^%RSEL only touches %ZR, leaves other vars intact."""
        from m2py.runtime.routines._pct_RSEL import SILENT

        rt = MUMPSRuntime()
        scope = {"X": MArray(), "_pct_ZR": MArray()}
        scope["X"].value = "keep"
        SILENT(rt, "test*", "SRC", _scope=scope)
        assert "X" in scope
        assert scope["X"].value == "keep"
        assert "_pct_ZR" not in scope


class TestEntryFunction:
    """D ^%RSEL (argumentless DO) uses _entry_function."""

    def test_entry_function_kills_zr(self):
        """D ^%RSEL kills %ZR."""
        from m2py.runtime.routines._pct_RSEL import _entry_function

        rt = MUMPSRuntime()
        scope = {"_pct_ZR": MArray()}
        _entry_function(rt, _scope=scope)
        assert "_pct_ZR" not in scope


class TestViewTrace:
    """VIEW 'TRACE' is a no-op in generated code."""

    def test_view_trace_generates_noop(self):
        """VIEW 'TRACE':1:expr generates pass comment."""
        from m2py.codegen import generate_python

        code = generate_python('TEST\n VIEW "TRACE":1\n Q\n')
        assert "pass" in code
        assert "VIEW" in code

    def test_view_trace_stop_generates_noop(self):
        """VIEW 'TRACE':0:expr generates pass comment."""
        from m2py.codegen import generate_python

        code = generate_python('TEST\n VIEW "TRACE":0\n Q\n')
        assert "pass" in code
