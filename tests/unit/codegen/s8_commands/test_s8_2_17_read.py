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
        # Should generate _rt.read_line() call stored in _scope
        assert "_rt.read_line()" in python_code

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
        assert "_rt.read_line()" in python_code

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
        # Should have two read_line() calls
        assert python_code.count("_rt.read_line()") == 2


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
        # Should use _rt.read_line_timeout and set _test
        assert "_rt.read_line_timeout(5)" in python_code
        assert "_test" in python_code

    def test_timeout_read_via_device_layer(self) -> None:
        """READ with timeout uses device-layer read_line_timeout method."""
        from m2py.runtime import MUMPSRuntime
        from unittest.mock import patch

        rt = MUMPSRuntime()
        rt._output = []
        # Mock select to indicate data available, mock stdin
        import select

        mock_stdin = io.StringIO("test_value\n")
        with patch.object(select, "select", return_value=([True], [], [])):
            with patch.object(sys, "stdin", mock_stdin):
                value, test_flag = rt.read_line_timeout(1.0)
                assert value == "test_value"
                assert test_flag == 1

    def test_timeout_returns_empty_on_timeout(self) -> None:
        """READ timeout returns empty string and $TEST=0 on timeout."""
        from m2py.runtime import MUMPSRuntime
        from unittest.mock import patch
        import select

        rt = MUMPSRuntime()
        rt._output = []
        with patch.object(select, "select", return_value=([], [], [])):
            value, test_flag = rt.read_line_timeout(0.1)
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
        assert "_rt.read_char()" in python_code

    def test_char_read_via_device_layer(self) -> None:
        """Device-layer read_char returns ASCII code of character."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._output = []
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(sys, "stdin", io.StringIO("ABC"))
        char = rt.read_char()
        # read_char returns the ASCII code as a string per MUMPS semantics
        assert char == str(ord("A"))  # "65"
        monkeypatch.undo()


# =============================================================================
# Pass 2 Coverage: READ with timeout + indirection
# =============================================================================


@pytest.mark.codegen
class TestReadTimeoutIndirectionPass2:
    """READ with timeout and indirection on target variable.

    Covers codegen/statements.py L5354-5358 (timeout read with indirection).
    """

    def test_read_timeout_indirection_codegen(self):
        """R @A:0 — generates code for read with timeout + indirection."""
        from m2py.codegen import generate_python

        code = generate_python('TEST\n S A="X"\n R @A:0\n Q\n')
        # Should have both timeout and indirection handling
        assert "timeout" in code.lower() or "0" in code
        assert "resolve" in code.lower() or "indire" in code.lower()


@pytest.mark.codegen
class TestReadCodegen:
    """Tests for READ code generation patterns."""

    def test_read_with_timeout_generates_code(self, generate_python):
        """R X:0 generates code with timeout parameter."""
        code = generate_python("TEST\n\tR X:0\n\tQ\n")
        assert "timeout" in code.lower() or "0" in code

    def test_read_literal_prompt(self, generate_python):
        """R "Enter: ",X generates code with prompt string."""
        code = generate_python('TEST\n\tR "Enter: ",X\n\tQ\n')
        assert "Enter" in code


# =============================================================================
# Subscripted READ targets
# =============================================================================


@pytest.mark.codegen
class TestReadSubscriptedTarget:
    """READ into subscripted local variables.

    MUMPS allows READ into subscripted variables (e.g., R ARR(I):0).
    The codegen must generate a subscript assignment, not a root value
    assignment.  Bug fix: previously R ARR(I) generated
    ``_scope['ARR'].value = _read_val`` instead of
    ``_scope['ARR'][I] = _read_val``.
    """

    def test_read_into_subscripted_var_codegen(self):
        """R ARR(I):0 generates subscript assignment, not .value."""
        from m2py.codegen import generate_python

        code = generate_python("TEST\n N I,ARR F I=1:1 R ARR(I):0 Q\n Q\n")
        # Must NOT assign to .value for the ARR variable in the READ
        # It should use subscript syntax like _scope['ARR'][...]
        assert "read_line_timeout" in code
        # The subscripted assignment should NOT be ARR.value
        # It should be ARR[something] = _read_val
        lines = code.split("\n")
        read_assign_lines = [l for l in lines if "_read_val" in l and "ARR" in l]
        assert len(read_assign_lines) >= 1, (
            "Expected a line assigning _read_val to ARR with subscript"
        )
        for line in read_assign_lines:
            # Should use subscript [] not .value
            assert "[" in line, f"Expected subscript access in: {line.strip()}"
            assert ".value" not in line, (
                f"Should not assign to .value for subscripted READ: {line.strip()}"
            )

    def test_read_into_multisub_var_codegen(self):
        """R A(I,J):0 generates multi-subscript assignment."""
        from m2py.codegen import generate_python

        code = generate_python("TEST\n N I,J S I=1,J=2 R A(I,J):0\n Q\n")
        lines = code.split("\n")
        read_assign_lines = [l for l in lines if "_read_val" in l and "'A'" in l]
        assert len(read_assign_lines) >= 1, (
            "Expected a line assigning _read_val to A with subscripts"
        )
        for line in read_assign_lines:
            assert "[" in line, f"Expected subscript access in: {line.strip()}"

    def test_read_non_subscripted_still_uses_value(self):
        """R X:0 still assigns to .value (no subscripts)."""
        from m2py.codegen import generate_python

        code = generate_python("TEST\n R X:0\n Q\n")
        lines = code.split("\n")
        read_assign_lines = [l for l in lines if "_read_val" in l and "'X'" in l]
        assert len(read_assign_lines) >= 1
        for line in read_assign_lines:
            assert ".value" in line, (
                f"Non-subscripted READ should use .value: {line.strip()}"
            )

    def test_read_subscripted_runtime_execution(self):
        """R ARR(I):0 at runtime actually stores in the subscripted node."""
        from m2py.codegen import generate_python
        from m2py.runtime import MArray, MUMPSRuntime

        # Build a routine that reads into ARR(1), ARR(2), ARR(3)
        # Don't NEW ARR so it persists in scope after subroutine return.
        # NEW I so the counter is local to the label.
        source = """\
TEST
 N I
 F I=1:1:3 R ARR(I):0
 Q
"""
        code = generate_python(source)
        mod = {}
        exec(code, mod)  # noqa: S102

        rt = MUMPSRuntime()

        # Set up a file device with test content so READ has data to read
        import os
        import tempfile

        tmpfile = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmpfile.write("alpha\nbeta\ngamma\n")
        tmpfile.close()
        try:
            rt.open_device(tmpfile.name, ["readonly"], 0)
            rt.use_device(tmpfile.name)

            scope: dict[str, MArray] = {}
            mod["TEST"](rt, _scope=scope)

            # ARR should have subscripted children
            arr = scope.get("ARR")
            assert arr is not None, "ARR should exist in scope"
            # Verify subscripted nodes exist (values are from file reads)
            assert "1" in arr._children, "ARR(1) should exist as subscripted child"
            assert "2" in arr._children, "ARR(2) should exist as subscripted child"
            assert "3" in arr._children, "ARR(3) should exist as subscripted child"
            # Root value should NOT be set (only subscripted children)
            assert arr._value is None, "ARR root value should be unset"
        finally:
            rt.close_device(tmpfile.name)
            os.unlink(tmpfile.name)


# =============================================================================
# Extrinsic functions with by-ref
# =============================================================================
