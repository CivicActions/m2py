"""Tests for ZPRINT command code generation (YDB extension).

Reference: YottaDB Z-Commands
024-vista-transpilation-fixes: ZPRINT now generates a no-op stub.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZprintCodegen:
    """Codegen-level tests for ZPRINT command (YDB).

    ZPRINT generates a no-op pass statement in transpiled code
    since the original MUMPS source is not available at runtime.
    """

    def test_zprint_generates_noop(self):
        """ZPRINT generates pass (no-op stub)."""
        code = "TEST\n ZPRINT TEST\n Q"
        result = generate_python(code)
        assert "pass  # ZPRINT" in result
