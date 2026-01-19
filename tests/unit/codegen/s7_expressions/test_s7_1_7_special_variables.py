"""Tests for Special Variables code generation (§7.1.7).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7

Spec 011: Implementation of special variable codegen for $HOROLOG, $JOB, $IO,
$X, $Y, $STORAGE, $STACK, $QUIT.
"""

import pytest


@pytest.mark.codegen
class TestSpecialVariablesCodegen:
    """Codegen-level tests for special variables code generation (§7.1.7)."""

    def test_sv_horolog(self, generate_python):
        """$HOROLOG generates runtime horolog() call (§7.1.7).

        Spec 011 (T051): $H generates _rt.horolog() call.
        """
        result = generate_python("TEST W $H Q")
        assert "_rt.horolog()" in result

    def test_sv_horolog_abbreviated(self, generate_python):
        """$H generates same as $HOROLOG (§7.1.7).

        Spec 011 (T051): Both forms use _rt.horolog().
        """
        full = generate_python("TEST W $HOROLOG Q")
        abbrev = generate_python("TEST W $H Q")
        assert "_rt.horolog()" in full
        assert "_rt.horolog()" in abbrev

    def test_sv_io(self, generate_python):
        """$IO generates runtime io() call (§7.1.7).

        Spec 011 (T053): $IO generates _rt.io() call.
        """
        result = generate_python("TEST W $IO Q")
        assert "_rt.io()" in result

    def test_sv_job(self, generate_python):
        """$JOB generates runtime job() call (§7.1.7).

        Spec 011 (T052): $J generates _rt.job() call.
        """
        result = generate_python("TEST W $J Q")
        assert "_rt.job()" in result

    def test_sv_job_abbreviated(self, generate_python):
        """$J generates same as $JOB (§7.1.7).

        Spec 011 (T052): Both forms use _rt.job().
        """
        full = generate_python("TEST W $JOB Q")
        abbrev = generate_python("TEST W $J Q")
        assert "_rt.job()" in full
        assert "_rt.job()" in abbrev

    def test_sv_test(self, generate_python):
        """$TEST generates test flag access (§7.1.7).

        Already implemented in Spec 005. $T returns int(_test).
        """
        result = generate_python("TEST W $T Q")
        assert "int(_test)" in result

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL codegen")
    def test_sv_tlevel(self, generate_python):
        """$TLEVEL generates transaction level access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    def test_sv_x(self, generate_python):
        """$X generates runtime x() call (§7.1.7).

        Spec 011 (T054): $X generates _rt.x() call.
        """
        result = generate_python("TEST W $X Q")
        assert "_rt.x()" in result

    def test_sv_y(self, generate_python):
        """$Y generates runtime y() call (§7.1.7).

        Spec 011 (T054): $Y generates _rt.y() call.
        """
        result = generate_python("TEST W $Y Q")
        assert "_rt.y()" in result

    def test_sv_quit(self, generate_python):
        """$QUIT generates runtime quit_flag() call (§7.1.7).

        Spec 011 (T057): $Q generates _rt.quit_flag() call.
        """
        result = generate_python("TEST W $Q Q")
        assert "_rt.quit_flag()" in result

    def test_sv_quit_abbreviated(self, generate_python):
        """$Q generates same as $QUIT (§7.1.7).

        Spec 011 (T057): Both forms use _rt.quit_flag().
        """
        full = generate_python("TEST W $QUIT Q")
        abbrev = generate_python("TEST W $Q Q")
        assert "_rt.quit_flag()" in full
        assert "_rt.quit_flag()" in abbrev

    def test_sv_storage(self, generate_python):
        """$STORAGE generates large constant (§7.1.7).

        Spec 011 (T055): $S generates a large integer constant.
        """
        result = generate_python("TEST W $S Q")
        # Should contain a large integer (we use 2147483647)
        assert "2147483647" in result

    def test_sv_stack(self, generate_python):
        """$STACK generates runtime stack_level() call (§7.1.7).

        Spec 011 (T056): $ST generates _rt.stack_level() call.
        """
        result = generate_python("TEST W $ST Q")
        assert "_rt.stack_level()" in result

    def test_sv_stack_full(self, generate_python):
        """$STACK full form generates same as abbreviated (§7.1.7).

        Spec 011 (T056): Both forms use _rt.stack_level().
        """
        full = generate_python("TEST W $STACK Q")
        abbrev = generate_python("TEST W $ST Q")
        assert "_rt.stack_level()" in full
        assert "_rt.stack_level()" in abbrev

    def test_sv_ecode(self, generate_python):
        """$ECODE generates _rt.ecode() call (§7.1.7).

        Spec 013 Phase 12 (FR-026): $ECODE returns comma-delimited error codes.
        """
        result = generate_python("TEST W $ECODE Q")
        assert "_rt.ecode()" in result

    def test_sv_ecode_abbreviated(self, generate_python):
        """$EC abbreviated form generates same call (§7.1.7).

        Spec 013 Phase 12: Both $ECODE and $EC use _rt.ecode().
        """
        full = generate_python("TEST W $ECODE Q")
        abbrev = generate_python("TEST W $EC Q")
        assert "_rt.ecode()" in full
        assert "_rt.ecode()" in abbrev

    def test_sv_etrap(self, generate_python):
        """$ETRAP generates _rt.etrap() call (§7.1.7).

        Spec 013 Phase 12 (FR-026): $ETRAP returns error trap code string.
        """
        result = generate_python("TEST W $ETRAP Q")
        assert "_rt.etrap()" in result

    def test_sv_etrap_abbreviated(self, generate_python):
        """$ET abbreviated form generates same call (§7.1.7).

        Spec 013 Phase 12: Both $ETRAP and $ET use _rt.etrap().
        """
        full = generate_python("TEST W $ETRAP Q")
        abbrev = generate_python("TEST W $ET Q")
        assert "_rt.etrap()" in full
        assert "_rt.etrap()" in abbrev

    def test_sv_zerror(self, generate_python):
        """$ZERROR generates _rt.zerror() call (§7.1.7).

        Spec 013 Phase 12 (FR-045): $ZERROR returns application error message.
        """
        result = generate_python("TEST W $ZERROR Q")
        assert "_rt.zerror()" in result

    def test_sv_zerror_abbreviated(self, generate_python):
        """$ZE abbreviated form generates same call (§7.1.7).

        Spec 013 Phase 12: Both $ZERROR and $ZE use _rt.zerror().
        """
        full = generate_python("TEST W $ZERROR Q")
        abbrev = generate_python("TEST W $ZE Q")
        assert "_rt.zerror()" in full
        assert "_rt.zerror()" in abbrev


@pytest.mark.codegen
class TestQuitSpecialVariableCodegen:
    """Codegen tests for $QUIT special variable.

    $QUIT returns 1 if current frame was invoked by extrinsic function
    or extrinsic variable, 0 otherwise. Used to determine if QUIT
    requires a return value.

    Reference: §7.1.4.10
    """

    def test_quit_generates_quit_flag_call(self, generate_python):
        """$QUIT generates _rt.quit_flag() call.

        Spec 011: The runtime tracks extrinsic context.
        """
        result = generate_python("TEST W $Q Q")
        assert "_rt.quit_flag()" in result

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT in extrinsic runtime test")
    def test_quit_in_extrinsic_returns_one(self, generate_python):
        """$QUIT returns 1 when called from extrinsic function.

        S X=$$FUNC  ; Inside FUNC, $QUIT=1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT in DO runtime test")
    def test_quit_in_do_returns_zero(self, generate_python):
        """$QUIT returns 0 when called from DO.

        D LABEL  ; Inside LABEL, $QUIT=0
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTextWithOffsetsCodegen:
    """Codegen tests for $TEXT with offsets.

    $TEXT retrieves source lines with various offset specifications.
    Supports label+offset, +N (nth line), and external routine refs.

    Reference: §7.1.5 ($TEXT function)
    """

    def test_text_with_label(self, execute_mumps):
        """$TEXT(LABEL) returns source at label.

        S A=$T(LABEL) returns first line of LABEL.
        """
        result = execute_mumps("TEST W $T(TEST) Q")
        assert result.output == "TEST W $T(TEST) Q"

    def test_text_with_label_offset(self, execute_mumps):
        """$TEXT(LABEL+n) returns line at offset from label.

        S A=$T(TEST+1) returns 1st line after TEST.
        """
        result = execute_mumps('TEST W $T(TEST+1) Q\n W "line2" Q')
        assert result.output == ' W "line2" Q'

    def test_text_with_line_number(self, execute_mumps):
        """$TEXT(+N) returns Nth line of routine.

        S A=$T(+1) returns 1st line of current routine.
        """
        result = execute_mumps("TEST W $T(+1) Q")
        assert result.output == "TEST W $T(+1) Q"

    def test_text_line_zero_returns_routine_name(self, execute_mumps):
        """$TEXT(+0) returns the routine name.

        S A=$T(+0) returns the routine name (lowercase convention).
        """
        result = execute_mumps("TEST W $T(+0) Q")
        assert result.output == "test"

    def test_text_different_label(self, execute_mumps):
        """$TEXT(LABEL) retrieves source from another label in same routine.

        Returns the source line for the specified label.
        """
        result = execute_mumps('TEST W $T(OTHER) Q\nOTHER W "hello" Q')
        assert result.output == 'OTHER W "hello" Q'

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $TEXT external routine (requires multi-routine)"
    )
    def test_text_external_routine(self, generate_python):
        """$TEXT(LABEL+N^ROUTINE) accesses external routine.

        S A=$T(MAIN+3^OTHER) returns line from OTHER routine.
        """
        pytest.fail("Stub - implement test")

    def test_text_with_variable_offset(self, execute_mumps):
        """$TEXT(+I) evaluates offset at runtime.

        S A=$T(+I) computes offset from I value.
        """
        result = execute_mumps("TEST S I=1 W $T(+I) Q")
        assert result.output == "TEST S I=1 W $T(+I) Q"


@pytest.mark.codegen
class TestTransactionSpecialVariablesCodegen:
    """Codegen tests for transaction special variables (LIM-016).

    $TRESTART has zero VistA usage and is deferred. Codegen should raise
    NotImplementedError explicitly.

    Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
    Limitation: docs/limitations.md - LIM-016: Zero-VistA-Usage Deferred Features
    """

    def test_lim016_trestart_raises_error(self, generate_python):
        """$TRESTART should raise NotImplementedError (LIM-016).

        $TRESTART has zero VistA usage. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="TRESTART"):
            generate_python("TEST W $TRESTART Q")
