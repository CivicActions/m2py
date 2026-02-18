"""Tests for ZSTEP command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 014: Verify LIM-015 errors for unimplemented Z-commands.
Spec 024 Phase 14: ZSTEP changed from error to no-op stub (debugger-only command).
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZstepCodegen:
    """Codegen-level tests for ZSTEP command (YDB).

    ZSTEP is a debugger-only command with no runtime impact.
    Phase 14 changed it from NotImplementedError to a no-op stub.
    """

    def test_zstep_into_transpiles(self):
        """ZSTEP INTO transpiles to a pass (no-op stub)."""
        code = "TEST\n ZSTEP INTO\n Q"
        result = generate_python(code)
        assert "pass  # ZSTEP command no-op (debugger)" in result

    def test_zstep_over_transpiles(self):
        """ZSTEP OVER transpiles to a pass."""
        code = "TEST\n ZSTEP OVER\n Q"
        result = generate_python(code)
        assert "pass  # ZSTEP command no-op (debugger)" in result

    def test_zstep_outof_transpiles(self):
        """ZSTEP OUTOF transpiles to a pass."""
        code = "TEST\n ZSTEP OUTOF\n Q"
        result = generate_python(code)
        assert "pass  # ZSTEP command no-op (debugger)" in result

    def test_zstep_with_action_transpiles(self):
        """ZSTEP INTO:action transpiles to a pass."""
        code = 'TEST\n ZSTEP INTO:"W X"\n Q'
        result = generate_python(code)
        assert "pass  # ZSTEP command no-op (debugger)" in result

    def test_zstep_argumentless_transpiles(self):
        """Argumentless ZSTEP transpiles to a pass."""
        code = "TEST\n ZSTEP\n Q"
        result = generate_python(code)
        assert "pass  # ZSTEP command no-op (debugger)" in result
