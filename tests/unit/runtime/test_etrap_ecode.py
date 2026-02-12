"""Unit tests for $ETRAP/$ECODE error handling (Phase 4: US2).

Tests:
- T014: $ECODE accumulation format (,M6,, ,M9,M6,, SET $ECODE="" clearing)
- T015: _handle_etrap() level-aware unwinding
- T016: NEW $ETRAP scoping and NEW $ESTACK
- T017: Nested error detection
"""

import pytest
from m2py.runtime import MUMPSRuntime
from m2py.core.exceptions import LVUNDEFError


class TestEcodeAccumulation:
    """T014: Tests for $ECODE accumulation format."""

    def test_first_error_single_code(self):
        """First error code should be wrapped with commas."""
        rt = MUMPSRuntime()
        assert rt.ecode() == ""
        rt._append_ecode("M6")
        assert rt.ecode() == ",M6,"

    def test_second_error_appends(self):
        """Second error code appends to existing."""
        rt = MUMPSRuntime()
        rt._append_ecode("M9")
        rt._append_ecode("M6")
        assert rt.ecode() == ",M9,M6,"

    def test_multiple_error_codes(self):
        """Multiple error codes accumulate in order."""
        rt = MUMPSRuntime()
        rt._append_ecode("M9")
        rt._append_ecode("M6")
        rt._append_ecode("Z150373850")
        assert rt.ecode() == ",M9,M6,Z150373850,"

    def test_set_ecode_empty_clears(self):
        """SET $ECODE="" clears all error codes."""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt._append_ecode("M9")
        assert rt.ecode() == ",M6,M9,"
        rt.set_ecode("")
        assert rt.ecode() == ""

    def test_set_ecode_clears_snapshot(self):
        """SET $ECODE="" also clears the stack snapshot."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", "TEST", "SUB", 1, "D SUB")
        rt._append_ecode("M6")
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        rt.set_ecode("")
        # Snapshot should be reset to None so next error can re-freeze
        assert rt._stack_snapshot is None

    def test_ydb_format_match(self):
        """$ECODE format matches YDB: ,M6,Z150373850,.

        YDB verified: S $ET="D ERR" ... W UNDEF → $ECODE=,M6,Z150373850,
        """
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt._append_ecode("Z150373850")
        assert rt.ecode() == ",M6,Z150373850,"

    def test_set_ecode_allows_refreeze_after_clear(self):
        """After SET $ECODE="", a new error can freeze a fresh snapshot."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", "TEST", "SUB1", 0, "")
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        assert len(rt._stack_snapshot) == 1

        # Clear $ECODE → resets snapshot to None
        rt.set_ecode("")
        assert rt._stack_snapshot is None

        # Push a second frame and re-freeze
        rt.push_stack_frame("DO", "TEST", "SUB2", 0, "")
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        assert len(rt._stack_snapshot) == 2  # Fresh snapshot with both frames


