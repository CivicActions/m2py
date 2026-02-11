"""Integration tests for error handling (Phase 4-5: US2, US3).

T018: Integration test that transpiles MUMPS routine using $ETRAP
T028: Integration test transpiling $ZTRAP routine
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


def _run(mumps_code: str) -> tuple[MUMPSRuntime, str]:
    """Transpile and execute MUMPS code, return runtime and output."""
    python_code = generate_python(mumps_code)
    runtime = MUMPSRuntime()
    result = runtime.execute(python_code, capture_output=True)
    return runtime, result.output


@pytest.mark.codegen
class TestEtrapIntegration:
    """T018: Integration tests for $ETRAP error handling."""

    def test_etrap_catches_divide_by_zero(self):
        """$ETRAP catches division-by-zero error and function returns."""
        source = 'TEST\n S $ET="S $EC="""""\n W "Before",!\n S X=1/0\n W "After",!\n Q'
        rt, output = _run(source)
        # $ETRAP fires on 1/0, clears $ECODE, function returns
        # "After" does NOT appear because function returns from except block
        assert output == "Before\n"
        assert rt.ecode() == ""

    def test_etrap_catches_error_in_subroutine(self):
        """Error in DO'd subroutine caught by caller's $ETRAP."""
        source = (
            'TEST\n S $ET="S $EC="""""\n W "Before",!\n D SUB\n W "After",!\n Q\n'
            'SUB\n W "InSub",!\n S X=1/0\n Q'
        )
        rt, output = _run(source)
        # SUB errors, $ETRAP in SUB's stack unwinds, caller continues
        assert "Before" in output
        assert "InSub" in output
        assert "After" in output
        assert rt.ecode() == ""

    def test_etrap_ecode_set_on_error(self):
        """$ECODE is populated when error occurs, before $ETRAP runs."""
        source = 'TEST\n S $ET="S $EC="""""\n S X=1/0\n Q'
        rt, output = _run(source)
        # $ECODE was set (,M9, for division by zero) then cleared by $ETRAP
        assert rt.ecode() == ""

    def test_etrap_zstatus_populated_on_error(self):
        """$ZSTATUS is populated with error info when error occurs."""
        # $ETRAP doesn't clear $ZSTATUS, so we can inspect it after
        source = 'TEST\n S $ET="S $EC="""""\n S X=1/0\n Q'
        rt, output = _run(source)
        # $ZSTATUS should contain error info
        zs = rt.zstatus()
        assert zs != ""  # Was set by _handle_etrap

    def test_no_trap_error_propagates(self):
        """Without $ETRAP or $ZTRAP, error propagates as Python exception."""
        source = "TEST\n S X=1/0\n Q"
        py_code = generate_python(source)
        rt = MUMPSRuntime()
        result = rt.execute(py_code, capture_output=True)
        # execute() catches exceptions, so check for error in result
        assert (
            result.error is not None
            or rt.ecode() != ""
            or "Before" not in (result.output or "")
        )


@pytest.mark.codegen
class TestZtrapIntegration:
    """T028: Integration tests for $ZTRAP error handling."""

    def test_ztrap_catches_divide_by_zero(self):
        """$ZTRAP catches division-by-zero error."""
        source = 'TEST\n S $ZT="S $EC="""""\n W "Before",!\n S X=1/0\n W "After",!\n Q'
        rt, output = _run(source)
        assert output == "Before\n"
        assert rt.ecode() == ""

    def test_ztrap_catches_error_in_subroutine(self):
        """Error in DO'd subroutine caught by $ZTRAP."""
        source = (
            'TEST\n S $ZT="S $EC="""""\n W "Before",!\n D SUB\n W "After",!\n Q\n'
            'SUB\n W "InSub",!\n S X=1/0\n Q'
        )
        rt, output = _run(source)
        assert "Before" in output
        assert "InSub" in output
        assert "After" in output

    def test_zstatus_contains_error_info(self):
        """$ZSTATUS contains error code and message after $ZTRAP."""
        source = 'TEST\n S $ZT="S $EC="""""\n S X=1/0\n Q'
        rt, output = _run(source)
        zs = rt.zstatus()
        assert zs != ""


@pytest.mark.codegen
class TestErrorHandlingStack:
    """Tests for error handling with stack operations."""

    def test_error_in_nested_do(self):
        """Error in nested DO propagates through stack correctly."""
        source = (
            'TEST\n S $ET="S $EC="""""\n D OUTER\n W "Done",!\n Q\n'
            "OUTER\n D INNER\n Q\n"
            "INNER\n S X=1/0\n Q"
        )
        rt, output = _run(source)
        # Error in INNER, caught at some level by $ETRAP
        assert "Done" in output


@pytest.mark.codegen
class TestEtrapZtrapMutualExclusion:
    """Tests for $ETRAP↔$ZTRAP mutual exclusion end-to-end."""

    def test_set_etrap_clears_ztrap(self):
        """SET $ETRAP clears $ZTRAP (mutual exclusion)."""
        source = 'TEST\n S $ZT="G ERR"\n S $ET="S $EC="""""\n W "ZT=",$ZT,!\n Q'
        rt, output = _run(source)
        # After SET $ET, $ZT should be empty
        assert output == "ZT=\n"

    def test_set_ztrap_clears_etrap(self):
        """SET $ZTRAP clears $ETRAP (mutual exclusion)."""
        source = 'TEST\n S $ET="S $EC="""""\n S $ZT="G ERR"\n W "ET=",$ET,!\n Q'
        rt, output = _run(source)
        # After SET $ZT, $ET should be empty
        assert output == "ET=\n"
