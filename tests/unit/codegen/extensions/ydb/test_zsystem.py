"""Tests for ZSYSTEM command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 021 Phase 11 (T072): Verify ZSYSTEM codegen emits _rt.zsystem() calls.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZsystemCodegen:
    """Codegen-level tests for ZSYSTEM command (YDB).

    Spec 021 Phase 11 (T072, T075): ZSYSTEM emits _rt.zsystem() call.
    """

    def test_zsystem_basic(self):
        """ZSYSTEM with string arg generates _rt.zsystem() call."""
        code = 'TEST\n ZSYSTEM "ls -la"\n Q'
        result = generate_python(code)
        assert '_rt.zsystem(m_str("ls -la"))' in result

    def test_zsystem_abbreviated(self):
        """ZSY generates _rt.zsystem() call."""
        code = 'TEST\n ZSY "echo hello"\n Q'
        result = generate_python(code)
        assert '_rt.zsystem(m_str("echo hello"))' in result

    def test_zsystem_no_args(self):
        """ZSYSTEM with no args generates _rt.zsystem() call."""
        code = "TEST\n ZSYSTEM\n Q"
        result = generate_python(code)
        assert "_rt.zsystem()" in result

    def test_zsystem_variable_arg(self):
        """ZSYSTEM with variable generates _rt.zsystem() call."""
        code = 'TEST\n S CMD="ls"\n ZSY CMD\n Q'
        result = generate_python(code)
        assert "_rt.zsystem(" in result

    def test_zsystem_exit_code_read(self):
        """$ZSYSTEM generates m_str(_rt.zsystem_exit()) call."""
        code = "TEST\n W $ZSYSTEM,!\n Q"
        result = generate_python(code)
        assert "_rt.zsystem_exit()" in result
