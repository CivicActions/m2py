"""Integration tests for TSTART restart variables (Spec 021 Phase 8).

T051: Transpile and execute TSTART/TCOMMIT/TROLLBACK routines with
restart variables and verify correct behavior.
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
class TestTStartRestartVarsIntegration:
    """Integration tests for TSTART with restart variables."""

    def test_tstart_named_vars_tcommit(self):
        """TSTART (X) + TCOMMIT: locals are NOT restored."""
        source = (
            'TEST\n S X=1,Y=2\n TS (X)\n S X=99,Y=99\n TC\n W "X=",X,!,"Y=",Y,!\n Q'
        )
        rt, output = _run(source)
        assert output == "X=99\nY=99\n"

    def test_tstart_named_vars_trollback(self):
        """TSTART (X) + TROLLBACK: locals are NOT restored (globals are)."""
        source = 'TEST\n S X=1,Y=2,^G=100\n TS (X)\n S X=99,Y=99,^G=200\n TRO\n W "X=",X,!,"Y=",Y,!,"^G=",^G,!\n Q'
        rt, output = _run(source)
        assert output == "X=99\nY=99\n^G=100\n"

    def test_tstart_star_tcommit(self):
        """TSTART * + TCOMMIT: locals are NOT restored."""
        source = 'TEST\n S X=1,Y=2\n TS *\n S X=99,Y=99\n TC\n W "X=",X,!,"Y=",Y,!\n Q'
        rt, output = _run(source)
        assert output == "X=99\nY=99\n"

    def test_tstart_empty_parens_no_restart_vars(self):
        """TSTART () with no restart vars works normally."""
        source = 'TEST\n S X=1\n TS ()\n S X=99\n TC\n W "X=",X,!\n Q'
        rt, output = _run(source)
        assert output == "X=99\n"

    def test_nested_tstart_tcommit(self):
        """Nested TSTART/TCOMMIT with restart vars."""
        source = 'TEST\n S X=1,Y=2\n TS (X)\n S X=10\n TS (Y)\n S Y=20\n TC\n TC\n W "X=",X,!,"Y=",Y,!\n Q'
        rt, output = _run(source)
        assert output == "X=10\nY=20\n"

    def test_tstart_tlevel(self):
        """$TLEVEL tracks transaction nesting correctly."""
        source = 'TEST\n W "$TL=",$TLEVEL,!\n TS ()\n W "$TL=",$TLEVEL,!\n TS ()\n W "$TL=",$TLEVEL,!\n TC\n W "$TL=",$TLEVEL,!\n TC\n W "$TL=",$TLEVEL,!\n Q'
        rt, output = _run(source)
        assert output == "$TL=0\n$TL=1\n$TL=2\n$TL=1\n$TL=0\n"

    def test_trollback_resets_tlevel(self):
        """TROLLBACK resets $TLEVEL to 0."""
        source = (
            'TEST\n TS ()\n TS ()\n W "$TL=",$TLEVEL,!\n TRO\n W "$TL=",$TLEVEL,!\n Q'
        )
        rt, output = _run(source)
        assert output == "$TL=2\n$TL=0\n"
