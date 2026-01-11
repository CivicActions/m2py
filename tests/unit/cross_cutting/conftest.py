"""Shared fixtures for cross-cutting tests.

Provides fixtures for testing runtime behavior that spans multiple
language features.
"""

import pytest


@pytest.fixture
def execute_mumps():
    """Fixture for parsing, generating, and executing MUMPS code.

    Returns a function that takes MUMPS source and returns execution result.

    Usage:
        def test_behavior(execute_mumps):
            result = execute_mumps("TEST\\n S X=1\\n W X\\n Q")
            assert result.output == "1"
    """
    from m2py.codegen import generate_python
    from m2py.runtime import MUMPSRuntime

    def _execute(source: str, *, capture_output: bool = True):
        """Execute MUMPS source and return result."""
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        return runtime.execute(python_code, capture_output=capture_output)

    return _execute
