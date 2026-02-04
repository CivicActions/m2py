"""Tests for READ command code generation (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17

Tests Python code generation for READ command including:
- Basic READ to variable
- READ with prompt strings
- READ with timeout
- READ single character (*X)
- Format controls in READ
"""

import io
import sys
import pytest

from m2py.codegen import generate_python


@pytest.mark.codegen
class TestReadCodeGeneration:
    """Test READ command generates correct Python code."""

    def test_basic_read_generates_input_call(self) -> None:
        """R X generates input() assignment."""
        source = """\
TEST
 R X
 Q
"""
        python_code = generate_python(source)
        # Should generate input() call stored in _scope
        assert "input()" in python_code

    def test_read_with_prompt_generates_print_and_input(self) -> None:
        """R 'Name: ',X generates print then input."""
        source = """\
TEST
 R "Enter: ",X
 Q
"""
        python_code = generate_python(source)
        # Should generate print for prompt and input for value
        # Note: repr() uses single quotes, so 'Enter: ' is expected
        assert (
            "print('Enter: ', end=" in python_code
            or 'print("Enter: ", end=' in python_code
        )
        assert "input()" in python_code

    def test_read_with_format_control_newline(self) -> None:
        """R !,X generates newline then input."""
        source = """\
TEST
 R !,X
 Q
"""
        python_code = generate_python(source)
        # Should generate newline format control via write_newline()
        assert "_rt.write_newline()" in python_code

    def test_multiple_read_targets(self) -> None:
        """R X,Y generates two input calls."""
        source = """\
TEST
 R X,Y
 Q
"""
        python_code = generate_python(source)
        # Should have two input() calls
        assert python_code.count("input()") == 2


@pytest.mark.codegen
class TestReadExecution:
    """Test READ command execution with mocked stdin."""

    def test_basic_read_captures_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """R X W X reads and writes the input value."""
        # Mock stdin
        monkeypatch.setattr(sys, "stdin", io.StringIO("hello\n"))

        source = """\
TEST
 R X
 W X,!
 Q
"""
        from m2py.runtime import MUMPSRuntime

        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)

        assert result.success
        assert result.output == "hello\n"

    def test_read_with_prompt_displays_prompt(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """R 'Name: ',X displays prompt before reading."""
        # Mock stdin
        monkeypatch.setattr(sys, "stdin", io.StringIO("John\n"))

        source = """\
TEST
 R "Name: ",X
 W X,!
 Q
"""
        from m2py.runtime import MUMPSRuntime

        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)

        assert result.success
        # The prompt goes to stdout (not captured by runtime)
        # But the READ value should be in the output
        assert "John" in result.output


@pytest.mark.codegen
class TestReadTimeout:
    """Test READ timeout functionality."""

    def test_timeout_read_generates_correct_code(self) -> None:
        """R X:5 generates correct code pattern with m_read_timeout."""
        source = """\
TEST
 R X:5
 Q
"""
        python_code = generate_python(source)
        # Should use m_read_timeout helper and set _test
        assert "m_read_timeout(5)" in python_code
        assert "_test" in python_code

    def test_timeout_helper_returns_tuple(self) -> None:
        """m_read_timeout returns (value, test_flag) tuple."""
        from m2py.runtime.helpers import m_read_timeout
        import select
        from unittest.mock import patch

        # Mock select to indicate data available
        with patch.object(select, "select", return_value=([True], [], [])):
            # Mock stdin.readline to return test value
            mock_stdin = io.StringIO("test_value\n")
            with patch.object(sys, "stdin", mock_stdin):
                value, test_flag = m_read_timeout(1.0)
                assert value == "test_value"
                assert test_flag == 1

    def test_timeout_helper_returns_empty_on_timeout(self) -> None:
        """m_read_timeout returns empty string and 0 on timeout."""
        from m2py.runtime.helpers import m_read_timeout
        import select
        from unittest.mock import patch

        # Mock select to indicate timeout (empty readable list)
        with patch.object(select, "select", return_value=([], [], [])):
            value, test_flag = m_read_timeout(0.1)
            assert value == ""
            assert test_flag == 0


@pytest.mark.codegen
class TestReadCharacter:
    """Test single character READ (R *X)."""

    def test_char_read_generates_m_read_char(self) -> None:
        """R *X generates m_read_char() call."""
        source = """\
TEST
 R *X
 Q
"""
        python_code = generate_python(source)
        assert "m_read_char()" in python_code

    def test_char_read_helper_reads_single_char(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """m_read_char reads exactly one character."""
        from m2py.runtime.helpers import m_read_char

        monkeypatch.setattr(sys, "stdin", io.StringIO("ABC"))
        char = m_read_char()
        assert char == "A"
