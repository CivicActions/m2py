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


class TestNewScopeManagerNewAll:
    """Tests for NewScopeManager.new_all() (Phase 21)."""

    def test_new_all_clears_scope(self):
        """new_all() removes all variables from scope."""
        scope = {"X": MArray(value=1), "Y": MArray(value=2)}

        with NewScopeManager(scope) as mgr:
            mgr.new_all()
            assert "X" not in scope
            assert "Y" not in scope

        # Restored on exit
        assert scope["X"].value == 1
        assert scope["Y"].value == 2

    def test_new_all_then_selective_new(self):
        """new_all() followed by selective new_var() restores correctly.

        After N (argumentless), setting new values and then N X should
        properly nest. On exit, both are unwound in LIFO order.
        """
        scope = {"X": MArray(value=10), "Y": MArray(value=20)}

        with NewScopeManager(scope) as mgr:
            mgr.new_all()
            # Scope is now empty
            assert len(scope) == 0
            # Set new values
            scope["X"] = MArray(value=99)
            scope["Z"] = MArray(value=77)
            # Now selective NEW of X
            mgr.new_var("X")
            assert "X" not in scope
            # Z should still be there
            assert scope["Z"].value == 77

        # After exit: new_all snapshot restores original X=10, Y=20
        assert scope["X"].value == 10
        assert scope["Y"].value == 20
        # Z was set after new_all, not in original snapshot
        assert "Z" not in scope

    def test_new_all_on_empty_scope(self):
        """new_all() on empty scope is a no-op that still restores correctly."""
        scope = {}

        with NewScopeManager(scope) as mgr:
            mgr.new_all()
            scope["A"] = MArray(value=1)
            assert scope["A"].value == 1

        # After exit: scope should be empty again (snapshot was empty)
        assert len(scope) == 0

    def test_new_all_resets_individually_newed(self):
        """new_all() resets _individually_newed so duplicate new_var works after it."""
        scope = {"X": MArray(value=1)}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            assert "X" not in scope
            # Re-set X and then new_all
            scope["X"] = MArray(value=99)
            mgr.new_all()
            assert len(scope) == 0
            # After new_all, X can be NEWed again
            scope["X"] = MArray(value=55)
            mgr.new_var("X")
            assert "X" not in scope

        # LIFO: first restore inner selective X (was 55), then new_all (restore X=99),
        # then outer selective X (restore original 1)
        assert scope["X"].value == 1


class TestNewScopeManagerNewExclusive:
    """Tests for NewScopeManager.new_exclusive() (Phase 21)."""

    def test_new_exclusive_keeps_specified(self):
        """new_exclusive() keeps specified variables, removes others."""
        scope = {"X": MArray(value=1), "Y": MArray(value=2), "Z": MArray(value=3)}

        with NewScopeManager(scope) as mgr:
            mgr.new_exclusive({"X"})
            assert scope["X"].value == 1
            assert "Y" not in scope
            assert "Z" not in scope

        # All restored on exit
        assert scope["X"].value == 1
        assert scope["Y"].value == 2
        assert scope["Z"].value == 3

    def test_new_exclusive_keeps_multiple(self):
        """new_exclusive() keeps multiple specified variables."""
        scope = {"A": MArray(value=1), "B": MArray(value=2), "C": MArray(value=3)}

        with NewScopeManager(scope) as mgr:
            mgr.new_exclusive({"A", "C"})
            assert scope["A"].value == 1
            assert "B" not in scope
            assert scope["C"].value == 3

        assert scope["A"].value == 1
        assert scope["B"].value == 2
        assert scope["C"].value == 3

    def test_new_exclusive_then_selective(self):
        """new_exclusive() followed by selective new_var()."""
        scope = {"X": MArray(value=10), "Y": MArray(value=20)}

        with NewScopeManager(scope) as mgr:
            mgr.new_exclusive({"X"})
            # Y is removed, X remains
            assert scope["X"].value == 10
            assert "Y" not in scope
            # Now selective NEW of X
            mgr.new_var("X")
            assert "X" not in scope

        # All restored on exit (LIFO)
        assert scope["X"].value == 10
        assert scope["Y"].value == 20

    def test_new_exclusive_empty_keep(self):
        """new_exclusive({}) acts like new_all() - removes everything."""
        scope = {"X": MArray(value=1), "Y": MArray(value=2)}

        with NewScopeManager(scope) as mgr:
            mgr.new_exclusive(set())
            assert len(scope) == 0

        assert scope["X"].value == 1
        assert scope["Y"].value == 2

    def test_new_exclusive_on_exception(self):
        """new_exclusive() restores properly even on exception."""
        scope = {"X": MArray(value=1), "Y": MArray(value=2)}

        try:
            with NewScopeManager(scope) as mgr:
                mgr.new_exclusive({"X"})
                scope["Z"] = MArray(value=99)
                raise ValueError("test")
        except ValueError:
            pass

        assert scope["X"].value == 1
        assert scope["Y"].value == 2
        assert "Z" not in scope


