"""Tests for MUMPSRuntime basic functionality.

Reference: Runtime API Contract (contracts/runtime-api.md)
"""

import pytest


@pytest.mark.runtime
class TestMUMPSRuntimeBasic:
    """Basic MUMPSRuntime functionality tests.

    Phase 10 validation: Verify core runtime API works correctly.
    """

    def test_write_and_get_output(self):
        """Runtime write() captures output and get_output() retrieves it."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.write("Hello")
        rt.write(" ")
        rt.write("World")
        assert rt.get_output() == "Hello World"

    def test_clear_output(self):
        """Runtime clear() resets output buffer."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.write("test")
        assert rt.get_output() == "test"
        rt.clear()
        assert rt.get_output() == ""

    def test_execute_simple_code(self):
        """Runtime execute() runs generated Python code."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        code = """
def TEST():
    global _test
    _rt.write("PASS")

_test = False
"""
        result = rt.execute(code)
        assert result.success is True
        assert result.output == "PASS"
        assert result.error is None

    def test_execute_captures_test_value(self):
        """Runtime execute() captures final $TEST value."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        code = """
def TEST():
    global _test
    _test = True

_test = False
"""
        result = rt.execute(code)
        assert result.success is True
        assert result.test_value is True

    def test_execute_handles_exceptions(self):
        """Runtime execute() captures exceptions and returns failure."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        code = """
def TEST():
    global _test
    raise ValueError("intentional error")

_test = False
"""
        result = rt.execute(code)
        assert result.success is False
        assert "intentional error" in result.error

    def test_execute_with_explicit_entry_point(self):
        """Runtime execute() can call specific entry point."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        code = """
def TEST():
    global _test
    _rt.write("FIRST")

def OTHER():
    global _test
    _rt.write("OTHER")

_test = False
"""
        result = rt.execute(code, entry_point="OTHER")
        assert result.success is True
        assert result.output == "OTHER"

    def test_execute_no_capture_output(self):
        """Runtime execute() with capture_output=False returns empty output."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        code = """
def TEST():
    global _test
    _rt.write("test")

_test = False
"""
        result = rt.execute(code, capture_output=False)
        assert result.success is True
        assert result.output == ""


@pytest.mark.runtime
class TestExecutionResult:
    """ExecutionResult dataclass tests."""

    def test_execution_result_fields(self):
        """ExecutionResult has correct fields."""
        from m2py.runtime import ExecutionResult

        result = ExecutionResult(
            output="hello",
            success=True,
            error=None,
            test_value=False,
        )
        assert result.output == "hello"
        assert result.success is True
        assert result.error is None
        assert result.test_value is False
