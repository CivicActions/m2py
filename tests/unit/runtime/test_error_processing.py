"""Tests for runtime error processing support.

Spec 013 Phase 12: Tests for $ECODE, $ETRAP, $ZERROR runtime implementation.

Reference: MUMPS 1995 ANSI Standard, Sections 6.3.2 and 7.1.4.10
"""

from m2py.runtime import MUMPSRuntime, MArray
from m2py.runtime.helpers import NewScopeManager


class TestErrorProcessingRuntime:
    """Runtime tests for error processing special variables."""

    def test_ecode_initial_value(self):
        """$ECODE starts as empty string.

        Spec 013 Phase 12 (FR-026): No active errors means $ECODE="".
        """
        rt = MUMPSRuntime()
        assert rt.ecode() == ""

    def test_ecode_set_and_get(self):
        """$ECODE can be set and retrieved.

        Spec 013 Phase 12: SET $ECODE=",M6," stores error code.
        """
        rt = MUMPSRuntime()
        rt.set_ecode(",M6,")
        assert rt.ecode() == ",M6,"

    def test_ecode_clear(self):
        """$ECODE can be cleared by setting to empty.

        Spec 013 Phase 12: SET $ECODE="" clears errors.
        """
        rt = MUMPSRuntime()
        rt.set_ecode(",M6,")
        rt.set_ecode("")
        assert rt.ecode() == ""

    def test_etrap_initial_value(self):
        """$ETRAP starts as empty string.

        Spec 013 Phase 12 (FR-026): No error trap initially.
        """
        rt = MUMPSRuntime()
        assert rt.etrap() == ""

    def test_etrap_set_and_get(self):
        """$ETRAP can be set and retrieved.

        Spec 013 Phase 12: SET $ETRAP="D ERR^ROUTINE" sets handler.
        """
        rt = MUMPSRuntime()
        rt.set_etrap("D ERR^ROUTINE")
        assert rt.etrap() == "D ERR^ROUTINE"

    def test_zerror_initial_value(self):
        """$ZERROR starts as empty string.

        Spec 013 Phase 12 (FR-045): No error message initially.
        """
        rt = MUMPSRuntime()
        assert rt.zerror() == ""

    def test_zerror_set_and_get(self):
        """$ZERROR can be set and retrieved.

        Spec 013 Phase 12: SET $ZERROR="Error message" sets message.
        """
        rt = MUMPSRuntime()
        rt.set_zerror("Error in module XYZ")
        assert rt.zerror() == "Error in module XYZ"


class TestNewScopeManagerSpecialVars:
    """Tests for NEW special variable support in NewScopeManager."""

    def test_new_etrap_saves_and_restores(self):
        """NEW $ETRAP saves value and restores on exit.

        Spec 013 Phase 12: VistA pattern N $ETRAP S $ETRAP="..."
        """
        rt = MUMPSRuntime()
        rt.set_etrap("D OUTER^ROUTINE")
        scope = {}

        with NewScopeManager(scope) as mgr:
            # Save current etrap and clear it
            mgr.new_special_var("etrap", rt.etrap(), rt.set_etrap)
            assert rt.etrap() == ""  # NEW clears it
            # Set new value
            rt.set_etrap("D INNER^ROUTINE")
            assert rt.etrap() == "D INNER^ROUTINE"

        # After scope exit, original value restored
        assert rt.etrap() == "D OUTER^ROUTINE"

    def test_new_ecode_saves_and_restores(self):
        """NEW $ECODE saves value and restores on exit.

        Spec 013 Phase 12: Save error state across subroutine calls.
        """
        rt = MUMPSRuntime()
        rt.set_ecode(",M6,")
        scope = {}

        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("ecode", rt.ecode(), rt.set_ecode)
            assert rt.ecode() == ""  # NEW clears it
            rt.set_ecode(",U1,")
            assert rt.ecode() == ",U1,"

        # After scope exit, original error state restored
        assert rt.ecode() == ",M6,"

    def test_new_special_var_only_once(self):
        """Duplicate NEW of same special var is no-op.

        First NEW wins - subsequent NEWs in same scope are ignored.
        """
        rt = MUMPSRuntime()
        rt.set_etrap("ORIGINAL")
        scope = {}

        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("etrap", rt.etrap(), rt.set_etrap)
            rt.set_etrap("FIRST")
            # Second NEW should be ignored
            mgr.new_special_var("etrap", rt.etrap(), rt.set_etrap)
            rt.set_etrap("SECOND")
            assert rt.etrap() == "SECOND"

        # Restore to ORIGINAL (first NEW saved it), not FIRST
        assert rt.etrap() == "ORIGINAL"

    def test_new_special_var_with_exception(self):
        """Special var restored even on exception.

        Spec 013 Phase 12: NEW semantics preserved on abnormal exit.
        """
        rt = MUMPSRuntime()
        rt.set_zerror("ORIGINAL")
        scope = {}

        try:
            with NewScopeManager(scope) as mgr:
                mgr.new_special_var("zerror", rt.zerror(), rt.set_zerror)
                rt.set_zerror("INSIDE")
                raise ValueError("test exception")
        except ValueError:
            pass

        # $ZERROR restored despite exception
        assert rt.zerror() == "ORIGINAL"

    def test_mixed_regular_and_special_vars(self):
        """Both regular vars and special vars work in same scope.

        VistA pattern: N X,$ETRAP S $ETRAP="...",X=1
        """
        rt = MUMPSRuntime()
        rt.set_etrap("ORIGINAL_ETRAP")
        scope = {"X": MArray(value=100)}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            mgr.new_special_var("etrap", rt.etrap(), rt.set_etrap)
            scope["X"] = MArray(value=999)
            rt.set_etrap("INNER_ETRAP")
            assert scope["X"].value == 999
            assert rt.etrap() == "INNER_ETRAP"

        # Both restored on exit
        assert scope["X"].value == 100
        assert rt.etrap() == "ORIGINAL_ETRAP"
