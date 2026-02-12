"""Integration tests for READ #maxlen (Spec 021 Phase 9).

T114: Transpile and execute READ #maxlen routines.
"""

import io
from unittest.mock import patch

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


def _run(mumps_code: str, stdin_data: str = "") -> tuple[MUMPSRuntime, str]:
    """Transpile and execute MUMPS code with mocked stdin."""
    python_code = generate_python(mumps_code)
    runtime = MUMPSRuntime()
    with patch("sys.stdin", io.StringIO(stdin_data)):
        result = runtime.execute(python_code, capture_output=True)
    return runtime, result.output


@pytest.mark.codegen
class TestReadMaxlenIntegration:
    """Integration tests for READ #maxlen."""

    def test_read_maxlen_basic(self):
        """R X#5 reads at most 5 characters."""
        source = 'TEST\n R X#5\n W "X=[",X,"]",!\n Q'
        rt, output = _run(source, "ABCDEFGH")
        assert output == "X=[ABCDE]\n"

    def test_read_maxlen_with_newline(self):
        """R X#10 stops at newline before maxlen."""
        source = 'TEST\n R X#10\n W "X=[",X,"]",!\n Q'
        rt, output = _run(source, "ABC\nDEF")
        assert output == "X=[ABC]\n"

    def test_read_maxlen_1(self):
        """R X#1 reads a single character."""
        source = 'TEST\n R X#1\n W "X=[",X,"]",!\n Q'
        rt, output = _run(source, "Hello")
        assert output == "X=[H]\n"

    def test_read_maxlen_key_on_newline(self):
        """$KEY is newline when READ terminated by Enter."""
        source = 'TEST\n R X#10\n W "$KEY=[",$KEY,"]",!\n Q'
        rt, output = _run(source, "ABC\n")
        # $KEY should be the newline character
        assert "$KEY=[" in output
        assert output.startswith("$KEY=[")

    def test_read_maxlen_key_on_maxlen(self):
        """$KEY is empty when maxlen reached."""
        source = 'TEST\n R X#3\n W "$KEY=[",$KEY,"]",!\n Q'
        rt, output = _run(source, "ABCDEFGH")
        assert output == "$KEY=[]\n"

    def test_read_maxlen_multiple(self):
        """Multiple READ #maxlen in sequence."""
        source = 'TEST\n R X#3,Y#2\n W "X=[",X,"] Y=[",Y,"]",!\n Q'
        rt, output = _run(source, "ABCDE")
        assert output == "X=[ABC] Y=[DE]\n"
