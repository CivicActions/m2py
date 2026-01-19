"""Tests for Z-function code generation (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
Spec 014: Verify LIM-015 errors for unimplemented Z-functions.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZfunctionsCodegen:
    """Codegen-level tests for Z-functions (YDB implementation-defined).

    All Z-functions are implementation-defined per FR-017.
    These tests verify that NotImplementedError is raised with LIM-015.
    """

    def test_zdate_raises_not_implemented(self):
        """$ZDATE raises NotImplementedError with LIM-015."""
        code = "TEST\n S X=$ZDATE(12345)\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)

    def test_zmessage_function_raises_not_implemented(self):
        """$ZMESSAGE raises NotImplementedError with LIM-015."""
        code = "TEST\n S X=$ZMESSAGE(150373210)\n Q"
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)

    def test_zwidth_raises_not_implemented(self):
        """$ZWIDTH raises NotImplementedError with LIM-015."""
        code = 'TEST\n S X=$ZWIDTH("ABC")\n Q'
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)
