"""Tests for ZCONTINUE command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 014: Verify LIM-015 errors for unimplemented Z-commands.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZcontinueCodegen:
    """Codegen-level tests for ZCONTINUE command (YDB).

    ZCONTINUE is not supported in m2py.
    This test verifies that NotImplementedError is raised with LIM-015.
    """

    def test_zcontinue_raises_not_implemented(self):
        """ZCONTINUE raises NotImplementedError with LIM-015."""
        code = "TEST\n ZCONTINUE\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)
