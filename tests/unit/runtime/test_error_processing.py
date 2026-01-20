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


class TestExceptionToEcode:
    """Tests for _exception_to_ecode() method (Spec 014 T055)."""

    def test_zero_division_error(self):
        """ZeroDivisionError maps to M9 (divide by zero)."""
        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(ZeroDivisionError()) == ",M9,"

    def test_key_error(self):
        """KeyError maps to M6 (undefined local variable)."""
        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(KeyError("X")) == ",M6,"

    def test_generic_runtime_error(self):
        """Generic RuntimeError maps to Z150373210."""
        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(RuntimeError("unknown")) == ",Z150373210,"

    def test_naked_error_in_message(self):
        """RuntimeError with 'naked' in message maps to M1."""
        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(RuntimeError("NAKEDERR")) == ",M1,"
        assert rt._exception_to_ecode(RuntimeError("naked reference error")) == ",M1,"

    def test_tcommit_error(self):
        """RuntimeError with TCOMMIT/M44 maps to M44."""
        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(RuntimeError("M44")) == ",M44,"
        assert rt._exception_to_ecode(RuntimeError("TCOMMIT without TSTART")) == ",M44,"

    def test_mruntimeerror_selectfalse(self):
        """MRuntimeError(SELECTFALSE) maps to M4."""
        from m2py.runtime.exceptions import MRuntimeError

        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(MRuntimeError("SELECTFALSE")) == ",M4,"

    def test_mruntimeerror_randargneg(self):
        """MRuntimeError(RANDARGNEG) maps to M28."""
        from m2py.runtime.exceptions import MRuntimeError

        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(MRuntimeError("RANDARGNEG")) == ",M28,"

    def test_mruntimeerror_unknown_code(self):
        """Unknown MRuntimeError code uses Z prefix."""
        from m2py.runtime.exceptions import MRuntimeError

        rt = MUMPSRuntime()
        assert rt._exception_to_ecode(MRuntimeError("FOOBAR")) == ",ZFOOBAR,"


class TestHandleEtrap:
    """Tests for _handle_etrap() method (Spec 014 T055)."""

    def test_no_etrap_returns_false(self):
        """Without $ETRAP set, returns False (propagate exception)."""
        rt = MUMPSRuntime()
        scope = {}
        assert rt._handle_etrap(ZeroDivisionError(), scope) is False
        # $ECODE should not be set when there's no handler
        assert rt.ecode() == ""

    def test_etrap_clears_ecode_returns_true(self):
        '''$ETRAP that clears $ECODE returns True (error handled).

        MUMPS: S $ETRAP="S $ECODE=""""
        '''
        rt = MUMPSRuntime()
        rt.set_etrap('S $ECODE=""')
        scope = {}
        result = rt._handle_etrap(ZeroDivisionError(), scope)
        assert result is True
        assert rt.ecode() == ""

    def test_etrap_preserves_ecode_returns_false(self):
        """$ETRAP that doesn't clear $ECODE returns False (propagate).

        MUMPS: S $ETRAP="W \"Logged\""  ; Doesn't clear $ECODE
        """
        rt = MUMPSRuntime()
        rt.set_etrap('W "Logged"')  # Doesn't clear $ECODE
        scope = {}
        result = rt._handle_etrap(ZeroDivisionError(), scope)
        assert result is False
        assert rt.ecode() == ",M9,"  # Set but not cleared

    def test_etrap_sets_ecode_from_exception(self):
        """$ETRAP execution sets $ECODE based on exception type."""
        rt = MUMPSRuntime()
        rt.set_etrap("Q")  # Does nothing, $ECODE stays set
        scope = {}
        rt._handle_etrap(KeyError("X"), scope)
        assert rt.ecode() == ",M6,"

    def test_etrap_sets_zerror(self):
        """$ETRAP execution sets $ZERROR to exception message."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $ECODE=""')
        scope = {}
        rt._handle_etrap(ValueError("custom error message"), scope)
        assert rt.zerror() == "custom error message"

    def test_etrap_can_access_scope(self):
        '''$ETRAP code can access and modify scope variables.

        MUMPS: S $ETRAP="S HANDLED=1 S $ECODE=""""
        '''
        rt = MUMPSRuntime()
        rt.set_etrap('S HANDLED=1 S $ECODE=""')
        scope = {}
        result = rt._handle_etrap(ZeroDivisionError(), scope)
        assert result is True
        # The $ETRAP code should have set HANDLED in scope
        assert "HANDLED" in scope
        assert scope["HANDLED"].value == 1

    def test_etrap_error_in_handler_returns_false(self):
        """Error in $ETRAP itself returns False (propagate original).

        If $ETRAP code itself causes an error, we propagate the original.
        """
        rt = MUMPSRuntime()
        # This will cause a syntax error in execute_mumps
        rt.set_etrap("INVALID CODE {{{")
        scope = {}
        result = rt._handle_etrap(ZeroDivisionError(), scope)
        assert result is False
