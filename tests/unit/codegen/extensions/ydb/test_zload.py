"""Tests for ZLOAD command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 024: ZLOAD now generates _rt.zlink() calls (same as ZLINK).

ZLOAD (ZL) loads a routine into the routine buffer. In transpiler context,
it is treated identically to ZLINK since Python has no routine buffer concept.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZloadCodegen:
    """Codegen-level tests for ZLOAD command (YDB extension).

    ZLOAD is treated as equivalent to ZLINK in the transpiler —
    both generate _rt.zlink() calls.
    """

    def test_zload_generates_zlink_call(self):
        """ZLOAD generates _rt.zlink() call."""
        code = 'TEST\n ZL "routine"\n Q'
        python_code = generate_python(code)
        assert '_rt.zlink("routine")' in python_code

    def test_zload_full_command_generates_zlink_call(self):
        """ZLOAD (full keyword) generates _rt.zlink() call."""
        code = 'TEST\n ZLOAD "routine"\n Q'
        python_code = generate_python(code)
        assert '_rt.zlink("routine")' in python_code

    def test_zload_with_postcondition(self):
        """ZLOAD with postcondition generates conditional _rt.zlink()."""
        code = 'TEST\n ZL:1 "routine"\n Q'
        python_code = generate_python(code)
        assert '_rt.zlink("routine")' in python_code

    def test_zload_no_args(self):
        """ZLOAD with no arguments generates pass comment."""
        code = "TEST\n ZL\n Q"
        python_code = generate_python(code)
        assert "pass  # ZLOAD (no args)" in python_code


# ZLOAD Execution (024-vista-transpilation-fixes, Contract 11)


@pytest.mark.codegen
@pytest.mark.ydb
class TestZloadExecution:
    """Execution tests for ZLOAD — ZLOAD is a no-op stub, code after it runs."""

    def test_zload_is_noop_stub(self, execute_mumps):
        """Contract 11: ZL followed by WRITE produces output (ZLOAD is no-op stub)."""
        code = 'ZLOAD1\n ZL "SOMEFILE"\n W "ok",!\n Q'
        result = execute_mumps(code)
        assert result.output == "ok\n"

    def test_zload_no_args_execution(self, execute_mumps):
        """ZLOAD with no args is a no-op, subsequent code runs."""
        code = 'TEST\n ZL\n W "after",!\n Q'
        result = execute_mumps(code)
        assert result.output == "after\n"
