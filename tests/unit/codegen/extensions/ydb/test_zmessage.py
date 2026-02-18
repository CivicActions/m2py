"""Tests for ZMESSAGE command code generation (YDB extension).

Reference: YottaDB Z-Commands
024-vista-transpilation-fixes: ZMESSAGE now generates RuntimeError raise.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZmessageCodegen:
    """Codegen-level tests for ZMESSAGE command (YDB).

    ZMESSAGE generates a RuntimeError raise with the error message from
    m_zmessage(), matching the error-signaling semantics of the command.
    """

    def test_zmessage_generates_raise(self):
        """ZMESSAGE generates RuntimeError raise."""
        code = "TEST\n ZMESSAGE 150373210\n Q"
        result = generate_python(code)
        assert "raise RuntimeError(m_zmessage(" in result
        assert "# ZMESSAGE" in result
