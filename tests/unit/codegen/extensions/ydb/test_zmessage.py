"""Tests for ZMESSAGE command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 014: Verify LIM-015 errors for unimplemented Z-commands.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZmessageCodegen:
    """Codegen-level tests for ZMESSAGE command (YDB).

    ZMESSAGE is not supported in m2py.
    This test verifies that NotImplementedError is raised with LIM-015.
    """

    def test_zmessage_raises_not_implemented(self):
        """ZMESSAGE raises NotImplementedError with LIM-015."""
        code = "TEST\n ZMESSAGE 150373210\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)
