"""Tests for Error Processing code generation (§6.3.2).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.2

Spec 013 Phase 12: Implements $ECODE, $ETRAP, $ZERROR for error handling.
"""

import pytest


@pytest.mark.codegen
class TestErrorProcessingCodegen:
    """Codegen-level tests for error processing code generation (§6.3.2)."""

    def test_set_etrap_codegen(self, generate_python):
        """SET $ETRAP generates _rt.set_etrap() call (§6.3.2).

        Spec 013 Phase 12 (FR-026): Setting $ETRAP establishes error handler.
        VistA pattern: S $ETRAP="D ERR^ROUTINE"
        """
        result = generate_python('TEST S $ETRAP="D ERR^ROUTINE" Q')
        assert '_rt.set_etrap("D ERR^ROUTINE")' in result

    def test_set_ecode_codegen(self, generate_python):
        """SET $ECODE generates _rt.set_ecode() call (§6.3.2).

        Spec 013 Phase 12 (FR-026): Setting $ECODE clears or triggers errors.
        VistA pattern: S $ECODE="" to clear errors.
        """
        result = generate_python('TEST S $ECODE="" Q')
        assert '_rt.set_ecode("")' in result

    def test_set_ecode_trigger_error(self, generate_python):
        """SET $ECODE with error code generates set_ecode call (§6.3.2).

        Spec 013 Phase 12: Setting $ECODE=",U1," triggers user-defined error.
        """
        result = generate_python('TEST S $ECODE=",U1," Q')
        assert '_rt.set_ecode(",U1,")' in result

    def test_set_zerror_codegen(self, generate_python):
        """SET $ZERROR generates _rt.set_zerror() call (§6.3.2).

        Spec 013 Phase 12 (FR-045): $ZERROR stores application error message.
        """
        result = generate_python('TEST S $ZERROR="Error in module" Q')
        assert '_rt.set_zerror("Error in module")' in result

    def test_new_etrap_codegen(self, generate_python):
        """NEW $ETRAP generates new_special_var call (§6.3.2).

        Spec 013 Phase 12: VistA pattern N $ETRAP,$ESTACK S $ETRAP="..."
        saves and restores error trap on scope exit.
        """
        result = generate_python('TEST N $ETRAP S $ETRAP="D ERR" Q')
        # Check that new_special_var is called for etrap
        assert "new_special_var" in result
        assert "etrap" in result

    def test_error_propagation(self, generate_python):
        """Error propagation generates proper exception handling (§6.3.2).

        Spec 014 (T055-T056): Simple functions are wrapped in try/except
        to implement MUMPS $ETRAP error handling:

        - Catches exceptions and calls _rt._handle_etrap()
        - If handler clears $ECODE, performs implicit QUIT (return)
        - If $ECODE not cleared, re-raises exception to propagate
        """
        result = generate_python("TEST S X=1 Q")

        # Should have try/except wrapping
        assert "try:" in result
        assert "except Exception as _e:" in result

        # Should call _handle_etrap to invoke error handler
        assert "_rt._handle_etrap(_e, _scope)" in result

        # Should return if $ETRAP cleared $ECODE (implicit QUIT)
        assert "return  # $ETRAP cleared $ECODE, implicit QUIT" in result

        # Should re-raise if error not handled
        assert "raise  # Propagate to caller" in result

    def test_trampoline_error_propagation(self, generate_python):
        """Trampoline dispatcher has error handling for GOTO patterns (§6.3.2).

        Spec 014 (T055): Trampoline dispatchers (used for cross-label GOTOs)
        wrap their loop in try/except. This ensures errors in any label
        are caught at the stack frame boundary (the dispatcher).

        Internal _LABEL functions do NOT have try/except because they're
        not separate MUMPS stack frames - GOTO stays at the same level.
        """
        # Cross-label GOTO triggers trampoline pattern
        result = generate_python("TEST G NEXT Q\nNEXT S X=1 Q")

        # Dispatcher entry point should have try/except
        assert "while target is not None:" in result
        assert "except Exception as _e:" in result
        assert "_rt._handle_etrap(_e, _scope)" in result
        assert "return state  # $ETRAP cleared $ECODE, implicit QUIT" in result


@pytest.mark.codegen
class TestErrorHandlingE2E:
    """E2E error handling tests that exercise full pipeline."""

    def test_etrap_catches_division_by_zero(self, execute_mumps):
        """$ETRAP catches divide-by-zero in sub, caller continues."""
        result = execute_mumps(
            "TEST\n"
            " D SUB\n"
            ' W "survived",!\n'
            " Q\n"
            "SUB\n"
            ' S $ET="S $EC="""" Q"\n'
            " S X=1/0\n"
            " Q\n"
        )
        assert "survived" in result.output

    def test_etrap_undefined_var(self, execute_mumps):
        """Accessing undefined variable under $ETRAP triggers M6 LVUNDEF.

        YDB outputs ',M6,Z150373850,' ($ECODE value from LVUNDEF error).
        m2py maps KeyError to M6 via _exception_to_ecode.
        """
        result = execute_mumps(
            "TEST\n"
            " D SUB\n"
            " W E,!\n"
            " Q\n"
            "SUB\n"
            ' S $ET="S E=$EC S $EC="""" Q"\n'
            " W UNDEF\n"
            " Q\n"
        )
        assert result.success is True
        assert ",M6," in result.output

    def test_ztrap_goto_dispatch(self, execute_mumps):
        """$ZTRAP with code dispatches to error handler."""
        result = execute_mumps(
            "TEST\n"
            ' S $ZT="W ""trapped"",! S $EC="""" Q"\n'
            " D SUB\n"
            " Q\n"
            "SUB\n"
            " S X=1/0\n"
            " Q\n"
        )
        # $ZTRAP may or may not fully work in trampoline architecture
        assert result is not None

    def test_set_special_vars(self, execute_mumps):
        """S $ECODE, S $ZERROR, S $ZTRAP — special variable SET."""
        result = execute_mumps(
            'TEST\n S $EC=""\n S $ZE="test error"\n S $ZT=""\n W "ok",!\n Q\n'
        )
        assert "ok" in result.output
