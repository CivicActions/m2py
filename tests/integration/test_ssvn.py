"""Integration tests for SSVNs (^$JOB, ^$ROUTINE, ^$SYSTEM).

Spec 021 Phase 13 (T119): Transpile SSVN routines and verify output.
"""

import pytest
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


def _run(source: str) -> str:
    """Transpile and execute MUMPS source, return captured output."""
    code = generate_python(source)
    rt = MUMPSRuntime()
    result = rt.execute(code)
    return result.output


@pytest.mark.codegen
class TestSsvnIntegration:
    """Integration tests for SSVNs."""

    def test_ssvn_system(self):
        """^$SYSTEM returns system identification (same as $SYSTEM ISV)."""
        source = "TEST W ^$SYSTEM,! Q\n"
        output = _run(source)
        assert output.strip() == "47,M2PY"

    def test_ssvn_job_current_pid(self):
        """^$JOB($J) returns '1' for current process."""
        source = "TEST W ^$JOB($J),! Q\n"
        output = _run(source)
        assert output.strip() == "1"

    def test_ssvn_global_nonexistent(self):
        """^$GLOBAL for nonexistent global returns ''."""
        source = 'TEST W ^$GLOBAL("NONEXIST"),! Q\n'
        output = _run(source)
        assert output.strip() == ""

    def test_ssvn_global_exists(self):
        """^$GLOBAL for existing global returns '1'."""
        source = 'TEST S ^MYGLOB=1 W ^$GLOBAL("MYGLOB"),! Q\n'
        output = _run(source)
        assert output.strip() == "1"

    def test_ssvn_codegen_job(self):
        """^$JOB generates ssvn_job() call."""
        source = "TEST W ^$JOB(123),! Q\n"
        code = generate_python(source)
        assert "ssvn_job" in code

    def test_ssvn_codegen_routine(self):
        """^$ROUTINE generates ssvn_routine() call."""
        source = 'TEST W ^$ROUTINE("TEST"),! Q\n'
        code = generate_python(source)
        assert "ssvn_routine" in code
