"""Tests for ZALLOCATE/ZDEALLOCATE command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 014: Verify LIM-015 errors for unimplemented Z-commands.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZallocateCodegen:
    """Codegen-level tests for ZALLOCATE/ZDEALLOCATE command (YDB).

    ZALLOCATE and ZDEALLOCATE are not supported in m2py.
    These tests verify that NotImplementedError is raised with LIM-015.
    """

    def test_zallocate_raises_not_implemented(self):
        """ZALLOCATE raises NotImplementedError with LIM-015."""
        code = "TEST\n ZALLOCATE ^X\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)

    def test_zdeallocate_raises_not_implemented(self):
        """ZDEALLOCATE raises NotImplementedError with LIM-015."""
        code = "TEST\n ZDEALLOCATE ^X\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)