class TestHandleEtrapLevelUnwinding:
    """T015: Tests for _handle_etrap() level-aware unwinding."""

    def test_handle_etrap_without_etrap_set_returns_false(self):
        """If $ETRAP is empty, _handle_etrap returns False."""
        rt = MUMPSRuntime()
        scope = {}
        exc = ValueError("test error")
        result = rt._handle_etrap(exc, scope)
        assert result is False

    def test_handle_etrap_with_etrap_executes_code(self):
        """_handle_etrap executes $ETRAP code when set."""
        rt = MUMPSRuntime()
        # Set up a simple $ETRAP that clears $ECODE
        rt.set_etrap('S $EC=""')
        scope = {}
        exc = ValueError("test error")
        result = rt._handle_etrap(exc, scope)
        # The trap should execute and clear $ECODE
        assert result is True
        assert rt.ecode() == ""

    def test_etrap_set_level_tracked(self):
        """$ETRAP set level is tracked for unwinding.

        Level should correspond to the stack depth where $ETRAP was SET.
        """
        rt = MUMPSRuntime()
        assert rt._etrap_set_level == 0

        rt.push_stack_frame("DO", "TEST", "MAIN", 0, "D SUB")
        rt.push_stack_frame("DO", "TEST", "SUB", 0, "D INNER")

        rt.set_etrap('S $EC=""')
        # Level should equal current stack depth (2 frames)
        assert rt._etrap_set_level == 2

    def test_etrap_set_level_at_different_depths(self):
        """$ETRAP set at depth 0 vs depth 3 tracks correctly."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        assert rt._etrap_set_level == 0

        for i in range(3):
            rt.push_stack_frame("DO", "TEST", f"SUB{i}", 0, "")
        rt.set_etrap("W $EC")
        assert rt._etrap_set_level == 3

    def test_etrap_ecode_set_on_error(self):
        """$ECODE is set when _handle_etrap is called."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        exc = ZeroDivisionError("division by zero")
        result = rt._handle_etrap(exc, scope)
        assert result is True

    def test_zerror_set_on_error(self):
        """$ZERROR is set to exception message on error."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        exc = ValueError("custom error message")
        rt._handle_etrap(exc, scope)
        assert rt.zerror() == "custom error message"

    def test_handle_etrap_sets_zstatus(self):
        """_handle_etrap populates $ZSTATUS with error info."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        exc = ZeroDivisionError("division by zero")
        rt._handle_etrap(exc, scope, routine="test", label="TEST", offset=3)
        zs = rt.zstatus()
        assert "TEST+3^test" in zs
        assert "DIVZERO" in zs

    def test_handle_etrap_sets_zposition(self):
        """_handle_etrap populates $ZPOSITION with label+offset^routine."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        exc = ZeroDivisionError("division by zero")
        rt._handle_etrap(exc, scope, routine="myroutine", label="ERRLABEL", offset=3)
        assert rt.zposition() == "ERRLABEL+3^myroutine"


class TestNewEtrapScoping:
    """T016: Tests for NEW $ETRAP scoping and NEW $ESTACK."""

    def test_new_etrap_saves_and_restores(self):
        """NEW $ETRAP saves current value and restores on scope exit.

        MUMPS semantics: NEW $ETRAP saves current value, then clears it.
        On scope exit (QUIT), the saved value is restored.
        """
        from m2py.runtime.helpers import NewScopeManager

        rt = MUMPSRuntime()
        scope = {}

        rt.set_etrap("outer trap")

        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("ETRAP", rt.etrap(), rt.set_etrap)
            assert rt.etrap() == ""
            rt.set_etrap("inner trap")
            assert rt.etrap() == "inner trap"

        assert rt.etrap() == "outer trap"

    def test_new_estack_saves_and_restores_etrap_set_level(self):
        """NEW $ESTACK saves _etrap_set_level and restores on scope exit."""
        from m2py.runtime.helpers import NewScopeManager

        rt = MUMPSRuntime()
        scope = {}

        rt.set_etrap('S $EC=""')
        original_level = rt._etrap_set_level

        rt.push_stack_frame("DO", "TEST", "SUB", 0, "")

        with NewScopeManager(scope) as mgr:
            mgr.new_special_var(
                "estack",
                rt._etrap_set_level,
                lambda v: setattr(rt, "_etrap_set_level", v),
            )
            rt._etrap_set_level = len(rt._stack_frames)
            assert rt._etrap_set_level == 1

        assert rt._etrap_set_level == original_level

    def test_new_etrap_nested_scopes(self):
        """Nested NEW $ETRAP scopes save and restore correctly."""
        from m2py.runtime.helpers import NewScopeManager

        rt = MUMPSRuntime()
        scope = {}

        rt.set_etrap("level0")

        with NewScopeManager(scope) as mgr1:
            mgr1.new_special_var("ETRAP", rt.etrap(), rt.set_etrap)
            assert rt.etrap() == ""
            rt.set_etrap("level1")

            with NewScopeManager(scope) as mgr2:
                mgr2.new_special_var("ETRAP", rt.etrap(), rt.set_etrap)
                assert rt.etrap() == ""
                rt.set_etrap("level2")
                assert rt.etrap() == "level2"

            assert rt.etrap() == "level1"

        assert rt.etrap() == "level0"


class TestNestedErrorDetection:
    """T017: Tests for nested error detection during error processing."""

    def test_in_error_handler_flag_set_during_handling(self):
        """_in_error_handler flag is True during $ETRAP execution."""
        rt = MUMPSRuntime()
        assert rt._in_error_handler is False

    def test_nested_error_returns_false(self):
        """Error during error processing returns False (propagate)."""
        rt = MUMPSRuntime()
        rt._in_error_handler = True
        rt.set_etrap('S $EC=""')
        scope = {}
        result = rt._handle_etrap(ValueError("nested error"), scope)
        assert result is False

    def test_nested_error_with_transaction_does_trollback(self):
        """Nested error with active transaction does TROLLBACK."""
        rt = MUMPSRuntime()
        rt._in_error_handler = True
        # Start a transaction via the globals backend
        rt._globals.transaction_start()
        assert rt.tlevel() > 0
        scope = {}
        result = rt._handle_etrap(ValueError("nested error"), scope)
        assert result is False
        # Transaction should have been rolled back
        assert rt.tlevel() == 0

    def test_max_nesting_depth_raises(self):
        """Max nesting depth prevents infinite error loops."""
        rt = MUMPSRuntime()
        assert rt._max_error_nesting == 20
        # Simulate exceeding max nesting
        rt._error_nesting_depth = 21
        with pytest.raises(RuntimeError, match="Maximum error handler nesting depth"):
            rt._handle_etrap(ValueError("error"), {})

    def test_error_handler_flag_cleared_after_handling(self):
        """_in_error_handler flag is cleared after error handling completes."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        rt._handle_etrap(ValueError("error"), scope)
        assert rt._in_error_handler is False

    def test_error_handler_flag_cleared_on_exception(self):
        """_in_error_handler flag is cleared even if handler raises."""
        rt = MUMPSRuntime()
        # Set a trap that itself errors
        rt.set_etrap("W UNDEF")
        scope = {}
        rt._handle_etrap(ValueError("error"), scope)
        # Flag should be cleared despite the error within the handler
        assert rt._in_error_handler is False


