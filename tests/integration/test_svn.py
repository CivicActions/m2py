"""Integration tests for YDB SVNs ($ZSEARCH, $ZMESSAGE, $ZRO, $ZJOB).

Spec 021 Phase 14 (T120): Transpile YDB SVN routines and verify output.
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
class TestSvnIntegration:
    """Integration tests for YDB SVNs."""

    def test_zjob_default(self):
        """$ZJOB is '0' before any JOB command."""
        source = "TEST W $ZJOB,! Q\n"
        output = _run(source)
        assert output.strip() == "0"

    def test_zro_returns_value(self):
        """$ZRO returns a string value."""
        source = "TEST W $ZRO,! Q\n"
        output = _run(source)
        assert output.strip() == "."

    def test_zmessage_generates_code(self):
        """$ZMESSAGE generates m_zmessage() call."""
        source = "TEST W $ZMESSAGE(150373850),! Q\n"
        code = generate_python(source)
        assert "m_zmessage" in code

    def test_zmessage_executes(self):
        """$ZMESSAGE returns error text."""
        source = "TEST W $ZMESSAGE(150373850),! Q\n"
        output = _run(source)
        assert "LVUNDEF" in output

    def test_zsearch_generates_code(self):
        """$ZSEARCH generates _rt.zsearch() call."""
        source = 'TEST W $ZSEARCH("*.m"),! Q\n'
        code = generate_python(source)
        assert "_rt.zsearch" in code

    def test_zsearch_executes(self):
        """$ZSEARCH returns file path or empty."""
        source = 'TEST W $ZSEARCH("*.nonexistent"),! Q\n'
        output = _run(source)
        assert output.strip() == ""
