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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ECODE codegen")
    def test_sv_ecode(self, generate_python):
        """$ECODE generates error code access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ETRAP codegen")
    def test_sv_etrap(self, generate_python):
        """$ETRAP generates error trap access (§7.1.7)."""
        pytest.fail("Stub - implement test")


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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT with label")
    def test_text_with_label(self, generate_python):
        """$TEXT(LABEL) returns source at label.

        S A=$T(MAIN) returns first line of MAIN label.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT with label+offset")
    def test_text_with_label_offset(self, generate_python):
        """$TEXT(LABEL+n) returns line at offset from label.

        S A=$T(TEX+5) returns 5th line after TEX.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT with +N")
    def test_text_with_line_number(self, generate_python):
        """$TEXT(+N) returns Nth line of routine.

        S A=$T(+5) returns 5th line of current routine.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT external routine")
    def test_text_external_routine(self, generate_python):
        """$TEXT(LABEL+N^ROUTINE) accesses external routine.

        S A=$T(MAIN+3^OTHER) returns line from OTHER routine.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT with variable offset")
    def test_text_with_variable_offset(self, generate_python):
        """$TEXT(LABEL+I) evaluates offset at runtime.

        S A=$T(TEX+I) computes offset from I value.
        """
        pytest.fail("Stub - implement test")