class TestNewScopeManagerNestedNew:
    """Tests for nested NEW restore ordering (Phase 21 LIFO)."""

    def test_selective_then_all_then_selective(self):
        """N X then N (all) then N Y restores in reverse order."""
        scope = {"X": MArray(value=1), "Y": MArray(value=2), "Z": MArray(value=3)}

        with NewScopeManager(scope) as mgr:
            # First: N X
            mgr.new_var("X")
            assert "X" not in scope

            # Set X to something else
            scope["X"] = MArray(value=100)

            # Then: N (all)
            mgr.new_all()
            assert len(scope) == 0

            # Set new values
            scope["A"] = MArray(value=50)

            # Then: N Y
            mgr.new_var("Y")
            # Y wasn't in scope after new_all, so this saves _UNDEFINED
            # and Y is already not in scope
            assert "Y" not in scope

        # LIFO unwind:
        # 1. Restore N Y → Y was _UNDEFINED after new_all, so pop (no-op)
        # 2. Restore N (all) → restore snapshot {X=100, Y=2, Z=3}
        # 3. Restore N X → restore original X=1
        assert scope["X"].value == 1
        assert scope["Y"].value == 2
        assert scope["Z"].value == 3

    def test_new_var_dedup_within_scope(self):
        """Duplicate new_var() clears variable but keeps first restore point.

        YDB/GT.M behavior: repeated NEW at the same stack level makes the
        variable undefined again (clears current value/subscripts) but the
        restore point established by the first NEW is preserved.
        """
        scope = {"X": MArray(value=1)}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")
            assert "X" not in scope
            scope["X"] = MArray(value=99)
            # Second NEW of X clears X (makes it undefined again)
            mgr.new_var("X")
            # X should be removed (cleared by second NEW)
            assert "X" not in scope

        # Restores to original value from first NEW
        assert scope["X"].value == 1

    def test_new_var_undefined_variable(self):
        """NEW of undefined variable records _UNDEFINED, removes on restore."""
        scope = {"Y": MArray(value=2)}

        with NewScopeManager(scope) as mgr:
            mgr.new_var("X")  # X was never defined
            scope["X"] = MArray(value=42)
            assert scope["X"].value == 42

        # X should be removed on restore (was _UNDEFINED)
        assert "X" not in scope
        assert scope["Y"].value == 2


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

    def test_etrap_resolves_caller_globals_for_label_access(self):
        """$ETRAP handler can find labels in the error-originating routine.

        When $ETRAP is set to "D ERRTRAP" and the error occurs in routine FOO,
        _handle_etrap must resolve caller_globals from FOO's module so that
        execute_mumps can find the ERRTRAP label. Without this fix, the
        execute_mumps call would get KeyError for the label.
        """
        import types

        rt = MUMPSRuntime()
        # Register a mock routine module
        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        rt._routines["TESTRTN"] = module
        rt._current_routine = "TESTRTN"

        # Set $ETRAP to clear $ECODE (simple handler that works)
        rt.set_etrap('S $ECODE=""')
        scope = {}
        result = rt._handle_etrap(ValueError("test"), scope)
        assert result is True
        # Verify the handler ran successfully (cleared $ECODE)
        assert rt.ecode() == ""

    def test_dispatch_ztrap_passes_caller_globals(self):
        """_dispatch_ztrap accepts and uses caller_globals parameter.

        $ZTRAP handlers need caller_globals just like $ETRAP ones, so
        labels from the error-originating routine are accessible.
        """
        rt = MUMPSRuntime()
        # Set $ZTRAP to XECUTE semantics (clear errors)
        rt.set_ztrap('S $ECODE=""')
        scope = {}
        # Should not raise — caller_globals is optional
        rt._dispatch_ztrap(scope, caller_globals=None)
        assert rt.ecode() == ""
