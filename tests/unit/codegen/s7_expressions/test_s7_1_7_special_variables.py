"""Tests for Special Variables code generation (§7.1.7).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
"""

import pytest


@pytest.mark.codegen
class TestSpecialVariablesCodegen:
    """Codegen-level tests for special variables code generation (§7.1.7)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $HOROLOG codegen")
    def test_sv_horolog(self, generate_python):
        """$HOROLOG generates date/time calculation (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $IO codegen")
    def test_sv_io(self, generate_python):
        """$IO generates current device access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $JOB codegen")
    def test_sv_job(self, generate_python):
        """$JOB generates os.getpid() (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEST codegen")
    def test_sv_test(self, generate_python):
        """$TEST generates test flag access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL codegen")
    def test_sv_tlevel(self, generate_python):
        """$TLEVEL generates transaction level access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $X codegen")
    def test_sv_x(self, generate_python):
        """$X generates cursor column access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $Y codegen")
    def test_sv_y(self, generate_python):
        """$Y generates cursor row access (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT basic codegen")
    def test_sv_quit(self, generate_python):
        """$QUIT generates quit flag access (§7.1.7)."""
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT in extrinsic")
    def test_quit_in_extrinsic_returns_one(self, generate_python):
        """$QUIT returns 1 when called from extrinsic function.

        S X=$$FUNC  ; Inside FUNC, $QUIT=1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT in DO")
    def test_quit_in_do_returns_zero(self, generate_python):
        """$QUIT returns 0 when called from DO.

        D LABEL  ; Inside LABEL, $QUIT=0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT tracking runtime")
    def test_quit_tracking_in_runtime(self, generate_python):
        """Runtime tracks $QUIT across call frames.

        Each call frame has its own $QUIT value.
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
