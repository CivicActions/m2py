"""Integration tests for ZSYSTEM command.

Spec 021 Phase 11 (T116): Transpile ZSYSTEM routines and verify output.
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
class TestZsystemIntegration:
    """Integration tests for ZSYSTEM command."""

    def test_zsystem_exit_code_success(self):
        """ZSYSTEM with successful command, $ZSY=0."""
        source = 'TEST ZSY "true" W $ZSY,! Q\n'
        output = _run(source)
        assert output.strip() == "0"

    def test_zsystem_exit_code_failure(self):
        """ZSYSTEM with failing command, $ZSY stores exit code."""
        source = 'TEST ZSY "exit 42" W $ZSY,! Q\n'
        output = _run(source)
        assert output.strip() == "42"

    def test_zsystem_empty_string(self):
        """ZSYSTEM with empty string is no-op."""
        source = 'TEST ZSY "" W $ZSY,! Q\n'
        output = _run(source)
        assert output.strip() == "0"

    def test_zsystem_multiple_commands(self):
        """Multiple ZSYSTEM commands, $ZSY shows last exit code."""
        source = 'TEST ZSY "exit 1" ZSY "exit 5" W $ZSY,! Q\n'
        output = _run(source)
        assert output.strip() == "5"

    def test_zsystem_abbreviated(self):
        """ZSY abbreviation works."""
        source = 'TEST ZSY "exit 3" W $ZSY,! Q\n'
        output = _run(source)
        assert output.strip() == "3"

    def test_zsystem_default_is_zero(self):
        """$ZSYSTEM is 0 before any ZSYSTEM command."""
        source = "TEST W $ZSY,! Q\n"
        output = _run(source)
        assert output.strip() == "0"