class TestExceptionToEcode:
    """Tests for _exception_to_ecode mapping."""

    def test_zero_division_maps_to_m9(self):
        """ZeroDivisionError maps to ,M9,."""
        rt = MUMPSRuntime()
        ecode = rt._exception_to_ecode(ZeroDivisionError())
        assert ecode == ",M9,"

    def test_key_error_maps_to_m6(self):
        """KeyError (undefined local) maps to ,M6,."""
        rt = MUMPSRuntime()
        ecode = rt._exception_to_ecode(KeyError("X"))
        assert ecode == ",M6,"

    def test_lvundef_error_maps_to_m6(self):
        """LVUNDEFError maps to ,M6, (MUMPS standard M6 = undefined local)."""
        rt = MUMPSRuntime()
        ecode = rt._exception_to_ecode(LVUNDEFError("X"))
        assert ecode == ",M6,"


class TestFormatZstatus:
    """Tests for $ZSTATUS formatting."""

    def test_basic_format(self):
        """$ZSTATUS format: errorcode,label+offset^routine,%YDB-E-ERRNAME, message.

        YDB verified: $ZSTATUS=150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: UNDEF
        """
        rt = MUMPSRuntime()
        zstatus = rt._format_zstatus(
            error_code="150373850",
            label="TEST",
            offset=3,
            routine="test",
            ydb_code="LVUNDEF",
            message="Undefined local variable: X",
        )
        assert (
            zstatus
            == "150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: X"
        )

    def test_empty_label_and_routine(self):
        """$ZSTATUS handles empty label and routine."""
        rt = MUMPSRuntime()
        zstatus = rt._format_zstatus(
            error_code="150373210",
            label="",
            offset=0,
            routine="",
            ydb_code="GENERIC",
            message="Generic error",
        )
        assert "150373210" in zstatus


class TestStackSnapshotOnError:
    """Tests for stack snapshot behavior during error handling."""

    def test_freeze_on_first_error_only(self):
        """Stack snapshot is frozen only on first error (empty→non-empty)."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", "TEST", "SUB1", 1, "D SUB1")

        # First error freezes snapshot
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        first_snapshot_len = len(rt._stack_snapshot)

        # Push more frames
        rt.push_stack_frame("DO", "TEST", "SUB2", 0, "D SUB2")

        # Second freeze should NOT update snapshot
        rt._freeze_stack_snapshot()
        assert len(rt._stack_snapshot) == first_snapshot_len  # Still 1

    def test_snapshot_cleared_on_ecode_reset(self):
        """Stack snapshot cleared (set to None) when SET $ECODE=""."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", "TEST", "SUB", 0, "")
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        rt.set_ecode("")
        assert rt._stack_snapshot is None
